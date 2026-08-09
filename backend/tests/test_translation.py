import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from journal_tracker.storage import Paper, PaperStorage
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


if __name__ == "__main__":
    unittest.main()
