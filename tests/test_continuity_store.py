from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "continuity_store.py"
CHECKER = ROOT / "scripts" / "check_continuity_workspace.py"


class ContinuityStoreCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        (self.workspace / "continuity").mkdir()
        (self.workspace / "production").mkdir()
        (self.workspace / "characters").mkdir()
        (self.workspace / "chapters/chapter-012").mkdir(parents=True)
        (self.workspace / "chapters/chapter-012/plan.md").write_text("# 未验收第十二章\n", encoding="utf-8")
        (self.workspace / "novel-state.yaml").write_text(
            "schema_version: 2\ncontinuity:\n  baseline_chapter: chapter_001\n  last_committed_chapter: chapter_011\n  recovery_path: production/recovery.md\n  quality_debt_open_count: 0\n",
            encoding="utf-8",
        )
        (self.workspace / "continuity/baseline.md").write_text(
            "# 连续性基线\n\n- 基线章节：`chapter-001`\n- 已确认：第十一章为最后验收章。\n",
            encoding="utf-8",
        )
        (self.workspace / "continuity/fact-ledger.md").write_text(
            "# 事实账本\n\n| ID | 稳定事实 | 发生章节 | 证据 | 涉及角色 | 状态与后续约束 |\n| --- | --- | --- | --- | --- | --- |\n| FACT-001 | 已发生的事实。 | chapter-011 | 正文证据 | CHAR-001 | 稳定；不得提前解释。 |\n",
            encoding="utf-8",
        )
        (self.workspace / "continuity/payoff-ledger.md").write_text(
            "# 伏笔账本\n\n| ID | 承诺/伏笔 | 来源 | 首现 | 目标窗口 | 当前状态 | 最近推进 | 风险与下次窗口 |\n| --- | --- | --- | --- | --- | --- | --- |\n| PAYOFF-001 | 未结承诺。 | 第一章正文 | chapter-001 | chapter-012 | pending | 第十一章推进 | 第十二章核验。 |\n",
            encoding="utf-8",
        )
        (self.workspace / "continuity/resource-ledger.md").write_text(
            "# 资源账本\n\n| ID | 资源 | 持有人/归属 | 可见性与状态 | 来源 | 使用窗口与禁止误用 |\n| --- | --- | --- | --- | --- | --- |\n| RESOURCE-001 | 封存物证。 | 大理寺 | 可复核 | chapter-011 | 不得单方拆封。 |\n",
            encoding="utf-8",
        )
        (self.workspace / "production/recovery.md").write_text("# 恢复\n", encoding="utf-8")
        (self.workspace / "production/quality-debt.md").write_text("# 质量债\n", encoding="utf-8")
        (self.workspace / "characters/character-roster.md").write_text(
            "# 角色\n\n| ID | 姓名/称呼 | 公开身份或功能 | 启用窗口 | 一眼识别锚点 | 档案 |\n| --- | --- | --- | --- | --- | --- |\n| CHAR-001 | 主角 | 调查者 | 开篇 | 纸角 | - |\n\n## 关系矩阵\n\n| 角色 A | 角色 B | 公开关系 | 隐秘绑定 | 当前方向 | 不可越过边界 |\n| --- | --- | --- | --- | --- | --- |\n| CHAR-001 | CHAR-001 | 自我关系 | 无 | 稳定 | 不得越界。 |\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_migrate_render_index_context_checkpoint_and_validate(self) -> None:
        preview = self.run_cli("migrate", str(self.workspace), "--dry-run")
        self.assertIn('"facts": 1', preview.stdout)
        self.assertFalse((self.workspace / "continuity/data").exists())

        migrated = self.run_cli("migrate", str(self.workspace))
        self.assertIn('"last_committed_chapter": "chapter_011"', migrated.stdout)
        self.assertTrue((self.workspace / "continuity/data/facts.yaml").is_file())
        self.assertTrue((self.workspace / "continuity/index.sqlite3").is_file())
        self.assertTrue((self.workspace / "continuity/legacy-markdown").is_dir())
        self.assertTrue((self.workspace / "continuity/data/checkpoints/checkpoint-011.yaml").is_file())

        facts = yaml.safe_load((self.workspace / "continuity/data/facts.yaml").read_text(encoding="utf-8"))
        self.assertEqual(facts[0]["introduced_in"], "chapter-011")
        self.assertFalse(any("012" in str(item) for item in facts))
        state = yaml.safe_load((self.workspace / "novel-state.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["schema_version"], 3)
        self.assertEqual(state["continuity"]["structured_store"]["authority"], "yaml")
        self.assertIn("generated-from: continuity/data revision 1", (self.workspace / "continuity/fact-ledger.md").read_text(encoding="utf-8"))

        self.run_cli("validate", str(self.workspace))
        checked = subprocess.run([sys.executable, str(CHECKER), str(self.workspace)], check=False, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

        indexed = self.run_cli("assemble-context", str(self.workspace), "--chapter", "12", "--characters", "CHAR-001")
        self.assertIn("SQLite candidates + YAML authority", indexed.stdout)
        (self.workspace / "continuity/index.sqlite3").unlink()
        fallback = self.run_cli("assemble-context", str(self.workspace), "--chapter", "12")
        self.assertIn("YAML direct fallback", fallback.stdout)
        self.run_cli("build-index", str(self.workspace))
        self.run_cli("checkpoint", str(self.workspace), "--chapter", "chapter-020", "--reason", "volume-end")
        self.assertTrue((self.workspace / "continuity/data/checkpoints/checkpoint-020.yaml").is_file())

    def test_validate_rejects_duplicate_ids_and_future_fact(self) -> None:
        self.run_cli("migrate", str(self.workspace))
        facts_path = self.workspace / "continuity/data/facts.yaml"
        facts = yaml.safe_load(facts_path.read_text(encoding="utf-8"))
        duplicate = dict(facts[0])
        duplicate["introduced_in"] = "chapter-012"
        facts.append(duplicate)
        facts_path.write_text(yaml.safe_dump(facts, allow_unicode=True, sort_keys=False), encoding="utf-8")
        result = self.run_cli("validate", str(self.workspace), check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate id FACT-001", result.stdout)
        self.assertIn("beyond last committed chapter", result.stdout)


if __name__ == "__main__":
    unittest.main()
