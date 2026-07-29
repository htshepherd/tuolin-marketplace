from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .media import probe_media


@dataclass(frozen=True)
class ProviderMediaResult:
    output_path: str
    external_task_id: str
    media_probe: dict[str, Any]
    actual_consumption: Any = None


@dataclass(frozen=True)
class ProviderImageBatchResult:
    manifest_path: str
    image_paths: tuple[str, ...]
    external_task_id: str
    media_probes: tuple[dict[str, Any], ...]
    actual_consumption: Any = None


FishTransport = Callable[[str, dict[str, str], bytes, float], dict[str, Any]]
HeyGenTransport = Callable[[str, str, dict[str, str], Any, float], dict[str, Any]]
HeyGenCommandRunner = Callable[[list[str], dict[str, str]], dict[str, Any]]
HeyGenSubmissionCallback = Callable[[str], None]
SupportVisualExecutor = Callable[[dict[str, Any], Path], dict[str, Any]]


class ProviderTaskPending(RuntimeError):
    def __init__(self, provider: str, task_id: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.task_id = task_id


class ProviderTaskFailed(RuntimeError):
    def __init__(self, provider: str, task_id: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.task_id = task_id


class FishAudioAdapter:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.fish.audio",
        timeout_seconds: float = 120.0,
        transport: FishTransport | None = None,
    ) -> None:
        if not str(api_key).strip():
            raise ValueError("Fish Audio API key不能为空。")
        self._api_key = str(api_key)
        self._base_url = str(base_url).rstrip("/")
        self._timeout_seconds = float(timeout_seconds)
        self._transport = transport or _fish_http_transport

    def synthesize(
        self,
        *,
        narration: str,
        voice_id: str,
        settings: dict[str, Any],
        output_path: Path,
    ) -> ProviderMediaResult:
        text = str(narration)
        if not text.strip():
            raise ValueError("Fish Audio输入逐字稿不能为空。")
        if not str(voice_id).strip():
            raise ValueError("Fish Audio voice ID不能为空。")
        output_format = str(settings.get("format") or "wav").casefold()
        if output_format not in {"mp3", "wav", "pcm", "opus"}:
            raise ValueError("Fish Audio format必须是mp3、wav、pcm或opus。")
        latency = str(settings.get("latency") or "normal").casefold()
        if latency not in {"normal", "balanced"}:
            raise ValueError("Fish Audio latency必须是normal或balanced。")
        payload = {
            "text": text,
            "reference_id": str(voice_id),
            "format": output_format,
            "normalize": bool(settings.get("normalize", True)),
            "latency": latency,
        }
        if settings.get("speed") is not None:
            speed = float(settings["speed"])
            if speed < 0.5 or speed > 2.0:
                raise ValueError("Fish Audio speed必须在0.5到2.0之间。")
            payload["prosody"] = {"speed": speed, "volume": float(settings.get("volume") or 0.0)}
        if settings.get("chunk_length") is not None:
            chunk_length = int(settings["chunk_length"])
            if chunk_length < 100 or chunk_length > 300:
                raise ValueError("Fish Audio chunk_length必须在100到300之间。")
            payload["chunk_length"] = chunk_length
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/msgpack",
            "Accept": "audio/*",
            "model": str(settings.get("model") or "s2-pro"),
        }
        try:
            response = self._transport(
                f"{self._base_url}/v1/tts",
                headers,
                _encode_msgpack(payload),
                self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise RuntimeError("Fish Audio请求超时。") from exc
        status = int(response.get("status") or 0)
        if status < 200 or status >= 300:
            raise RuntimeError(f"Fish Audio返回HTTP {status}。")
        body = response.get("body")
        if not isinstance(body, (bytes, bytearray)) or not body:
            raise ValueError("Fish Audio返回了空或畸形音频。")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_bytes(bytes(body))
        temporary.replace(output_path)
        probe = probe_media(output_path)
        if probe["has_video"] or not probe["has_audio"]:
            raise ValueError("Fish Audio输出不是有效的纯音频文件。")
        response_headers = {str(key).casefold(): str(value) for key, value in dict(response.get("headers") or {}).items()}
        task_id = response_headers.get("x-request-id") or response_headers.get("x-task-id") or "fish-sync-response"
        return ProviderMediaResult(
            output_path=str(output_path),
            external_task_id=task_id,
            media_probe=probe,
            actual_consumption=response_headers.get("x-credits-used"),
        )


class SupportVisualAdapter:
    """Replaceable production boundary for a Codex-connected image generator.

    The executor receives the exact authorized batch plus a dedicated output
    directory. It must return real local image paths and a provider task ID;
    prompts or task metadata alone are never treated as generated images.
    """

    def __init__(self, executor: SupportVisualExecutor) -> None:
        if not callable(executor):
            raise ValueError("辅助图片执行器不能为空。")
        self._executor = executor

    def generate(self, *, batch: dict[str, Any], output_dir: Path) -> ProviderImageBatchResult:
        items = list(batch.get("images") or [])
        expected_count = int(batch.get("count") or len(items))
        if not items or expected_count != len(items):
            raise ValueError("辅助图片批次数量或逐项用途无效。")
        output_dir.mkdir(parents=True, exist_ok=False)
        try:
            response = self._executor(dict(batch), output_dir)
        except TimeoutError as exc:
            raise RuntimeError("辅助图片供应商请求超时。") from exc
        if not isinstance(response, dict):
            raise ValueError("辅助图片供应商返回畸形结果。")
        raw_paths = list(response.get("image_paths") or [])
        if len(raw_paths) != expected_count:
            raise ValueError("辅助图片供应商返回数量与授权批次不一致。")
        image_paths: list[str] = []
        probes: list[dict[str, Any]] = []
        for index, raw_path in enumerate(raw_paths, start=1):
            source = Path(str(raw_path)).expanduser().resolve()
            if not source.is_file() or source.stat().st_size <= 0:
                raise ValueError(f"辅助图片{index}不存在或为空。")
            target = output_dir / f"support-{index:02d}{source.suffix.casefold() or '.png'}"
            if source != target.resolve():
                shutil.copy2(source, target)
            probe = probe_media(target)
            if not probe["has_video"] or probe["has_audio"] or probe["width"] <= 0 or probe["height"] <= 0:
                raise ValueError(f"辅助图片{index}不是可读静态图像。")
            image_paths.append(str(target))
            probes.append(probe)
        task_id = str(response.get("task_id") or response.get("request_id") or "").strip()
        if not task_id:
            raise ValueError("辅助图片供应商响应缺少task_id。")
        manifest_path = output_dir / "manifest.json"
        _write_json(
            manifest_path,
            {
                "schema_version": "avatar-support-visual-batch-v1",
                "provider": str(batch.get("provider") or "connected_image_generator"),
                "count": expected_count,
                "images": image_paths,
                "items": items,
                "media_probes": probes,
                "viewer_facing_ai_label": False,
                "generation_provenance": "provider_generated",
                "mode": "real",
            },
        )
        return ProviderImageBatchResult(
            manifest_path=str(manifest_path),
            image_paths=tuple(image_paths),
            external_task_id=task_id,
            media_probes=tuple(probes),
            actual_consumption=response.get("actual_consumption"),
        )


class HeyGenAdapter:
    """Deprecated v2 HTTP compatibility adapter used only by isolated fixtures.

    Production workflow must use :class:`HeyGenCLIAdapter`; HeyGen's current
    CLI routes to the supported v3 API and keeps credentials out of commands.
    """
    def __init__(
        self,
        *,
        api_key: str,
        api_base_url: str = "https://api.heygen.com",
        upload_base_url: str = "https://upload.heygen.com",
        timeout_seconds: float = 120.0,
        poll_interval_seconds: float = 5.0,
        max_polls: int = 120,
        transport: HeyGenTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not str(api_key).strip():
            raise ValueError("HeyGen API key不能为空。")
        self._api_key = str(api_key)
        self._api_base_url = str(api_base_url).rstrip("/")
        self._upload_base_url = str(upload_base_url).rstrip("/")
        self._timeout_seconds = float(timeout_seconds)
        self._poll_interval_seconds = float(poll_interval_seconds)
        self._max_polls = int(max_polls)
        self._transport = transport or _heygen_http_transport
        self._sleep = sleep

    def generate_presenter(
        self,
        *,
        audio_path: Path,
        avatar_id: str,
        settings: dict[str, Any],
        output_path: Path,
    ) -> ProviderMediaResult:
        if not audio_path.is_file() or audio_path.stat().st_size <= 0:
            raise ValueError("HeyGen输入音频不存在或为空。")
        if not str(avatar_id).strip():
            raise ValueError("HeyGen avatar ID不能为空。")
        headers = {"X-Api-Key": self._api_key}
        upload = self._transport(
            "POST",
            f"{self._upload_base_url}/v1/asset",
            {**headers, "Content-Type": "application/octet-stream"},
            audio_path.read_bytes(),
            self._timeout_seconds,
        )
        asset_id = _response_data(upload, "HeyGen音频上传").get("id")
        if not asset_id:
            raise ValueError("HeyGen音频上传响应缺少asset ID。")
        width = int(settings.get("width") or 1080)
        height = int(settings.get("height") or 1920)
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": str(avatar_id),
                        "avatar_style": str(settings.get("avatar_style") or "normal"),
                    },
                    "voice": {"type": "audio", "audio_asset_id": str(asset_id)},
                    "background": {"type": "color", "value": str(settings.get("background_color") or "#101010")},
                }
            ],
            "dimension": {"width": width, "height": height},
        }
        created = self._transport(
            "POST",
            f"{self._api_base_url}/v2/video/generate",
            {**headers, "Content-Type": "application/json"},
            payload,
            self._timeout_seconds,
        )
        video_id = _response_data(created, "HeyGen视频创建").get("video_id")
        if not video_id:
            raise ValueError("HeyGen视频创建响应缺少video ID。")
        video_url = None
        for _ in range(self._max_polls):
            status_response = self._transport(
                "GET",
                f"{self._api_base_url}/v1/video_status.get?video_id={video_id}",
                headers,
                None,
                self._timeout_seconds,
            )
            data = _response_data(status_response, "HeyGen视频状态")
            status = str(data.get("status") or "").casefold()
            if status == "completed":
                video_url = str(data.get("video_url") or "")
                break
            if status in {"failed", "error", "canceled", "cancelled"}:
                raise RuntimeError(f"HeyGen视频任务失败：{data.get('error') or status}")
            self._sleep(self._poll_interval_seconds)
        if not video_url:
            raise RuntimeError("HeyGen视频任务查询超时。")
        downloaded = self._transport("GET", video_url, {}, None, self._timeout_seconds)
        status = int(downloaded.get("status") or 0)
        body = downloaded.get("body")
        if status < 200 or status >= 300 or not isinstance(body, (bytes, bytearray)) or not body:
            raise ValueError("HeyGen成片下载为空或失败。")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_bytes(bytes(body))
        temporary.replace(output_path)
        probe = probe_media(output_path)
        if not probe["has_video"] or not probe["has_audio"]:
            raise ValueError("HeyGen输出缺少视频或音轨。")
        return ProviderMediaResult(
            output_path=str(output_path),
            external_task_id=str(video_id),
            media_probe=probe,
            actual_consumption=_response_data(created, "HeyGen视频创建").get("credits_used"),
        )


class HeyGenCLIAdapter:
    """Production adapter for HeyGen CLI v0.5+ and the supported v3 API."""

    def __init__(
        self,
        *,
        cli_path: str | None = None,
        command_runner: HeyGenCommandRunner | None = None,
        poll_interval_seconds: float = 5.0,
        max_polls: int = 360,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        resolved = cli_path or shutil.which("heygen") or str(Path.home() / ".local" / "bin" / "heygen")
        if command_runner is None and not Path(resolved).is_file() and shutil.which(resolved) is None:
            raise ValueError("找不到HeyGen CLI；请安装官方CLI或在新会话连接HeyGen App。")
        self._cli_path = str(resolved)
        self._runner = command_runner or _run_heygen_command
        self._poll_interval_seconds = float(poll_interval_seconds)
        self._max_polls = int(max_polls)
        self._sleep = sleep

    def generate_presenter(
        self,
        *,
        audio_path: Path,
        avatar_id: str,
        settings: dict[str, Any],
        output_path: Path,
        resume_task_id: str | None = None,
        on_submitted: HeyGenSubmissionCallback | None = None,
    ) -> ProviderMediaResult:
        if not audio_path.is_file() or audio_path.stat().st_size <= 0:
            raise ValueError("HeyGen输入音频不存在或为空。")
        if not str(avatar_id).strip():
            raise ValueError("HeyGen avatar ID不能为空。")
        environment = dict(os.environ)
        environment.setdefault("HEYGEN_OUTPUT", "json")
        auth = self._runner([self._cli_path, "auth", "status"], environment)
        _require_heygen_success("HeyGen身份验证", auth)
        asset_id = ""
        request = {
            "type": "avatar",
            "avatar_id": str(avatar_id),
            "aspect_ratio": "9:16",
            "resolution": "1080p",
            "output_format": "mp4",
            "fit": str(settings.get("fit") or "cover"),
            "background": {
                "type": "color",
                "value": str(settings.get("background_color") or "#0D1321"),
            },
            "title": str(settings.get("title") or output_path.stem),
        }
        engine = str(settings.get("engine") or "avatar_iv")
        if engine not in {"avatar_iii", "avatar_iv", "avatar_v"}:
            raise ValueError("HeyGen engine必须是avatar_iii、avatar_iv或avatar_v。")
        request["engine"] = {"type": engine}
        if settings.get("motion_prompt"):
            request["motion_prompt"] = str(settings["motion_prompt"])
        request_path = output_path.with_suffix(".request.json")
        receipt_path = output_path.with_suffix(".task.json")
        receipt = _read_json_if_present(receipt_path)
        if receipt:
            asset_id = str(receipt.get("asset_id") or "")
            if asset_id:
                request["audio_asset_id"] = asset_id
        _write_json(request_path, request)
        request_hash = hashlib.sha256(request_path.read_bytes()).hexdigest()
        if resume_task_id:
            video_id = str(resume_task_id)
            if receipt and str(receipt.get("video_id") or "") not in {"", video_id}:
                raise ValueError("HeyGen恢复任务ID与本地回执冲突。")
            if receipt and str(receipt.get("request_sha256") or "") != request_hash:
                raise ValueError("HeyGen本地任务回执与当前请求不匹配，拒绝重复提交。")
        elif receipt:
            if str(receipt.get("request_sha256") or "") != request_hash:
                raise ValueError("HeyGen本地任务回执与当前请求不匹配，拒绝重复提交。")
            video_id = str(receipt.get("video_id") or "")
            if not video_id:
                raise ValueError("HeyGen本地任务回执缺少video_id。")
        else:
            uploaded = self._runner([self._cli_path, "asset", "create", "--file", str(audio_path)], environment)
            _require_heygen_success("HeyGen音频上传", uploaded)
            asset_data = _heygen_cli_data(uploaded, "HeyGen音频上传")
            asset_id = str(asset_data.get("asset_id") or "")
            if not asset_id:
                raise ValueError("HeyGen音频上传响应缺少asset_id。")
            request["audio_asset_id"] = asset_id
            _write_json(request_path, request)
            request_hash = hashlib.sha256(request_path.read_bytes()).hexdigest()
            created = self._runner(
                [self._cli_path, "video", "create", "--data", str(request_path)],
                environment,
            )
            _require_heygen_success("HeyGen视频创建", created)
            created_data = _heygen_cli_data(created, "HeyGen视频创建")
            video_id = str(created_data.get("video_id") or "")
            if not video_id:
                raise ValueError("HeyGen视频创建响应缺少video_id。")
            _write_json(
                receipt_path,
                {
                    "schema_version": "heygen-task-receipt-v1",
                    "video_id": video_id,
                    "asset_id": asset_id,
                    "request_sha256": request_hash,
                },
            )
        if on_submitted is not None:
            on_submitted(video_id)
        detail: dict[str, Any] = {}
        status = ""
        for poll_number in range(self._max_polls):
            detail_response = self._runner([self._cli_path, "video", "get", video_id], environment)
            _require_heygen_success("HeyGen视频状态", detail_response)
            detail = _heygen_cli_data(detail_response, "HeyGen视频状态")
            status = str(detail.get("status") or "").casefold()
            if status in {"completed", "success", "succeeded"}:
                break
            if status in {"failed", "error", "canceled", "cancelled"}:
                raise ProviderTaskFailed("heygen", video_id, f"HeyGen视频任务失败：{detail.get('error') or status}")
            if poll_number + 1 < self._max_polls:
                self._sleep(self._poll_interval_seconds)
        else:
            raise ProviderTaskPending("heygen", video_id, "HeyGen任务仍在执行；可稍后继续查询，不会重复提交。")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        downloaded = self._runner(
            [
                self._cli_path,
                "video",
                "download",
                video_id,
                "--output-path",
                str(output_path),
                "--force",
            ],
            environment,
        )
        _require_heygen_success("HeyGen视频下载", downloaded)
        try:
            probe = probe_media(output_path)
        except (ValueError, RuntimeError) as exc:
            raise ProviderTaskFailed("heygen", video_id, f"HeyGen下载产物不可读：{exc}") from exc
        if not probe["has_video"] or not probe["has_audio"]:
            raise ProviderTaskFailed("heygen", video_id, "HeyGen CLI输出缺少视频或音轨。")
        return ProviderMediaResult(
            output_path=str(output_path),
            external_task_id=video_id,
            media_probe=probe,
            actual_consumption=detail.get("credits_used"),
        )


def _fish_http_transport(
    url: str,
    headers: dict[str, str],
    payload: bytes,
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return {"status": response.status, "headers": dict(response.headers.items()), "body": response.read()}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "headers": dict(exc.headers.items()), "body": exc.read()}
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise TimeoutError from exc
        raise RuntimeError(f"Fish Audio网络请求失败：{exc.reason}") from exc


def _encode_msgpack(value: Any) -> bytes:
    """Encode the subset of MessagePack used by Fish Audio TTS requests.

    Keeping this tiny encoder local avoids making natural-language plugin use
    depend on an extra Python package. It supports the JSON-like values present
    in the official Fish Audio request schema.
    """

    if value is None:
        return b"\xc0"
    if value is False:
        return b"\xc2"
    if value is True:
        return b"\xc3"
    if isinstance(value, int) and not isinstance(value, bool):
        if 0 <= value <= 0x7F:
            return bytes([value])
        if -32 <= value < 0:
            return bytes([value & 0xFF])
        if 0 <= value <= 0xFF:
            return b"\xcc" + struct.pack(">B", value)
        if 0 <= value <= 0xFFFF:
            return b"\xcd" + struct.pack(">H", value)
        if 0 <= value <= 0xFFFFFFFF:
            return b"\xce" + struct.pack(">I", value)
        if value >= 0:
            return b"\xcf" + struct.pack(">Q", value)
        if value >= -0x80:
            return b"\xd0" + struct.pack(">b", value)
        if value >= -0x8000:
            return b"\xd1" + struct.pack(">h", value)
        if value >= -0x80000000:
            return b"\xd2" + struct.pack(">i", value)
        return b"\xd3" + struct.pack(">q", value)
    if isinstance(value, float):
        return b"\xcb" + struct.pack(">d", value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        size = len(raw)
        if size <= 31:
            return bytes([0xA0 | size]) + raw
        if size <= 0xFF:
            return b"\xd9" + struct.pack(">B", size) + raw
        if size <= 0xFFFF:
            return b"\xda" + struct.pack(">H", size) + raw
        return b"\xdb" + struct.pack(">I", size) + raw
    if isinstance(value, (list, tuple)):
        size = len(value)
        if size <= 15:
            prefix = bytes([0x90 | size])
        elif size <= 0xFFFF:
            prefix = b"\xdc" + struct.pack(">H", size)
        else:
            prefix = b"\xdd" + struct.pack(">I", size)
        return prefix + b"".join(_encode_msgpack(item) for item in value)
    if isinstance(value, dict):
        size = len(value)
        if size <= 15:
            prefix = bytes([0x80 | size])
        elif size <= 0xFFFF:
            prefix = b"\xde" + struct.pack(">H", size)
        else:
            prefix = b"\xdf" + struct.pack(">I", size)
        return prefix + b"".join(
            _encode_msgpack(str(key)) + _encode_msgpack(item)
            for key, item in value.items()
        )
    raise TypeError(f"无法编码为MessagePack的值：{type(value).__name__}")


def _response_data(response: dict[str, Any], operation: str) -> dict[str, Any]:
    status = int(response.get("status") or 0)
    if status < 200 or status >= 300:
        raise RuntimeError(f"{operation}返回HTTP {status}。")
    payload = response.get("json")
    if payload is None and isinstance(response.get("body"), (bytes, bytearray)):
        try:
            payload = json.loads(bytes(response["body"]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{operation}返回畸形JSON。") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{operation}返回畸形JSON。")
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise ValueError(f"{operation}响应缺少data对象。")
    return data


def _heygen_http_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    body: Any,
    timeout_seconds: float,
) -> dict[str, Any]:
    data = None
    if isinstance(body, (bytes, bytearray)):
        data = bytes(body)
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read()
            content_type = str(response.headers.get("Content-Type") or "")
            parsed = None
            if "json" in content_type:
                parsed = json.loads(response_body.decode("utf-8"))
            return {"status": response.status, "headers": dict(response.headers.items()), "body": response_body, "json": parsed}
    except urllib.error.HTTPError as exc:
        response_body = exc.read()
        return {"status": exc.code, "headers": dict(exc.headers.items()), "body": response_body}
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise TimeoutError from exc
        raise RuntimeError(f"HeyGen网络请求失败：{exc.reason}") from exc


def _run_heygen_command(command: list[str], environment: dict[str, str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("找不到HeyGen CLI。") from exc
    return {"returncode": completed.returncode, "stdout": completed.stdout or "", "stderr": completed.stderr or ""}


def _require_heygen_success(operation: str, result: dict[str, Any]) -> None:
    if int(result.get("returncode") or 0) == 0:
        return
    detail = _redact_cli_text(str(result.get("stderr") or result.get("stdout") or "unknown error"))[-2000:]
    raise RuntimeError(f"{operation}失败：{detail}")


def _heygen_cli_data(result: dict[str, Any], operation: str) -> dict[str, Any]:
    try:
        payload = json.loads(str(result.get("stdout") or "{}"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{operation}返回畸形JSON。") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{operation}返回畸形JSON。")
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise ValueError(f"{operation}响应缺少data对象。")
    return data


def _redact_cli_text(value: str) -> str:
    import re

    text = re.sub(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+", r"\1 ***", str(value))
    return re.sub(
        r"(?i)([?&](?:api[_-]?key|token|access[_-]?token|secret|password|cookie)=)[^&#\s]+",
        r"\1***",
        text,
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"本地任务回执损坏：{path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"本地任务回执损坏：{path}")
    return value
