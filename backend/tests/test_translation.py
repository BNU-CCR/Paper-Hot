import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from journal_tracker.storage import Paper, PaperStorage
from journal_tracker.text import clean_translated_abstract, clean_translated_title
from journal_tracker.translation import SiliconFlowTranslator, translate_pending_papers


class FakeResponse:
    def __init__(self, status_code, content="", headers=None):
        self.status_code = status_code
        self._content = content
        self.headers = headers or {}
        self.text = content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class TranslationTests(unittest.TestCase):
    def test_translated_title_removes_model_wrappers(self):
        cases = {
            "论文标题：中国共同基金市场中的议程设置": "中国共同基金市场中的议程设置",
            "标题：聊天机器人与孤独感": "聊天机器人与孤独感",
            "**论文标题：**  \n“以自己的方式掌控我的健康！”": "以自己的方式掌控我的健康！",
            "这篇论文的标题是：\n\n《Instagram在意大利政治中的多模态应用》": "Instagram在意大利政治中的多模态应用",
            "将这篇论文的标题翻译为中文如下：\n“人工智能治理的实践化”": "人工智能治理的实践化",
            "翻译这篇论文的标题为：‘扭转注视的方向：性别化的戏仿’": "扭转注视的方向：性别化的戏仿",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(clean_translated_title(raw), expected)

    def test_translated_title_preserves_internal_quotes_and_colons(self):
        title = "TikTok“难民”：用户迁移的动机及其政治背景"
        self.assertEqual(clean_translated_title(title), title)

    def test_translated_abstract_removes_model_prefix_and_preserves_paragraphs(self):
        cases = {
            "这篇论文的摘要如下：\n\n第一段。\n\n第二段。": "第一段。\n\n第二段。",
            "**论文摘要：**\n\n**目的：** 研究问题。": "**目的：** 研究问题。",
            "本文摘要如下：摘要正文。": "摘要正文。",
            "请翻译这篇论文的摘要：\n摘要正文。": "摘要正文。",
            "```text\n摘要：正文。\n```": "正文。",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(clean_translated_abstract(raw), expected)

    def test_429_honors_retry_after_then_succeeds(self):
        sleeps = []
        session = FakeSession([
            FakeResponse(429, headers={"Retry-After": "2"}),
            FakeResponse(200, "中文标题"),
        ])
        translator = SiliconFlowTranslator(
            api_key="test",
            session=session,
            sleep=sleeps.append,
            clock=lambda: 0,
        )

        self.assertEqual(translator.translate_text("English title", "标题"), "中文标题")
        self.assertEqual(sleeps, [2.0])
        self.assertEqual(len(session.calls), 2)

    def test_translation_is_checkpointed_and_not_selected_again(self):
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            paper_id = storage.add_paper(Paper(
                title="English title",
                abstract="English abstract",
                link="https://example.org/translated",
                source_type="openalex",
                screening_status="screened",
            ))
            translator = SiliconFlowTranslator(
                api_key="test",
                session=FakeSession([FakeResponse(200, "中文标题"), FakeResponse(200, "中文摘要")]),
                sleep=lambda _: None,
                clock=lambda: 0,
            )

            report = translate_pending_papers(storage, translator, 10)

            paper = storage.get_paper_by_id(paper_id)
            self.assertEqual(report, {"selected": 1, "translated": 1, "failed": 0})
            self.assertEqual(paper.title_zh, "中文标题")
            self.assertEqual(paper.abstract_zh, "中文摘要")
            self.assertEqual(paper.translation_status, "translated")
            self.assertEqual(storage.get_papers_needing_translation(10), [])

    def test_existing_translated_titles_are_cleaned_without_retranslation(self):
        with TemporaryDirectory() as tmp_dir:
            storage = PaperStorage(Path(tmp_dir) / "papers.db")
            paper_id = storage.add_paper(Paper(
                title="English title",
                abstract="",
                link="https://example.org/already-translated",
                source_type="openalex",
                screening_status="screened",
            ))
            source_hash = storage.translation_source_hash("English title", "")
            storage.update_paper_translation(
                paper_id,
                "论文标题：《中文标题》",
                "这篇论文的摘要如下：\n\n摘要正文。",
                "test-model",
                source_hash,
            )

            report = translate_pending_papers(
                storage,
                SiliconFlowTranslator(api_key="test", session=FakeSession([])),
                10,
            )

            self.assertEqual(report, {"selected": 0, "translated": 0, "failed": 0})
            cleaned = storage.get_paper_by_id(paper_id)
            self.assertEqual(cleaned.title_zh, "中文标题")
            self.assertEqual(cleaned.abstract_zh, "摘要正文。")


if __name__ == "__main__":
    unittest.main()
