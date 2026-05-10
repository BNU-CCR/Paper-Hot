import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.config import Config


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class ConfigTests(unittest.TestCase):
    def test_config_reads_discovery_and_filter_settings(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir()

            write_file(
                config_dir / "journals.yaml",
                """
journals:
  - name: "Journal A"
    keywords:
      - "llm communication"
      - "platform politics"
global_keywords:
  - "llm communication"
  - "misinformation"
""".strip(),
            )
            write_file(
                config_dir / "prompts.yaml",
                """
filter_system_prompt: "system prompt from yaml"
filter_user_template: "title={title}"
""".strip(),
            )
            write_file(
                config_dir / "settings.yaml",
                """
anthropic_api_key: ""
semantic_scholar_api_key: "semantic-test-key"
claude_model: "claude-test-model"
""".strip(),
            )

            config = Config(config_dir)

            self.assertEqual(config.semantic_scholar_api_key, "semantic-test-key")
            self.assertEqual(config.claude_model, "claude-test-model")
            self.assertEqual(config.filter_system_prompt, "system prompt from yaml")
            self.assertEqual(config.filter_user_template, "title={title}")
            self.assertEqual(
                config.get_discovery_keywords(),
                ["llm communication", "platform politics", "misinformation"],
            )


if __name__ == "__main__":
    unittest.main()
