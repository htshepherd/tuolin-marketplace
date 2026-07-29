from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .media import probe_media, run_ffmpeg


class HyperFramesUnavailable(RuntimeError):
    """Raised when HyperFrames cannot produce a usable render."""


HyperFramesExecutor = Callable[[dict[str, Any], Path], Any]


@dataclass(frozen=True)
class CompositionResult:
    output_path: str
    path_used: str
    media_probe: dict[str, Any]
    fallback_reason: str | None = None
    diagnostics: dict[str, Any] | None = None


class HyperFramesAdapter:
    """Small boundary around the Codex HyperFrames integration.

    The concrete desktop integration is injected so workflow state never depends
    on a plugin-specific response shape.
    """

    def __init__(self, executor: HyperFramesExecutor | None = None) -> None:
        self._executor = executor

    def render(self, contract: dict[str, Any], output_path: Path) -> CompositionResult:
        if self._executor is None:
            raise HyperFramesUnavailable("HyperFrames执行器未安装。")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            response = self._executor(contract, output_path)
        except Exception as exc:
            raise HyperFramesUnavailable(f"HyperFrames执行失败：{exc}") from exc
        candidate = output_path
        if isinstance(response, (str, Path)):
            candidate = Path(response).expanduser().resolve()
        elif isinstance(response, dict) and response.get("output_path"):
            candidate = Path(str(response["output_path"])).expanduser().resolve()
        if candidate != output_path.resolve():
            if not candidate.is_file():
                raise HyperFramesUnavailable("HyperFrames未返回可用文件。")
            shutil.copy2(candidate, output_path)
        try:
            media_probe = validate_composition_output(output_path, contract)
        except Exception as exc:
            raise HyperFramesUnavailable(f"HyperFrames产物不完整：{exc}") from exc
        return CompositionResult(str(output_path), "hyperframes", media_probe)


HyperFramesCommandRunner = Callable[[list[str], Path, dict[str, str]], dict[str, Any]]


class HyperFramesCLIAdapter:
    """Production adapter for the official ``npx hyperframes`` workflow."""

    def __init__(
        self,
        *,
        command_runner: HyperFramesCommandRunner | None = None,
        quality: str = "high",
        inspect_samples: int = 12,
    ) -> None:
        if quality not in {"draft", "standard", "high"}:
            raise ValueError("HyperFrames质量必须是draft、standard或high。")
        self._runner = command_runner or _run_hyperframes_command
        self._quality = quality
        self._inspect_samples = int(inspect_samples)

    def render(self, contract: dict[str, Any], output_path: Path) -> CompositionResult:
        output_path = output_path.resolve()
        project_dir = output_path.parent / "hyperframes-project"
        diagnostics_dir = output_path.parent / "hyperframes-diagnostics"
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ)
        environment["HYPERFRAMES_SKIP_SKILLS"] = "1"
        stages: dict[str, Any] = {}
        try:
            if not (project_dir / "hyperframes.json").is_file():
                init = self._runner(
                    [
                        "npx",
                        "hyperframes",
                        "init",
                        project_dir.name,
                        "--example",
                        "blank",
                        "--resolution",
                        "portrait",
                        "--non-interactive",
                        "--skill",
                        "tuolin-avatar-video",
                    ],
                    output_path.parent,
                    environment,
                )
                stages["init"] = _safe_command_result(init)
                _require_command_success("HyperFrames init", init)
            _write_hyperframes_project(project_dir, contract)
            lint = self._runner(
                ["npx", "hyperframes", "lint", str(project_dir), "--json"],
                output_path.parent,
                environment,
            )
            stages["lint"] = _safe_command_result(lint)
            _require_command_success("HyperFrames lint", lint)
            inspect = self._runner(
                [
                    "npx",
                    "hyperframes",
                    "inspect",
                    str(project_dir),
                    "--json",
                    "--samples",
                    str(self._inspect_samples),
                ],
                output_path.parent,
                environment,
            )
            stages["inspect"] = _safe_command_result(inspect)
            _require_command_success("HyperFrames inspect", inspect)
            rendered = self._runner(
                [
                    "npx",
                    "hyperframes",
                    "render",
                    str(project_dir),
                    "--output",
                    str(output_path),
                    "--fps",
                    "30",
                    "--quality",
                    self._quality,
                    "--strict",
                    "--no-best-effort",
                    "--skill",
                    "tuolin-avatar-video",
                ],
                output_path.parent,
                environment,
            )
            stages["render"] = _safe_command_result(rendered)
            _require_command_success("HyperFrames render", rendered)
            probe = validate_composition_output(output_path, contract)
        except Exception as exc:
            _write_json_file(diagnostics_dir / "stages.json", {"status": "failed", "stages": stages, "error": _safe_text(str(exc))})
            if isinstance(exc, HyperFramesUnavailable):
                raise
            raise HyperFramesUnavailable(f"HyperFrames CLI执行失败：{_safe_text(str(exc))}") from exc
        diagnostics = {
            "status": "completed",
            "project_dir": str(project_dir),
            "stages": stages,
        }
        _write_json_file(diagnostics_dir / "stages.json", diagnostics)
        return CompositionResult(str(output_path), "hyperframes", probe, diagnostics=diagnostics)


class FFmpegComposer:
    def __init__(self, ffmpeg_command: str = "ffmpeg") -> None:
        self._ffmpeg_command = ffmpeg_command

    def render(self, contract: dict[str, Any], output_path: Path) -> CompositionResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        timeline = list(contract.get("timeline") or [])
        if not timeline:
            raise ValueError("组合合同缺少时间线。")
        presenter = Path(str(contract["presenter_path"]))
        audio = Path(str(contract["audio_path"]))
        with tempfile.TemporaryDirectory(prefix="avatar-compose-", dir=str(output_path.parent)) as temporary:
            segment_paths: list[Path] = []
            for index, segment in enumerate(timeline, start=1):
                segment_path = Path(temporary) / f"segment-{index:04d}.mp4"
                self._render_segment(segment, presenter, segment_path)
                segment_paths.append(segment_path)
            concat_file = Path(temporary) / "segments.txt"
            concat_file.write_text(
                "".join(f"file '{path.as_posix()}'\n" for path in segment_paths),
                encoding="utf-8",
            )
            master_path = Path(temporary) / "master.mp4"
            run_ffmpeg(
                [
                    self._ffmpeg_command,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    "-i",
                    str(audio),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-t",
                    str(contract["duration_seconds"]),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    "-shortest",
                    str(master_path),
                ]
            )
            self._apply_packaging(master_path, contract, output_path)
        media_probe = validate_composition_output(output_path, contract)
        return CompositionResult(str(output_path), "ffmpeg_fallback", media_probe)

    def _apply_packaging(self, master_path: Path, contract: dict[str, Any], output_path: Path) -> None:
        captions = dict(contract.get("captions") or {})
        bgm = contract.get("bgm")
        if not captions.get("burned") and not bgm:
            shutil.move(master_path, output_path)
            return
        command = [self._ffmpeg_command, "-y", "-i", str(master_path)]
        if bgm:
            command.extend(["-stream_loop", "-1", "-i", str(bgm["path"])])
        if captions.get("burned"):
            subtitle_path = _escape_filter_path(Path(str(captions.get("path") or "")))
            style = "Alignment=2,MarginV=250,FontSize=18,Outline=2,Shadow=0"
            command.extend(["-vf", f"subtitles=filename='{subtitle_path}':force_style='{style}'"])
        if bgm:
            volume = float(bgm["volume"])
            command.extend(
                [
                    "-filter_complex",
                    f"[1:a]volume={volume},atrim=0:{contract['duration_seconds']}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[a]",
                    "-map",
                    "0:v:0",
                    "-map",
                    "[a]",
                ]
            )
        else:
            command.extend(["-map", "0:v:0", "-map", "0:a:0"])
        command.extend(
            [
                "-t",
                str(contract["duration_seconds"]),
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                "-shortest",
                str(output_path),
            ]
        )
        run_ffmpeg(command)

    def _render_segment(self, segment: dict[str, Any], presenter: Path, output: Path) -> None:
        duration = float(segment["end_seconds"]) - float(segment["start_seconds"])
        mode = str(segment.get("mode") or "presenter")
        common = [
            "-t",
            str(duration),
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x101010,setsar=1,fps=30",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
        if mode == "presenter":
            command = [
                self._ffmpeg_command,
                "-y",
                "-ss",
                str(segment["start_seconds"]),
                "-i",
                str(presenter),
                *common,
            ]
        else:
            visual = Path(str(segment.get("visual_path") or ""))
            if not visual.is_file():
                raise ValueError(f"证据/辅助画面不存在：{visual}")
            command = [self._ffmpeg_command, "-y", "-loop", "1", "-i", str(visual), *common]
        run_ffmpeg(command)


def validate_composition_output(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    probe = probe_media(path)
    if not probe["has_video"] or not probe["has_audio"]:
        raise ValueError("成片缺少视频或音轨。")
    if (probe["width"], probe["height"]) != (1080, 1920):
        raise ValueError("成片不是1080x1920竖屏。")
    if str(probe.get("video_codec") or "").casefold() != "h264":
        raise ValueError("成片视频编码不是H.264。")
    if str(probe.get("audio_codec") or "").casefold() != "aac":
        raise ValueError("成片音频编码不是AAC。")
    if probe.get("pixel_format") not in {"yuv420p", "yuvj420p"}:
        raise ValueError("成片像素格式不兼容。")
    if abs(float(probe.get("frame_rate") or 0) - float(contract.get("frame_rate") or 30)) > 0.1:
        raise ValueError("成片帧率与组合合同不一致。")
    if abs(float(probe["duration_seconds"]) - float(contract["duration_seconds"])) > 1.0:
        raise ValueError("成片时长与组合合同不一致。")
    captions = dict(contract.get("captions") or {})
    if captions.get("burned"):
        caption_path = Path(str(captions.get("path") or ""))
        if not caption_path.is_file() or caption_path.stat().st_size <= 0:
            raise ValueError("硬字幕策略缺少可用字幕源文件。")
    return probe


def _escape_filter_path(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"字幕文件不存在：{path}")
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _run_hyperframes_command(command: list[str], cwd: Path, environment: dict[str, str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HyperFramesUnavailable(f"找不到HyperFrames命令依赖：{command[0]}") from exc
    return {"returncode": completed.returncode, "stdout": completed.stdout or "", "stderr": completed.stderr or ""}


def _require_command_success(operation: str, result: dict[str, Any]) -> None:
    if int(result.get("returncode") or 0) == 0:
        return
    detail = _safe_text(str(result.get("stderr") or result.get("stdout") or "unknown error"))[-2000:]
    raise HyperFramesUnavailable(f"{operation}失败：{detail}")


def _safe_command_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "returncode": int(result.get("returncode") or 0),
        "stdout": _safe_text(str(result.get("stdout") or ""))[-4000:],
        "stderr": _safe_text(str(result.get("stderr") or ""))[-4000:],
    }


def _safe_text(value: str) -> str:
    text = re.sub(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", r"\1 ***", str(value))
    return re.sub(
        r"(?i)([?&](?:api[_-]?key|token|access[_-]?token|secret|password|cookie)=)[^&#\s]+",
        r"\1***",
        text,
    )


def _write_hyperframes_project(project_dir: Path, contract: dict[str, Any]) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = project_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    presenter_asset = _copy_hyperframes_asset(Path(str(contract["presenter_path"])), assets_dir, "presenter")
    audio_asset = _copy_hyperframes_asset(Path(str(contract["audio_path"])), assets_dir, "narration")
    visual_assets: dict[str, str] = {}
    for index, path_value in enumerate([*contract.get("official_visuals", []), *contract.get("support_visuals", [])], start=1):
        source = Path(str(path_value)).resolve()
        visual_assets[str(source)] = _copy_hyperframes_asset(source, assets_dir, f"visual-{index:03d}")
    bgm_asset = None
    if contract.get("bgm"):
        bgm_asset = _copy_hyperframes_asset(Path(str(contract["bgm"]["path"])), assets_dir, "bgm")
    cues = _parse_srt(Path(str(contract.get("captions", {}).get("path") or ""))) if contract.get("captions", {}).get("burned") else []
    index_html = _render_hyperframes_html(
        contract,
        presenter_asset=presenter_asset,
        audio_asset=audio_asset,
        visual_assets=visual_assets,
        bgm_asset=bgm_asset,
        cues=cues,
    )
    (project_dir / "index.html").write_text(index_html, encoding="utf-8")
    (project_dir / "DESIGN.md").write_text(_hyperframes_design(), encoding="utf-8")
    _write_json_file(project_dir / "composition-contract.json", contract)


def _copy_hyperframes_asset(source: Path, assets_dir: Path, stem: str) -> str:
    if not source.is_file() or source.stat().st_size <= 0:
        raise HyperFramesUnavailable(f"HyperFrames输入素材不存在或为空：{source}")
    suffix = source.suffix.casefold() or ".bin"
    target = assets_dir / f"{stem}{suffix}"
    shutil.copy2(source, target)
    return f"assets/{target.name}"


def _parse_srt(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise HyperFramesUnavailable(f"硬字幕文件不存在：{path}")
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip())
    cues = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3 or " --> " not in lines[1]:
            raise HyperFramesUnavailable("SRT字幕格式无效。")
        start_value, end_value = lines[1].split(" --> ", 1)
        cues.append({"start": _srt_seconds(start_value), "end": _srt_seconds(end_value), "text": " ".join(lines[2:])})
    return cues


def _srt_seconds(value: str) -> float:
    matched = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", value.strip())
    if not matched:
        raise HyperFramesUnavailable("SRT字幕时间格式无效。")
    hours, minutes, seconds, milliseconds = (int(part) for part in matched.groups())
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def _render_hyperframes_html(
    contract: dict[str, Any],
    *,
    presenter_asset: str,
    audio_asset: str,
    visual_assets: dict[str, str],
    bgm_asset: str | None,
    cues: list[dict[str, Any]],
) -> str:
    duration = float(contract["duration_seconds"])
    title_layout = dict(contract.get("title_layout") or {}) if isinstance(contract.get("title_layout"), dict) else {}
    parameter_layout = dict(contract.get("parameter_layout") or {}) if isinstance(contract.get("parameter_layout"), dict) else {}
    title_position = str(title_layout.get("position") or "bottom").casefold()
    if title_position not in {"top", "center", "bottom"}:
        title_position = "bottom"
    title_alignment = str(title_layout.get("alignment") or "left").casefold()
    if title_alignment not in {"left", "center", "right"}:
        title_alignment = "left"
    title_size = max(48, min(96, int(title_layout.get("font_size") or 74)))
    parameter_columns = max(1, min(3, int(parameter_layout.get("columns") or 2)))
    transition_value = contract.get("transitions")
    transition_kind = str(
        transition_value.get("type") if isinstance(transition_value, dict) else transition_value or "signal_wipe"
    ).casefold()
    if transition_kind not in {"signal_wipe", "wipe", "fade", "simple_cut", "cut", "none"}:
        transition_kind = "signal_wipe"
    overlay_justify = {"top": "flex-start", "center": "center", "bottom": "flex-end"}[title_position]
    overlay_align = {"left": "flex-start", "center": "center", "right": "flex-end"}[title_alignment]
    media_clips = []
    overlay_clips = []
    animation_lines = []
    transition_clips = []
    for index, segment in enumerate(contract["timeline"], start=1):
        start = float(segment["start_seconds"])
        end = float(segment["end_seconds"])
        clip_duration = end - start
        mode = str(segment.get("mode") or "presenter")
        if mode == "presenter":
            media_clips.append(
                f'<video id="media-{index}" class="clip scene-media" style="opacity:0" src="{presenter_asset}" muted playsinline '
                f'data-start="{start:g}" data-duration="{clip_duration:g}" data-media-start="{start:g}" data-track-index="0"></video>'
            )
        else:
            visual_source = str(Path(str(segment.get("visual_path") or "")).resolve())
            asset = visual_assets.get(visual_source)
            if not asset:
                raise HyperFramesUnavailable("HyperFrames时间线引用了未复制的确认图片。")
            media_clips.append(
                f'<img id="media-{index}" class="clip scene-media evidence" style="opacity:0" src="{asset}" '
                f'data-start="{start:g}" data-duration="{clip_duration:g}" data-track-index="0" />'
            )
        display = dict(segment.get("display") or {})
        title = str(display.get("title") or segment.get("purpose") or "Product evidence")
        eyebrow = str(display.get("eyebrow") or "TUOLIN · PRODUCT BRIEF")
        body = str(display.get("body") or "")
        parameters = list(display.get("parameters") or [])
        parameter_html = "".join(
            f'<div class="parameter"><span>{html.escape(str(item.get("label") or ""))}</span><strong>{html.escape(str(item.get("value") or ""))}</strong></div>'
            for item in parameters
            if isinstance(item, dict)
        )
        body_html = f"<p>{html.escape(body)}</p>" if body else ""
        parameters_html = f'<div class="parameters">{parameter_html}</div>' if parameter_html else ""
        overlay_clips.append(
            f'<section id="overlay-{index}" class="clip scene-overlay" style="opacity:0" data-start="{start:g}" '
            f'data-duration="{clip_duration:g}" data-track-index="1">'
            f'<div class="eyebrow">{html.escape(eyebrow)}</div>'
            f'<h1>{html.escape(title)}</h1>'
            f'{body_html}'
            f'{parameters_html}'
            '</section>'
        )
        animation_lines.append(
            f'tl.to("#media-{index}", {{ opacity: 1, scale: 1, duration: 0.45, ease: "power2.out" }}, {start:g});'
        )
        animation_lines.append(
            f'tl.to("#overlay-{index}", {{ opacity: 1, duration: 0.25, ease: "power1.out" }}, {start:g});'
        )
        animation_lines.append(
            f'tl.from("#overlay-{index} .eyebrow", {{ opacity: 0, y: 24, duration: 0.35, ease: "power3.out" }}, {start + 0.08:g});'
        )
        animation_lines.append(
            f'tl.from("#overlay-{index} h1", {{ opacity: 0, y: 42, duration: 0.45, ease: "power3.out" }}, {start + 0.16:g});'
        )
        if body:
            animation_lines.append(
                f'tl.from("#overlay-{index} p", {{ opacity: 0, y: 28, duration: 0.4, ease: "power2.out" }}, {start + 0.24:g});'
            )
        if parameters:
            animation_lines.append(
                f'tl.from("#overlay-{index} .parameter", {{ opacity: 0, x: 30, stagger: 0.08, duration: 0.35, ease: "power2.out" }}, {start + 0.28:g});'
            )
        if index > 1 and transition_kind not in {"simple_cut", "cut", "none"}:
            transition_start = max(0.0, start - 0.18)
            transition_clips.append(
                f'<div id="transition-{index}" class="clip transition transition-{transition_kind}" data-start="{transition_start:g}" data-duration="0.36" data-track-index="3"></div>'
            )
            if transition_kind == "fade":
                animation_lines.append(
                    f'tl.fromTo("#transition-{index}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.18, ease: "power1.in" }}, {transition_start:g})'
                    f'.to("#transition-{index}", {{ opacity: 0, duration: 0.18, ease: "power1.out" }}, {start:g});'
                )
            else:
                animation_lines.append(
                    f'tl.fromTo("#transition-{index}", {{ scaleX: 0, transformOrigin: "left center" }}, '
                    f'{{ scaleX: 1, duration: 0.18, ease: "power2.in" }}, {transition_start:g})'
                    f'.to("#transition-{index}", {{ scaleX: 0, transformOrigin: "right center", duration: 0.18, ease: "power2.out" }}, {start:g});'
                )
    caption_clips = []
    for index, cue in enumerate(cues, start=1):
        cue_duration = max(0.05, float(cue["end"]) - float(cue["start"]))
        caption_clips.append(
            f'<div id="caption-{index}" class="clip caption" data-start="{float(cue["start"]):g}" '
            f'data-duration="{cue_duration:g}" data-track-index="2"><div class="caption-content">{html.escape(str(cue["text"]))}</div></div>'
        )
        animation_lines.append(
            f'tl.from("#caption-{index} .caption-content", {{ opacity: 0, y: 18, duration: 0.16, ease: "power2.out" }}, {float(cue["start"]):g});'
        )
        animation_lines.append(
            f'tl.to("#caption-{index} .caption-content", {{ opacity: 0, scale: 0.98, duration: 0.12, ease: "power2.in" }}, {max(float(cue["start"]), float(cue["end"]) - 0.12):g});'
        )
        animation_lines.append(f'tl.set("#caption-{index} .caption-content", {{ opacity: 0, visibility: "hidden" }}, {float(cue["end"]):g});')
    bgm_html = ""
    if bgm_asset:
        bgm_html = (
            f'<audio id="bgm" class="clip" src="{bgm_asset}" data-start="0" data-duration="{duration:g}" '
            f'data-track-index="6" data-volume="{float(contract["bgm"]["volume"]):g}"></audio>'
        )
    repeat_count = max(0, int(duration // 6) - 1)
    return f'''<!doctype html>
<html lang="{html.escape(str(contract["language_version"]))}" data-resolution="portrait">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1920" />
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    @font-face {{ font-family: "Avenir Next"; src: local("Avenir Next"); }}
    @font-face {{ font-family: "Noto Sans SC"; src: local("Noto Sans SC"); }}
    @font-face {{ font-family: "JetBrains Mono"; src: local("JetBrains Mono"); }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #0d1321; color: #f0ebd8; font-family: "Avenir Next", "Noto Sans SC", sans-serif; }}
    #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #0d1321; }}
    .scene-media {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; background: #0d1321; }}
    .scene-media.evidence {{ object-fit: contain; padding: 220px 64px 360px; background: radial-gradient(circle at 70% 25%, #263b57 0%, #0d1321 62%); }}
    .depth {{ position: absolute; inset: 0; pointer-events: none; background-image: linear-gradient(rgba(183,211,75,.055) 1px, transparent 1px), linear-gradient(90deg, rgba(183,211,75,.055) 1px, transparent 1px); background-size: 54px 54px; mix-blend-mode: screen; }}
    .glow {{ position: absolute; width: 720px; height: 720px; left: -180px; top: 780px; border-radius: 50%; background: radial-gradient(circle, rgba(183,211,75,.17), rgba(183,211,75,0) 68%); }}
    .scene-overlay {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: {overlay_justify}; align-items: {overlay_align}; gap: 18px; padding: 180px 72px 330px; text-align: {title_alignment}; background: linear-gradient(180deg, transparent 42%, rgba(13,19,33,.9) 88%); }}
    .eyebrow {{ font-family: "JetBrains Mono", monospace; font-size: 26px; letter-spacing: 4px; color: #b7d34b; text-transform: uppercase; }}
    h1 {{ margin: 0; max-width: 900px; font-size: {title_size}px; line-height: 1.04; font-weight: 760; letter-spacing: -2px; text-wrap: balance; }}
    p {{ margin: 0; max-width: 860px; font-size: 36px; line-height: 1.34; color: #d3d9df; }}
    .parameters {{ display: grid; grid-template-columns: repeat({parameter_columns}, minmax(0, 1fr)); gap: 12px; width: min(900px, 100%); }}
    .parameter {{ min-width: 280px; padding: 16px 20px; border: 1px solid rgba(183,211,75,.36); background: rgba(13,19,33,.78); }}
    .parameter span {{ display: block; font-size: 20px; color: #9ba6b2; }}
    .parameter strong {{ display: block; margin-top: 6px; font-size: 30px; color: #f0ebd8; }}
    .caption {{ position: absolute; left: 70px; right: 70px; bottom: 190px; min-height: 100px; display: flex; align-items: center; justify-content: center; }}
    .caption-content {{ width: 100%; padding: 18px 28px; border-radius: 18px; background: rgba(7,11,19,.88); color: #f5f2e8; font-size: 46px; line-height: 1.23; font-weight: 680; text-align: center; text-wrap: balance; box-shadow: 0 16px 50px rgba(0,0,0,.25); }}
    .transition {{ position: absolute; inset: 0; background: #b7d34b; z-index: 50; }}
    .transition-fade {{ background: #0d1321; }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{duration:g}" data-width="1080" data-height="1920" data-fps="30">
    <div id="depth" class="clip depth" data-start="0" data-duration="{duration:g}" data-track-index="4"><div id="glow" class="glow"></div></div>
    {''.join(media_clips)}
    {''.join(overlay_clips)}
    {''.join(caption_clips)}
    {''.join(transition_clips)}
    <audio id="narration" class="clip" src="{audio_asset}" data-start="0" data-duration="{duration:g}" data-track-index="5" data-volume="1"></audio>
    {bgm_html}
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});
    tl.from("#depth", {{ opacity: 0, duration: 0.45, ease: "power2.out" }}, 0);
    tl.fromTo("#glow", {{ scale: 0.92, opacity: 0.55 }}, {{ scale: 1.08, opacity: 0.82, duration: 3, yoyo: true, repeat: {repeat_count}, ease: "sine.inOut" }}, 0);
    {''.join(animation_lines)}
    window.__timelines["main"] = tl;
  </script>
</body>
</html>
'''


def _hyperframes_design() -> str:
    return """# Tuolin Digital Avatar Visual Identity

## Style Prompt

Dark technical industrial editorial treatment derived from the user-provided short-video reference: restrained graphite/navy canvas, precise information hierarchy, acid-green status accents, subtle grid depth, and confident product-first framing. Motion is clean, physical, and brief; verified product evidence remains visually dominant.

## Colors

- Background: `#0D1321`
- Elevated surface: `#1D2D44`
- Primary text: `#F0EBD8`
- Secondary text: `#D3D9DF`
- Signal accent: `#B7D34B`

## Typography

- Display/body: Avenir Next with Noto Sans SC fallback
- Technical labels: JetBrains Mono

## What NOT to Do

- No generic cyan/purple gradients or gradient text.
- No invented certification badges, parameter values, or customer logos.
- No decorative motion that obscures the presenter face or formal evidence.
- No continuous looping or non-deterministic animation.
- No viewer-facing AI/simulation label unless explicitly requested.
"""


def _write_json_file(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)
