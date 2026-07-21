from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from .agent import LinkedInSearchStepResult
from .browser_contract import _append_change, _append_history, _load_run, _write_json_atomic


ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg"}
MAX_EVIDENCE_BYTES = 20 * 1024 * 1024


def record_browser_evidence(
    run_dir: Path,
    screenshot_path: Path,
    *,
    reason: str,
    candidate_id: str = "",
    explicitly_authorized: bool = False,
    disputed_state: bool = False,
    platform_stop: bool = False,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    """Persist an already-captured screenshot only for an approved evidence case."""
    run_dir, state_path, state = _load_run(run_dir)
    if not (explicitly_authorized or disputed_state or platform_stop):
        raise ValueError("默认不得保存截图；仅限用户明确要求、争议状态或平台级停止证据。")
    if platform_stop and state.get("phase") != "platform_stopped":
        raise ValueError("只有已记录 Platform-Level Stop 的运行可以按 platform_stop 保存证据。")
    reason = reason.strip()
    if not reason:
        raise ValueError("截图证据必须说明保存原因。")
    source = Path(screenshot_path).expanduser().resolve()
    if not source.is_file() or source.suffix.casefold() not in ALLOWED_SUFFIXES:
        raise ValueError("截图证据必须是存在的 PNG 或 JPEG 文件。")
    if source.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("截图证据超过 20 MiB，拒绝保存。")
    signature = source.read_bytes()[:12]
    if not (signature.startswith(b"\x89PNG\r\n\x1a\n") or signature.startswith(b"\xff\xd8\xff")):
        raise ValueError("截图文件内容不是可识别的 PNG 或 JPEG。")
    if candidate_id and candidate_id not in set(state.get("candidate_ids") or []):
        raise ValueError("截图关联的 candidate_id 不属于当前运行。")
    timestamp = _aware(now).isoformat()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    destination = evidence_dir / f"{timestamp.replace(':', '').replace('+', '_')}_{digest[:12]}{source.suffix.casefold()}"
    shutil.copy2(source, destination)
    metadata = {
        "screenshot_path": str(destination),
        "sha256": digest,
        "reason": reason,
        "candidate_id": candidate_id or None,
        "basis": (
            "platform_stop"
            if platform_stop
            else "disputed_state"
            if disputed_state
            else "explicit_user_authorization"
        ),
        "recorded_at": timestamp,
        "authentication_secrets_reviewed": False,
    }
    metadata_path = destination.with_suffix(destination.suffix + ".json")
    _write_json_atomic(metadata_path, metadata)
    state.setdefault("evidence", []).append(metadata)
    state.setdefault("files", {}).setdefault("browser_evidence", []).extend([str(destination), str(metadata_path)])
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"保存浏览器截图证据：{reason}；sha256={digest}。")
    return LinkedInSearchStepResult(
        str(run_dir),
        str(state_path),
        state["status"],
        state["phase"],
        (str(destination), str(metadata_path), str(state_path)),
        "截图证据已按例外规则保存并绑定原因。请人工确认画面未包含不必要的会话或个人数据。",
    )


def _aware(now: datetime | None) -> datetime:
    value = now or datetime.now().astimezone()
    return value.astimezone() if value.tzinfo is None else value
