from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from .project_layout import KNOWLEDGE_DIRS, ProjectPaths


def refresh_navigation(paths: ProjectPaths, reason: str = "refresh") -> dict[str, list[str]]:
    """Rebuild navigation files without depending on fragile text patches."""
    backups: list[Path] = []
    homepage_path = paths.knowledge_dir / "首页.md"
    _replace_with_backup(paths, homepage_path, _render_homepage(paths), backups, reason)
    _ensure_changelog(paths, backups, reason)
    if backups:
        _write_recovery_report(paths, backups, reason)
    return {"backups": [str(path) for path in backups]}


def append_changelog_entry(
    paths: ProjectPaths,
    title: str,
    entries: list[str],
    reason: str = "append_changelog",
) -> Path:
    """Append a changelog entry; rebuild a corrupt changelog before appending."""
    backups: list[Path] = []
    path = paths.knowledge_dir / "变更记录.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _read_navigation_text(path)
    if text is None or not text.lstrip().startswith("# 变更记录"):
        if path.exists():
            backups.append(_backup_navigation_file(paths, path, reason))
        text = "# 变更记录\n\n"

    lines = ["", f"## {_now()} {title}", "", *entries, ""]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")
    if backups:
        _write_recovery_report(paths, backups, reason)
    return path


def _render_homepage(paths: ProjectPaths) -> str:
    lines = [
        "# 拓霖知识库",
        "",
        "本页由系统根据正式知识卡目录自动生成。正式知识卡只存放在下面 10 类目录中。",
        "",
        "## 知识卡目录",
        "",
    ]
    for directory in KNOWLEDGE_DIRS:
        count = len(list((paths.knowledge_dir / directory).rglob("*.md"))) if (paths.knowledge_dir / directory).exists() else 0
        lines.append(f"- [{directory}]({directory}/)：{count} 张")
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "- `raw/` 是原始资料，不在这里移动、删除或重命名。",
            "- `generated/` 是可重建的索引、报告和缓存，不是人工维护的正式知识。",
            "- `复核项/` 中的内容确认前不得作为确定事实或对外表达使用。",
            "",
        ]
    )
    return "\n".join(lines)


def _ensure_changelog(paths: ProjectPaths, backups: list[Path], reason: str) -> None:
    path = paths.knowledge_dir / "变更记录.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _read_navigation_text(path)
    if text is None or not text.lstrip().startswith("# 变更记录"):
        if path.exists():
            backups.append(_backup_navigation_file(paths, path, reason))
        path.write_text("# 变更记录\n\n", encoding="utf-8")


def _replace_with_backup(
    paths: ProjectPaths,
    path: Path,
    content: str,
    backups: list[Path],
    reason: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_navigation_text(path)
    if existing == content:
        return
    if path.exists():
        backups.append(_backup_navigation_file(paths, path, reason))
    path.write_text(content, encoding="utf-8")


def _read_navigation_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _backup_navigation_file(paths: ProjectPaths, path: Path, reason: str) -> Path:
    backup_dir = paths.generated_dir / "cache" / "navigation-backups" / _safe_timestamp()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{path.stem}-{reason}{path.suffix}"
    shutil.copy2(path, backup_path)
    return backup_path


def _write_recovery_report(paths: ProjectPaths, backups: list[Path], reason: str) -> None:
    report_path = paths.generated_dir / "reports" / "NAVIGATION_RECOVERY_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NAVIGATION_RECOVERY_REPORT",
        "",
        f"- generated_at: {_now()}",
        f"- reason: {reason}",
        "",
        "## Backups",
        "",
        *[f"- {path}" for path in backups],
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _safe_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
