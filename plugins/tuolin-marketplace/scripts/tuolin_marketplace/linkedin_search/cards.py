from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


IDENTITY_FIELDS = (
    "candidate_id",
    "post_url",
    "company_url",
    "member_profile_url",
)


def candidate_identity(card: dict[str, Any]) -> dict[str, str]:
    return {
        "candidate_id": str(card.get("candidate_id") or ""),
        "post_url": str(card.get("post_url") or ""),
        "company_url": str((card.get("company") or {}).get("url") or ""),
        "member_profile_url": str((card.get("selected_member") or {}).get("profile_url") or ""),
    }


def candidate_identity_digest(card: dict[str, Any]) -> str:
    value = candidate_identity(card)
    if any(not value[field] for field in IDENTITY_FIELDS):
        raise ValueError("候选身份缺少 candidate、post、company 或 member profile 标识。")
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_candidate_identity(card: dict[str, Any], expected_digest: str) -> None:
    if candidate_identity_digest(card) != expected_digest:
        raise ValueError(f"候选身份已变化：{card.get('candidate_id')}。必须重新审核，旧授权无效。")


def candidate_review_digest(card: dict[str, Any]) -> str:
    snapshot = {
        "identity": candidate_identity(card),
        "source_keyword": card.get("source_keyword"),
        "post_text": card.get("post_text"),
        "relevance_decision": card.get("relevance_decision"),
        "relevance_reason": card.get("relevance_reason"),
        "fit_status": card.get("fit_status"),
        "business_role": card.get("business_role"),
        "supporting_evidence": card.get("supporting_evidence"),
        "material_doubts": card.get("material_doubts"),
        "author": card.get("author"),
        "company": card.get("company"),
        "selected_member": card.get("selected_member"),
        "selection_reason": card.get("selection_reason"),
        "connect_path": card.get("connect_path"),
    }
    serialized = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_candidate_review(card: dict[str, Any], expected_digest: str) -> None:
    if candidate_review_digest(card) != expected_digest:
        raise ValueError(f"候选审核内容已变化：{card.get('candidate_id')}。必须重新审核，旧授权无效。")


def persist_candidate_card(run_dir: Path, card: dict[str, Any]) -> tuple[Path, Path]:
    candidate_dir = Path(run_dir) / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    candidate_id = str(card["candidate_id"])
    card["identity_digest"] = candidate_identity_digest(card)
    json_path = candidate_dir / f"{candidate_id}.json"
    markdown_path = candidate_dir / f"{candidate_id}.md"
    _write_json_atomic(json_path, card)
    markdown_path.write_text(render_candidate_card(card), encoding="utf-8")
    return markdown_path, json_path


def render_candidate_card(card: dict[str, Any], *, heading: str | None = None) -> str:
    member = card["selected_member"]
    company = card["company"]
    author = card["author"]
    author_type = "公司" if author.get("type") == "company" else "个人"
    note = card.get("note_decision")
    lines = [
        heading or f"## 候选卡：{member['name']}",
        "",
        f"- Candidate ID：{card['candidate_id']}",
        f"- 来源关键词：{card['source_keyword']}",
        "",
        "### 完整可见贴文",
        "",
        card["post_text"],
        "",
        f"- 贴文 URL：{card['post_url']}",
        f"- 相关理由：{card['relevance_reason']}",
        f"- 暂定业务角色：{card.get('business_role') or 'ambiguous'}",
        f"- 支持证据：{card.get('supporting_evidence') or card['relevance_reason']}",
        f"- 重大疑点：{card.get('material_doubts') or '无'}",
        "- 判断性质：AI 暂定，最终由人工批量审核决定",
        f"- 作者：{author['name']}（{author_type}）",
        f"- 作者主页：{author['profile_url']}",
        f"- 公司：{company['name']}",
        f"- 公司主页：{company['url']}",
        f"- 联系人：{member['name']}",
        f"- 职位：{member['title']}",
        f"- 联系人公司：{member['company']}",
        f"- Profile：{member['profile_url']}",
        f"- Connect 证据：{card.get('connect_path') or '未验证'}",
    ]
    if card.get("selection_reason"):
        lines.append(f"- 联系人选择理由：{card['selection_reason']}")
    lines.extend(
        [
            f"- 审核状态：{card.get('approval')}",
            f"- 留言决策：{json.dumps(note, ensure_ascii=False) if note is not None else '未决定'}",
            f"- 最终结果：{card.get('final_outcome') or '未执行'}",
            f"- 身份摘要：{card.get('identity_digest') or candidate_identity_digest(card)}",
            "",
        ]
    )
    return "\n".join(lines)


def render_candidate_batch(payload: dict[str, Any], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        f"候选人数：{payload['candidate_count']}",
        "",
        "确认前可以删除候选；删除后不会自动找补。",
        "",
    ]
    for index, card in enumerate(payload.get("candidates") or [], start=1):
        lines.append(render_candidate_card(card, heading=f"## {index}. {card['selected_member']['name']}").rstrip())
        lines.append("")
    return "\n".join(lines)


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
