from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_interface import knowledge_status, open_reviews
from .card_validator import PROFILE
from .downstream_context import build_downstream_context
from .generated_index import rebuild_generated_indexes
from .natural_language import route_natural_language
from .partitions import find_partition, scan_partition
from .partition_organizer import organize_partition
from .project_layout import initialize_project, inspect_project, resolve_paths
from .question_answering import answer_question
from .review_workflow import apply_review_decision, create_review_preview, list_review_items


@dataclass(frozen=True)
class AcceptanceCheck:
    check_id: str
    title: str
    prd_use_cases: tuple[str, ...]
    passed: bool
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["prd_use_cases"] = list(self.prd_use_cases)
        return data


def run_acceptance(project_dir: Path | None = None, write_report: bool = True) -> dict[str, Any]:
    root = project_dir.resolve() if project_dir else Path(tempfile.mkdtemp(prefix="tuolin-acceptance-")).resolve()
    plugin_root = Path(__file__).resolve().parents[2]
    paths = resolve_paths(root, {})
    checks: list[AcceptanceCheck] = []

    created = initialize_project(paths)
    _prepare_sample_raw(paths)
    raw_snapshot = _raw_snapshot(paths.raw_dir)

    checks.append(
        _check(
            "AC-001",
            "初始化三层目录与 Codex 插件边界",
            ("UC-006",),
            (
                paths.raw_dir.exists()
                and paths.knowledge_dir.exists()
                and paths.generated_dir.exists()
                and (plugin_root / ".codex-plugin" / "plugin.json").exists()
                and (plugin_root / "scripts" / "windows_check_dependencies.ps1").exists()
            ),
            {
                "created_count": len(created),
                "project": inspect_project(paths),
                "plugin_root": str(plugin_root),
                "plugin_manifest_exists": (plugin_root / ".codex-plugin" / "plugin.json").exists(),
                "windows_dependency_check_exists": (plugin_root / "scripts" / "windows_check_dependencies.ps1").exists(),
            },
        )
    )

    recommendation = route_natural_language(paths, "整理一下拓霖知识库。")
    checks.append(
        _check(
            "AC-003",
            "自然语言推荐下一步并等待确认",
            ("UC-007", "UC-008"),
            recommendation.needs_confirmation and not recommendation.executed and bool(recommendation.copyable_reply),
            recommendation.to_dict(),
        )
    )

    product_result = route_natural_language(paths, "确认，开始整理石英纤维隔热带资料。")
    checks.append(
        _check(
            "AC-004",
            "整理一个带 PDF、图片和视频素材的产品分区",
            ("UC-001",),
            product_result.executed and (paths.knowledge_dir / "产品" / "石英纤维隔热带.md").exists(),
            product_result.to_dict(),
        )
    )

    domain_results = {
        name: organize_partition(paths, name).__dict__
        for name in ["公司能力", "标准法规", "市场情报", "销售物料", "客户问题/客服反馈"]
    }
    counts_by_type = knowledge_status(paths)["manifest_summary"]["counts_by_type"]
    checks.append(
        _check(
            "AC-005",
            "10 类通用卡片都有样例，video_profile 由专用视频发布链路管理",
            ("UC-001", "UC-002", "UC-005"),
            all(
                counts_by_type.get(card_type, 0) > 0
                for card_type in PROFILE["card_types"]
                if card_type != "video_profile"
            )
            and counts_by_type.get("video_profile") == 0,
            {"counts_by_type": counts_by_type, "domain_results": domain_results},
        )
    )

    reviews = list_review_items(paths, "石英纤维隔热带")
    review_id = reviews[0].review_id if reviews else ""
    preview = create_review_preview(paths, review_id, "approve_external") if review_id else None
    applied = (
        apply_review_decision(paths, review_id, "approve_external", preview.confirmation_token, reviewer="acceptance")
        if preview
        else None
    )
    product_cards = knowledge_status(paths)["manifest_summary"]["counts_by_status"]
    checks.append(
        _check(
            "AC-006",
            "复核预览后用确认令牌更新 official 卡",
            ("UC-002", "UC-003"),
            bool(applied and applied.updated_cards and product_cards.get("official", 0) > 0),
            {
                "open_review_count_before": len(reviews),
                "preview": preview.__dict__ if preview else None,
                "applied": applied.__dict__ if applied else None,
                "open_reviews_after": len(open_reviews(paths)),
            },
        )
    )

    answer = answer_question(paths, "根据现有资料，帮我写一段石英纤维隔热带产品介绍。")
    checks.append(
        _check(
            "AC-007",
            "official-only 问答只使用已确认卡片",
            ("UC-004",),
            answer.answerable and "product/quartz_fiber_tape" in answer.used_cards,
            answer.to_dict(),
        )
    )

    downstream = build_downstream_context(paths, "linkedin_post", product_id="product/quartz_fiber_tape", query="产品介绍")
    checks.append(
        _check(
            "AC-008",
            "下游 Agent 上下文只读取 generated 接口",
            ("UC-005",),
            downstream["raw_access"] is False and bool(downstream["cards_by_type"].get("product")),
            downstream,
        )
    )

    checks.append(
        _check(
            "AC-009",
            "整理、复核、问答和下游上下文不会修改 raw",
            ("UC-001", "UC-003", "UC-004", "UC-005"),
            _raw_snapshot(paths.raw_dir) == raw_snapshot,
            {"raw_file_count": len(raw_snapshot)},
        )
    )

    new_raw_file = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "acceptance-new-report.md"
    new_raw_file.write_text("acceptance raw change", encoding="utf-8")
    post_change_snapshot = _raw_snapshot(paths.raw_dir)
    quartz = find_partition("石英纤维隔热带")
    quartz_status = scan_partition(paths, quartz)
    checks.append(
        _check(
            "AC-010",
            "raw 变化后推荐先更新对应分区",
            ("UC-009",),
            quartz_status.status == "needs_update" and quartz_status.recommended_next_action == "update_first",
            quartz_status.__dict__,
        )
    )
    checks.append(
        _check(
            "AC-011",
            "更新检查不会改 raw",
            ("UC-009",),
            _raw_snapshot(paths.raw_dir) == post_change_snapshot,
            {"raw_file_count": len(post_change_snapshot)},
        )
    )

    shutil.rmtree(paths.generated_dir)
    rebuilt = rebuild_generated_indexes(paths)
    checks.append(
        _check(
            "AC-012",
            "删除 generated 后可从 knowledge/okf 重建",
            ("UC-006",),
            (paths.generated_dir / "agent-interface" / "manifest.json").exists() and rebuilt["card_count"] > 0,
            rebuilt,
        )
    )

    report = _report(paths, checks)
    if write_report:
        report_path = paths.generated_dir / "reports" / "ACCEPTANCE_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_render_report(report), encoding="utf-8")
        report["report_path"] = str(report_path)
    return report


def _prepare_sample_raw(paths) -> None:
    files = {
        "01_产品/02_石英纤维隔热带/01_检测报告与认证/quartz-report.pdf": "PDF placeholder",
        "01_产品/02_石英纤维隔热带/01_检测报告与认证/quartz-report.md": "石英纤维隔热带检测报告可读正文。",
        "01_产品/02_石英纤维隔热带/02_产品图片/quartz-product.jpg": "image placeholder",
        "01_产品/02_石英纤维隔热带/03_产品视频/quartz-video.mp4": "video placeholder",
        "01_产品/02_石英纤维隔热带/04_应用场景素材/exhaust-pipe.jpg": "application image placeholder",
        "02_公司能力/01_公司介绍/company.md": "拓霖公司介绍样例。",
        "03_标准法规/01_中国标准/gb-t-3003.md": "中国标准样例。",
        "04_市场情报/01_市场现状与平台调研/europe-market.md": "欧洲市场调研样例。",
        "05_销售物料/01_Datasheet/quartz-datasheet.md": "石英纤维隔热带 Datasheet 样例。",
        "06_客户问题与客服反馈/02_已归类问题素材/冒烟异味/smoke-question.md": "客户询问冒烟异味样例。",
    }
    for relative, content in files.items():
        path = paths.raw_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _raw_snapshot(raw_dir: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    if not raw_dir.exists():
        return snapshot
    for path in sorted(item for item in raw_dir.rglob("*") if item.is_file()):
        snapshot[path.relative_to(raw_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def _check(check_id: str, title: str, prd_use_cases: tuple[str, ...], passed: bool, details: dict[str, Any]) -> AcceptanceCheck:
    return AcceptanceCheck(check_id, title, prd_use_cases, bool(passed), details)


def _report(paths, checks: list[AcceptanceCheck]) -> dict[str, Any]:
    coverage = {f"UC-{number:03d}": False for number in range(1, 10)}
    for check in checks:
        if check.passed:
            for use_case in check.prd_use_cases:
                coverage[use_case] = True
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_dir": str(paths.project_dir),
        "passed": all(check.passed for check in checks) and all(coverage.values()),
        "check_count": len(checks),
        "passed_count": sum(1 for check in checks if check.passed),
        "prd_use_case_coverage": coverage,
        "checks": [check.to_dict() for check in checks],
    }


def _render_report(report: dict[str, Any]) -> str:
    lines = [
        "# ACCEPTANCE_REPORT",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- passed: {str(report['passed']).lower()}",
        f"- check_count: {report['check_count']}",
        f"- passed_count: {report['passed_count']}",
        "",
        "## PRD Use Case Coverage",
        "",
    ]
    for use_case, covered in report["prd_use_case_coverage"].items():
        lines.append(f"- {use_case}: {'pass' if covered else 'missing'}")
    lines.extend(["", "## Checks", ""])
    for check in report["checks"]:
        lines.extend(
            [
                f"### {check['check_id']} {check['title']}",
                "",
                f"- passed: {str(check['passed']).lower()}",
                f"- prd_use_cases: {', '.join(check['prd_use_cases'])}",
                "",
            ]
        )
    return "\n".join(lines)
