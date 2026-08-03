import unittest
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from journal_tracker import main as main_module
from journal_tracker.config import Config


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class ConfigTests(unittest.TestCase):
    def test_process_environment_overrides_checked_in_ai_defaults(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir()
            write_file(config_dir / "journals.yaml", "journals: []")
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(
                config_dir / "settings.yaml",
                'anthropic_base_url: "https://checked-in.example/anthropic"\n'
                'claude_model: "checked-in-model"',
            )

            with patch.dict(
                "journal_tracker.config.os.environ",
                {
                    "ANTHROPIC_BASE_URL": "https://ci.example/anthropic",
                    "AI_MODEL": "ci-model",
                },
                clear=True,
            ):
                config = Config(config_dir)
                self.assertEqual(config.anthropic_base_url, "https://ci.example/anthropic")
                self.assertEqual(config.claude_model, "ci-model")

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

    def test_config_reads_method_label_settings(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir()

            write_file(config_dir / "journals.yaml", "journals: []")
            write_file(
                config_dir / "prompts.yaml",
                """
method_labels:
  - "纯质性分析"
  - "计算传播学"
method_system_prompt: "method system prompt from yaml"
method_user_template: "title={title}"
""".strip(),
            )
            write_file(config_dir / "settings.yaml", "{}")

            config = Config(config_dir)

            self.assertEqual(config.method_labels, ["纯质性分析", "计算传播学"])
            self.assertEqual(config.method_system_prompt, "method system prompt from yaml")
            self.assertEqual(config.method_user_template, "title={title}")

    def test_config_uses_database_path_relative_to_custom_config_dir(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            config_dir.mkdir()

            write_file(config_dir / "journals.yaml", "journals: []")
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(
                config_dir / "settings.yaml",
                """
database:
  path: "data/papers.db"
""".strip(),
            )

            config = Config(config_dir)

            self.assertEqual(config.database_path, project_dir / "data" / "papers.db")

    def test_config_reads_api_keys_from_local_env_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            config_dir.mkdir()

            write_file(config_dir / "journals.yaml", "journals: []")
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(config_dir / "settings.yaml", "{}")
            write_file(
                project_dir / ".env",
                """
ANTHROPIC_API_KEY=anthropic-from-env-file
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
AI_MODEL=deepseek-v4-flash
SEMANTIC_SCHOLAR_API_KEY=semantic-from-env-file
""".strip(),
            )

            with patch("journal_tracker.config.os.environ", {}):
                config = Config(config_dir)

            self.assertEqual(config.anthropic_api_key, "anthropic-from-env-file")
            self.assertEqual(config.anthropic_base_url, "https://api.deepseek.com/anthropic")
            self.assertEqual(config.claude_model, "deepseek-v4-flash")
            self.assertEqual(config.semantic_scholar_api_key, "semantic-from-env-file")

    def test_config_reads_api_keys_from_key_env_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            config_dir.mkdir()

            write_file(config_dir / "journals.yaml", "journals: []")
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(config_dir / "settings.yaml", "{}")
            write_file(
                project_dir / "key.env",
                """
ANTHROPIC_API_KEY=deepseek-from-key-env
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
AI_MODEL=deepseek-v4-flash
SEMANTIC_SCHOLAR_API_KEY=semantic-from-key-env
""".strip(),
            )

            with patch("journal_tracker.config.os.environ", {}):
                config = Config(config_dir)

            self.assertEqual(config.anthropic_api_key, "deepseek-from-key-env")
            self.assertEqual(config.anthropic_base_url, "https://api.deepseek.com/anthropic")
            self.assertEqual(config.claude_model, "deepseek-v4-flash")
            self.assertEqual(config.semantic_scholar_api_key, "semantic-from-key-env")

    def test_config_returns_tracked_redlist_journals_by_priority(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir()

            write_file(
                config_dir / "journals.yaml",
                """
journals:
  - name: "Core Journal"
    priority: "core"
    track_from_year: 2026
  - name: "Watch Journal"
    priority: "watch"
    track_from_year: 2026
  - name: "Skip Journal"
    priority: "skip"
    track_from_year: 2026
""".strip(),
            )
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(config_dir / "settings.yaml", "{}")

            config = Config(config_dir)

            tracked = config.get_tracked_journals()
            self.assertEqual([journal["name"] for journal in tracked], ["Core Journal", "Watch Journal"])
            self.assertTrue(all(journal["track_from_year"] == 2026 for journal in tracked))

            core_only = config.get_tracked_journals(include_priorities=("core",))
            self.assertEqual([journal["name"] for journal in core_only], ["Core Journal"])

    def test_cli_doctor_reports_local_env_keys(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            config_dir = project_dir / "config"
            config_dir.mkdir()

            write_file(
                config_dir / "journals.yaml",
                """
journals: []
global_keywords:
  - computational communication
""".strip(),
            )
            write_file(config_dir / "prompts.yaml", "{}")
            write_file(config_dir / "settings.yaml", "{}")
            write_file(
                project_dir / ".env",
                """
ANTHROPIC_API_KEY=anthropic-from-env-file
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
SEMANTIC_SCHOLAR_API_KEY=semantic-from-env-file
""".strip(),
            )

            stdout = io.StringIO()
            with patch("journal_tracker.config.os.environ", {}):
                with patch("sys.argv", ["main", "--config", str(config_dir), "doctor"]):
                    with patch("sys.stdout", stdout):
                        with self.assertRaises(SystemExit) as exit_info:
                            main_module.main()

            self.assertEqual(exit_info.exception.code, 0)
            output = stdout.getvalue()
            self.assertIn("Anthropic API Key: OK", output)
            self.assertIn("Semantic Scholar API Key: OK", output)
            self.assertIn("AI Base URL: https://api.deepseek.com/anthropic", output)


if __name__ == "__main__":
    unittest.main()
