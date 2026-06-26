import unittest
from unittest.mock import Mock, patch

from src.filter import PaperFilter


class FakeConfig:
    anthropic_api_key = "deepseek-test-key"
    anthropic_base_url = "https://api.deepseek.com/anthropic"
    claude_model = "deepseek-v4-flash"
    filter_system_prompt = ""
    filter_user_template = ""


class PaperFilterTests(unittest.TestCase):
    def test_filter_initializes_anthropic_client_with_deepseek_base_url(self) -> None:
        with patch("src.filter.get_config", return_value=FakeConfig()):
            with patch("src.filter.anthropic.Anthropic", return_value=Mock()) as mock_client:
                paper_filter = PaperFilter()

        self.assertEqual(paper_filter.model, "deepseek-v4-flash")
        mock_client.assert_called_once_with(
            api_key="deepseek-test-key",
            base_url="https://api.deepseek.com/anthropic",
        )


if __name__ == "__main__":
    unittest.main()
