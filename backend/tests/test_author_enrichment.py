import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from journal_tracker.author_enrichment import (
    enrich_paper_authors,
    match_paper_authors,
    normalize_person_name,
)
from journal_tracker.storage import Paper, PaperStorage


class StaticCrossrefClient:
    def fetch_authors(self, doi):
        return [
            {"order": 0, "name": "Alice M. Smith", "orcid": "0000-0001", "affiliations": ["University A"]},
            {"order": 1, "name": "Wei Zhang", "orcid": "", "affiliations": []},
        ]


class StaticSemanticClient:
    def fetch_paper_authors(self, doi):
        return [
            {"order": 0, "author_id": "S1", "name": "Alice M Smith", "orcid": "0000-0001", "aliases": [], "affiliations": ["University A"]},
            {"order": 1, "author_id": "S2", "name": "Wei Zhang", "orcid": "", "aliases": ["Zhang Wei"], "affiliations": ["Institute B"]},
        ]


class FailingCrossrefClient:
    def fetch_authors(self, doi):
        raise RuntimeError("not deposited")


class AuthorEnrichmentTests(unittest.TestCase):
    def test_name_normalization_handles_punctuation_and_diacritics(self):
        self.assertEqual(normalize_person_name("José M. Pérez"), "josemperez")

    def test_semantic_author_batch_requests_supported_fields_only(self):
        from journal_tracker.author_enrichment import SemanticScholarAuthorClient

        class Response:
            def __init__(self, payload):
                self.payload = payload

            status_code = 200
            headers = {}

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class Session:
            def __init__(self):
                self.headers = {}
                self.calls = []

            def request(self, method, url, **kwargs):
                self.calls.append((method, url, kwargs))
                if len(self.calls) == 1:
                    return Response({"authors": [{"authorId": "S1", "name": "Alice"}]})
                return Response([{"authorId": "S1", "name": "Alice", "affiliations": []}])

        session = Session()
        client = SemanticScholarAuthorClient(session=session)
        client.fetch_paper_authors("10.1/test")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[1][2]["params"]["fields"], "name,aliases,affiliations")

    def test_match_uses_orcid_then_paper_scoped_name(self):
        authors, ambiguous = match_paper_authors(
            StaticCrossrefClient().fetch_authors("10.1/test"),
            StaticSemanticClient().fetch_paper_authors("10.1/test"),
        )
        self.assertEqual(ambiguous, 0)
        self.assertEqual(authors[0]["match_method"], "orcid")
        self.assertEqual(authors[0]["semantic_scholar_author_id"], "S1")
        self.assertEqual(authors[1]["match_method"], "exact_name")
        self.assertEqual(authors[1]["affiliations"], ["Institute B"])

    def test_pipeline_persists_rows_and_skips_completed_paper(self):
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            paper_id = storage.add_paper(Paper(
                title="Paper",
                authors="Alice M. Smith, Wei Zhang",
                doi="10.1/test",
                link="https://example.org/paper",
                source_type="openalex",
                screening_status="screened",
            ))

            report = enrich_paper_authors(
                storage, StaticCrossrefClient(), StaticSemanticClient(), limit=10
            )

            self.assertEqual(report["enriched_papers"], 1)
            self.assertEqual(report["matched_s2_authors"], 2)
            self.assertEqual(report["authors_with_affiliations"], 2)
            with storage._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM paper_author_enrichment WHERE paper_id = ? ORDER BY author_order",
                    (paper_id,),
                ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["orcid"], "0000-0001")
            self.assertEqual(json.loads(rows[1]["affiliations_json"]), ["Institute B"])
            self.assertEqual(storage.get_papers_missing_author_enrichment(10), [])

    def test_pipeline_keeps_semantic_scholar_only_results(self):
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            storage.add_paper(Paper(
                title="Paper",
                doi="10.1/s2-only",
                link="https://example.org/s2-only",
                source_type="openalex",
                screening_status="screened",
            ))
            report = enrich_paper_authors(
                storage, FailingCrossrefClient(), StaticSemanticClient(), limit=10
            )
            self.assertEqual(report["enriched_papers"], 1)
            self.assertEqual(report["crossref_unavailable"], 1)
            self.assertEqual(report["authors"], 2)


if __name__ == "__main__":
    unittest.main()
