from __future__ import annotations

import re
from pathlib import Path


def write_srt(narration: str, language: str, duration_seconds: float, output_path: Path) -> Path:
    text = str(narration).strip()
    if not text:
        raise ValueError("字幕不能从空旁白生成。")
    if language not in {"en", "zh"}:
        raise ValueError("字幕语言必须与运行语言一致。")
    chunks = _caption_chunks(text, language)
    weights = [max(len(re.sub(r"\s+", "", item)), 1) for item in chunks]
    total_weight = sum(weights)
    cursor = 0.0
    cues = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        end = duration_seconds if index == len(chunks) else cursor + duration_seconds * weight / total_weight
        cues.append(f"{index}\n{_timestamp(cursor)} --> {_timestamp(end)}\n{chunk}\n")
        cursor = end
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(cues), encoding="utf-8")
    return output_path


def _caption_chunks(text: str, language: str) -> list[str]:
    sentence_pattern = r"(?<=[。！？!?])" if language == "zh" else r"(?<=[.!?])\s+"
    sentences = [item.strip() for item in re.split(sentence_pattern, text) if item.strip()]
    limit = 18 if language == "zh" else 52
    chunks: list[str] = []
    for sentence in sentences or [text]:
        if len(sentence) <= limit:
            chunks.append(sentence)
            continue
        if language == "en":
            words = sentence.split()
            current = []
            for word in words:
                candidate = " ".join([*current, word])
                if current and len(candidate) > limit:
                    chunks.append(" ".join(current))
                    current = [word]
                else:
                    current.append(word)
            if current:
                chunks.append(" ".join(current))
        else:
            chunks.extend(sentence[start : start + limit] for start in range(0, len(sentence), limit))
    return chunks


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
