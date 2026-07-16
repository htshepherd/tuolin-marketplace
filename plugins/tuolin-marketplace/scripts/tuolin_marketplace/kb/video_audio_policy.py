from __future__ import annotations

from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Protocol


class SpeechTranscriptionAdapter(Protocol):
    is_local: bool

    def transcribe(self, audio_path: Path) -> dict:
        ...


def transcribe_video_audio(
    audio_path: Path,
    adapter: SpeechTranscriptionAdapter,
    *,
    allow_external_upload: bool = False,
) -> dict:
    source = audio_path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if not getattr(adapter, "is_local", False) and not allow_external_upload:
        raise PermissionError(
            "external ASR upload requires explicit authorization"
        )
    output = adapter.transcribe(source)
    if not isinstance(output, dict):
        raise ValueError("speech transcription adapter must return an object")
    required = {
        "language",
        "segments",
        "unrecognized_ranges",
        "tool",
        "model_version",
    }
    missing = sorted(required - set(output))
    if missing:
        raise ValueError(
            "speech transcription output missing fields: "
            + ", ".join(missing)
        )
    segments = []
    for item in output["segments"]:
        start = float(item["start_seconds"])
        end = float(item["end_seconds"])
        if start < 0 or end <= start:
            raise ValueError("transcript segment has an invalid time range")
        segments.append(
            {
                "start_seconds": start,
                "end_seconds": end,
                "text": str(item.get("text") or ""),
                "confidence": float(item.get("confidence", 0)),
                "speaker": item.get("speaker"),
            }
        )
    unrecognized = []
    for item in output["unrecognized_ranges"]:
        start = float(item["start_seconds"])
        end = float(item["end_seconds"])
        if start < 0 or end <= start:
            raise ValueError("unrecognized audio range is invalid")
        unrecognized.append(
            {"start_seconds": start, "end_seconds": end}
        )
    return {
        "status": "available",
        "language": str(output["language"]),
        "segments": segments,
        "unrecognized_ranges": unrecognized,
        "tool": str(output["tool"]),
        "model_version": str(output["model_version"]),
        "adapter_scope": "local" if getattr(adapter, "is_local", False) else "external_authorized",
    }


def build_video_audio_analysis(
    *,
    has_audio: bool,
    speech_presence: str,
    audio_observations: list[str] | tuple[str, ...],
    transcript: dict | None,
) -> dict:
    if speech_presence not in {"none", "unclear", "clear"}:
        raise ValueError("speech_presence must be none, unclear, or clear")
    observations = [
        str(item).strip()
        for item in audio_observations
        if str(item).strip()
    ]
    if not has_audio:
        return {
            "has_audio": False,
            "speech_presence": "none",
            "audio_observations": ["无音轨。"],
            "transcript_detail": {"status": "not_applicable"},
            "audio_understanding_incomplete": False,
            "analysis_completeness": "complete",
            "important_speech_assessment": "none",
            "source_audio_use_policy": "not_applicable",
        }
    if speech_presence == "none":
        return {
            "has_audio": True,
            "speech_presence": "none",
            "audio_observations": observations,
            "transcript_detail": {"status": "not_applicable"},
            "audio_understanding_incomplete": False,
            "analysis_completeness": "complete",
            "important_speech_assessment": "none",
            "source_audio_use_policy": "retain",
        }
    if transcript is not None:
        return {
            "has_audio": True,
            "speech_presence": speech_presence,
            "audio_observations": observations,
            "transcript_detail": transcript,
            "audio_understanding_incomplete": False,
            "analysis_completeness": "complete",
            "important_speech_assessment": "reviewed_from_transcript",
            "source_audio_use_policy": "human-review-required",
        }
    return {
        "has_audio": True,
        "speech_presence": speech_presence,
        "audio_observations": observations,
        "transcript_detail": {"status": "unavailable"},
        "audio_understanding_incomplete": True,
        "analysis_completeness": "visual_complete_audio_incomplete",
        "important_speech_assessment": "unknown",
        "source_audio_use_policy": "human-review-required",
    }


def redact_transcript_for_downstream(transcript: dict) -> dict:
    downstream = deepcopy(transcript)
    redacted_count = 0
    for segment in downstream.get("segments", []):
        if not segment.get("sensitive"):
            continue
        segment["text"] = "[敏感内容已隐藏]"
        segment["redacted"] = True
        redacted_count += 1
    downstream["downstream_redaction"] = {
        "applied": redacted_count > 0,
        "redacted_segment_count": redacted_count,
    }
    return downstream


def build_downstream_audio_summary(profile: dict) -> dict:
    transcript = dict(profile.get("transcript_detail") or {})
    segments = list(transcript.get("segments") or [])
    return {
        "has_audio": profile.get("media_facts", {}).get("has_audio"),
        "speech_presence": profile.get("speech_presence", "unknown"),
        "transcript_status": transcript.get("status", "unavailable"),
        "language": transcript.get("language"),
        "audio_understanding_incomplete": bool(
            profile.get("audio_understanding_incomplete")
            or profile.get("analysis_completeness")
            == "visual_complete_audio_incomplete"
        ),
        "source_audio_use_policy": profile.get(
            "source_audio_use_policy",
            "human-review-required",
        ),
        "sensitive_segment_count": sum(
            1 for item in segments if item.get("sensitive")
        ),
    }


def decide_segment_audio_policy(
    *,
    speech_understanding: str,
    privacy_risk: bool,
    rights_risk: bool,
    spoken_claim_risk: bool,
) -> str:
    if speech_understanding not in {"none", "complete", "incomplete"}:
        raise ValueError(
            "speech_understanding must be none, complete, or incomplete"
        )
    if privacy_risk or rights_risk:
        return "mute-required"
    if spoken_claim_risk:
        return "human-review-required"
    if speech_understanding == "incomplete":
        return "mute-recommended"
    return "retain"


def refresh_video_profile_audio(
    profile: dict,
    *,
    transcript: dict,
    audio_observations: list[str] | tuple[str, ...],
    source_audio_use_policy: str,
) -> dict:
    if source_audio_use_policy not in {
        "retain",
        "mute-recommended",
        "mute-required",
        "human-review-required",
    }:
        raise ValueError("invalid source audio use policy")
    if transcript.get("status") != "available":
        raise ValueError("audio refresh requires an available transcript")
    refreshed = deepcopy(profile)
    refreshed["audio_observations"] = [
        str(item).strip()
        for item in audio_observations
        if str(item).strip()
    ]
    refreshed["transcript_detail"] = deepcopy(transcript)
    refreshed["source_audio_use_policy"] = source_audio_use_policy
    refreshed["audio_understanding_incomplete"] = False
    refreshed["important_speech_assessment"] = "reviewed_from_transcript"
    refreshed["analysis_completeness"] = "complete"
    provenance = dict(refreshed.get("analysis_provenance") or {})
    provenance["audio_transcription"] = {
        "tool": transcript.get("tool"),
        "model_version": transcript.get("model_version"),
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
        "refresh_scope": "audio_only",
    }
    refreshed["analysis_provenance"] = provenance
    refreshed.pop("profile_revision", None)
    refreshed.pop("content_digest", None)
    canonical = json.dumps(
        refreshed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    refreshed["content_digest"] = f"sha256:{digest}"
    refreshed["profile_revision"] = f"video_profile_rev_{digest[:16]}"
    return refreshed
