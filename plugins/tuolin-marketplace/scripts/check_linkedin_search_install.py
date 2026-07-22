from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_PLUGIN_VERSION = "1.52.2"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Tuolin LinkedIn Search installation readiness.")
    parser.add_argument("--project-dir", default=".", help="Tuolin knowledge project directory.")
    args = parser.parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    plugin_root = Path(__file__).resolve().parents[1]
    checks: list[dict[str, Any]] = []

    _check(checks, "python", sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (requires >= 3.10)")
    manifest_path = plugin_root / ".codex-plugin" / "plugin.json"
    manifest = _read_json_or_error(manifest_path, checks, "plugin_manifest")
    if manifest is not None:
        version = str(manifest.get("version") or "")
        _check(checks, "plugin_version", version == EXPECTED_PLUGIN_VERSION, f"installed={version or 'missing'}, expected={EXPECTED_PLUGIN_VERSION}")

    required_runtime = [
        plugin_root / "skills" / "tuolin-linkedin-search" / "SKILL.md",
        plugin_root / "scripts" / "create_linkedin_search_run.py",
        plugin_root / "scripts" / "update_linkedin_search_run.py",
        plugin_root / "scripts" / "tuolin_marketplace" / "linkedin_search" / "dispatch.py",
    ]
    missing_runtime = [str(path) for path in required_runtime if not path.is_file()]
    _check(checks, "linkedin_search_runtime", not missing_runtime, "complete" if not missing_runtime else f"missing={missing_runtime}")

    interface_dir = project_dir / "generated" / "agent-interface"
    agent_manifest = _read_json_or_error(interface_dir / "manifest.json", checks, "agent_interface_manifest")
    summary = _read_json_or_error(interface_dir / "manifest_summary.json", checks, "agent_interface_summary")
    cards_dir = interface_dir / "cards"
    _check(checks, "agent_interface_cards", cards_dir.is_dir(), str(cards_dir))
    if agent_manifest is not None and summary is not None:
        manifest_revision = str(agent_manifest.get("interface_revision") or "")
        summary_revision = str(summary.get("interface_revision") or "")
        _check(
            checks,
            "agent_interface_revision",
            bool(manifest_revision) and manifest_revision == summary_revision,
            f"manifest={manifest_revision or 'missing'}, summary={summary_revision or 'missing'}",
        )
        validation_errors = int(summary.get("validation_error_count") or 0)
        _check(checks, "agent_interface_validation", validation_errors == 0, f"validation_error_count={validation_errors}")

    automated_ready = all(item["passed"] for item in checks)
    report = {
        "workflow": "tuolin-linkedin-search-install-check",
        "expected_plugin_version": EXPECTED_PLUGIN_VERSION,
        "project_dir": str(project_dir),
        "automated_preflight_passed": automated_ready,
        "checks": checks,
        "human_checks_still_required": [
            "Codex 中已安装并启用官方 chrome@openai-bundled 插件",
            "Chrome 使用老板本人现有 profile，LinkedIn 已登录",
            "用户先授权只读 LinkedIn 操作；真实邀请仍需最终批次确认",
        ],
        "next_instruction": (
            "在新 Codex 会话中发起一个只读 LinkedIn 搜索测试。"
            if automated_ready
            else "先修复 failed 检查；知识接口缺失时使用 $tuolin-kb 刷新并验证。"
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if automated_ready else 2


def _read_json_or_error(path: Path, checks: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("top level is not an object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _check(checks, name, False, f"{path}: {exc}")
        return None
    _check(checks, name, True, str(path))
    return value


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


if __name__ == "__main__":
    raise SystemExit(main())
