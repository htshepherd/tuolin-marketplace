from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .agent_interface import refresh_agent_interface_after_write
from .card_validator import parse_frontmatter, validate_card_file
from .video_audio_policy import refresh_video_profile_audio
from .video_profile_maintenance import register_video_cache_entry
from .video_test_evidence import validate_test_video_profile_metadata
from ..shared.project_layout import ProjectPaths


InterfaceVerifier = Callable[[ProjectPaths, dict], None]


@dataclass(frozen=True)
class VideoProfilePublication:
    status: str
    profile_id: str
    profile_revision: str
    content_digest: str
    interface_revision: str
    markdown_path: Path
    structured_path: Path


@dataclass(frozen=True)
class VideoProfileRevocation:
    status: str
    profile_id: str
    profile_revision: str
    interface_revision: str
    affected_run_count: int
    structured_path: Path


def exclude_published_video_profile_use(
    paths: ProjectPaths,
    profile_id: str,
    *,
    segment_ids: list[str] | tuple[str, ...] = (),
    capabilities: list[str] | tuple[str, ...] = (),
    reason: str,
    excluded_by: str,
) -> VideoProfilePublication:
    requested_segments = {
        str(item).strip() for item in segment_ids if str(item).strip()
    }
    requested_capabilities = {
        str(item).strip() for item in capabilities if str(item).strip()
    }
    if not requested_segments and not requested_capabilities:
        raise ValueError(
            "profile exclusion requires segment IDs or capabilities"
        )
    current = json.loads(
        _formal_profile_path(paths, profile_id).read_text(encoding="utf-8")
    )
    known_segments = {
        str(item.get("segment_id"))
        for item in current.get("key_segments", [])
    }
    unknown_segments = sorted(requested_segments - known_segments)
    if unknown_segments:
        raise ValueError(
            "profile exclusion references unknown segments: "
            + ", ".join(unknown_segments)
        )
    known_capabilities = {
        str(item) for item in current.get("use_capabilities", [])
    }
    unknown_capabilities = sorted(
        requested_capabilities - known_capabilities
    )
    if unknown_capabilities:
        raise ValueError(
            "profile exclusion references unknown capabilities: "
            + ", ".join(unknown_capabilities)
        )
    excluded_at = datetime.now(timezone.utc).isoformat()
    key_segments = deepcopy(current.get("key_segments", []))
    for segment in key_segments:
        if segment.get("segment_id") not in requested_segments:
            continue
        segment["use_exclusion"] = {
            "status": "excluded",
            "reason": reason.strip(),
            "excluded_by": excluded_by.strip(),
            "excluded_at": excluded_at,
        }
    remaining_capabilities = [
        item
        for item in current.get("use_capabilities", [])
        if item not in requested_capabilities
    ]
    if key_segments and all(
        segment.get("use_exclusion", {}).get("status") == "excluded"
        for segment in key_segments
    ):
        remaining_capabilities = []
    exclusions = list(current.get("exclusions") or [])
    exclusions.append(
        {
            "type": "video_use_exclusion",
            "segment_ids": sorted(requested_segments),
            "capabilities": sorted(requested_capabilities),
            "reason": reason.strip(),
            "excluded_by": excluded_by.strip(),
            "excluded_at": excluded_at,
        }
    )
    publication = amend_published_video_profile(
        paths,
        profile_id,
        changes={
            "key_segments": key_segments,
            "use_capabilities": remaining_capabilities,
            "exclusions": exclusions,
        },
        amendment_reason=reason,
        amended_by=excluded_by,
    )
    _remove_excluded_segments_from_run_authorizations(
        paths,
        profile_id=profile_id,
        segment_ids=requested_segments,
    )
    return publication


def revoke_published_video_profile(
    paths: ProjectPaths,
    profile_id: str,
    *,
    reason: str,
    revoked_by: str,
) -> VideoProfileRevocation:
    normalized_reason = reason.strip()
    reviewer = revoked_by.strip()
    if not normalized_reason or not reviewer:
        raise ValueError("profile revocation requires reason and reviewer")
    formal_path = _formal_profile_path(paths, profile_id)
    profile = json.loads(formal_path.read_text(encoding="utf-8"))
    profile["processing_state"] = "revoked"
    profile["use_capabilities"] = []
    profile["revocation"] = {
        "status": "revoked",
        "reason": normalized_reason,
        "revoked_by": reviewer,
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "prior_profile_revision": profile["profile_revision"],
    }
    exclusions = list(profile.get("exclusions") or [])
    exclusions.append(f"revoked:{normalized_reason}")
    profile["exclusions"] = exclusions
    _assign_profile_revision(profile)
    staged_path = _stage_profile_republication(
        paths,
        profile,
        prefix="revocation",
    )
    publication = publish_staged_video_profile(staged_path, paths)
    affected_runs = _revoke_existing_run_authorizations(
        paths,
        profile_id=profile_id,
        asset_id=str(profile["video_asset_id"]),
        reason=normalized_reason,
    )
    return VideoProfileRevocation(
        status="revoked",
        profile_id=profile_id,
        profile_revision=publication.profile_revision,
        interface_revision=publication.interface_revision,
        affected_run_count=affected_runs,
        structured_path=publication.structured_path,
    )


def amend_published_video_profile(
    paths: ProjectPaths,
    profile_id: str,
    *,
    changes: dict,
    amendment_reason: str,
    amended_by: str,
) -> VideoProfilePublication:
    reason = amendment_reason.strip()
    reviewer = amended_by.strip()
    if not reason or not reviewer:
        raise ValueError("profile amendment requires reason and reviewer")
    allowed_fields = {
        "title",
        "summary",
        "product_visibility",
        "key_segments",
        "anchor_moments",
        "representative_frames",
        "use_capabilities",
        "audio_observations",
        "transcript_detail",
        "source_audio_use_policy",
        "observation_confidence",
        "risk_summary",
        "evidence_links",
        "analysis_completeness",
        "analysis_provenance",
        "exclusions",
        "test_context",
        "test_risk_review",
    }
    unsupported = sorted(set(changes) - allowed_fields)
    if unsupported:
        raise ValueError(
            "profile amendment contains protected fields: "
            + ", ".join(unsupported)
        )
    formal_path = _formal_profile_path(paths, profile_id)
    current = json.loads(formal_path.read_text(encoding="utf-8"))
    amended = deepcopy(current)
    for field, value in changes.items():
        amended[field] = deepcopy(value)
    amended.setdefault("amendments", []).append(
        {
            "reason": reason,
            "amended_by": reviewer,
            "amended_at": datetime.now(timezone.utc).isoformat(),
            "prior_profile_revision": current["profile_revision"],
            "changed_fields": sorted(changes),
        }
    )
    _assign_profile_revision(amended)
    staged_path = _stage_profile_republication(
        paths,
        amended,
        prefix="amendment",
    )
    return publish_staged_video_profile(staged_path, paths)


def refresh_published_video_profile_audio(
    paths: ProjectPaths,
    profile_id: str,
    *,
    transcript: dict,
    audio_observations: list[str] | tuple[str, ...],
    source_audio_use_policy: str,
) -> VideoProfilePublication:
    parts = profile_id.split("/")
    if (
        len(parts) != 3
        or parts[0] != "video_profile"
        or not re.fullmatch(r"[a-z0-9_-]+", parts[1])
        or not re.fullmatch(r"video_asset_[0-9a-f]{32}", parts[2])
    ):
        raise ValueError("invalid formal video profile ID")
    product_slug, asset_id = parts[1], parts[2]
    formal_path = (
        paths.knowledge_dir
        / "视频档案"
        / product_slug
        / f"{asset_id}.json"
    )
    if not formal_path.is_file():
        raise FileNotFoundError(formal_path)
    current = json.loads(formal_path.read_text(encoding="utf-8"))
    if current.get("profile_id") != profile_id:
        raise ValueError("formal video profile identity mismatch")
    refreshed = refresh_video_profile_audio(
        current,
        transcript=transcript,
        audio_observations=audio_observations,
        source_audio_use_policy=source_audio_use_policy,
    )
    staging_dir = (
        paths.generated_dir
        / "staging"
        / "video-profiles"
        / f"audio-refresh-{refreshed['profile_revision'].removeprefix('video_profile_rev_')}"
        / product_slug
    )
    staged_json = staging_dir / f"{asset_id}.json"
    staged_markdown = staging_dir / f"{asset_id}.md"
    staging_dir.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(staged_json, refreshed)
    staged_markdown.write_text(
        "\n".join(
            [
                "---",
                'type: "video_profile_draft"',
                f'id: "{refreshed["profile_id"]}"',
                f'profile_revision: "{refreshed["profile_revision"]}"',
                f'content_digest: "{refreshed["content_digest"]}"',
                "---",
                "",
                "# 音频转录增量更新",
                "",
                "本暂存稿只更新音频理解、转录和音频 provenance。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return publish_staged_video_profile(staged_json, paths)


def _formal_profile_path(paths: ProjectPaths, profile_id: str) -> Path:
    parts = profile_id.split("/")
    if (
        len(parts) != 3
        or parts[0] != "video_profile"
        or not re.fullmatch(r"[a-z0-9_-]+", parts[1])
        or not re.fullmatch(r"video_asset_[0-9a-f]{32}", parts[2])
    ):
        raise ValueError("invalid formal video profile ID")
    path = paths.knowledge_dir / "视频档案" / parts[1] / f"{parts[2]}.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _assign_profile_revision(profile: dict) -> None:
    profile.pop("profile_revision", None)
    profile.pop("content_digest", None)
    canonical = json.dumps(
        profile,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    profile["content_digest"] = f"sha256:{digest}"
    profile["profile_revision"] = f"video_profile_rev_{digest[:16]}"


def _stage_profile_republication(
    paths: ProjectPaths,
    profile: dict,
    *,
    prefix: str,
) -> Path:
    product_slug = str(profile["product_id"]).split("/", 1)[1]
    asset_id = str(profile["video_asset_id"])
    revision_suffix = str(profile["profile_revision"]).removeprefix(
        "video_profile_rev_"
    )
    staging_dir = (
        paths.generated_dir
        / "staging"
        / "video-profiles"
        / f"{prefix}-{revision_suffix}"
        / product_slug
    )
    staged_json = staging_dir / f"{asset_id}.json"
    staged_markdown = staging_dir / f"{asset_id}.md"
    staging_dir.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(staged_json, profile)
    staged_markdown.write_text(
        "\n".join(
            [
                "---",
                'type: "video_profile_draft"',
                f'id: "{profile["profile_id"]}"',
                f'profile_revision: "{profile["profile_revision"]}"',
                f'content_digest: "{profile["content_digest"]}"',
                "---",
                "",
                str(profile.get("summary") or ""),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return staged_json


def publish_staged_video_profile(
    staged_structured_path: Path,
    paths: ProjectPaths,
    *,
    interface_verifier: InterfaceVerifier | None = None,
) -> VideoProfilePublication:
    staged_json = staged_structured_path.expanduser().resolve()
    staging_root = (paths.generated_dir / "staging" / "video-profiles").resolve()
    try:
        staged_json.relative_to(staging_root)
    except ValueError as exc:
        raise ValueError("video profile publication requires a staged profile") from exc
    if not staged_json.is_file() or staged_json.suffix.lower() != ".json":
        raise FileNotFoundError(staged_json)
    staged_markdown = staged_json.with_suffix(".md")
    if not staged_markdown.is_file():
        raise FileNotFoundError(staged_markdown)
    profile = json.loads(staged_json.read_text(encoding="utf-8"))
    _validate_staged_profile(profile, staged_json, paths)
    _validate_staged_markdown(staged_markdown, profile)

    product_slug = str(profile["product_id"]).split("/", 1)[1]
    asset_id = str(profile["video_asset_id"])
    formal_dir = paths.knowledge_dir / "视频档案" / product_slug
    markdown_path = formal_dir / f"{asset_id}.md"
    structured_path = formal_dir / f"{asset_id}.json"
    formal_dir.mkdir(parents=True, exist_ok=True)
    inspection_report_path = _profile_inspection_report_path(
        paths,
        profile,
    )

    with tempfile.TemporaryDirectory(
        prefix="video-profile-publication-",
        dir=str(paths.project_dir),
    ) as backup_tmp:
        backup_root = Path(backup_tmp)
        interface_dir = paths.generated_dir / "agent-interface"
        indexes_dir = paths.generated_dir / "indexes"
        media_index_dir = (
            paths.generated_dir / "cache" / "video-profile-interface"
        )
        maintenance_dir = (
            paths.generated_dir / "cache" / "video-profile-maintenance"
        )
        _snapshot_directory(interface_dir, backup_root / "agent-interface")
        _snapshot_directory(indexes_dir, backup_root / "indexes")
        _snapshot_directory(
            media_index_dir,
            backup_root / "video-profile-interface-cache",
        )
        _snapshot_directory(
            maintenance_dir,
            backup_root / "video-profile-maintenance-cache",
        )
        prior_markdown = markdown_path.read_bytes() if markdown_path.is_file() else None
        prior_structured = structured_path.read_bytes() if structured_path.is_file() else None
        prior_inspection = (
            inspection_report_path.read_bytes()
            if inspection_report_path is not None
            and inspection_report_path.is_file()
            else None
        )
        try:
            _write_pair(
                markdown_path,
                _render_formal_markdown(profile),
                structured_path,
                profile,
            )
            validation = validate_card_file(markdown_path)
            if not validation.valid:
                raise ValueError(
                    "formal video profile validation failed: "
                    + "; ".join(validation.errors)
                )
            refreshed = refresh_agent_interface_after_write(
                paths,
                action="publish_video_profile",
                expected_card_ids=[str(profile["profile_id"])],
            )
            _verify_published_interface(paths, profile)
            if interface_verifier is not None:
                interface_verifier(paths, profile)
            _mark_profile_inspection_published(
                paths,
                profile,
                report_path=inspection_report_path,
            )
        except Exception:
            _restore_file(markdown_path, prior_markdown)
            _restore_file(structured_path, prior_structured)
            _restore_directory(
                backup_root / "agent-interface",
                interface_dir,
            )
            _restore_directory(
                backup_root / "indexes",
                indexes_dir,
            )
            _restore_directory(
                backup_root / "video-profile-interface-cache",
                media_index_dir,
            )
            _restore_directory(
                backup_root / "video-profile-maintenance-cache",
                maintenance_dir,
            )
            if inspection_report_path is not None:
                _restore_file(
                    inspection_report_path,
                    prior_inspection,
                )
            raise

    refresh = refreshed["agent_interface_refresh"]
    return VideoProfilePublication(
        status="published",
        profile_id=str(profile["profile_id"]),
        profile_revision=str(profile["profile_revision"]),
        content_digest=str(profile["content_digest"]),
        interface_revision=str(refresh["interface_revision"]),
        markdown_path=markdown_path,
        structured_path=structured_path,
    )


def _mark_profile_inspection_published(
    paths: ProjectPaths,
    profile: dict,
    *,
    report_path: Path | None,
) -> None:
    if report_path is None:
        return
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["formal_profile_published"] = True
    report["published_profile_id"] = profile["profile_id"]
    report["published_profile_revision"] = profile["profile_revision"]
    report["published_at"] = datetime.now(timezone.utc).isoformat()
    _write_json_atomic(report_path, report)
    register_video_cache_entry(
        paths,
        report_path,
        kind="inspection_report",
        state="complete",
        last_used_at=report["published_at"],
        profile_revision=str(profile["profile_revision"]),
    )


def _profile_inspection_report_path(
    paths: ProjectPaths,
    profile: dict,
) -> Path | None:
    provenance = dict(profile.get("analysis_provenance") or {})
    report_ref = str(provenance.get("inspection_report_ref") or "").strip()
    if not report_ref:
        return None
    report_path = (paths.generated_dir / report_ref).resolve()
    inspection_root = (
        paths.generated_dir / "cache" / "video-tracer-inspection"
    ).resolve()
    try:
        report_path.relative_to(inspection_root)
    except ValueError as exc:
        raise ValueError(
            "published profile inspection report escapes tracer cache"
        ) from exc
    return report_path


def _validate_staged_profile(
    profile: dict,
    staged_path: Path,
    paths: ProjectPaths,
) -> None:
    required = {
        "profile_id",
        "video_asset_id",
        "product_id",
        "profile_revision",
        "content_digest",
        "source_revision",
        "source_classification",
        "observed_classifications",
        "title",
        "summary",
        "product_visibility",
        "key_segments",
        "representative_frames",
        "use_capabilities",
        "risk_summary",
        "processing_state",
    }
    missing = sorted(required - set(profile))
    if missing:
        raise ValueError(
            "staged video profile missing fields: " + ", ".join(missing)
        )
    asset_id = str(profile["video_asset_id"])
    if not re.fullmatch(r"video_asset_[0-9a-f]{32}", asset_id):
        raise ValueError("invalid staged video asset ID")
    if staged_path.stem != asset_id:
        raise ValueError("staged video profile path must use video_asset_id")
    product_id = str(profile["product_id"])
    if not re.fullmatch(r"product/[a-z0-9_-]+", product_id):
        raise ValueError("invalid staged video product ID")
    expected_id = f"video_profile/{product_id.split('/', 1)[1]}/{asset_id}"
    if profile["profile_id"] != expected_id:
        raise ValueError("staged video profile identity does not match product and asset")
    if not re.fullmatch(r"video_profile_rev_[0-9a-f]{16}", str(profile["profile_revision"])):
        raise ValueError("invalid staged video profile revision")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(profile["content_digest"])):
        raise ValueError("invalid staged video profile content digest")
    validate_test_video_profile_metadata(
        profile,
        require_human_review=True,
    )
    for frame in profile.get("representative_frames", []):
        generated_ref = str(frame.get("generated_ref") or "")
        media_path = (paths.generated_dir / generated_ref).resolve()
        try:
            media_path.relative_to(paths.generated_dir.resolve())
        except ValueError as exc:
            raise ValueError("staged representative frame escapes generated_dir") from exc
        if not media_path.is_file():
            raise FileNotFoundError(media_path)


def _validate_staged_markdown(path: Path, profile: dict) -> None:
    frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    for field in ("id", "profile_revision", "content_digest"):
        expected_field = "profile_id" if field == "id" else field
        if frontmatter.get(field) != profile.get(expected_field):
            raise ValueError(f"staged Markdown and JSON disagree on {field}")


def _render_formal_markdown(profile: dict) -> str:
    now = datetime.now(timezone.utc).isoformat()
    raw_partition = "raw/" + "/".join(
        str(item).strip("/")
        for item in profile.get("source_classification", [])
        if str(item).strip("/")
    ) + "/"
    evidence_refs = [
        str(item)
        for item in profile.get("evidence_links", [])
        if isinstance(item, str) and item.strip()
    ]
    tags = ["视频档案", *[str(item) for item in profile.get("observed_classifications", [])]]
    lines = [
        "---",
        "card_template_version: video-profile-card-v1",
        "type: video_profile",
        f"id: {profile['profile_id']}",
        f"title: {profile['title']}",
        "aliases: []",
        "status: review_required",
        "usage_scope: review_before_external",
        "raw_partitions:",
        f"  - {raw_partition}",
        "tags:",
        *[f"  - {item}" for item in tags],
        f"updated_at: {now}",
        f"last_reviewed_at: {now}",
        "evidence_refs:" if evidence_refs else "evidence_refs: []",
        *[f"  - {item}" for item in evidence_refs],
        "review_refs: []",
        f"video_asset_id: {profile['video_asset_id']}",
        f"product_id: {profile['product_id']}",
        f"profile_revision: {profile['profile_revision']}",
        f"content_digest: {profile['content_digest']}",
        f"processing_state: {profile['processing_state']}",
        "use_capabilities:",
        *[f"  - {item}" for item in profile.get("use_capabilities", [])],
        "---",
        "",
        "# 视频讲了什么",
        "",
        str(profile["summary"]),
        "",
        "## 关键片段",
        "",
    ]
    for segment in profile.get("key_segments", []):
        lines.extend(
            [
                f"### {segment['segment_id']}",
                "",
                f"- 时间：{float(segment['start_seconds']):.3f}s–{float(segment['end_seconds']):.3f}s",
                f"- 画面描述：{segment.get('description', '')}",
                f"- 动作：{segment.get('action', '')}",
                f"- 产品可见度：{segment.get('product_visibility', '')}",
                f"- 复用模式：{segment.get('reuse_mode', '')}",
                f"- 编辑适用性：{segment.get('editing_suitability', '')}",
                "",
            ]
        )
    lines.extend(["## 代表帧", ""])
    for frame in profile.get("representative_frames", []):
        lines.append(
            f"- {float(frame['timestamp_seconds']):.3f}s：{frame.get('description', '')}"
        )
    lines.extend(["", "## 风险与使用边界", ""])
    lines.extend(f"- {item}" for item in profile.get("risk_summary", []))
    return "\n".join(lines) + "\n"


def _write_pair(
    markdown_path: Path,
    markdown_text: str,
    structured_path: Path,
    profile: dict,
) -> None:
    markdown_tmp = markdown_path.with_suffix(".md.tmp")
    structured_tmp = structured_path.with_suffix(".json.tmp")
    markdown_tmp.write_text(markdown_text, encoding="utf-8")
    structured_tmp.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    structured_tmp.replace(structured_path)
    markdown_tmp.replace(markdown_path)


def _verify_published_interface(paths: ProjectPaths, profile: dict) -> None:
    manifest = json.loads(
        (paths.generated_dir / "agent-interface" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    video_manifest = json.loads(
        (
            paths.generated_dir
            / "agent-interface"
            / "video-profiles"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    if video_manifest.get("interface_revision") != manifest.get("interface_revision"):
        raise RuntimeError("video profile interface revision was not activated")
    catalog = json.loads(
        (
            paths.generated_dir
            / "agent-interface"
            / "video-profiles"
            / "catalog.json"
        ).read_text(encoding="utf-8")
    )
    entry = next(
        (
            item
            for item in catalog
            if item.get("profile_id") == profile.get("profile_id")
        ),
        None,
    )
    detail_path = (
        paths.generated_dir
        / "agent-interface"
        / "video-profiles"
        / "details"
        / f"{profile['video_asset_id']}.json"
    )
    if profile.get("processing_state") == "revoked":
        if entry is not None or detail_path.exists():
            raise RuntimeError(
                "revoked video profile remains available in Agent interface"
            )
        return
    if entry is None:
        raise RuntimeError("published video profile is missing from catalog")
    if entry.get("profile_revision") != profile.get("profile_revision"):
        raise RuntimeError("published video profile catalog revision mismatch")
    detail = json.loads(detail_path.read_text(encoding="utf-8"))
    if detail.get("content_digest") != profile.get("content_digest"):
        raise RuntimeError("published video profile detail digest mismatch")
    if len(detail.get("representative_frames", [])) != len(
        profile.get("representative_frames", [])
    ):
        raise RuntimeError("published video profile media references are incomplete")


def _revoke_existing_run_authorizations(
    paths: ProjectPaths,
    *,
    profile_id: str,
    asset_id: str,
    reason: str,
) -> int:
    root = paths.generated_dir / "reports" / "video-creation"
    if not root.is_dir():
        return 0
    affected = 0
    revoked_at = datetime.now(timezone.utc).isoformat()
    for authorization_path in root.rglob(
        "video_profile_authorizations.json"
    ):
        authorization = json.loads(
            authorization_path.read_text(encoding="utf-8")
        )
        changed = False
        for item in authorization.get("authorized_profiles", []):
            if (
                item.get("profile_id") != profile_id
                and item.get("video_asset_id") != asset_id
            ):
                continue
            if not item.get("revoked"):
                affected += 1
            item["revoked"] = True
            item["revoked_at"] = revoked_at
            item["revocation_reason"] = reason
            changed = True
        if changed:
            _write_json_atomic(authorization_path, authorization)
    return affected


def _remove_excluded_segments_from_run_authorizations(
    paths: ProjectPaths,
    *,
    profile_id: str,
    segment_ids: set[str],
) -> None:
    root = paths.generated_dir / "reports" / "video-creation"
    if not root.is_dir():
        return
    for authorization_path in root.rglob(
        "video_profile_authorizations.json"
    ):
        authorization = json.loads(
            authorization_path.read_text(encoding="utf-8")
        )
        changed = False
        for item in authorization.get("authorized_profiles", []):
            if item.get("profile_id") != profile_id:
                continue
            prior_segments = list(item.get("segments", []))
            item["segments"] = [
                segment
                for segment in prior_segments
                if segment.get("segment_id") not in segment_ids
            ]
            changed = changed or item["segments"] != prior_segments
        if changed:
            _write_json_atomic(authorization_path, authorization)


def _snapshot_directory(source: Path, backup: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, backup)


def _restore_directory(backup: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if backup.is_dir():
        shutil.copytree(backup, target)


def _restore_file(path: Path, prior_bytes: bytes | None) -> None:
    if prior_bytes is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(prior_bytes)


def _write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
