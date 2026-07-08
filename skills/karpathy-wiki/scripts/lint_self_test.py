#!/usr/bin/env python3
"""Self-test for karpathy-wiki lint behavior.

The fixture is intentionally tiny and uses only the Python standard library.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "scripts" / "lint.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def run_lint(wiki: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(LINT), str(wiki)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(result.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="karpathy-wiki-lint-test-") as td:
        wiki = Path(td) / "wiki"
        for dirname in [
            "claims",
            "concepts",
            "entities",
            "comparisons",
            "queries",
            "synthesis",
            "raw/01-访谈材料",
        ]:
            (wiki / dirname).mkdir(parents=True, exist_ok=True)

        write(
            wiki / "SCHEMA.md",
            """
            # Schema

            ## Tag Taxonomy
            - `社会资本（Social Capital）`
            - `方法论`
            """,
        )
        write(
            wiki / "index.md",
            """
            # Index

            ## 论证节点 / Claims
            - [[核心命题]]

            ## 概念
            - [[社会资本（Social Capital）]]

            ## 综述入口
            - [[研究路线图]]
            """,
        )
        write(wiki / "log.md", "# Log")
        write(
            wiki / "raw/01-访谈材料/访谈A.md",
            """
            ---
            ingested: 2026-06-12
            sha256: intentionally-wrong
            ---

            访谈材料正文。
            """,
        )
        write(
            wiki / "concepts/社会资本（Social Capital）.md",
            """
            ---
            title: 社会资本（Social Capital）
            created: 2026-06-12
            updated: 2026-06-12
            type: concept
            tags: [社会资本（Social Capital）]
            sources: [raw/01-访谈材料/访谈A.md]
            confidence: medium
            ---

            # 社会资本（Social Capital）

            关联 [[核心命题]] 与 [[研究路线图]]。
            """,
        )
        write(
            wiki / "claims/核心命题.md",
            """
            ---
            title: 核心命题
            type: claim
            claim_type: main
            core: true
            status: supported
            confidence: medium
            supports: []
            opposes: []
            limits: []
            depends_on: []
            related_concepts: [社会资本（Social Capital）]
            related_entities: []
            related_comparisons: []
            sources: [社会资本（Social Capital）]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 核心命题

            ## 命题
            社会资本影响行动者的资源可得性。

            ## 关系
            - 支撑：无
            - 反对：无
            - 限定：[[争议命题]]
            - 依赖：[[社会资本（Social Capital）]]

            ## 关键证据
            - [[社会资本（Social Capital）]]：访谈材料显示资源网络差异。
              - 证据位置：`raw/01-访谈材料/访谈A.md:1`

            ## 写作用途
            可用于文献综述。
            """,
        )
        write(
            wiki / "claims/普通命题.md",
            """
            ---
            title: 普通命题
            type: claim
            claim_type: support
            core: false
            status: working
            confidence: medium
            supports: [核心命题]
            opposes: []
            limits: []
            depends_on: []
            related_concepts: [社会资本（Social Capital）]
            related_entities: []
            related_comparisons: []
            sources: [社会资本（Social Capital）]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 普通命题

            ## 命题
            普通命题不需要出现在 index。

            ## 关系
            - 支撑：[[核心命题]]
            - 反对：无
            - 限定：无
            - 依赖：[[社会资本（Social Capital）]]
            """,
        )
        write(
            wiki / "claims/争议命题.md",
            """
            ---
            title: 争议命题
            type: claim
            claim_type: objection
            core: false
            status: contested
            confidence: medium
            supports: []
            opposes: [核心命题]
            limits: [核心命题]
            depends_on: []
            related_concepts: [社会资本（Social Capital）]
            related_entities: []
            related_comparisons: []
            sources: [社会资本（Social Capital）]
            created: 2026-06-12
            updated: 2026-06-12
            ---

            # 争议命题

            ## 命题
            社会资本也可能再生产不平等。

            ## 关系
            - 支撑：无
            - 反对：[[核心命题]]
            - 限定：[[核心命题]]
            - 依赖：[[社会资本（Social Capital）]]
            """,
        )
        write(
            wiki / "synthesis/研究路线图.md",
            """
            ---
            title: 研究路线图
            created: 2026-06-12
            updated: 2026-06-12
            type: synthesis
            tags: [方法论]
            sources: [核心命题]
            confidence: medium
            ---

            # 研究路线图

            入口页，连接 [[核心命题]] 与 [[社会资本（Social Capital）]]。
            """,
        )

        report = run_lint(wiki)
        findings = report.get("findings", {})

        assert report["total_raw_files"] == 1, report
        assert "研究路线图" not in findings.get("index", {}).get("index_entries_without_page", []), report
        assert "普通命题" not in findings.get("index", {}).get("pages_not_in_index", []), report
        assert not findings.get("tag_issues"), report
        assert not any(
            issue.get("issue", "").startswith("tag ")
            for issue in findings.get("frontmatter", [])
        ), report
        assert any(
            item.get("page") == "claims/争议命题.md"
            for item in findings.get("contradictions", [])
        ), report
        assert any(
            item.get("file") == "raw/01-访谈材料/访谈A.md"
            for item in findings.get("source_drift", [])
        ), report

    print("karpathy-wiki lint self-test passed")


if __name__ == "__main__":
    main()
