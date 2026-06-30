import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from src.coverage import CoverageVerifier, CrossrefClient, normalize_doi
from src.storage import Paper, PaperStorage


class CoverageVerifierTests(unittest.TestCase):
    def test_normalize_doi_strips_url_prefix_and_lowercases(self) -> None:
        self.assertEqual(
            normalize_doi("https://doi.org/10.1000/ABC "),
            "10.1000/abc",
        )

    def test_verifier_compares_openalex_and_crossref_dois_by_journal(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            storage.add_paper(
                Paper(
                    title="Shared paper",
                    journal="Communication Research",
                    doi="10.1000/shared",
                    link="https://example.org/shared",
                    source_type="openalex",
                    screening_status="screened",
                )
            )
            storage.add_paper(
                Paper(
                    title="OpenAlex only paper",
                    journal="Communication Research",
                    doi="10.1000/openalex-only",
                    link="https://example.org/openalex-only",
                    source_type="openalex",
                    screening_status="screened",
                )
            )

            crossref_client = Mock()
            crossref_client.fetch_journal_works.return_value = [
                {"title": "Shared paper", "doi": "10.1000/shared"},
                {"title": "Crossref only paper", "doi": "10.1000/crossref-only"},
            ]

            report = CoverageVerifier(storage, crossref_client).verify(
                journals=[
                    {
                        "name": "Communication Research",
                        "issn": ["0093-6502"],
                        "track_from_year": 2026,
                    }
                ]
            )

            journal_report = report["journals"][0]
            self.assertEqual(journal_report["journal"], "Communication Research")
            self.assertEqual(journal_report["openalex_count"], 2)
            self.assertEqual(journal_report["crossref_count"], 2)
            self.assertEqual(journal_report["matched_count"], 1)
            self.assertEqual(journal_report["missing_in_openalex"], ["10.1000/crossref-only"])
            self.assertEqual(journal_report["missing_in_crossref"], ["10.1000/openalex-only"])
            self.assertEqual(report["summary"]["journals_checked"], 1)
            self.assertEqual(report["summary"]["total_missing_in_openalex"], 1)

    def test_crossref_client_maps_items_to_doi_title_records(self) -> None:
        client = CrossrefClient()
        client._get_json = Mock(
            return_value={
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/Test",
                            "title": ["A Crossref Paper"],
                            "container-title": ["Communication Research"],
                            "published-print": {"date-parts": [[2026, 3, 1]]},
                        }
                    ]
                }
            }
        )

        records = client.fetch_journal_works(["0093-6502"], from_year=2026, until_date="2026-06-29")

        self.assertEqual(records[0]["doi"], "10.1000/test")
        self.assertEqual(records[0]["title"], "A Crossref Paper")
        params = client._get_json.call_args.args[1]
        self.assertEqual(
            params["filter"],
            "from-pub-date:2026-01-01,until-pub-date:2026-06-29,type:journal-article",
        )
        self.assertEqual(params["select"], "DOI,title,container-title,published-print,published-online")

    def test_verifier_writes_report_json(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            crossref_client = Mock()
            crossref_client.fetch_journal_works.return_value = []
            output_path = Path(tmp_dir) / "coverage.json"

            report = CoverageVerifier(storage, crossref_client).verify(
                journals=[{"name": "Journal A", "issn": ["1234-5678"]}],
                output_path=output_path,
            )

            saved = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"], report["summary"])


if __name__ == "__main__":
    unittest.main()
