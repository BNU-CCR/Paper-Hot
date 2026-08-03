"""AI筛选模块 - Anthropic 兼容 API（Claude / DeepSeek）"""

import json
import anthropic
from typing import Optional, Dict, Any

from .config import get_config


class PaperFilter:
    """使用 Anthropic 兼容 API 进行论文 AI 筛选"""

    DEFAULT_SYSTEM_PROMPT = """你是一个计算传播学领域的学术审稿人。你的任务是判断一篇论文是否属于计算传播领域。

## 判断标准

### 纳入标准（满足任一即可）：
1. **选题相关**：研究主题涉及
   - 人工智能/AI/机器学习
   - 大语言模型/LLM/生成式 AI
   - 社交媒体平台（Twitter/X, Facebook, 微信，微博等）
   - 算法推荐/信息茧房/过滤气泡
   - 社交网络分析
   - 计算宣传/虚假信息/机器人账号
   - 数字方法/计算社会科学

2. **方法相关**：使用计算方法
   - 文本分析/自然语言处理
   - 网络分析/图分析
   - 机器学习/深度学习
   - API 数据采集/大数据处理
   - 计算实验/AB 测试

3. **AI/大模型特别条款**：
   - 只要是讨论 AI/大模型的社会影响、使用行为、传播效果等
   - 即使方法较传统（如调查、实验），也纳入

### 排除标准（满足任一即排除）：
- 纯理论/哲学思辨（无经验数据）
- 纯批判性分析（文化研究取径）
- 传统问卷调查（无计算元素）
- 纯粹的方法论论文（无实质传播问题）

## 输出格式

请严格按照以下 JSON 格式输出，不要输出其他内容：

{
  "relevance": "High/Medium/Low",
  "reason": "简要说明判断理由，50 字以内",
  "tags": ["标签 1", "标签 2"],
  "summary": "论文核心内容总结，100 字以内"
}

### 相关性分级说明：
- **High**: 明确是计算传播研究，有计算方法 + 领域议题
- **Medium**: 边缘相关，如方法是计算的但议题较远，或议题相关但方法传统
- **Low**: 不相关，纯理论/批判/传统方法
"""

    DEFAULT_USER_PROMPT_TEMPLATE = """请判断以下论文是否属于计算传播领域：

**标题**：{title}

**摘要**：{abstract}

**作者**：{authors}

**期刊**：{journal}

请按照标准判断，严格只输出JSON格式结果。"""

    # 固定研究方法标签分类（AI 只能从中选择唯一一个，不确定时留空）
    DEFAULT_METHOD_LABELS = [
        "纯质性分析",
        "传统量化分析",
        "纯理论分析",
        "综述",
        "计算传播学",
    ]

    DEFAULT_METHOD_SYSTEM_PROMPT = """你是计算传播学领域的研究方法分类员。请根据论文的标题、摘要、作者和期刊，从以下固定方法标签中选出唯一一个最匹配的分类：
- 纯质性分析
- 传统量化分析
- 纯理论分析
- 综述
- 计算传播学

规则：
- 只能输出列表中的标签之一，不能自创。
- 计算传播学指使用大规模数字数据与计算方法（NLP、网络分析、机器学习、API 采集等）的实证研究。
- 若无法确定或明显不属于任何一类，method 输出空字符串。

严格只输出 JSON：
{"method": "计算传播学"}"""

    DEFAULT_METHOD_USER_TEMPLATE = """请判断以下论文的研究方法类别：

**标题**：{title}

**摘要**：{abstract}

**作者**：{authors}

**期刊**：{journal}

请从固定方法标签中选出唯一一个，严格只输出JSON结果。"""

    def __init__(self, api_key: Optional[str] = None):
        config = get_config()
        self.api_key = api_key or config.anthropic_api_key
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
        self.base_url = config.anthropic_base_url
        self.model = config.claude_model
        self.system_prompt = config.filter_system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.user_prompt_template = (
            config.filter_user_template or self.DEFAULT_USER_PROMPT_TEMPLATE
        )
        self.method_labels = config.method_labels or list(self.DEFAULT_METHOD_LABELS)
        self.method_system_prompt = (
            config.method_system_prompt or self.DEFAULT_METHOD_SYSTEM_PROMPT
        )
        self.method_user_template = (
            config.method_user_template or self.DEFAULT_METHOD_USER_TEMPLATE
        )
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = anthropic.Anthropic(**client_kwargs)

    def filter_paper(
        self,
        title: str,
        abstract: str,
        authors: str = "",
        journal: str = ""
    ) -> Dict[str, Any]:
        """
        筛选单篇论文

        Returns:
            dict: {
                "relevance": "High/Medium/Low",
                "reason": str,
                "tags": list[str],
                "summary": str
            }
        """
        user_prompt = self.user_prompt_template.format(
            title=title,
            abstract=abstract[:2000] if abstract else "无摘要",
            authors=authors or "未知",
            journal=journal or "未知"
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        # 解析响应。DeepSeek Anthropic-compatible API 可能先返回 thinking block。
        response_text = self._extract_response_text(response)
        result = self._parse_json_response(response_text)

        # 验证必需字段
        if "relevance" not in result:
            result["relevance"] = "Low"
        if "reason" not in result:
            result["reason"] = "AI响应格式异常"
        if "tags" not in result:
            result["tags"] = []
        if "summary" not in result:
            result["summary"] = ""

        # 确保relevance是有效值
        if result["relevance"] not in ["High", "Medium", "Low"]:
            result["relevance"] = "Low"

        # 研究方法标签：只接受固定分类学中的值，缺失/非法/不确定一律归 ""
        method = result.get("method", "")
        result["method"] = method if method in self.method_labels else ""

        return result

    def _extract_response_text(self, response) -> str:
        """从 Anthropic 兼容响应中提取文本内容，跳过 thinking/tool 等非文本块。"""
        for block in getattr(response, "content", []):
            text = getattr(block, "text", None)
            if text:
                return text.strip()
        raise ValueError("AI响应中没有可解析的文本内容")

    def _parse_json_response(self, response_text: str) -> dict:
        """容错解析 AI 响应中的 JSON：先整段解析，再尝试提取 {} 块。"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != 0:
                return json.loads(response_text[start:end])
            raise ValueError(f"无法解析AI响应: {response_text[:200]}") from None

    def label_method(
        self,
        title: str,
        abstract: str,
        authors: str = "",
        journal: str = "",
    ) -> str:
        """
        为论文打一个固定的研究方法标签（仅回填用，不影响 relevance/tags/summary）。

        Returns:
            str: 命中固定分类学的方法标签，无法确定或非法时返回空字符串。
        """
        user_prompt = self.method_user_template.format(
            title=title,
            abstract=abstract[:2000] if abstract else "无摘要",
            authors=authors or "未知",
            journal=journal or "未知",
        )
        response = self.client.messages.create(
            model=self.model,
            # Keep the same generous budget as filter_paper: DeepSeek's thinking
            # block consumes tokens and max_tokens=100 truncated the JSON reply.
            max_tokens=500,
            system=self.method_system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )
        result = self._parse_json_response(self._extract_response_text(response))
        method = result.get("method", "")
        return method if method in self.method_labels else ""

    def filter_papers(self, papers: list) -> list:
        """批量筛选论文"""
        results = []
        for paper in papers:
            try:
                result = self.filter_paper(
                    title=paper.get("title", ""),
                    abstract=paper.get("abstract", ""),
                    authors=paper.get("authors", ""),
                    journal=paper.get("journal", "")
                )
                results.append({**paper, **result})
            except Exception as e:
                print(f"筛选论文 '{paper.get('title', 'Unknown')}' 时出错: {e}")
                results.append({
                    **paper,
                    "relevance": "Low",
                    "reason": f"筛选出错: {str(e)[:30]}",
                    "tags": [],
                    "summary": ""
                })
        return results
