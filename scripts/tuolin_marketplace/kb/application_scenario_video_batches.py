from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import hashlib
from pathlib import Path

from ..shared.project_layout import ProjectPaths
from .video_profile_batches import (
    BatchProcessor,
    VideoProfileBatchResult,
    process_video_profile_batch,
)
from .video_profiles import (
    FrameDecoder,
    VIDEO_SUFFIXES,
    inspect_video_candidate,
)


@dataclass(frozen=True)
class ApplicationVideoClassification:
    source_application_scenario: str
    source_descendant_context: tuple[str, ...]
    source_path_context: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioAcceptanceSample:
    strategy: str
    selected_asset_ids: tuple[str, ...]
    total_count: int


@dataclass(frozen=True)
class ApplicationScenarioBatch:
    source_application_scenario: str
    batch_result: VideoProfileBatchResult
    acceptance_sample: ScenarioAcceptanceSample


@dataclass(frozen=True)
class ApplicationScenarioBatchesResult:
    status: str
    batch_id: str
    scenarios: tuple[ApplicationScenarioBatch, ...]


def classify_application_video(
    video_path: Path,
    application_root: Path,
    paths: ProjectPaths,
) -> ApplicationVideoClassification:
    source = video_path.expanduser().resolve()
    root = application_root.expanduser().resolve()
    try:
        root.relative_to(paths.raw_dir.resolve())
    except ValueError as exc:
        raise ValueError("application scenario root must be under raw_dir") from exc
    try:
        relative = source.relative_to(root)
    except ValueError as exc:
        raise ValueError("application video must be under the fixed application root") from exc
    if not source.is_file() or source.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError("application video must be a supported video file")
    if len(relative.parts) < 2:
        raise ValueError(
            "application videos must be placed under a first-level scenario folder"
        )
    directory_parts = tuple(relative.parts[:-1])
    return ApplicationVideoClassification(
        source_application_scenario=directory_parts[0],
        source_descendant_context=directory_parts[1:],
        source_path_context=directory_parts,
    )


def combine_application_classification(
    source: ApplicationVideoClassification,
    *,
    observed_application_scenarios: list[str] | tuple[str, ...],
) -> dict:
    observed = [
        str(item).strip()
        for item in observed_application_scenarios
        if str(item).strip()
    ]
    if not observed:
        state = "visual_observation_missing"
    elif source.source_application_scenario in observed:
        state = "source_and_visual_aligned"
    else:
        state = "conflict_review_required"
    return {
        "source_application_scenario": source.source_application_scenario,
        "source_descendant_context": list(source.source_descendant_context),
        "source_path_context": list(source.source_path_context),
        "observed_application_scenarios": observed,
        "classification_state": state,
        "source_scenario_is_visual_fact": False,
    }


def plan_scenario_acceptance_sample(
    items: list[dict] | tuple[dict, ...],
    *,
    first_batch: bool,
) -> ScenarioAcceptanceSample:
    values = list(items)
    if not values:
        return ScenarioAcceptanceSample(
            strategy="empty",
            selected_asset_ids=(),
            total_count=0,
        )
    if first_batch and len(values) <= 10:
        return ScenarioAcceptanceSample(
            strategy="first_batch_full",
            selected_asset_ids=tuple(str(item["asset_id"]) for item in values),
            total_count=len(values),
        )
    if first_batch:
        target = 5
        strategy = "first_batch_risk_based"
    else:
        target = max(3, math.ceil(len(values) * 0.10))
        strategy = "stable_increment_ten_percent"
    selected: list[str] = []

    def add(item: dict | None) -> None:
        if item is None:
            return
        asset_id = str(item.get("asset_id") or "")
        if asset_id and asset_id not in selected:
            selected.append(asset_id)

    add(next((item for item in values if item.get("preferred")), None))
    confidence_order = {"low": 0, "medium": 1, "high": 2}
    add(
        min(
            values,
            key=lambda item: (
                confidence_order.get(str(item.get("confidence") or ""), 3),
                str(item.get("asset_id") or ""),
            ),
        )
    )
    add(
        max(
            values,
            key=lambda item: (
                float(item.get("duration_seconds") or 0),
                str(item.get("asset_id") or ""),
            ),
        )
    )
    add(next((item for item in values if item.get("has_audio")), None))
    for item in sorted(values, key=_scenario_sample_risk_key):
        add(item)
        if len(selected) >= target:
            break
    return ScenarioAcceptanceSample(
        strategy=strategy,
        selected_asset_ids=tuple(selected),
        total_count=len(values),
    )


def process_application_scenario_batches(
    application_root: Path,
    paths: ProjectPaths,
    *,
    product_id: str,
    batch_id: str,
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
    codex_visual_review_available: bool = True,
    optional_asr_available: bool = False,
    runner=None,
    frame_decoder: FrameDecoder | None = None,
    processor: BatchProcessor | None = None,
) -> ApplicationScenarioBatchesResult:
    root = application_root.expanduser().resolve()
    try:
        root.relative_to(paths.raw_dir.resolve())
    except ValueError as exc:
        raise ValueError("application scenario root must be under raw_dir") from exc
    if not root.is_dir():
        raise FileNotFoundError(root)
    scenario_dirs = sorted(
        (
            item
            for item in root.iterdir()
            if item.is_dir()
            and any(
                path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
                for path in item.rglob("*")
            )
        ),
        key=lambda item: item.name,
    )
    scenario_results: list[ApplicationScenarioBatch] = []
    for scenario_dir in scenario_dirs:
        scenario_hash = hashlib.sha256(
            scenario_dir.name.encode("utf-8")
        ).hexdigest()[:12]
        kwargs = {}
        if runner is not None:
            kwargs["runner"] = runner
        scenario_processor = processor or _application_video_processor
        batch_result = process_video_profile_batch(
            scenario_dir,
            paths,
            product_id=product_id,
            batch_id=f"{batch_id}--scenario_{scenario_hash}",
            ffprobe_path=ffprobe_path,
            ffmpeg_path=ffmpeg_path,
            codex_visual_review_available=codex_visual_review_available,
            optional_asr_available=optional_asr_available,
            frame_decoder=frame_decoder,
            processor=scenario_processor,
            **kwargs,
        )
        manifest = json.loads(
            batch_result.manifest_path.read_text(encoding="utf-8")
        )
        sample_items = [
            {
                "asset_id": item["asset_id"],
                "preferred": False,
                "confidence": item.get("acceptance_facts", {}).get(
                    "confidence",
                    "low" if item.get("status") != "valid" else "medium",
                ),
                "duration_seconds": item.get("acceptance_facts", {}).get(
                    "duration_seconds",
                    0,
                ),
                "has_audio": item.get("acceptance_facts", {}).get(
                    "has_audio",
                    False,
                ),
            }
            for item in manifest.get("items", [])
        ]
        prior_scope = next(
            (
                item
                for item in read_application_scenario_scopes(paths, product_id)
                if item.get("source_application_scenario") == scenario_dir.name
                and item.get("status") == "verified"
            ),
            None,
        )
        acceptance_sample = plan_scenario_acceptance_sample(
            sample_items,
            first_batch=prior_scope is None,
        )
        profile_ids = [
            f"video_profile/{product_id.split('/', 1)[1]}/{item['asset_id']}"
            for item in manifest.get("items", [])
            if item.get("status") == "valid"
        ]
        record_application_scenario_scope(
            paths,
            product_id=product_id,
            source_application_scenario=scenario_dir.name,
            profile_ids=profile_ids,
            status="pending_acceptance",
            acceptance_sample=acceptance_sample,
        )
        scenario_results.append(
            ApplicationScenarioBatch(
                source_application_scenario=scenario_dir.name,
                batch_result=batch_result,
                acceptance_sample=acceptance_sample,
            )
        )
    blocked = any(
        item.batch_result.status.startswith("blocked")
        for item in scenario_results
    )
    return ApplicationScenarioBatchesResult(
        status=(
            "blocked_scenario_batches"
            if blocked
            else "awaiting_scenario_acceptance"
        ),
        batch_id=batch_id,
        scenarios=tuple(scenario_results),
    )


def _application_video_processor(
    video: Path,
    _asset,
    context: dict,
) -> dict:
    source_classification = tuple(
        video.parent.resolve().relative_to(
            context["paths"].raw_dir.resolve()
        ).parts
    )
    inspection = inspect_video_candidate(
        video,
        context["paths"],
        product_id=context["product_id"],
        source_classification=source_classification,
        ffprobe_path=context["ffprobe_path"],
        ffmpeg_path=context["ffmpeg_path"],
        runner=context["runner"],
        frame_decoder=context.get("frame_decoder"),
    )
    return {
        "status": "valid",
        "report_path": str(inspection.report_path),
        "acceptance_facts": {
            "duration_seconds": inspection.media_facts.duration_seconds,
            "has_audio": inspection.media_facts.has_audio,
            "confidence": (
                "medium"
                if inspection.status == "awaiting_codex_review"
                else "low"
            ),
        },
    }


def _scenario_sample_risk_key(item: dict) -> tuple:
    confidence_order = {"low": 0, "medium": 1, "high": 2}
    return (
        0 if item.get("preferred") else 1,
        confidence_order.get(str(item.get("confidence") or ""), 3),
        0 if item.get("has_audio") else 1,
        -float(item.get("duration_seconds") or 0),
        str(item.get("asset_id") or ""),
    )


def record_application_scenario_scope(
    paths: ProjectPaths,
    *,
    product_id: str,
    source_application_scenario: str,
    profile_ids: list[str] | tuple[str, ...],
    status: str,
    acceptance_sample: ScenarioAcceptanceSample | None = None,
) -> dict:
    if status not in {"pending_acceptance", "verified", "revoked"}:
        raise ValueError("invalid application scenario scope status")
    scenario = source_application_scenario.strip()
    if not scenario:
        raise ValueError("source application scenario is required")
    ledger = _read_scope_ledger(paths, product_id)
    scopes = ledger["scopes"]
    existing = next(
        (
            item
            for item in scopes
            if item.get("source_application_scenario") == scenario
        ),
        None,
    )
    entry = {
        "source_application_scenario": scenario,
        "status": status,
        "profile_ids": list(dict.fromkeys(str(item) for item in profile_ids)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if acceptance_sample is not None:
        entry["acceptance_sample"] = {
            "strategy": acceptance_sample.strategy,
            "selected_asset_ids": list(
                acceptance_sample.selected_asset_ids
            ),
            "total_count": acceptance_sample.total_count,
        }
    if existing is None:
        scopes.append(entry)
    else:
        existing.clear()
        existing.update(entry)
    _write_scope_ledger(paths, product_id, ledger)
    return entry


def revoke_application_scenario_scope(
    paths: ProjectPaths,
    *,
    product_id: str,
    source_application_scenario: str,
    reason: str,
) -> dict:
    explanation = reason.strip()
    if not explanation:
        raise ValueError("scenario revocation requires a reason")
    ledger = _read_scope_ledger(paths, product_id)
    entry = next(
        (
            item
            for item in ledger["scopes"]
            if item.get("source_application_scenario")
            == source_application_scenario
        ),
        None,
    )
    if entry is None:
        raise KeyError(
            f"application scenario scope not found: {source_application_scenario}"
        )
    entry["status"] = "revoked"
    entry["revocation_reason"] = explanation
    entry["revoked_at"] = datetime.now(timezone.utc).isoformat()
    entry["updated_at"] = entry["revoked_at"]
    _write_scope_ledger(paths, product_id, ledger)
    return dict(entry)


def accept_application_scenario_scope(
    paths: ProjectPaths,
    *,
    product_id: str,
    source_application_scenario: str,
    accepted_asset_ids: list[str] | tuple[str, ...],
) -> dict:
    ledger = _read_scope_ledger(paths, product_id)
    entry = next(
        (
            item
            for item in ledger["scopes"]
            if item.get("source_application_scenario")
            == source_application_scenario
        ),
        None,
    )
    if entry is None:
        raise KeyError(
            f"application scenario scope not found: {source_application_scenario}"
        )
    if entry.get("status") != "pending_acceptance":
        raise ValueError("application scenario scope is not awaiting acceptance")
    sample = dict(entry.get("acceptance_sample") or {})
    required = list(sample.get("selected_asset_ids") or [])
    accepted = list(dict.fromkeys(str(item) for item in accepted_asset_ids))
    if set(accepted) != set(required) or len(accepted) != len(required):
        raise ValueError(
            "application scenario verification requires the complete acceptance sample"
        )
    timestamp = datetime.now(timezone.utc).isoformat()
    entry["status"] = "verified"
    entry["accepted_asset_ids"] = accepted
    entry["accepted_at"] = timestamp
    entry["updated_at"] = timestamp
    entry.pop("revocation_reason", None)
    entry.pop("revoked_at", None)
    _write_scope_ledger(paths, product_id, ledger)
    return dict(entry)


def read_application_scenario_scopes(
    paths: ProjectPaths,
    product_id: str,
) -> list[dict]:
    return list(_read_scope_ledger(paths, product_id)["scopes"])


def _scope_ledger_path(paths: ProjectPaths, product_id: str) -> Path:
    if "/" not in product_id:
        raise ValueError("product_id must contain a product slug")
    product_slug = product_id.split("/", 1)[1]
    return (
        paths.generated_dir
        / "staging"
        / "video-profiles"
        / "scenario-scopes"
        / product_slug
        / "scopes.json"
    )


def _read_scope_ledger(paths: ProjectPaths, product_id: str) -> dict:
    path = _scope_ledger_path(paths, product_id)
    if not path.is_file():
        return {
            "schema_version": "application-scenario-scope-ledger-v1",
            "product_id": product_id,
            "scopes": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or data.get("product_id") != product_id
        or not isinstance(data.get("scopes"), list)
    ):
        raise ValueError(f"invalid application scenario scope ledger: {path}")
    return data


def _write_scope_ledger(
    paths: ProjectPaths,
    product_id: str,
    ledger: dict,
) -> None:
    path = _scope_ledger_path(paths, product_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
