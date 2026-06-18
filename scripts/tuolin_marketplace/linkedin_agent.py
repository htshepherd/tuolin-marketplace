from __future__ import annotations

import csv
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .downstream_context import build_downstream_context
from .project_layout import ProjectPaths


INTERNAL_PRODUCT_ID = "product/quartz_fiber_tape"
INTERNAL_PRODUCT_NAME = "石英纤维隔热带"
EXTERNAL_PRODUCT_NAME_ZH = "特种玻璃纤维带"
EXTERNAL_PRODUCT_NAME_EN = "Specialty Glass Fiber Tape"
DEFAULT_CONTACT_EMAIL = "tuolin@tuolintech.com"
DEFAULT_CAMPAIGN_DAYS = 30
DEFAULT_TRANSPARENT_LOGO_RELATIVE_PATH = Path("assets/logo/tuolin-logo-transparent.png")
MARKETING_REVIEW_FILENAME = "01_中文策划_营销审阅.md"
DESKTOP_DELIVERY_DIR_PREFIX = "LinkedIn-30-Day-Special-Fiberglass-Tape-For-Review"

IMAGE_STYLE_CATEGORIES = [
    {"slug": "original-light-enhancement", "name": "原图轻量增强型", "recommended_for": ["产品", "首发", "日常"]},
    {"slug": "minimal-premium", "name": "极简高端型", "recommended_for": ["首发", "复盘", "品牌"]},
    {"slug": "industrial-technical", "name": "工业技术型", "recommended_for": ["技术", "参数", "工程"]},
    {"slug": "engineering-drawing", "name": "工程图纸型", "recommended_for": ["尺寸", "工程", "规格"]},
    {"slug": "product-detail-closeup", "name": "产品细节特写型", "recommended_for": ["织纹", "细节", "不刺痒"]},
    {"slug": "technical-parameter-card", "name": "技术参数卡片型", "recommended_for": ["1000", "参数", "卖点"]},
    {"slug": "three-benefit-banner", "name": "三大卖点横幅型", "recommended_for": ["1000", "不刺痒", "不冒烟"]},
    {"slug": "application-scenario", "name": "应用场景型", "recommended_for": ["应用", "场景"]},
    {"slug": "exhaust-wrap-scenario", "name": "排气管包覆场景型", "recommended_for": ["排气", "exhaust"]},
    {"slug": "industrial-pipe-insulation", "name": "工业管道保温型", "recommended_for": ["管道", "保温"]},
    {"slug": "high-temperature-test", "name": "高温测试型", "recommended_for": ["高温", "1000"]},
    {"slug": "cutting-processing", "name": "切割加工型", "recommended_for": ["切割", "加工", "不冒烟"]},
    {"slug": "comfortable-handling", "name": "手感舒适型", "recommended_for": ["不刺痒", "安装"]},
    {"slug": "pain-point-solution", "name": "痛点解决型", "recommended_for": ["痛点", "问题"]},
    {"slug": "buyer-checklist", "name": "采购清单型", "recommended_for": ["采购", "清单"]},
    {"slug": "inquiry-conversion", "name": "询盘转化型", "recommended_for": ["询盘", "样品", "联系"]},
    {"slug": "specification-display", "name": "规格展示型", "recommended_for": ["规格", "尺寸"]},
    {"slug": "multi-spec-combination", "name": "多规格组合型", "recommended_for": ["多规格", "组合"]},
    {"slug": "split-screen-comparison", "name": "分屏对比型", "recommended_for": ["对比", "传统"]},
    {"slug": "qa-education", "name": "问答科普型", "recommended_for": ["FAQ", "为什么", "科普"]},
]

CONFIRMED_CLAIMS = [
    {"zh": "耐高温1000度", "en": "withstands temperatures up to 1000°C", "tokens": ["1000", "1000°", "1000度"]},
    {"zh": "不刺痒", "en": "no itching sensation when handled", "tokens": ["不刺痒", "no itching", "itching"]},
    {"zh": "不冒烟", "en": "no smoke during use", "tokens": ["不冒烟", "no smoke", "smoke"]},
]


@dataclass(frozen=True)
class ProjectValidation:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class LinkedInCampaignResult:
    campaign_dir: str
    plan_path: str
    manifest_path: str
    context_id: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LinkedInImageSelectionResult:
    campaign_dir: str
    day_number: int
    selection_path: str
    manifest_path: str
    source_images: tuple[dict[str, Any], ...]
    recommended_categories: tuple[dict[str, str], ...]
    not_recommended_categories: tuple[dict[str, str], ...]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LinkedInImageGenerationPlan:
    campaign_dir: str
    day_number: int
    manifest_path: str
    source_image: str
    categories: tuple[dict[str, str], ...]
    output_dirs: tuple[str, ...]
    desktop_output_dirs: tuple[str, ...]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_linkedin_campaign_request(text: str) -> bool:
    utterance = text.strip().lower()
    if not utterance:
        return False
    mentions_linkedin = "linkedin" in utterance or "领英" in utterance
    mentions_campaign = any(token in utterance for token in ["30天", "发帖", "发贴", "宣传", "计划"])
    return mentions_linkedin and mentions_campaign


def validate_linkedin_project(paths: ProjectPaths) -> ProjectValidation:
    required = [
        paths.generated_dir / "agent-interface" / "manifest.json",
        paths.generated_dir / "agent-interface" / "manifest_summary.json",
        paths.generated_dir / "agent-interface" / "cards",
        paths.generated_dir / "indexes" / "cards.json",
    ]
    errors = []
    for path in required:
        if not path.exists():
            errors.append(f"缺少知识库 Agent读取接口文件：{_display_path(paths.project_dir, path)}")
    return ProjectValidation(valid=not errors, errors=tuple(errors))


def default_linkedin_transparent_logo_path(paths: ProjectPaths) -> Path:
    config = paths.config or {}
    linkedin_config = config.get("linkedin")
    configured = None
    if isinstance(linkedin_config, dict):
        configured = linkedin_config.get("transparent_logo_path")
    if not configured:
        configured = config.get("linkedin_transparent_logo_path")
    if not configured:
        configured = str(DEFAULT_TRANSPARENT_LOGO_RELATIVE_PATH)
    return _resolve_project_path(paths.project_dir, str(configured))


def create_linkedin_campaign_plan(
    paths: ProjectPaths,
    request_text: str,
    output_root: Path | None = None,
    now: datetime | None = None,
) -> LinkedInCampaignResult:
    validation = validate_linkedin_project(paths)
    if not validation.valid:
        raise ValueError("当前目录不是可用于 LinkedIn Agent 的知识库项目目录：" + "；".join(validation.errors))

    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M")
    root = output_root or Path.home() / "Desktop"
    campaign_dir = root.expanduser().resolve() / f"拓霖领英30天_{EXTERNAL_PRODUCT_NAME_ZH}_{timestamp}"
    _ensure_campaign_dirs(campaign_dir)

    context = build_downstream_context(
        paths,
        "linkedin_post",
        product_id=INTERNAL_PRODUCT_ID,
        query=request_text,
        include_review_items=True,
    )
    claim_sources = _claim_sources(context, request_text)
    plan_path = campaign_dir / "01_中文策划.md"
    manifest_path = campaign_dir / "campaign-manifest.json"

    content_assets = _content_assets(context)
    plan_path.write_text(_render_chinese_plan(request_text, context, claim_sources, content_assets), encoding="utf-8")
    manifest = _manifest(
        campaign_dir,
        plan_path,
        context,
        claim_sources,
        content_assets,
        request_text,
        timestamp,
        default_transparent_logo_path=default_linkedin_transparent_logo_path(paths),
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInCampaignResult(
        campaign_dir=str(campaign_dir),
        plan_path=str(plan_path),
        manifest_path=str(manifest_path),
        context_id=context["context_id"],
        status="planning_ready",
    )


def _resolve_project_path(project_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return path.resolve()


def confirm_linkedin_campaign_plan(campaign_dir: Path, overwrite: bool = False) -> LinkedInCampaignResult:
    return decide_linkedin_marketing_review(campaign_dir, "skipped", overwrite=overwrite)


def create_linkedin_marketing_review(campaign_dir: Path, overwrite: bool = False) -> LinkedInCampaignResult:
    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status not in {"planning_ready", "marketing_review_ready"}:
        raise ValueError(f"当前活动状态是 {status!r}，不能进行营销策划审阅。请先生成中文策划。")

    plan_path = Path(manifest["files"]["chinese_plan"])
    if not plan_path.exists():
        raise ValueError(f"找不到已生成的中文策划文件：{plan_path}")

    review_path = campaign_dir / MARKETING_REVIEW_FILENAME
    if review_path.exists() and not overwrite:
        raise FileExistsError(f"营销策划审阅文件已存在，未覆盖：{review_path}")

    review = _marketing_review_payload(plan_path, manifest)
    review_path.write_text(_render_marketing_review(review, manifest), encoding="utf-8")
    manifest["status"] = "marketing_review_ready"
    _append_status_history(manifest, "marketing_review_ready")
    manifest["marketing_review"] = {
        "status": "ready",
        "review_path": str(review_path),
        "result": review["result"],
        "decision": None,
        "decision_at": None,
        "applied_to_chinese_draft": False,
        "risk_override": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInCampaignResult(
        campaign_dir=str(campaign_dir),
        plan_path=str(review_path),
        manifest_path=str(manifest_path),
        context_id=manifest["context"]["context_id"],
        status="marketing_review_ready",
    )


def decide_linkedin_marketing_review(
    campaign_dir: Path,
    decision: str,
    overwrite: bool = False,
) -> LinkedInCampaignResult:
    if decision not in {"skipped", "accepted", "rejected"}:
        raise ValueError(f"不支持的营销策划审阅决策：{decision}")

    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status not in {"planning_ready", "marketing_review_ready"}:
        raise ValueError(f"当前活动状态是 {status!r}，不能生成中文30天贴文总稿。请先完成中文策划。")

    plan_path = Path(manifest["files"]["chinese_plan"])
    if not plan_path.exists():
        raise ValueError(f"找不到已生成的中文策划文件：{plan_path}")

    if decision in {"accepted", "rejected"}:
        review_path = Path(str(manifest.get("marketing_review", {}).get("review_path", "")))
        if not review_path.exists():
            raise ValueError("采纳或不采纳营销审阅建议前，必须先生成营销策划审阅文件。")

    draft_path = campaign_dir / "02_中文30天贴文总稿.md"
    if draft_path.exists() and not overwrite:
        raise FileExistsError(f"中文30天贴文总稿已存在，未覆盖：{draft_path}")

    manifest["marketing_review"] = _resolved_marketing_review(manifest, decision)
    _append_status_history(manifest, f"marketing_review_{decision}")
    manifest["status"] = "chinese_draft_ready"
    _append_status_history(manifest, "chinese_draft_ready")
    manifest["files"]["chinese_draft"] = str(draft_path)
    draft_path.write_text(_render_chinese_30_day_draft(manifest), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInCampaignResult(
        campaign_dir=str(campaign_dir),
        plan_path=str(draft_path),
        manifest_path=str(manifest_path),
        context_id=manifest["context"]["context_id"],
        status="chinese_draft_ready",
    )


def confirm_linkedin_chinese_draft(campaign_dir: Path, overwrite: bool = False) -> LinkedInCampaignResult:
    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status != "chinese_draft_ready":
        raise ValueError(f"当前活动状态是 {status!r}，不能生成英文发布包。请先完成中文30天贴文总稿。")

    draft_path = Path(manifest["files"]["chinese_draft"])
    if not draft_path.exists():
        raise ValueError(f"找不到已生成的中文30天贴文总稿：{draft_path}")

    overview_path = campaign_dir / "03_英文发布总览.md"
    calendar_path = campaign_dir / "04_英文发布日历.csv"
    daily_dir = campaign_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    daily_paths = [daily_dir / f"day-{day['day']:02d}.md" for day in _campaign_days()]
    existing = [path for path in [overview_path, calendar_path, *daily_paths] if path.exists()]
    if existing and not overwrite:
        raise FileExistsError("英文发布包文件已存在，未覆盖：" + "；".join(str(path) for path in existing))

    english_posts = [_english_post(day, manifest) for day in _campaign_days()]
    overview_path.write_text(_render_english_overview(english_posts, manifest), encoding="utf-8")
    _write_english_calendar(calendar_path, english_posts)
    for post, path in zip(english_posts, daily_paths):
        path.write_text(_render_daily_english_file(post, manifest), encoding="utf-8")
    manual_files = _write_manual_posting_package(campaign_dir, english_posts, manifest)

    _append_status_history(manifest, "chinese_draft_confirmed")
    manifest["status"] = "english_package_ready"
    _append_status_history(manifest, "english_package_ready")
    manifest["files"]["english_overview"] = str(overview_path)
    manifest["files"]["english_calendar"] = str(calendar_path)
    manifest["files"]["daily_files"] = [str(path) for path in daily_paths]
    manifest["files"].update(manual_files)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInCampaignResult(
        campaign_dir=str(campaign_dir),
        plan_path=str(overview_path),
        manifest_path=str(manifest_path),
        context_id=manifest["context"]["context_id"],
        status="english_package_ready",
    )


def create_linkedin_image_selection_sheet(campaign_dir: Path, day_number: int) -> LinkedInImageSelectionResult:
    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")
    if day_number < 1 or day_number > DEFAULT_CAMPAIGN_DAYS:
        raise ValueError(f"Day 必须在 1 到 {DEFAULT_CAMPAIGN_DAYS} 之间：{day_number}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status not in {"english_package_ready", "image_selection_ready", "image_generation_ready"}:
        raise ValueError(f"当前活动状态是 {status!r}，不能生成发布图选择单。请先生成英文发布包和人工发布包。")

    source_images = _day_source_images(campaign_dir, day_number)
    if not source_images:
        raise ValueError(f"Day {day_number:02d} 的 assets 目录没有源图。请先把当天源图放入该目录。")

    day = _campaign_days()[day_number - 1]
    recommended = _recommended_image_categories(day, source_images)
    not_recommended = _not_recommended_image_categories(day, source_images)
    selection_path = _manual_day_dir(campaign_dir, day_number) / "Publishing Image Selection.md"
    selection_path.write_text(
        _render_image_selection_sheet(day, manifest, source_images, recommended, not_recommended),
        encoding="utf-8",
    )

    day_key = f"day-{day_number:02d}"
    manifest.setdefault("single_day_images", {})[day_key] = {
        "selection_sheet_status": "shown",
        "selection_sheet_path": str(selection_path),
        "source_images": source_images,
        "recommended_categories": recommended,
        "not_recommended_categories": not_recommended,
    }
    manifest["status"] = "image_selection_ready"
    _append_status_history(manifest, f"{day_key}_image_selection_ready")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInImageSelectionResult(
        campaign_dir=str(campaign_dir),
        day_number=day_number,
        selection_path=str(selection_path),
        manifest_path=str(manifest_path),
        source_images=tuple(source_images),
        recommended_categories=tuple(recommended),
        not_recommended_categories=tuple(not_recommended),
        status="image_selection_ready",
    )


def prepare_linkedin_image_generation(
    campaign_dir: Path,
    day_number: int,
    source_index: int,
    category_values: list[str],
) -> LinkedInImageGenerationPlan:
    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")
    if day_number < 1 or day_number > DEFAULT_CAMPAIGN_DAYS:
        raise ValueError(f"Day 必须在 1 到 {DEFAULT_CAMPAIGN_DAYS} 之间：{day_number}")
    if not category_values:
        raise ValueError("生成单日发布图需要选择 1-3 个风格类别。")
    if len(category_values) > 3:
        raise ValueError("一次最多只能选择 3 个发布图风格类别。")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    day_key = f"day-{day_number:02d}"
    selection = manifest.get("single_day_images", {}).get(day_key)
    if not selection:
        raise ValueError(f"请先生成 Day {day_number:02d} 发布图选择单。")
    source_images = selection.get("source_images", [])
    if source_index < 1 or source_index > len(source_images):
        raise ValueError(f"源图编号无效：{source_index}。请选择 1 到 {len(source_images)}。")
    source_image = source_images[source_index - 1]
    categories = [_resolve_image_category(value) for value in category_values]
    output_dirs = []
    desktop_output_dirs = []
    for category in categories:
        output_dir = _manual_day_publish_images_dir(campaign_dir, day_number) / category["slug"]
        output_dir.mkdir(parents=True, exist_ok=True)
        output_dirs.append(str(output_dir))
        desktop_root = manifest.get("desktop_delivery", {}).get("path")
        if desktop_root:
            desktop_dir = (
                Path(desktop_root)
                / "Manual-Posting-Package"
                / f"Day {day_number:02d}"
                / "Publish-Images"
                / category["slug"]
            )
            desktop_dir.mkdir(parents=True, exist_ok=True)
            desktop_output_dirs.append(str(desktop_dir))

    selection.update(
        {
            "selected_source_image": source_image,
            "selected_categories": categories,
            "output_dirs": output_dirs,
            "desktop_output_dirs": desktop_output_dirs,
            "generation_status": "ready_for_codex_image_model",
            "generated_at": None,
        }
    )
    manifest["status"] = "image_generation_ready"
    _append_status_history(manifest, f"{day_key}_image_generation_ready")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInImageGenerationPlan(
        campaign_dir=str(campaign_dir),
        day_number=day_number,
        manifest_path=str(manifest_path),
        source_image=str(source_image["path"]),
        categories=tuple(categories),
        output_dirs=tuple(output_dirs),
        desktop_output_dirs=tuple(desktop_output_dirs),
        status="image_generation_ready",
    )


def _ensure_campaign_dirs(campaign_dir: Path) -> None:
    for relative in [
        ".",
        "daily",
        "assets/logo",
        "assets/source-images",
    ]:
        (campaign_dir / relative).mkdir(parents=True, exist_ok=True)


def _claim_sources(context: dict[str, Any], request_text: str) -> list[dict[str, Any]]:
    context_text = _context_text(context).lower()
    request_lower = request_text.lower()
    result = []
    for claim in CONFIRMED_CLAIMS:
        supported = any(token.lower() in context_text for token in claim["tokens"])
        user_confirmed = any(token.lower() in request_lower for token in claim["tokens"]) or claim["zh"] in request_text
        if supported:
            source = "official_external_knowledge"
        elif user_confirmed:
            source = "campaign_user_confirmed"
        else:
            source = "missing"
        result.append(
            {
                "claim_zh": claim["zh"],
                "claim_en": claim["en"],
                "source": source,
                "requires_publish_review": source != "official_external_knowledge",
            }
        )
    return result


def _context_text(context: dict[str, Any]) -> str:
    parts: list[str] = []
    for cards in context.get("cards_by_type", {}).values():
        for card in cards:
            parts.extend(
                [
                    card.get("title", ""),
                    " ".join(card.get("aliases", [])),
                    " ".join(card.get("tags", [])),
                    card.get("body_excerpt", ""),
                ]
            )
    for evidence in context.get("evidence", []):
        parts.extend([evidence.get("title", ""), evidence.get("body_excerpt", "")])
    return "\n".join(parts)


def _content_assets(context: dict[str, Any]) -> list[dict[str, Any]]:
    assets = []
    for card in context.get("cards_by_type", {}).get("content_asset", []):
        frontmatter = card.get("frontmatter", {})
        assets.append(
            {
                "id": card.get("id", ""),
                "title": card.get("title", ""),
                "media_types": frontmatter.get("media_types", []),
                "usable_for": frontmatter.get("usable_for", []),
                "tags": card.get("tags", []),
                "card_path": card.get("path", ""),
                "usage_note": "仅用于配图、画面说明和 image brief，不能证明产品性能事实。",
            }
        )
    return assets


def _marketing_review_payload(plan_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    plan_text = plan_path.read_text(encoding="utf-8")
    risks: list[str] = []
    suggestions: list[str] = []

    if EXTERNAL_PRODUCT_NAME_ZH not in plan_text:
        risks.append(f"策划中没有稳定出现对外中文产品名「{EXTERNAL_PRODUCT_NAME_ZH}」。")
        suggestions.append(f"统一使用「{EXTERNAL_PRODUCT_NAME_ZH}」作为中文对外名称。")
    if EXTERNAL_PRODUCT_NAME_EN not in plan_text:
        suggestions.append(f"在英文对外素材中统一使用「{EXTERNAL_PRODUCT_NAME_EN}」。")
    for claim in CONFIRMED_CLAIMS:
        if claim["zh"] not in plan_text and not any(token in plan_text for token in claim["tokens"]):
            risks.append(f"核心卖点「{claim['zh']}」覆盖不足。")
            suggestions.append(f"在内容节奏中补充「{claim['zh']}」对应的教育或转化主题。")

    blocked_terms = ["环保", "无致癌", "马力提升", "降噪", "固定降温", "A1", "asbestos-free"]
    found_blocked = [term for term in blocked_terms if term.lower() in plan_text.lower()]
    if found_blocked:
        risks.append("策划中出现需要报告或证据支持的高风险词：" + "、".join(found_blocked))
        suggestions.append("删除或改为仅在报告已审核并附图时使用的谨慎表述。")

    if not risks:
        result = "recommended"
        conclusion = "建议通过"
        risks.append("未发现阻塞性营销策划风险。")
    elif len(risks) <= 2:
        result = "recommended_with_changes"
        conclusion = "建议修改后通过"
    else:
        result = "not_recommended"
        conclusion = "不建议直接继续"

    suggestions.extend(
        [
            "保持欧美 B2B 语气，优先面向工业采购、分销商、维修维护团队和热管理相关从业者。",
            "将图片生产与内容包生产拆开，发布图按 Day 单独生成。",
            "继续避免把内容素材当作性能事实证据。",
        ]
    )
    return {
        "result": result,
        "conclusion": conclusion,
        "risks": risks,
        "suggestions": suggestions,
    }


def _render_marketing_review(review: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [
        "# LinkedIn 中文策划营销审阅",
        "",
        "## 审阅结论",
        "",
        f"- 结论：{review['conclusion']}",
        f"- 是否建议进入中文 30 天贴文总稿：{'是' if review['result'] != 'not_recommended' else '否，除非员工确认 override'}",
        "",
        "## 审阅范围",
        "",
        "- 只审阅 `01_中文策划.md` 的营销质量、市场适配和对外表达风险。",
        "- 不调用知识库复核项流程。",
        "- 不写回正式知识层。",
        "",
        "## 检查项",
        "",
        f"- 欧美 B2B 市场适配：面向工业采购、工业品分销商、维修维护团队和热管理相关从业者。",
        f"- 对外中文名：{EXTERNAL_PRODUCT_NAME_ZH}",
        f"- 对外英文名：{EXTERNAL_PRODUCT_NAME_EN}",
        "- 核心卖点：1000°C working temperature、itch-free handling、no smoke。",
        "- 发布方式：人工检查后手动发布，不自动发布。",
        "",
        "## 风险",
        "",
    ]
    lines.extend(f"- {risk}" for risk in review["risks"])
    lines.extend(["", "## 修改建议", ""])
    lines.extend(f"- {suggestion}" for suggestion in review["suggestions"])
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 如采纳：生成中文 30 天贴文总稿时应用上述建议。",
            "- 如不采纳：仍可继续生成中文 30 天贴文总稿，但 manifest 和总稿中应记录未采纳状态。",
        ]
    )
    return "\n".join(lines) + "\n"


def _resolved_marketing_review(manifest: dict[str, Any], decision: str) -> dict[str, Any]:
    current = dict(manifest.get("marketing_review") or {})
    if not current:
        current = {
            "status": "skipped",
            "review_path": None,
            "result": "not_reviewed",
        }
    current["status"] = decision
    current["decision"] = decision
    current["decision_at"] = datetime.now().strftime("%Y%m%d_%H%M%S")
    current["applied_to_chinese_draft"] = decision == "accepted"
    current["risk_override"] = decision == "rejected" and current.get("result") == "not_recommended"
    return current


def _marketing_review_lines(manifest: dict[str, Any]) -> list[str]:
    review = manifest.get("marketing_review") or {}
    status = review.get("status", "skipped")
    if status == "accepted":
        return [
            f"- 营销策划审阅：已采纳。",
            f"- 审阅文件：{review.get('review_path')}",
            "- 本中文总稿生成时应应用审阅建议。",
        ]
    if status == "rejected":
        lines = [
            "- 营销策划审阅：未采纳，员工确认继续。",
            f"- 审阅文件：{review.get('review_path')}",
        ]
        if review.get("risk_override"):
            lines.append("- 审阅结论为不建议继续，但员工已确认 override。")
        return lines
    if status == "ready":
        return ["- 营销策划审阅：已生成但尚未决策。"]
    return ["- 营销策划审阅：已跳过。"]


def _render_chinese_plan(
    request_text: str,
    context: dict[str, Any],
    claim_sources: list[dict[str, Any]],
    content_assets: list[dict[str, Any]],
) -> str:
    product_cards = context.get("cards_by_type", {}).get("product", [])
    scenario_cards = context.get("cards_by_type", {}).get("application_scenario", [])
    sales_cards = context.get("cards_by_type", {}).get("sales_material", [])
    asset_cards = context.get("cards_by_type", {}).get("content_asset", [])
    risk_items = context.get("risk_items", [])
    lines = [
        "# LinkedIn 30天中文策划",
        "",
        "## 活动定位",
        "",
        f"- 内部检索产品：{INTERNAL_PRODUCT_NAME} / {INTERNAL_PRODUCT_ID}",
        f"- 对外中文产品名：{EXTERNAL_PRODUCT_NAME_ZH}",
        f"- 对外英文产品名：{EXTERNAL_PRODUCT_NAME_EN}",
        "- 目标市场：欧美市场",
        "- 目标受众：工业采购、工业品分销商、维修维护团队、热管理相关从业者",
        "- 发布方式：人工检查后手动发布，不自动发布 LinkedIn",
        "",
        "## 用户原始需求",
        "",
        request_text.strip(),
        "",
        "## 可用知识上下文",
        "",
        f"- 产品卡：{len(product_cards)} 张",
        f"- 应用场景卡：{len(scenario_cards)} 张",
        f"- 销售物料卡：{len(sales_cards)} 张",
        f"- 内容素材卡：{len(asset_cards)} 张（只用于配图，不证明产品事实）",
        f"- 风险提示：{len(risk_items)} 条",
        "",
        "## 核心卖点与发布前复核",
        "",
    ]
    for item in claim_sources:
        review = "需要发布前复核" if item["requires_publish_review"] else "已有正式对外知识支持"
        lines.append(f"- {item['claim_zh']}：{item['source']}，{review}")
    lines.extend(
        [
            "",
            "## 30天内容节奏",
            "",
            "- 第1-5天：产品认知与核心差异化，建立“特种玻璃纤维带”的对外名称。",
            "- 第6-10天：围绕高温隔热、接触体验和使用过程稳定性展开应用教育。",
            "- 第11-15天：面向采购和分销商说明适用场景、选型关注点和询盘信息。",
            "- 第16-20天：用 FAQ、误区澄清和对比角度降低客户疑虑。",
            "- 第21-25天：突出工厂供货、资料索取、样品沟通和长期合作价值。",
            "- 第26-30天：复盘核心卖点，形成询盘和样品请求的轻量 CTA。",
            "",
            "## 配图策略",
            "",
            "- 优先使用 Agent读取接口中允许对外使用的真实内容素材。",
            "- 没有真实素材时，只生成配图 brief 和 AI 作图提示，不伪装成产品实拍。",
            "- 每张图预留 Tuolin 透明 logo 和 2-3 个画面 tags。",
            "",
            "## 可用配图素材",
            "",
            *_asset_plan_lines(content_assets),
            "",
            "## 下一步",
            "",
            "确认本策划后，生成 `02_中文30天贴文总稿.md`。",
        ]
    )
    return "\n".join(lines) + "\n"


def _manifest(
    campaign_dir: Path,
    plan_path: Path,
    context: dict[str, Any],
    claim_sources: list[dict[str, Any]],
    content_assets: list[dict[str, Any]],
    request_text: str,
    timestamp: str,
    default_transparent_logo_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "linkedin-campaign-v1",
        "status": "planning_ready",
        "status_history": [{"status": "planning_ready", "at": timestamp}],
        "created_at": timestamp,
        "campaign_dir": str(campaign_dir),
        "request_text": request_text,
        "product": {
            "internal_id": INTERNAL_PRODUCT_ID,
            "internal_name": INTERNAL_PRODUCT_NAME,
            "external_name_zh": EXTERNAL_PRODUCT_NAME_ZH,
            "external_name_en": EXTERNAL_PRODUCT_NAME_EN,
        },
        "contact_email": DEFAULT_CONTACT_EMAIL,
        "campaign_days": DEFAULT_CAMPAIGN_DAYS,
        "context": {
            "context_id": context["context_id"],
            "interface_revision": context["interface_revision"],
            "raw_access": context["raw_access"],
            "policy": context["policy"],
        },
        "claim_sources": claim_sources,
        "content_assets": content_assets,
        "image_policy": {
            "source_boundary": "Agent读取接口中的 content_asset 卡",
            "content_assets_prove_product_facts": False,
            "missing_real_asset_behavior": "生成配图 brief 和 AI 作图提示，不伪装成产品实拍",
            "watermark_requires_transparent_logo": True,
            "default_transparent_logo_path": str(default_transparent_logo_path),
            "transparent_logo_config_key": "linkedin.transparent_logo_path",
        },
        "files": {
            "chinese_plan": str(plan_path),
            "chinese_draft": None,
            "english_overview": None,
            "english_calendar": None,
            "daily_dir": str(campaign_dir / "daily"),
            "logo_dir": str(campaign_dir / "assets" / "logo"),
            "default_transparent_logo": str(default_transparent_logo_path),
            "source_images_dir": str(campaign_dir / "assets" / "source-images"),
        },
    }


def _append_status_history(manifest: dict[str, Any], status: str) -> None:
    history = manifest.setdefault("status_history", [])
    history.append({"status": status, "at": datetime.now().strftime("%Y%m%d_%H%M%S")})


def _render_chinese_30_day_draft(manifest: dict[str, Any]) -> str:
    claim_lines = _claim_review_lines(manifest.get("claim_sources", []))
    lines = [
        "# LinkedIn 30天中文贴文总稿",
        "",
        "## 活动说明",
        "",
        f"- 对外产品名：{EXTERNAL_PRODUCT_NAME_ZH}",
        f"- 对外英文名：{EXTERNAL_PRODUCT_NAME_EN}",
        "- 排期方式：Day 1 到 Day 30，不绑定具体日期。",
        "- 发布方式：人工检查后手动发布 LinkedIn。",
        f"- 联系邮箱：{manifest.get('contact_email', DEFAULT_CONTACT_EMAIL)}",
        "",
        "## 营销策划审阅状态",
        "",
        *_marketing_review_lines(manifest),
        "",
        "## 发布前复核提示",
        "",
        *claim_lines,
        "",
        "## 30天贴文",
        "",
    ]
    for day in _campaign_days():
        lines.extend(_render_day(day, manifest))
    lines.extend(
        [
            "## 下一步",
            "",
            "确认中文30天贴文总稿后，生成英文发布总览、英文发布日历和 `daily/day-01.md` 到 `daily/day-30.md`。",
        ]
    )
    return "\n".join(lines) + "\n"


def _claim_review_lines(claim_sources: list[dict[str, Any]]) -> list[str]:
    if not claim_sources:
        return ["- 暂无已识别核心卖点，请发布前人工复核。"]
    lines = []
    for item in claim_sources:
        review = "发布前需要人工复核" if item.get("requires_publish_review") else "已有正式对外知识支持"
        lines.append(f"- {item.get('claim_zh', '')}：{review}")
    return lines


def _asset_plan_lines(content_assets: list[dict[str, Any]]) -> list[str]:
    if not content_assets:
        return ["- 当前没有可用真实内容素材；后续每日文件只生成配图 brief 和 AI 作图提示，不伪装成产品实拍。"]
    lines = []
    for asset in content_assets:
        media = ", ".join(asset.get("media_types", [])) or "未标明媒体类型"
        lines.append(f"- {asset['title']}（{asset['id']}，{media}）：仅用于配图，不证明产品性能事实。")
    return lines


def _campaign_days() -> list[dict[str, Any]]:
    return [
        {"day": 1, "theme": "对外名称发布", "angle": "介绍特种玻璃纤维带，说明它面向高温隔热应用。", "tags": ["Specialty Glass Fiber Tape", "High Temperature", "Tuolin"]},
        {"day": 2, "theme": "1000度耐高温", "angle": "围绕耐高温1000度建立第一核心卖点。", "tags": ["1000°C", "Heat Resistance", "Thermal Insulation"]},
        {"day": 3, "theme": "不刺痒触感", "angle": "解释直接接触时不刺痒对安装和维护人员的价值。", "tags": ["No Itching", "Installer Friendly", "Safer Handling"]},
        {"day": 4, "theme": "不冒烟体验", "angle": "强调使用过程中不冒烟对室内、车间和维护场景的意义。", "tags": ["No Smoke", "Clean Use", "Workshop Safety"]},
        {"day": 5, "theme": "三大卖点整合", "angle": "把耐高温、不刺痒、不冒烟组合成采购记忆点。", "tags": ["1000°C", "No Itching", "No Smoke"]},
        {"day": 6, "theme": "排气管隔热场景", "angle": "说明特种玻璃纤维带可服务排气管等高温隔热场景。", "tags": ["Exhaust Wrap", "Heat Shield", "Industrial Tape"]},
        {"day": 7, "theme": "维修维护团队", "angle": "面向维护团队讲安装体验和稳定使用感。", "tags": ["Maintenance", "Easy Handling", "Thermal Protection"]},
        {"day": 8, "theme": "工业采购关注点", "angle": "从采购视角说明性能、使用体验和供货沟通。", "tags": ["Industrial Sourcing", "Procurement", "Specifications"]},
        {"day": 9, "theme": "分销商卖点", "angle": "帮助分销商理解产品对终端客户的表达方式。", "tags": ["Distributor", "B2B Sales", "Product Selling Points"]},
        {"day": 10, "theme": "样品沟通", "angle": "引导客户索取规格和样品信息。", "tags": ["Sample Request", "Specification", "Tuolin"]},
        {"day": 11, "theme": "高温隔热科普", "angle": "用教育型内容解释为什么高温带材需要稳定耐温。", "tags": ["Thermal Management", "Heat Control", "Industrial Safety"]},
        {"day": 12, "theme": "安装体验科普", "angle": "强调不刺痒对频繁安装、维修和现场操作的影响。", "tags": ["No Itching", "Installation", "Worker Comfort"]},
        {"day": 13, "theme": "使用过程清洁感", "angle": "围绕不冒烟说明客户对现场体验的期待。", "tags": ["No Smoke", "Clean Workshop", "Reliable Use"]},
        {"day": 14, "theme": "材料选择误区", "angle": "提醒客户不要只看名称，要看耐温、触感和使用表现。", "tags": ["Material Selection", "Buyer Tips", "High Temperature"]},
        {"day": 15, "theme": "中期卖点复盘", "angle": "复盘前半个月核心信息，形成询盘提示。", "tags": ["1000°C", "No Itching", "No Smoke"]},
        {"day": 16, "theme": "FAQ：为什么改叫特种玻璃纤维带", "angle": "解释对外名称用于欧美市场沟通，内部知识仍可追溯。", "tags": ["FAQ", "Product Naming", "Global Market"]},
        {"day": 17, "theme": "FAQ：适合谁采购", "angle": "明确工业采购、分销商和维护团队是核心受众。", "tags": ["Procurement", "Distributor", "Maintenance"]},
        {"day": 18, "theme": "FAQ：如何确认规格", "angle": "引导客户通过邮件沟通应用、温度和尺寸需求。", "tags": ["Specification", "Application", "Inquiry"]},
        {"day": 19, "theme": "应用建议", "angle": "建议客户根据高温位置、接触需求和现场环境选型。", "tags": ["Application Advice", "Heat Zone", "Tape Selection"]},
        {"day": 20, "theme": "采购检查清单", "angle": "给采购一个简短检查清单：耐温、触感、烟雾、供货资料。", "tags": ["Buying Checklist", "High Temperature", "B2B"]},
        {"day": 21, "theme": "工厂供货沟通", "angle": "强调 Tuolin 可围绕规格、样品和应用问题进行沟通。", "tags": ["Factory Supply", "Tuolin", "B2B"]},
        {"day": 22, "theme": "资料索取", "angle": "引导客户索取 datasheet、规格或应用建议。", "tags": ["Datasheet", "Specification", "Contact Us"]},
        {"day": 23, "theme": "样品测试", "angle": "鼓励客户用样品验证现场安装和使用体验。", "tags": ["Sample Testing", "Field Trial", "High Temperature"]},
        {"day": 24, "theme": "分销合作", "angle": "面向分销商说明稳定卖点适合做目录和客户沟通。", "tags": ["Distribution", "Catalog Product", "B2B Partnership"]},
        {"day": 25, "theme": "长期合作价值", "angle": "强调稳定命名、稳定卖点和持续供货沟通。", "tags": ["Long Term Supply", "Tuolin", "Industrial Products"]},
        {"day": 26, "theme": "卖点复盘：耐高温", "angle": "再次突出1000度耐高温，服务最后一周转化。", "tags": ["1000°C", "Heat Resistance", "Thermal Tape"]},
        {"day": 27, "theme": "卖点复盘：不刺痒", "angle": "再次突出安装和维护时的接触体验。", "tags": ["No Itching", "Installer Friendly", "Maintenance"]},
        {"day": 28, "theme": "卖点复盘：不冒烟", "angle": "再次突出使用过程体验和现场清洁感。", "tags": ["No Smoke", "Clean Use", "Workshop"]},
        {"day": 29, "theme": "三卖点采购总结", "angle": "把三大卖点整理成采购或分销商可复制的总结。", "tags": ["1000°C", "No Itching", "No Smoke"]},
        {"day": 30, "theme": "询盘收口", "angle": "用清晰 CTA 收口，邀请客户索取规格、样品或应用建议。", "tags": ["Inquiry", "Sample", "Tuolin"]},
    ]


def _render_day(day: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    day_number = int(day["day"])
    cta = _day_cta(day_number, manifest)
    body = (
        f"{EXTERNAL_PRODUCT_NAME_ZH}的第 {day_number} 天主题是「{day['theme']}」。"
        f"{day['angle']} 对欧美工业采购、分销商和维修维护团队来说，"
        "这类内容的重点不是夸大承诺，而是把产品名称、应用价值和可沟通信息讲清楚。"
        f"本帖应继续围绕耐高温1000度、不刺痒、不冒烟三个核心特性展开，"
        "并在发布前核对这些卖点是否已有正式证据或本次人工确认记录。"
        f"{cta}"
    )
    image_guidance = _image_guidance(day, manifest)
    return [
        f"### Day {day_number}: {day['theme']}",
        "",
        f"- **主题**：{day['theme']}",
        f"- **中文贴文**：{body}",
        f"- **配图方向**：{image_guidance['zh']}",
        f"- **画面 tags**：{', '.join(day['tags'])}",
        "- **发布前复核**：确认耐高温1000度、不刺痒、不冒烟的表达符合正式知识或本次人工确认卖点。",
        "",
    ]


def _day_cta(day_number: int, manifest: dict[str, Any]) -> str:
    if day_number in {10, 15, 20, 22, 23, 25, 30}:
        email = manifest.get("contact_email", DEFAULT_CONTACT_EMAIL)
        return f" 如需规格、样品或应用建议，可通过 {email} 联系 Tuolin。"
    return " 如需进一步沟通，可以在人工发布时根据评论和私信情况补充轻量 CTA。"


def _english_post(day: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    day_number = int(day["day"])
    hashtags = _hashtags(day)
    cta = _english_cta(day_number, manifest)
    image_guidance = _image_guidance(day, manifest)
    body = (
        f"Day {day_number} focuses on {day['theme']}. {EXTERNAL_PRODUCT_NAME_EN} is positioned for B2B buyers "
        "who need a high-temperature insulation tape that is easy to explain, easy to evaluate, and suitable for "
        "industrial sourcing conversations. The message for this post is simple: buyers should look beyond a generic "
        "material name and check the practical details that matter during installation and use.\n\n"
        f"For this topic, highlight that the tape is presented for applications where heat resistance, cleaner handling, "
        "and stable use experience matter. The campaign claims to review before publishing are 1000°C heat resistance, "
        "no itching sensation when handled, and no smoke during use. Keep the wording factual, avoid overpromising, "
        "and use the post to invite a specific application discussion.\n\n"
        f"{cta}"
    )
    return {
        "day": day_number,
        "theme": day["theme"],
        "title": f"Day {day_number}: {day['theme']}",
        "body": body,
        "hashtags": hashtags,
        "image_brief": image_guidance["en"],
        "asset_reference": image_guidance["asset_reference"],
        "visual_tags": day["tags"],
        "review_note": "Review 1000°C heat resistance, no itching, and no smoke claims before publishing.",
    }


def _image_guidance(day: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str | None]:
    assets = manifest.get("content_assets", [])
    if assets:
        asset = assets[(int(day["day"]) - 1) % len(assets)]
        title = asset.get("title", "approved content asset")
        asset_id = asset.get("id", "")
        return {
            "zh": f"优先使用已批准内容素材「{title}」（{asset_id}）；该素材只用于画面，不证明性能事实。",
            "en": (
                f"Use the approved content asset '{title}' ({asset_id}) as the first choice for this post. "
                "Use it for visuals only; it does not prove product performance claims. Add the daily visual tags in open space."
            ),
            "asset_reference": asset_id,
        }
    return {
        "zh": f"当前没有可用真实内容素材；围绕「{day['theme']}」生成配图 brief 或 AI 作图提示，不伪装成产品实拍。",
        "en": (
            f"No approved real content asset is available for this campaign. Create an image brief for '{day['theme']}' only; "
            "do not present AI-generated output as a real product photo."
        ),
        "asset_reference": None,
    }


def _hashtags(day: dict[str, Any]) -> list[str]:
    base = ["#ThermalInsulation", "#HighTemperature", "#IndustrialProducts"]
    theme = str(day["theme"])
    if "分销" in theme:
        base.append("#B2BDistribution")
    elif "采购" in theme or "询盘" in theme or "资料" in theme or "样品" in theme:
        base.append("#IndustrialSourcing")
    elif "不刺痒" in theme or "安装" in theme:
        base.append("#WorkplaceSafety")
    elif "不冒烟" in theme:
        base.append("#CleanManufacturing")
    else:
        base.append("#ThermalManagement")
    base.append("#Tuolin")
    return base[:5]


def _english_cta(day_number: int, manifest: dict[str, Any]) -> str:
    email = manifest.get("contact_email", DEFAULT_CONTACT_EMAIL)
    if day_number in {10, 15, 20, 22, 23, 25, 30}:
        return f"For specifications, samples, or application guidance, contact Tuolin at {email}."
    return "If this fits a project you are evaluating, send us the application details and temperature requirements."


def _render_english_overview(posts: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    lines = [
        "# LinkedIn 30-Day English Publishing Overview",
        "",
        f"- Product name: {EXTERNAL_PRODUCT_NAME_EN}",
        f"- Chinese external name: {EXTERNAL_PRODUCT_NAME_ZH}",
        "- Schedule: Day 1 to Day 30, no fixed calendar dates.",
        "- Publishing: manual review and manual LinkedIn posting only.",
        f"- Contact: {manifest.get('contact_email', DEFAULT_CONTACT_EMAIL)}",
        "",
        "## Publishing Safety",
        "",
        "- Do not use `Quartz Fiber Tape` in user-copyable external posts.",
        "- Review 1000°C heat resistance, no itching, and no smoke claims before publishing.",
        "- Use content assets for images only; they do not prove product performance facts.",
        "",
        "## Daily Summary",
        "",
    ]
    for post in posts:
        lines.append(
            f"- Day {post['day']}: {post['theme']} | hashtags: {' '.join(post['hashtags'])} | file: daily/day-{post['day']:02d}.md"
        )
    return "\n".join(lines) + "\n"


def _write_english_calendar(path: Path, posts: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["day", "theme", "daily_file", "hashtags", "asset_reference", "image_brief", "review_note"],
        )
        writer.writeheader()
        for post in posts:
            writer.writerow(
                {
                    "day": f"Day {post['day']}",
                    "theme": post["theme"],
                    "daily_file": f"daily/day-{post['day']:02d}.md",
                    "hashtags": " ".join(post["hashtags"]),
                    "asset_reference": post["asset_reference"] or "",
                    "image_brief": post["image_brief"],
                    "review_note": post["review_note"],
                }
            )


def _render_daily_english_file(post: dict[str, Any], manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {post['title']}",
            "",
            "## LinkedIn Post",
            "",
            post["body"],
            "",
            "## Hashtags",
            "",
            " ".join(post["hashtags"]),
            "",
            "## Image Brief",
            "",
            post["image_brief"],
            "",
            "## Approved Asset Reference",
            "",
            post["asset_reference"] or "No approved real content asset available. Use image brief only.",
            "",
            "## Visual Tags",
            "",
            ", ".join(post["visual_tags"]),
            "",
            "## Review Before Publishing",
            "",
            post["review_note"],
            "",
            "## Publishing Boundary",
            "",
            "- Manual LinkedIn posting only.",
            "- Do not present AI-generated imagery as a real product photo.",
            "- Do not write this campaign output back to the formal knowledge base.",
            f"- Contact email, when needed: {manifest.get('contact_email', DEFAULT_CONTACT_EMAIL)}",
        ]
    ) + "\n"


def _manual_package_dir(campaign_dir: Path) -> Path:
    return campaign_dir / "Manual-Posting-Package"


def _manual_day_dir(campaign_dir: Path, day_number: int) -> Path:
    return _manual_package_dir(campaign_dir) / f"Day {day_number:02d}"


def _manual_day_assets_dir(campaign_dir: Path, day_number: int) -> Path:
    return _manual_day_dir(campaign_dir, day_number) / "assets"


def _manual_day_publish_images_dir(campaign_dir: Path, day_number: int) -> Path:
    return _manual_day_dir(campaign_dir, day_number) / "Publish-Images"


def copy_linkedin_campaign_to_desktop(
    campaign_dir: Path,
    desktop_dir: Path | None = None,
    now: datetime | None = None,
) -> LinkedInCampaignResult:
    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    draft_path = Path(manifest.get("files", {}).get("chinese_draft") or campaign_dir / "02_中文30天贴文总稿.md")
    if not draft_path.exists():
        raise ValueError("复制到桌面前，请先生成详细 30 天发帖内容（02_中文30天贴文总稿.md）。")
    source_inventory = _desktop_delivery_inventory(campaign_dir)
    _validate_desktop_delivery_source(source_inventory)

    root = (desktop_dir or Path.home() / "Desktop").expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    destination = root / f"{DESKTOP_DELIVERY_DIR_PREFIX}-{stamp}"
    if destination.exists():
        raise FileExistsError(f"桌面交付目录已存在，未覆盖：{destination}")

    manifest["desktop_delivery"] = {
        "path": str(destination),
        "created_at": stamp,
        "source_campaign_dir": str(campaign_dir),
        "source_inventory": source_inventory,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copytree(campaign_dir, destination)
    copied_inventory = _desktop_delivery_inventory(destination)
    _validate_desktop_delivery_copy(source_inventory, copied_inventory)
    manifest["desktop_delivery"]["copied_inventory"] = copied_inventory
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(manifest_path, destination / "campaign-manifest.json")
    return LinkedInCampaignResult(
        campaign_dir=str(campaign_dir),
        plan_path=str(destination),
        manifest_path=str(manifest_path),
        context_id=manifest["context"]["context_id"],
        status=manifest["status"],
    )


def _desktop_delivery_inventory(root: Path) -> dict[str, Any]:
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    manual_dir = root / "Manual-Posting-Package"
    day_dirs = sorted(path for path in manual_dir.glob("Day [0-9][0-9]") if path.is_dir())
    return {
        "daily_files": len(list((root / "daily").glob("day-*.md"))),
        "manual_package_exists": manual_dir.is_dir(),
        "manual_day_dirs": len(day_dirs),
        "manual_post_content_files": sum(1 for day_dir in day_dirs if (day_dir / "LinkedIn Post Content.md").exists()),
        "manual_asset_note_files": sum(1 for day_dir in day_dirs if (day_dir / "Asset Notes.md").exists()),
        "manual_source_images": _count_images(manual_dir, image_suffixes, include_segment="assets"),
        "manual_publish_images": _count_images(manual_dir, image_suffixes, include_segment="Publish-Images"),
        "legacy_publish_images": _count_images(root / "Publish-Images-With-Tags-Logo", image_suffixes),
    }


def _count_images(root: Path, suffixes: set[str], include_segment: str | None = None) -> int:
    if not root.exists():
        return 0
    count = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if include_segment and include_segment not in path.parts:
            continue
        count += 1
    return count


def _validate_desktop_delivery_source(inventory: dict[str, Any]) -> None:
    if not inventory["manual_package_exists"]:
        raise ValueError("复制到桌面前，请先生成英文发布包和人工发布包（Manual-Posting-Package）。")
    if inventory["manual_day_dirs"] < DEFAULT_CAMPAIGN_DAYS:
        raise ValueError(f"人工发布包不完整：只找到 {inventory['manual_day_dirs']} 个 Day 目录。")
    if inventory["manual_post_content_files"] < DEFAULT_CAMPAIGN_DAYS:
        raise ValueError(f"人工发布包不完整：只找到 {inventory['manual_post_content_files']} 个每日贴文文件。")
    if inventory["manual_asset_note_files"] < DEFAULT_CAMPAIGN_DAYS:
        raise ValueError(f"人工发布包不完整：只找到 {inventory['manual_asset_note_files']} 个素材说明文件。")


def _validate_desktop_delivery_copy(source: dict[str, Any], copied: dict[str, Any]) -> None:
    keys = [
        "daily_files",
        "manual_day_dirs",
        "manual_post_content_files",
        "manual_asset_note_files",
        "manual_source_images",
        "manual_publish_images",
        "legacy_publish_images",
    ]
    missing = [key for key in keys if copied.get(key, 0) < source.get(key, 0)]
    if missing:
        details = "；".join(f"{key}: source={source.get(key, 0)}, copied={copied.get(key, 0)}" for key in missing)
        raise RuntimeError(f"桌面交付副本不完整：{details}")


def _write_manual_posting_package(
    campaign_dir: Path,
    posts: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    package_dir = _manual_package_dir(campaign_dir)
    package_dir.mkdir(parents=True, exist_ok=True)
    overview_path = package_dir / "Campaign Overview.md"
    calendar_path = package_dir / "Publishing Calendar.csv"
    overview_path.write_text(_render_manual_campaign_overview(posts, manifest), encoding="utf-8")
    _write_manual_calendar(calendar_path, posts)

    day_dirs = []
    post_content_files = []
    asset_note_files = []
    for post in posts:
        day_number = int(post["day"])
        day_dir = _manual_day_dir(campaign_dir, day_number)
        assets_dir = _manual_day_assets_dir(campaign_dir, day_number)
        assets_dir.mkdir(parents=True, exist_ok=True)
        post_path = day_dir / "LinkedIn Post Content.md"
        asset_path = day_dir / "Asset Notes.md"
        post_path.write_text(_render_manual_post_content(post), encoding="utf-8")
        asset_path.write_text(_render_manual_asset_notes(post), encoding="utf-8")
        day_dirs.append(str(day_dir))
        post_content_files.append(str(post_path))
        asset_note_files.append(str(asset_path))

    return {
        "manual_package_dir": str(package_dir),
        "manual_overview": str(overview_path),
        "manual_calendar": str(calendar_path),
        "manual_day_dirs": day_dirs,
        "manual_post_content_files": post_content_files,
        "manual_asset_note_files": asset_note_files,
    }


def _render_manual_campaign_overview(posts: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    lines = [
        "# Manual LinkedIn Posting Package Overview",
        "",
        f"- Product name: {EXTERNAL_PRODUCT_NAME_EN}",
        f"- Chinese external name: {EXTERNAL_PRODUCT_NAME_ZH}",
        "- Market: Europe and North America",
        "- Publishing mode: manual review and manual LinkedIn posting only.",
        "- Core claims to review before posting: 1000°C heat resistance, no itching sensation, and no smoke during use.",
        "- Product images and content assets support visual layout only; they do not prove product performance claims.",
        f"- Contact: {manifest.get('contact_email', DEFAULT_CONTACT_EMAIL)}",
        "",
        "## Daily Index",
        "",
    ]
    for post in posts:
        lines.append(
            f"- Day {post['day']:02d}: {post['theme']} | "
            f"Post: Day {post['day']:02d}/LinkedIn Post Content.md | "
            f"Publishing images: Day {post['day']:02d}/Publish-Images/"
        )
    return "\n".join(lines) + "\n"


def _write_manual_calendar(path: Path, posts: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "day",
                "theme",
                "post_content_file",
                "asset_notes_file",
                "publishing_images_dir",
                "hashtags",
                "manual_review_status",
            ],
        )
        writer.writeheader()
        for post in posts:
            day = int(post["day"])
            writer.writerow(
                {
                    "day": f"Day {day:02d}",
                    "theme": post["theme"],
                    "post_content_file": f"Day {day:02d}/LinkedIn Post Content.md",
                    "asset_notes_file": f"Day {day:02d}/Asset Notes.md",
                    "publishing_images_dir": f"Day {day:02d}/Publish-Images/",
                    "hashtags": " ".join(post["hashtags"]),
                    "manual_review_status": "unchecked",
                }
            )


def _render_manual_post_content(post: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {post['title']}",
            "",
            "## Copy For LinkedIn",
            "",
            post["body"],
            "",
            "## Hashtags",
            "",
            " ".join(post["hashtags"]),
            "",
            "## Manual Review",
            "",
            "- Check product name before posting: Specialty Glass Fiber Tape.",
            "- Check the 1000°C, no itching, and no smoke wording before posting.",
            "- Post manually from the LinkedIn account; do not schedule automatically from this package.",
        ]
    ) + "\n"


def _render_manual_asset_notes(post: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Day {post['day']:02d} Asset Notes",
            "",
            "## Source Images",
            "",
            "Place approved source images for this Day in `assets/` before generating publishing images.",
            "",
            "## Image Brief",
            "",
            post["image_brief"],
            "",
            "## Visual Tags",
            "",
            ", ".join(post["visual_tags"]),
            "",
            "## Boundary",
            "",
            "- Use approved source images or generated image briefs only.",
            "- Do not present AI-generated imagery as a real product photo.",
            "- Visual assets do not prove product performance claims.",
            "",
            "## Regeneration",
            "",
            (
                f"To create publishing images, ask Codex to generate the Day {post['day']:02d} "
                "publishing image selection sheet, then choose one source image and 1-3 style categories."
            ),
        ]
    ) + "\n"


def _day_source_images(campaign_dir: Path, day_number: int) -> list[dict[str, Any]]:
    assets_dir = _manual_day_assets_dir(campaign_dir, day_number)
    suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    images = []
    if not assets_dir.exists():
        return images
    for index, path in enumerate(sorted(item for item in assets_dir.iterdir() if item.suffix.lower() in suffixes), 1):
        images.append(
            {
                "index": index,
                "path": str(path),
                "filename": path.name,
                "role": _source_image_role(path),
            }
        )
    return images


def _source_image_role(path: Path) -> str:
    name = path.name.lower()
    if any(token in name for token in ["exhaust", "pipe", "flue", "stove", "application", "scene"]):
        return "scenario"
    if any(token in name for token in ["texture", "closeup", "detail"]):
        return "detail"
    return "product"


def _recommended_image_categories(day: dict[str, Any], source_images: list[dict[str, Any]]) -> list[dict[str, str]]:
    text = f"{day['theme']} {day['angle']} {' '.join(day['tags'])}".lower()
    roles = {image["role"] for image in source_images}
    slugs: list[str]
    if "排气" in text or "exhaust" in text:
        slugs = ["exhaust-wrap-scenario", "industrial-technical", "three-benefit-banner"]
    elif "采购" in text or "询盘" in text or "样品" in text:
        slugs = ["buyer-checklist", "inquiry-conversion", "technical-parameter-card"]
    elif "不刺痒" in text or "itch" in text:
        slugs = ["comfortable-handling", "product-detail-closeup", "pain-point-solution"]
    elif "不冒烟" in text or "smoke" in text:
        slugs = ["cutting-processing", "pain-point-solution", "three-benefit-banner"]
    elif "1000" in text or "高温" in text:
        slugs = ["technical-parameter-card", "high-temperature-test", "industrial-technical"]
    elif "detail" in roles:
        slugs = ["product-detail-closeup", "comfortable-handling", "minimal-premium"]
    else:
        slugs = ["original-light-enhancement", "minimal-premium", "technical-parameter-card"]
    return [_category_for_slug(slug) for slug in slugs]


def _not_recommended_image_categories(day: dict[str, Any], source_images: list[dict[str, Any]]) -> list[dict[str, str]]:
    roles = {image["role"] for image in source_images}
    result = []
    scenario_categories = {
        "application-scenario": "当前 Day 没有明确真实应用场景源图时，不建议生成场景型图片。",
        "exhaust-wrap-scenario": "需要真实排气管或包覆场景源图，不能从白底产品图编造。",
        "industrial-pipe-insulation": "需要真实工业管道或保温现场源图，不能从白底产品图编造。",
        "cutting-processing": "需要真实裁切或加工动作源图，否则容易误导。",
    }
    if "scenario" not in roles:
        for slug, reason in scenario_categories.items():
            category = _category_for_slug(slug)
            result.append({"slug": category["slug"], "name": category["name"], "reason": reason})
    return result[:6]


def _render_image_selection_sheet(
    day: dict[str, Any],
    manifest: dict[str, Any],
    source_images: list[dict[str, Any]],
    recommended: list[dict[str, str]],
    not_recommended: list[dict[str, str]],
) -> str:
    day_number = int(day["day"])
    lines = [
        f"# Day {day_number:02d} Publishing Image Selection",
        "",
        "## Day Content",
        "",
        f"- Theme: {day['theme']}",
        f"- Core angle: {day['angle']}",
        f"- Product: {EXTERNAL_PRODUCT_NAME_EN}",
        f"- Contact: {manifest.get('contact_email', DEFAULT_CONTACT_EMAIL)}",
        f"- Visual tags: {', '.join(day['tags'])}",
        "",
        "## Source Images",
        "",
    ]
    for image in source_images:
        lines.append(f"{image['index']}. `{image['filename']}` ({image['role']})")
    lines.extend(
        [
            "",
            "## Size Recommendation",
            "",
            "- Default: keep source image dimensions.",
            "- Use another size only when the user explicitly requests it.",
            "",
            "## Recommended Categories",
            "",
        ]
    )
    for category in recommended:
        lines.append(f"- {category['name']} (`{category['slug']}`)")
    lines.extend(["", "## All Categories", ""])
    for index, category in enumerate(IMAGE_STYLE_CATEGORIES, 1):
        lines.append(f"{index}. {category['name']} (`{category['slug']}`)")
    if not_recommended:
        lines.extend(["", "## Not Recommended For Current Source", ""])
        for category in not_recommended:
            lines.append(f"- {category['name']}：{category['reason']}")
    lines.extend(
        [
            "",
            "## Next Input Example",
            "",
            f"Day {day_number:02d} 源图选 1，风格选：{recommended[0]['name']}、{recommended[1]['name']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _resolve_image_category(value: str) -> dict[str, str]:
    cleaned = value.strip().strip("`")
    for category in IMAGE_STYLE_CATEGORIES:
        if cleaned == category["slug"] or cleaned == category["name"]:
            return {"slug": category["slug"], "name": category["name"]}
    raise ValueError(f"未知发布图风格类别：{value}")


def _category_for_slug(slug: str) -> dict[str, str]:
    for category in IMAGE_STYLE_CATEGORIES:
        if category["slug"] == slug:
            return {"slug": category["slug"], "name": category["name"]}
    raise ValueError(f"未知发布图风格类别 slug：{slug}")


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    return safe or "linkedin_campaign"
