import unittest
from unittest.mock import Mock

from src.discovery import OpenAlexDiscovery


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


if __name__ == "__main__":
    unittest.main()
