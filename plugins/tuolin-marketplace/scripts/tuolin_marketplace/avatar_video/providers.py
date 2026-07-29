from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECRET_TOKENS = ("api_key", "apikey", "token", "cookie", "authorization", "secret", "password")


def provider_input_fingerprint(provider: str, input_revision: str, settings: dict[str, Any]) -> str:
    return _digest(
        {
            "provider": provider,
            "input_revision": input_revision,
            "settings": redact_secrets(settings),
        }
    )


def find_provider_attempt(root: Path, provider: str, input_fingerprint: str) -> dict[str, Any] | None:
    for attempt in read_provider_attempts(root, provider):
        if attempt.get("input_fingerprint") == input_fingerprint and attempt.get("status") not in {"failed", "rejected"}:
            return attempt
    return None


def claim_provider_execution(
    root: Path,
    *,
    provider: str,
    input_fingerprint: str,
    authorization_id: str,
) -> bool:
    """Atomically consume one authorization/fingerprint before external I/O.

    A surviving claim with no result is treated as an uncertain submission and
    deliberately blocks blind resubmission. A newly authorized retry has a new
    authorization ID and therefore a different fingerprint/claim.
    """

    claims_dir = root / "providers" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    path = claims_dir / f"{provider}-{input_fingerprint}.json"
    payload = json.dumps(
        {
            "schema_version": "avatar-provider-execution-claim-v1",
            "provider": provider,
            "input_fingerprint": input_fingerprint,
            "authorization_id": authorization_id,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        # The claim intentionally remains: uncertain external execution must not
        # be converted into an automatic second paid submission.
        raise
    return True


def record_provider_attempt(
    root: Path,
    *,
    provider: str,
    input_revision: str,
    settings: dict[str, Any],
    authorization_id: str,
    mode: str,
    status: str,
    output: str,
    task_id: str,
    estimated_consumption: Any = None,
    actual_consumption: Any = None,
    media_probe: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    safe_settings = redact_secrets(settings)
    fingerprint = provider_input_fingerprint(provider, input_revision, safe_settings)
    existing = find_provider_attempt(root, provider, fingerprint)
    if existing is not None:
        return existing, False
    attempts = read_provider_attempts(root, provider)
    number = len(attempts) + 1
    attempt_id = f"{provider}-{number:04d}"
    attempt = {
        "schema_version": "avatar-provider-attempt-v1",
        "attempt_id": attempt_id,
        "provider": provider,
        "attempt_number": number,
        "mode": mode,
        "input_revision": input_revision,
        "input_fingerprint": fingerprint,
        "settings": safe_settings,
        "authorization_id": authorization_id,
        "external_task_id": task_id,
        "estimated_consumption": estimated_consumption,
        "actual_consumption": actual_consumption,
        "output": output,
        "media_probe": dict(media_probe or {}),
        "status": status,
        "review": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(_attempt_path(root, provider, number), attempt)
    return attempt, True


def review_provider_attempt(
    root: Path,
    provider: str,
    attempt_id: str,
    *,
    accepted: bool,
    reason: str,
) -> dict[str, Any]:
    path, attempt = _find_attempt_file(root, provider, attempt_id)
    if attempt.get("review") is not None:
        previous = bool(attempt["review"].get("accepted"))
        if previous != bool(accepted) or str(attempt["review"].get("reason") or "") != str(reason or ""):
            raise ValueError("供应商尝试的审查结果不可覆盖。")
        return attempt
    if not accepted and not str(reason).strip():
        raise ValueError("拒绝供应商结果必须记录原因。")
    attempt["review"] = {
        "accepted": bool(accepted),
        "reason": str(reason).strip(),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    attempt["status"] = "accepted" if accepted else "rejected"
    _write_json(path, attempt)
    return attempt


def transition_provider_attempt(
    root: Path,
    provider: str,
    attempt_id: str,
    *,
    status: str,
    output: str | None = None,
    actual_consumption: Any = None,
    media_probe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Advance one immutable provider attempt without changing its identity/input.

    Only execution-state fields may change. This is used for asynchronous paid
    tasks that are durably recorded as soon as the provider returns a task ID.
    """

    path, attempt = _find_attempt_file(root, provider, attempt_id)
    current = str(attempt.get("status") or "")
    allowed = {
        "submitted": {"running", "completed_pending_review", "failed"},
        "running": {"running", "completed_pending_review", "failed"},
        "completed_pending_review": {"completed_pending_review"},
    }
    if status not in allowed.get(current, set()):
        raise ValueError(f"非法供应商尝试状态迁移：{current} -> {status}")
    attempt["status"] = status
    if output is not None:
        attempt["output"] = str(output)
    if actual_consumption is not None:
        attempt["actual_consumption"] = actual_consumption
    if media_probe is not None:
        attempt["media_probe"] = dict(media_probe)
    attempt["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(path, attempt)
    return attempt


def read_provider_attempts(root: Path, provider: str | None = None) -> list[dict[str, Any]]:
    providers_root = root / "providers"
    if not providers_root.exists():
        return []
    pattern = f"{provider}-attempt-*.json" if provider else "*-attempt-*.json"
    attempts = [_read_json(path) for path in sorted(providers_root.glob(pattern))]
    attempts.sort(key=lambda item: (str(item.get("provider")), int(item.get("attempt_number") or 0)))
    return attempts


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): ("***" if any(token in str(key).casefold() for token in SECRET_TOKENS) else redact_secrets(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(value: str) -> str:
    text = str(value)
    text = re.sub(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", r"\1 ***", text)
    text = re.sub(
        r"(?i)([?&](?:api[_-]?key|token|access[_-]?token|secret|password|cookie)=)[^&#\s]+",
        r"\1***",
        text,
    )
    return text


def _attempt_path(root: Path, provider: str, number: int) -> Path:
    return root / "providers" / f"{provider}-attempt-{number:04d}.json"


def _find_attempt_file(root: Path, provider: str, attempt_id: str) -> tuple[Path, dict[str, Any]]:
    for path in sorted((root / "providers").glob(f"{provider}-attempt-*.json")):
        attempt = _read_json(path)
        if attempt.get("attempt_id") == attempt_id:
            return path, attempt
    raise KeyError(f"provider attempt not found: {attempt_id}")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
