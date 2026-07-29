from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tuolin_marketplace.avatar_video.agent import (
    accept_avatar_delivery,
    compose_avatar_video,
    confirm_avatar_inputs,
    confirm_avatar_presenter,
    confirm_avatar_production_plan,
    create_avatar_video_run,
    generate_fish_audio_input,
    generate_heygen_presenter,
    get_avatar_final_review,
    record_avatar_material_inspection,
    resume_avatar_video_run,
    revise_avatar_video,
    write_avatar_production_plan,
)
from tuolin_marketplace.avatar_video.provider_adapters import FishAudioAdapter, HeyGenCLIAdapter
from tuolin_marketplace.avatar_video.composition import HyperFramesCLIAdapter
from tuolin_marketplace.shared.project_layout import load_project_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal natural-language workflow bridge for $tuolin-avatar-video.")
    parser.add_argument("action", choices=("create", "resume", "inspect-material", "write-plan", "confirm-plan", "fish", "confirm-inputs", "heygen", "confirm-presenter", "compose", "review-final", "accept", "revise"))
    parser.add_argument("--run-dir")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--config")
    parser.add_argument("--request", default="")
    parser.add_argument("--product-id")
    parser.add_argument("--language", choices=("en", "zh"))
    parser.add_argument("--duration", type=int)
    parser.add_argument("--payload-file")
    parser.add_argument("--category")
    parser.add_argument("--composer", choices=("hyperframes", "ffmpeg"), default="hyperframes")
    args = parser.parse_args()
    payload = _payload(args.payload_file)

    if args.action == "create":
        project_dir = Path(args.project_dir).resolve()
        config_path = Path(args.config).resolve() if args.config else None
        paths = resolve_paths(project_dir, load_project_config(project_dir, config_path))
        result = create_avatar_video_run(
            paths,
            args.request,
            product_id=_required(args.product_id, "--product-id"),
            language_version=_required(args.language, "--language"),
            duration_seconds=int(_required(args.duration, "--duration")),
            initial_brief=payload,
            invoked_skill="$tuolin-avatar-video",
        )
    else:
        run_dir = Path(_required(args.run_dir, "--run-dir")).resolve()
        actions = {
            "resume": lambda: resume_avatar_video_run(run_dir),
            "inspect-material": lambda: record_avatar_material_inspection(run_dir, payload),
            "write-plan": lambda: write_avatar_production_plan(run_dir, payload),
            "confirm-plan": lambda: confirm_avatar_production_plan(run_dir),
            "fish": lambda: generate_fish_audio_input(run_dir, FishAudioAdapter(api_key=_required(os.environ.get("FISH_AUDIO_API_KEY"), "FISH_AUDIO_API_KEY"))),
            "confirm-inputs": lambda: confirm_avatar_inputs(run_dir),
            "heygen": lambda: generate_heygen_presenter(run_dir, HeyGenCLIAdapter()),
            "confirm-presenter": lambda: confirm_avatar_presenter(run_dir),
            "compose": lambda: compose_avatar_video(
                run_dir,
                hyperframes=HyperFramesCLIAdapter() if args.composer == "hyperframes" else None,
            ),
            "review-final": lambda: get_avatar_final_review(run_dir),
            "accept": lambda: accept_avatar_delivery(run_dir),
            "revise": lambda: revise_avatar_video(run_dir, args.request, category=_required(args.category, "--category"), changes=payload),
        }
        result = actions[args.action]()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _payload(path_value: str | None) -> dict:
    if not path_value:
        return {}
    value = json.loads(Path(path_value).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("payload必须是JSON对象。")
    return value


def _required(value, label: str):
    if value is None or value == "":
        raise ValueError(f"缺少{label}。")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
