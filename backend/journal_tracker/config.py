"""配置管理模块"""

import os
from pathlib import Path
from typing import List, Optional, Sequence
import yaml


class Config:
    """论文追踪系统配置"""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).resolve().parents[1] / "config"
        self.config_dir = Path(config_dir)
        self.backend_root = self.config_dir.parent
        if self.backend_root.name == "backend":
            self.project_root = self.backend_root.parent
        else:
            self.project_root = self.backend_root
        self.env_file = self._load_env_file()
        self._load_configs()

    def _load_env_file(self) -> dict:
        """读取项目根目录本地 env 文件，便于安全注入 API key。"""
        env_candidates = [
            self.project_root / ".env",
            self.project_root / "key.env",
            self.project_root / ".local" / "key.env",
        ]
        env_path = next((path for path in env_candidates if path.exists()), None)
        if env_path is None:
            return {}

        values = {}
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    def _load_configs(self):
        """加载所有配置文件"""
        # 加载期刊配置
        journals_path = self.config_dir / "journals.yaml"
        if journals_path.exists():
            with open(journals_path, "r", encoding="utf-8") as f:
                self.journals = yaml.safe_load(f) or {}
        else:
            self.journals = {"journals": []}

        # 加载提示词配置
        prompts_path = self.config_dir / "prompts.yaml"
        if prompts_path.exists():
            with open(prompts_path, "r", encoding="utf-8") as f:
                self.prompts = yaml.safe_load(f) or {}
        else:
            self.prompts = {}

        # 加载设置
        settings_path = self.config_dir / "settings.yaml"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                self.settings = yaml.safe_load(f) or {}
        else:
            self.settings = {}

    @property
    def data_dir(self) -> Path:
        """数据目录"""
        data_dir = self.database_path.parent
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @property
    def database_path(self) -> Path:
        """数据库路径"""
        configured_path = self.settings.get("database", {}).get("path", "data/papers.db")
        path = Path(configured_path)
        if path.is_absolute():
            return path
        return self.backend_root / path

    @property
    def public_data_dir(self) -> Path:
        """公开数据导出目录"""
        if self.backend_root.name == "backend":
            public_dir = self.project_root / "frontend" / "public" / "data"
        else:
            public_dir = self.project_root / "public" / "data"
        public_dir.mkdir(parents=True, exist_ok=True)
        return public_dir

    @property
    def anthropic_api_key(self) -> str:
        """获取 Anthropic 兼容 API Key，可用于 Claude 或 DeepSeek。"""
        api_key = self.env_file.get("ANTHROPIC_API_KEY", "")
        if api_key:
            return api_key
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            return api_key
        # 从设置中读取
        return self.settings.get("anthropic_api_key", "")

    @property
    def anthropic_base_url(self) -> str:
        """获取 Anthropic 兼容 API Base URL。"""
        base_url = self.env_file.get("ANTHROPIC_BASE_URL", "")
        if base_url:
            return base_url
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        if base_url:
            return base_url
        base_url = self.settings.get("anthropic_base_url", "")
        if base_url:
            return base_url
        return ""

    @property
    def openalex_api_key(self) -> str:
        """获取 OpenAlex API Key（可选但推荐，提高请求限制）。"""
        api_key = self.env_file.get("OPENALEX_API_KEY", "")
        if api_key:
            return api_key
        api_key = os.environ.get("OPENALEX_API_KEY", "")
        if api_key:
            return api_key
        return self.settings.get("openalex_api_key", "")

    @property
    def semantic_scholar_api_key(self) -> str:
        """获取 Semantic Scholar API Key"""
        api_key = self.env_file.get("SEMANTIC_SCHOLAR_API_KEY", "")
        if api_key:
            return api_key
        api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        if api_key:
            return api_key
        return self.settings.get("semantic_scholar_api_key", "")

    @property
    def siliconflow_api_key(self) -> str:
        """Get the SiliconFlow key used only by the translation pipeline."""
        return self.env_file.get("SILICONFLOW_API_KEY", "") or os.environ.get("SILICONFLOW_API_KEY", "")

    @property
    def translation_config(self) -> dict:
        """Return non-secret translation endpoint, model, and throttling settings."""
        return self.settings.get("translation", {})

    @property
    def claude_model(self) -> str:
        """获取筛选模型名，兼容 Claude/DeepSeek Anthropic API。"""
        model = self.env_file.get("AI_MODEL") or self.env_file.get("ANTHROPIC_MODEL", "")
        if model:
            return model
        model = os.environ.get("AI_MODEL") or os.environ.get("ANTHROPIC_MODEL", "")
        if model:
            return model
        model = self.settings.get("claude_model", "")
        if model:
            return model
        return "deepseek-v4-flash"

    @property
    def filter_system_prompt(self) -> str:
        """获取筛选 system prompt"""
        return self.prompts.get("filter_system_prompt", "")

    @property
    def filter_user_template(self) -> str:
        """获取筛选 user prompt 模板"""
        return self.prompts.get("filter_user_template", "")

    @property
    def method_labels(self) -> List[str]:
        """固定研究方法标签分类（AI 只能从中选择唯一一个）。"""
        return self.prompts.get("method_labels", [])

    @property
    def method_system_prompt(self) -> str:
        """获取方法标签回填 system prompt。"""
        return self.prompts.get("method_system_prompt", "")

    @property
    def method_user_template(self) -> str:
        """获取方法标签回填 user 模板。"""
        return self.prompts.get("method_user_template", "")

    @property
    def hotspot_system_prompt(self) -> str:
        """获取当期热点归纳 prompt。"""
        return self.prompts.get("hotspot_system_prompt", "")

    @property
    def hotspot_network_config(self) -> dict:
        """获取热点网络构建参数。"""
        return self.settings.get("hotspot_network", {})

    @property
    def topic_overrides(self) -> dict:
        """获取主题人工重命名和合并规则。"""
        overrides_path = self.config_dir / "topic_overrides.yaml"
        if overrides_path.exists():
            with open(overrides_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    @property
    def notification_config(self) -> dict:
        """获取通知配置"""
        return self.settings.get("notification", {})

    def get_journal_keywords(self, journal_name: str) -> List[str]:
        """获取期刊的搜索关键词"""
        for journal in self.journals.get("journals", []):
            if journal.get("name") == journal_name:
                return journal.get("keywords", [])
        return []

    def get_tracked_journals(
        self,
        include_priorities: Sequence[str] = ("core", "watch"),
    ) -> List[dict]:
        """Return red-list journals that should be fetched by default."""
        allowed = set(include_priorities)
        tracked = []
        for journal in self.journals.get("journals", []):
            priority = journal.get("priority", "core")
            if priority not in allowed:
                continue
            normalized = dict(journal)
            normalized.setdefault("priority", priority)
            normalized.setdefault("track_from_year", 2026)
            tracked.append(normalized)
        return tracked

    def get_all_keywords(self) -> List[str]:
        """获取所有期刊的关键词"""
        keywords = []
        for journal in self.journals.get("journals", []):
            keywords.extend(journal.get("keywords", []))
        return list(set(keywords))

    def get_discovery_keywords(self) -> List[str]:
        """获取论文发现所用关键词，优先合并期刊和全局关键词"""
        keywords: List[str] = []
        for journal in self.journals.get("journals", []):
            keywords.extend(journal.get("keywords", []))
        keywords.extend(self.journals.get("global_keywords", []))

        deduped: List[str] = []
        seen = set()
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                deduped.append(keyword)
        return deduped


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config
