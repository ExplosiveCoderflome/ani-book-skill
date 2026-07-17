from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SerialChapterWorkflowDocsTests(unittest.TestCase):
    def test_skill_keeps_multi_chapter_requests_serial(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("[parallel-chapter-production.md]", skill)
        self.assertIn("do not create child agents", skill)
        self.assertIn("one chapter before planning the next", skill)

    def test_contract_keeps_candidates_transient_and_coordinator_owned(self) -> None:
        contract = (ROOT / "references" / "parallel-chapter-production.md").read_text(
            encoding="utf-8"
        )
        for required_text in (
            "（暂停）",
            "不得创建子代理",
            "不得创建子代理、滚动预热或采用本页候选合同",
        ):
            self.assertIn(required_text, contract)

    def test_serial_contract_discards_prefetched_candidates(self) -> None:
        contract = (ROOT / "references" / "parallel-chapter-production.md").read_text(
            encoding="utf-8"
        )
        ledgers = (ROOT / "references" / "continuity-ledgers.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("不得保留或采用任何旧的后续章节候选", ledgers)


if __name__ == "__main__":
    unittest.main()
