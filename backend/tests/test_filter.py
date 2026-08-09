import unittest
from unittest.mock import Mock, patch

from journal_tracker.filter import PaperFilter


class FakeConfig:
    anthropic_api_key = "deepseek-test-key"
    anthropic_base_url = "https://api.deepseek.com/anthropic"
    claude_model = "deepseek-v4-flash"
    filter_system_prompt = ""
    filter_user_template = ""
    method_labels = []
    method_system_prompt = ""
    method_user_template = ""


class PaperFilterTests(unittest.TestCase):
    def test_filter_initializes_anthropic_client_with_deepseek_base_url(self) -> None:
        with patch("journal_tracker.filter.get_config", return_value=FakeConfig()):
            with patch("journal_tracker.filter.anthropic.Anthropic", return_value=Mock()) as mock_client:
                paper_filter = PaperFilter()

        self.assertEqual(paper_filter.model, "deepseek-v4-flash")
        mock_client.assert_called_once_with(
            api_key="deepseek-test-key",
            base_url="https://api.deepseek.com/anthropic",
        )

    def _filter_paper_with_text(self, text: str) -> dict:
        thinking_block = Mock()
        del thinking_block.text
        text_block = Mock()
        text_block.text = text

        client = Mock()
        client.messages.create.return_value = Mock(content=[thinking_block, text_block])

        with patch("journal_tracker.filter.get_config", return_value=FakeConfig()):
            with patch("journal_tracker.filter.anthropic.Anthropic", return_value=client):
                paper_filter = PaperFilter()

        return paper_filter.filter_paper(
            title="Computational communication paper",
            abstract="This paper analyzes social media with computational methods.",
        )

    def test_filter_extracts_json_from_text_block_after_thinking_block(self) -> None:
        result = self._filter_paper_with_text("""
{
  "relevance": "High",
  "reason": "使用计算方法研究传播问题",
  "tags": ["计算传播", "社交媒体"],
  "summary": "论文使用计算方法分析社交媒体传播现象。"
}
""".strip())

        self.assertEqual(result["relevance"], "High")
        self.assertEqual(result["tags"], ["计算传播", "社交媒体"])
        self.assertEqual(result["method"], "")

    def test_filter_validates_method_against_configured_taxonomy(self) -> None:
        config = FakeConfig()
        config.method_labels = ["质性分析", "量化分析", "理论分析", "综述", "计算传播学"]
        text_block = Mock()
        text_block.text = """
{
  "relevance": "High",
  "reason": "计算传播研究",
  "tags": ["AI"],
  "summary": "摘要",
  "method": "计算传播学"
}
""".strip()
        client = Mock()
        client.messages.create.return_value = Mock(content=[text_block])
        with patch("journal_tracker.filter.get_config", return_value=config):
            with patch("journal_tracker.filter.anthropic.Anthropic", return_value=client):
                paper_filter = PaperFilter()
        result = paper_filter.filter_paper(title="T", abstract="A")
        self.assertEqual(result["method"], "计算传播学")

    def test_filter_coerces_invalid_or_missing_method_to_empty(self) -> None:
        config = FakeConfig()
        config.method_labels = ["质性分析", "量化分析", "理论分析", "综述", "计算传播学"]
        text_block = Mock()
        text_block.text = """
{
  "relevance": "High",
  "reason": "计算传播研究",
  "tags": ["AI"],
  "summary": "摘要",
  "method": "自创的标签"
}
""".strip()
        client = Mock()
        client.messages.create.return_value = Mock(content=[text_block])
        with patch("journal_tracker.filter.get_config", return_value=config):
            with patch("journal_tracker.filter.anthropic.Anthropic", return_value=client):
                paper_filter = PaperFilter()
        result = paper_filter.filter_paper(title="T", abstract="A")
        self.assertEqual(result["method"], "")

    def _label_method_with_text(self, text: str, method_labels=None) -> str:
        config = FakeConfig()
        if method_labels:
            config.method_labels = method_labels
        text_block = Mock()
        text_block.text = text
        client = Mock()
        client.messages.create.return_value = Mock(content=[text_block])
        with patch("journal_tracker.filter.get_config", return_value=config):
            with patch("journal_tracker.filter.anthropic.Anthropic", return_value=client):
                paper_filter = PaperFilter()
        return paper_filter.label_method(title="T", abstract="A")

    def test_label_method_returns_valid_label(self) -> None:
        method = self._label_method_with_text(
            '{"method": "综述"}',
            method_labels=["质性分析", "量化分析", "理论分析", "综述", "计算传播学"],
        )
        self.assertEqual(method, "综述")

    def test_label_method_returns_empty_for_invalid_or_uncertain(self) -> None:
        config = FakeConfig()
        config.method_labels = ["质性分析", "量化分析", "理论分析", "综述", "计算传播学"]
        for text in ['{"method": "不存在"}', '{"method": ""}']:
            text_block = Mock()
            text_block.text = text
            client = Mock()
            client.messages.create.return_value = Mock(content=[text_block])
            with patch("journal_tracker.filter.get_config", return_value=config):
                with patch("journal_tracker.filter.anthropic.Anthropic", return_value=client):
                    paper_filter = PaperFilter()
            self.assertEqual(paper_filter.label_method(title="T", abstract="A"), "")

    def test_extract_response_text_skips_thinking_block_with_text(self) -> None:
        """DeepSeek may put text on a thinking block; the JSON text block wins."""
        thinking = Mock(type="thinking", text="让我先思考一下这个主题...")
        text_block = Mock(type="text", text='{"method": "计算传播学"}')
        client = Mock()
        client.messages.create.return_value = Mock(content=[thinking, text_block])
        config = FakeConfig()
        config.method_labels = ["质性分析", "量化分析", "理论分析", "综述", "计算传播学"]
        with patch("journal_tracker.filter.get_config", return_value=config):
            with patch("journal_tracker.filter.anthropic.Anthropic", return_value=client):
                paper_filter = PaperFilter()
        method = paper_filter.label_method(title="T", abstract="A")
        self.assertEqual(method, "计算传播学")

    def test_call_messages_retries_when_response_has_no_text(self) -> None:
        """Transient no-text responses (thinking-only) are retried with backoff."""
        client = Mock()
        no_text = Mock(content=[Mock(type="thinking", text=None)])
        ok_text = Mock(content=[Mock(type="text", text='{"method": "综述"}')])
        client.messages.create.side_effect = [no_text, no_text, ok_text]
        config = FakeConfig()
        config.method_labels = ["质性分析", "量化分析", "理论分析", "综述", "计算传播学"]
        with patch("journal_tracker.filter.get_config", return_value=config):
            with patch("journal_tracker.filter.anthropic.Anthropic", return_value=client):
                paper_filter = PaperFilter()
        method = paper_filter.label_method(title="T", abstract="A")
        self.assertEqual(method, "综述")
        self.assertEqual(client.messages.create.call_count, 3)


if __name__ == "__main__":
    unittest.main()
