import unittest
from unittest.mock import Mock

from journal_tracker.discovery import OpenAlexDiscovery, DiscoveredPaper


def _make_work(index: int) -> dict:
    """Build a minimal OpenAlex work dict with a unique DOI."""
    return {
        "id": f"https://openalex.org/W{index}",
        "title": f"Paper {index}",
        "doi": f"https://doi.org/10.1000/{index}",
        "publication_date": f"2025-0{index % 9 + 1}-01",
        "primary_location": {"source": {"display_name": "Journal A"}},
        "authorships": [],
        "abstract_inverted_index": None,
    }


class OpenAlexDiscoveryTests(unittest.TestCase):
    def test_search_journal_updates_filters_by_source_id_and_maps_papers(self) -> None:
        discovery = OpenAlexDiscovery()
        requested = []

        def fake_get_json(path, params):
            requested.append((path, params))
            return {
                "results": [
                    {
                        "title": "OpenAlex paper",
                        "doi": "https://doi.org/10.1000/openalex",
                        "publication_date": "2026-03-14",
                        "cited_by_count": 7,
                        "biblio": {"volume": "12", "issue": "3"},
                        "id": "https://openalex.org/W1",
                        "primary_location": {
                            "landing_page_url": "https://example.org/openalex",
                            "source": {"display_name": "Communication Research"},
                        },
                        "authorships": [
                            {"author": {"display_name": "Alice"}},
                            {"author": {"display_name": "Bob"}},
                        ],
                        "abstract_inverted_index": {
                            "This": [0],
                            "is": [1],
                            "an": [2],
                            "abstract": [3],
                        },
                    }
                ]
            }

        discovery._get_json = Mock(side_effect=fake_get_json)

        papers = discovery.search_journal_updates(
            journals=[
                {
                    "name": "Communication Research",
                    "openalex_source_id": "S28604305",
                    "track_from_year": 2026,
                }
            ],
            limit_per_journal=5,
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "OpenAlex paper")
        self.assertEqual(papers[0].abstract, "This is an abstract")
        self.assertEqual(papers[0].authors, "Alice, Bob")
        self.assertEqual(papers[0].journal, "Communication Research")
        self.assertEqual(papers[0].published_date, "2026-03-14")
        self.assertEqual(papers[0].doi, "10.1000/openalex")
        self.assertEqual(papers[0].link, "https://example.org/openalex")
        self.assertEqual(papers[0].citation_count, 7)
        self.assertEqual(papers[0].volume, "12")
        self.assertEqual(papers[0].issue, "3")
        self.assertIn("biblio", requested[0][1]["select"])
        self.assertEqual(requested[0][0], "/works")
        self.assertIn("primary_location.source.id:S28604305", requested[0][1]["filter"])
        self.assertIn("from_publication_date:2026-01-01", requested[0][1]["filter"])
        self.assertEqual(discovery.last_run_report["successful_queries"], 1)

    def test_search_journal_updates_falls_back_to_issn_l_when_source_id_missing(self) -> None:
        discovery = OpenAlexDiscovery()
        discovery._get_json = Mock(return_value={"results": []})

        discovery.search_journal_updates(
            journals=[
                {
                    "name": "Journal A",
                    "issn_l": "1234-5678",
                    "track_from_year": 2026,
                }
            ],
            limit_per_journal=3,
        )

        params = discovery._get_json.call_args.args[1]
        self.assertIn("primary_location.source.issn:1234-5678", params["filter"])
        self.assertEqual(params["per-page"], 3)

    def test_works_filters_builds_optional_date_window(self) -> None:
        filters = OpenAlexDiscovery._works_filters("primary_location.source.id:S1", 2025, 2026)
        self.assertIn("primary_location.source.id:S1", filters)
        self.assertIn("from_publication_date:2025-01-01", filters)
        self.assertIn("to_publication_date:2026-12-31", filters)
        self.assertIn("type:article", filters)

        no_to = OpenAlexDiscovery._works_filters("primary_location.source.id:S1", 2026)
        self.assertIn("from_publication_date:2026-01-01", no_to)
        self.assertFalse(any("to_publication_date" in f for f in no_to))

    def test_search_all_paginates_and_uses_year_window(self) -> None:
        discovery = OpenAlexDiscovery()
        calls = []

        def fake_get_json(path, params):
            calls.append(params)
            page = params.get("page", 1)
            if page == 1:
                results = [_make_work(i) for i in range(100)]
            elif page == 2:
                results = [_make_work(i) for i in range(100, 150)]
            else:
                results = []
            return {"meta": {"count": 150}, "results": results}

        discovery._get_json = Mock(side_effect=fake_get_json)

        papers = discovery.search_all_by_journal_config(
            {"name": "Journal A", "openalex_source_id": "S1", "track_from_year": 2026},
            from_year=2025,
            to_year=2026,
            max_per_journal=1000,
        )

        self.assertEqual(len(papers), 150)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["page"], 1)
        self.assertEqual(calls[1]["page"], 2)
        filters = calls[0]["filter"]
        self.assertIn("primary_location.source.id:S1", filters)
        self.assertIn("from_publication_date:2025-01-01", filters)
        self.assertIn("to_publication_date:2026-12-31", filters)

    def test_search_all_respects_max_per_journal_cap(self) -> None:
        discovery = OpenAlexDiscovery()
        discovery._get_json = Mock(
            return_value={"meta": {"count": 500}, "results": [_make_work(i) for i in range(100)]}
        )
        papers = discovery.search_all_by_journal_config(
            {"name": "Journal A", "openalex_source_id": "S1"},
            from_year=2025,
            to_year=2026,
            max_per_journal=50,
        )
        self.assertEqual(len(papers), 50)
        # The cap was hit on the first page, so no second page request.
        discovery._get_json.assert_called_once()

    def test_backfill_journal_updates_dedupes_and_reports(self) -> None:
        discovery = OpenAlexDiscovery()

        def make_paper(doi: str) -> DiscoveredPaper:
            return DiscoveredPaper(title=f"Paper {doi}", abstract="", authors="", journal="",
                                   published_date="2025-01-01", link=f"https://doi.org/{doi}",
                                   doi=doi)

        discovery.search_all_by_journal_config = Mock(side_effect=[
            [make_paper("10.1000/dup"), make_paper("10.1000/a")],
            [make_paper("10.1000/dup"), make_paper("10.1000/b")],
        ])

        papers = discovery.backfill_journal_updates(
            journals=[
                {"name": "Journal A", "openalex_source_id": "S1"},
                {"name": "Journal B", "openalex_source_id": "S2"},
            ],
            from_year=2025,
            to_year=2026,
        )

        self.assertEqual(len(papers), 3)  # duplicate DOI "10.1000/dup" removed
        report = discovery.last_run_report
        self.assertEqual(report["requested_queries"], 2)
        self.assertEqual(report["successful_queries"], 2)
        self.assertEqual(report["raw_papers"], 4)
        self.assertEqual(report["duplicate_papers"], 1)
        self.assertEqual(report["returned_papers"], 3)


if __name__ == "__main__":
    unittest.main()
