import unittest
from unittest.mock import Mock, patch

import requests

from src.discovery import PaperDiscovery


class FakeResponse:
    def __init__(self, payload=None, status_error=None):
        self._payload = payload or {}
        self._status_error = status_error

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


if __name__ == "__main__":
    unittest.main()
