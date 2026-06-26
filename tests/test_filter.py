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

    def test_filter_extracts_json_from_text_block_after_thinking_block(self) -> None:
        thinking_block = Mock()
        del thinking_block.text
        text_block = Mock()
        text_block.text = """
{
  "relevance": "High",
  "reason": "使用计算方法研究传播问题",
  "tags": ["计算传播", "社交媒体"],
  "summary": "论文使用计算方法分析社交媒体传播现象。"
}
""".strip()

        client = Mock()
        client.messages.create.return_value = Mock(content=[thinking_block, text_block])

        with patch("src.filter.get_config", return_value=FakeConfig()):
            with patch("src.filter.anthropic.Anthropic", return_value=client):
                paper_filter = PaperFilter()

        result = paper_filter.filter_paper(
            title="Computational communication paper",
            abstract="This paper analyzes social media with computational methods.",
        )

        self.assertEqual(result["relevance"], "High")
        self.assertEqual(result["tags"], ["计算传播", "社交媒体"])


if __name__ == "__main__":
    unittest.main()
