import io
import unittest
from unittest.mock import Mock, patch

import requests

from src.discovery import DiscoveredPaper, PaperDiscovery


class FakeResponse:
    def __init__(self, payload=None, status_error=None, headers=None):
        self._payload = payload or {}
        self._status_error = status_error
        self.headers = headers or {}

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._payload


class PaperDiscoveryTests(unittest.TestCase):
    def test_search_retries_after_rate_limit(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        rate_limited = FakeResponse(
            status_error=requests.HTTPError("429 Client Error")
        )
        success = FakeResponse(
            payload={
                "data": [
                    {
                        "title": "Recovered paper",
                        "abstract": "Recovered abstract",
                        "authors": [{"name": "Alice"}],
                        "year": 2026,
                        "journal": {"name": "Journal A"},
                        "externalIds": {"DOI": "10.1000/recovered"},
                        "url": "https://example.org/recovered",
                        "citationCount": 12,
                    }
                ]
            }
        )
        discovery.session.get = Mock(side_effect=[rate_limited, success])

        with patch("src.discovery.time.sleep") as mock_sleep:
            papers = discovery.search_papers("computational communication", limit=1)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "Recovered paper")
        self.assertEqual(discovery.session.get.call_count, 2)
        mock_sleep.assert_called_once_with(1.0)

    def test_search_retries_after_temporary_server_error(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        server_error = requests.HTTPError("503 Server Error")
        server_error.response = FakeResponse(headers={})
        success = FakeResponse(payload={"data": [{"title": "Recovered after 503"}]})
        discovery.session.get = Mock(side_effect=[FakeResponse(status_error=server_error), success])

        with patch("src.discovery.time.sleep") as mock_sleep:
            papers = discovery.search_papers("computational communication", limit=1)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "Recovered after 503")
        self.assertEqual(discovery.session.get.call_count, 2)
        mock_sleep.assert_called_once_with(1.0)

    def test_rate_limit_retry_uses_retry_after_header(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        rate_limit_error = requests.HTTPError("429 Client Error")
        rate_limit_error.response = FakeResponse(headers={"Retry-After": "7"})
        success = FakeResponse(payload={"data": [{"title": "Recovered with retry after"}]})
        discovery.session.get = Mock(side_effect=[FakeResponse(status_error=rate_limit_error), success])

        with patch("src.discovery.time.sleep") as mock_sleep:
            papers = discovery.search_papers("computational communication", limit=1)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "Recovered with retry after")
        mock_sleep.assert_called_once_with(7.0)

    def test_search_recent_papers_spreads_limit_without_zero_sized_queries(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        recorded_limits = []

        def fake_search(query, year=None, limit=10):
            recorded_limits.append(limit)
            return []

        discovery.search_papers = fake_search

        discovery.search_recent_papers(
            keywords=["k1", "k2", "k3", "k4", "k5"],
            limit=3,
        )

        self.assertEqual(recorded_limits, [1, 1, 1])

    def test_search_recent_papers_limits_small_batch_query_count(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        recorded_limits = []

        def fake_search(query, year=None, limit=10):
            recorded_limits.append(limit)
            return []

        discovery.search_papers = fake_search

        discovery.search_recent_papers(
            keywords=["k1", "k2", "k3", "k4", "k5", "k6"],
            limit=5,
        )

        self.assertEqual(len(recorded_limits), 3)
        self.assertGreaterEqual(sum(recorded_limits), 5)
        self.assertTrue(all(limit > 0 for limit in recorded_limits))

    def test_search_recent_papers_records_run_report(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")

        def fake_search(query, year=None, limit=10):
            if query == "k2":
                return []
            return [
                DiscoveredPaper(
                    title=f"{query} paper",
                    abstract="",
                    authors="",
                    journal="",
                    published_date="2026",
                    link=f"https://example.org/{query}",
                    doi="",
                )
            ]

        discovery.search_papers = fake_search

        papers = discovery.search_recent_papers(
            keywords=["k1", "k2", "k3"],
            limit=3,
        )

        self.assertEqual(len(papers), 2)
        self.assertEqual(discovery.last_run_report["requested_queries"], 3)
        self.assertEqual(discovery.last_run_report["successful_queries"], 2)
        self.assertEqual(discovery.last_run_report["empty_queries"], 1)
        self.assertEqual(discovery.last_run_report["failed_queries"], 0)
        self.assertEqual(discovery.last_run_report["returned_papers"], 2)

    def test_search_recent_report_counts_request_errors_as_failures(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        discovery._get_json = Mock(side_effect=requests.RequestException("network down"))

        with patch("src.discovery.time.sleep"):
            with patch("sys.stdout", io.StringIO()):
                papers = discovery.search_recent_papers(keywords=["k1"], limit=1)

        self.assertEqual(papers, [])
        self.assertEqual(discovery.last_run_report["failed_queries"], 1)
        self.assertEqual(discovery.last_run_report["empty_queries"], 0)
        self.assertEqual(discovery.last_run_report["errors"], ["k1: network down"])

    def test_search_journal_updates_queries_each_tracked_journal_from_year(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        searched = []

        def fake_search(journal, year=None, limit=10):
            searched.append((journal, year, limit))
            if journal == "Journal A":
                return [
                    DiscoveredPaper(
                        title="Journal A paper",
                        abstract="",
                        authors="",
                        journal="Journal A",
                        published_date="2026",
                        link="https://example.org/a",
                        doi="10.1000/a",
                    )
                ]
            return []

        discovery.search_by_journal = fake_search

        papers = discovery.search_journal_updates(
            journals=[
                {"name": "Journal A", "track_from_year": 2026},
                {"name": "Journal B", "track_from_year": 2026},
            ],
            limit_per_journal=2,
        )

        self.assertEqual([paper.title for paper in papers], ["Journal A paper"])
        self.assertEqual(searched, [("Journal A", 2026, 2), ("Journal B", 2026, 2)])
        self.assertEqual(discovery.last_run_report["requested_queries"], 2)
        self.assertEqual(discovery.last_run_report["successful_queries"], 1)
        self.assertEqual(discovery.last_run_report["empty_queries"], 1)
        self.assertEqual(discovery.last_run_report["returned_papers"], 1)

    def test_search_by_journal_filters_out_non_matching_venues(self) -> None:
        discovery = PaperDiscovery(api_key="test-key")
        discovery.search_papers = Mock(
            return_value=[
                DiscoveredPaper(
                    title="Correct venue paper",
                    abstract="",
                    authors="",
                    journal="Communication Research",
                    published_date="2026",
                    link="https://example.org/correct",
                    doi="10.1000/correct",
                ),
                DiscoveredPaper(
                    title="Wrong venue paper",
                    abstract="",
                    authors="",
                    journal="Communication Research Reports",
                    published_date="2026",
                    link="https://example.org/wrong",
                    doi="10.1000/wrong",
                ),
            ]
        )

        papers = discovery.search_by_journal("Communication Research", year=2026, limit=2)

        self.assertEqual([paper.title for paper in papers], ["Correct venue paper"])


if __name__ == "__main__":
    unittest.main()
