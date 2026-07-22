from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_PLUGIN_VERSION = "1.53.0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Tuolin LinkedIn Search installation readiness.")
    parser.add_argument("--project-dir", default=".", help="Writable Tuolin operational workspace.")
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

    try:
        generated_dir = project_dir / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        probe = generated_dir / ".linkedin-search-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        _check(checks, "operational_workspace_writable", False, str(exc))
    else:
        _check(checks, "operational_workspace_writable", True, str(generated_dir))

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
            else "先修复 failed 检查；此工作流不要求安装产品知识库。"
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
