from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analysis_retrieval.py"


class AnalysisRetrievalCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        (self.workspace / "notes").mkdir()
        (self.workspace / "sections").mkdir()
        (self.workspace / "graph").mkdir()
        (self.workspace / "analysis-state.yaml").write_text(
            'source:\n  fingerprint: "sha256:TEST"\n',
            encoding="utf-8",
        )
        (self.workspace / "notes" / "segment-001.md").write_text(
            '<!-- retrieval-meta: {"chapter_start":1,"chapter_end":3,"dimensions":["progression"],"characters":["林越"]} -->\n'
            "# 第一阶段\n\n林越完成第一次升级循环，以资源代价换取能力突破，并在章末发现新的敌人。\n",
            encoding="utf-8",
        )
        (self.workspace / "notes" / "segment-002.md").write_text(
            '<!-- retrieval-meta: {"chapter_start":4,"chapter_end":6,"dimensions":["cliffhanger"],"characters":["林越"]} -->\n'
            "# 第二阶段\n\n新的敌人阻断奖励兑现，结尾用身份揭示形成下一章问题。\n",
            encoding="utf-8",
        )
        (self.workspace / "sections" / "overview.md").write_text(
            "# 总览\n\n当前样本显示故事依靠升级与身份悬念推动追读。\n",
            encoding="utf-8",
        )
        nodes = [
            {"id": "CHAR-001", "type": "character", "label": "林越", "source_refs": ["segment-001"], "confidence": "high"},
            {"id": "EVENT-001", "type": "event", "label": "首次突破", "source_refs": ["segment-001"], "confidence": "high"},
            {"id": "PROMISE-001", "type": "promise", "label": "新敌人身份", "source_refs": ["segment-002"], "confidence": "medium"},
        ]
        edges = [
            {"id": "EDGE-001", "source": "CHAR-001", "relation": "causes", "target": "EVENT-001", "evidence": ["CLAIM-001"], "confidence": "high"},
            {"id": "EDGE-002", "source": "EVENT-001", "relation": "opens", "target": "PROMISE-001", "evidence": ["CLAIM-002"], "confidence": "medium"},
        ]
        (self.workspace / "graph" / "nodes.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in nodes) + "\n",
            encoding="utf-8",
        )
        (self.workspace / "graph" / "edges.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in edges) + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_build_search_and_graph_trace(self) -> None:
        build = json.loads(self.run_cli("build", str(self.workspace)).stdout)
        self.assertGreaterEqual(build["chunks"], 3)
        self.assertEqual(build["nodes"], 3)
        self.assertEqual(build["edges"], 2)

        search = json.loads(self.run_cli(
            "search",
            str(self.workspace),
            "升级循环",
            "--dimension",
            "progression",
            "--neighbor",
            "0",
            "--format",
            "json",
        ).stdout)
        self.assertTrue(search)
        self.assertEqual(search[0]["path"], "notes/segment-001.md")
        self.assertIn("lexical", search[0]["reasons"])

        index_path = self.workspace / "retrieval" / "analysis-index.sqlite3"
        connection = sqlite3.connect(index_path)
        try:
            rows = connection.execute("SELECT chunk_id, relative_path FROM chunks").fetchall()
        finally:
            connection.close()
        embeddings = [
            {
                "chunk_id": chunk_id,
                "model": "fixture",
                "vector": [1.0, 0.0] if path == "notes/segment-002.md" else [0.0, 1.0],
            }
            for chunk_id, path in rows
        ]
        embeddings_path = self.workspace / "retrieval" / "embeddings.jsonl"
        embeddings_path.write_text(
            "\n".join(json.dumps(item) for item in embeddings) + "\n",
            encoding="utf-8",
        )
        query_vector_path = self.workspace / "retrieval" / "query-vector.json"
        query_vector_path.write_text(
            json.dumps({"model": "fixture", "vector": [1.0, 0.0]}),
            encoding="utf-8",
        )
        vector_search = json.loads(self.run_cli(
            "search",
            str(self.workspace),
            "无词法命中",
            "--query-vector",
            str(query_vector_path),
            "--neighbor",
            "0",
            "--format",
            "json",
        ).stdout)
        self.assertTrue(vector_search)
        self.assertEqual(vector_search[0]["path"], "notes/segment-002.md")
        self.assertIn("vector", vector_search[0]["reasons"])

        nodes = json.loads(self.run_cli(
            "nodes",
            str(self.workspace),
            "林越",
        ).stdout)
        self.assertEqual(nodes[0]["id"], "CHAR-001")

        neighbors = json.loads(self.run_cli(
            "neighbors",
            str(self.workspace),
            "首次突破",
            "--depth",
            "1",
        ).stdout)
        self.assertEqual(len(neighbors["edges"]), 2)

        trace = json.loads(self.run_cli(
            "trace",
            str(self.workspace),
            "CHAR-001",
            "PROMISE-001",
        ).stdout)
        self.assertTrue(trace["found"])
        self.assertEqual(len(trace["edges"]), 2)

    def test_build_rejects_unknown_graph_endpoint(self) -> None:
        invalid_edge = {
            "id": "EDGE-BROKEN",
            "source": "CHAR-001",
            "relation": "causes",
            "target": "MISSING-001",
        }
        (self.workspace / "graph" / "edges.jsonl").write_text(
            json.dumps(invalid_edge) + "\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "build", str(self.workspace)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("edge endpoints must exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
