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


def _resolve_generation_logo_path(
    campaign_dir: Path,
    manifest: dict[str, Any],
    explicit_logo_path: Path | None,
) -> Path:
    if explicit_logo_path is not None:
        return explicit_logo_path.expanduser().resolve()

    configured = (
        manifest.get("files", {}).get("transparent_logo")
        or manifest.get("files", {}).get("default_transparent_logo")
        or manifest.get("image_policy", {}).get("default_transparent_logo_path")
    )
    if not configured:
        raise ValueError(
            "生成 LinkedIn 配图需要透明背景 logo。"
            f"请把 logo 放到 {DEFAULT_TRANSPARENT_LOGO_RELATIVE_PATH}，"
            "或在命令中提供 logo 路径。"
        )
    path = Path(str(configured)).expanduser()
    if not path.is_absolute():
        path = campaign_dir / path
    return path.resolve()


def confirm_linkedin_campaign_plan(campaign_dir: Path, overwrite: bool = False) -> LinkedInCampaignResult:
    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status != "planning_ready":
        raise ValueError(f"当前活动状态是 {status!r}，不能生成中文30天贴文总稿。请先完成中文策划。")

    plan_path = Path(manifest["files"]["chinese_plan"])
    if not plan_path.exists():
        raise ValueError(f"找不到已生成的中文策划文件：{plan_path}")

    draft_path = campaign_dir / "02_中文30天贴文总稿.md"
    if draft_path.exists() and not overwrite:
        raise FileExistsError(f"中文30天贴文总稿已存在，未覆盖：{draft_path}")

    draft_path.write_text(_render_chinese_30_day_draft(manifest), encoding="utf-8")
    _append_status_history(manifest, "planning_confirmed")
    manifest["status"] = "chinese_draft_ready"
    _append_status_history(manifest, "chinese_draft_ready")
    manifest["files"]["chinese_draft"] = str(draft_path)
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


def generate_linkedin_publishing_images(
    campaign_dir: Path,
    logo_path: Path | None,
    source_image_path: Path,
    overwrite: bool = False,
) -> LinkedInCampaignResult:
    campaign_dir = campaign_dir.expanduser().resolve()
    source_image_path = source_image_path.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")
    if not source_image_path.exists():
        raise ValueError(f"找不到源图片文件：{source_image_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resolved_logo_path = _resolve_generation_logo_path(campaign_dir, manifest, logo_path)
    if not resolved_logo_path.exists():
        logo_path_label = "指定路径" if logo_path is not None else "配置路径"
        raise ValueError(
            f"找不到透明 logo 文件：{resolved_logo_path}。"
            f"请把透明背景 logo 放到{logo_path_label} {resolved_logo_path}，或在命令中提供 logo 路径。"
        )
    status = manifest.get("status")
    if status not in {"english_package_ready", "image_assets_ready"}:
        raise ValueError(f"当前活动状态是 {status!r}，不能生成发布图。请先生成英文发布包。")

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("生成发布图需要 Pillow 图片库。请先安装 Pillow，或只使用 image brief。") from exc

    logo = Image.open(resolved_logo_path).convert("RGBA")
    if not _has_transparency(logo):
        raise ValueError("logo 文件必须是带透明通道的图片。请提供独立透明 logo，不要使用带背景的参考图。")

    source = Image.open(source_image_path).convert("RGB")
    output_dir = Path(manifest["files"]["publishing_images_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = [output_dir / f"day-{day['day']:02d}.png" for day in _campaign_days()]
    existing = [path for path in output_paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError("发布图已存在，未覆盖：" + "；".join(str(path) for path in existing))

    font_large = _load_font(ImageFont, 34)
    font_small = _load_font(ImageFont, 22)
    generated = []
    manual_generated = []
    for day, output_path in zip(_campaign_days(), output_paths):
        tags = [str(tag) for tag in day["tags"][:3]]
        image = _compose_publishing_image(source, logo, tags, font_large, font_small)
        image.save(output_path)
        generated.append(str(output_path))
        manual_path = _manual_day_assets_dir(campaign_dir, int(day["day"])) / "linkedin-publishing-image.png"
        manual_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output_path, manual_path)
        manual_generated.append(str(manual_path))
        _upsert_daily_image_reference(campaign_dir / "daily" / f"day-{int(day['day']):02d}.md", output_path)
        _upsert_manual_asset_note(campaign_dir, int(day["day"]), output_path, manual_path, tags)

    manifest["status"] = "image_assets_ready"
    _append_status_history(manifest, "image_assets_ready")
    manifest["files"]["transparent_logo"] = str(resolved_logo_path)
    manifest["files"]["publishing_image_source"] = str(source_image_path)
    manifest["files"]["publishing_images"] = generated
    manifest["files"]["manual_publishing_images"] = manual_generated
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInCampaignResult(
        campaign_dir=str(campaign_dir),
        plan_path=generated[0],
        manifest_path=str(manifest_path),
        context_id=manifest["context"]["context_id"],
        status="image_assets_ready",
    )


def regenerate_linkedin_publishing_image(
    campaign_dir: Path,
    day_number: int,
    tags: list[str],
    logo_path: Path | None = None,
    source_image_path: Path | None = None,
) -> LinkedInCampaignResult:
    campaign_dir = campaign_dir.expanduser().resolve()
    manifest_path = campaign_dir / "campaign-manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"找不到 LinkedIn 活动 manifest：{manifest_path}")
    if day_number < 1 or day_number > DEFAULT_CAMPAIGN_DAYS:
        raise ValueError(f"Day 必须在 1 到 {DEFAULT_CAMPAIGN_DAYS} 之间：{day_number}")
    clean_tags = [tag.strip() for tag in tags if tag.strip()]
    if not clean_tags:
        raise ValueError("重新生成单日发布图需要至少 1 个 tag。")
    if len(clean_tags) > 3:
        clean_tags = clean_tags[:3]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    if status not in {"english_package_ready", "image_assets_ready"}:
        raise ValueError(f"当前活动状态是 {status!r}，不能重新生成发布图。请先生成英文发布包。")

    resolved_source = source_image_path
    if resolved_source is None:
        configured_source = manifest.get("files", {}).get("publishing_image_source")
        if configured_source:
            resolved_source = Path(str(configured_source))
    if resolved_source is None:
        raise ValueError("重新生成单日发布图需要源图。请先生成整套配图，或在命令中提供源图路径。")
    resolved_source = resolved_source.expanduser().resolve()
    if not resolved_source.exists():
        raise ValueError(f"找不到源图片文件：{resolved_source}")

    resolved_logo_path = _resolve_generation_logo_path(campaign_dir, manifest, logo_path)
    if not resolved_logo_path.exists():
        raise ValueError(f"找不到透明 logo 文件：{resolved_logo_path}")

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("生成发布图需要 Pillow 图片库。请先安装 Pillow，或只使用 image brief。") from exc

    logo = Image.open(resolved_logo_path).convert("RGBA")
    if not _has_transparency(logo):
        raise ValueError("logo 文件必须是带透明通道的图片。请提供独立透明 logo，不要使用带背景的参考图。")
    source = Image.open(resolved_source).convert("RGB")
    font_large = _load_font(ImageFont, 34)
    font_small = _load_font(ImageFont, 22)
    image = _compose_publishing_image(source, logo, clean_tags, font_large, font_small)

    output_dir = Path(manifest["files"]["publishing_images_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"day-{day_number:02d}.png"
    image.save(output_path)

    manual_path = _manual_day_assets_dir(campaign_dir, day_number) / "linkedin-publishing-image.png"
    manual_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output_path, manual_path)
    _upsert_daily_image_reference(campaign_dir / "daily" / f"day-{day_number:02d}.md", output_path)
    _upsert_manual_asset_note(campaign_dir, day_number, output_path, manual_path, clean_tags)

    manifest["status"] = "image_assets_ready"
    _append_status_history(manifest, f"day_{day_number:02d}_image_regenerated")
    manifest["files"]["transparent_logo"] = str(resolved_logo_path)
    manifest["files"]["publishing_image_source"] = str(resolved_source)
    manifest.setdefault("custom_visual_tags", {})[f"day-{day_number:02d}"] = clean_tags
    _upsert_manifest_file_list(manifest, "publishing_images", str(output_path), day_number)
    _upsert_manifest_file_list(manifest, "manual_publishing_images", str(manual_path), day_number)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedInCampaignResult(
        campaign_dir=str(campaign_dir),
        plan_path=str(output_path),
        manifest_path=str(manifest_path),
        context_id=manifest["context"]["context_id"],
        status="image_assets_ready",
    )


def _ensure_campaign_dirs(campaign_dir: Path) -> None:
    for relative in [
        ".",
        "daily",
        "assets/logo",
        "assets/source-images",
        "assets/publishing-images",
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
            "publishing_images_dir": str(campaign_dir / "assets" / "publishing-images"),
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
            f"Assets: Day {post['day']:02d}/assets/linkedin-publishing-image.png"
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
                "publishing_image_file",
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
                    "publishing_image_file": f"Day {day:02d}/assets/linkedin-publishing-image.png",
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
            "## Publishing Image",
            "",
            "assets/linkedin-publishing-image.png",
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
                f"To adjust this day's image tags, ask Codex to regenerate Day {post['day']:02d} "
                "with the new tags."
            ),
        ]
    ) + "\n"


def _compose_publishing_image(source, logo, tags: list[str], font_large, font_small):
    from PIL import ImageDraw

    image = _canvas_from_source(source)
    draw = ImageDraw.Draw(image)
    _draw_visual_tags(draw, tags, font_large, font_small)
    _paste_logo(image, logo)
    return image


def _upsert_manual_asset_note(
    campaign_dir: Path,
    day_number: int,
    standard_image_path: Path,
    manual_image_path: Path,
    tags: list[str],
) -> None:
    note_path = _manual_day_dir(campaign_dir, day_number) / "Asset Notes.md"
    if not note_path.exists():
        return
    text = note_path.read_text(encoding="utf-8")
    section = "\n".join(
        [
            "## Generated Publishing Image",
            "",
            f"- Standard path: {standard_image_path}",
            f"- Manual package path: {manual_image_path}",
            f"- Current visual tags: {', '.join(tags)}",
            "",
        ]
    )
    marker = "\n## Generated Publishing Image\n"
    if marker not in text:
        note_path.write_text(text.rstrip() + "\n\n" + section, encoding="utf-8")
        return
    before, _marker, after = text.partition(marker)
    next_section_index = after.find("\n## ")
    tail = "" if next_section_index == -1 else after[next_section_index:]
    note_path.write_text(before.rstrip() + "\n\n" + section.rstrip() + "\n" + tail, encoding="utf-8")


def _upsert_manifest_file_list(manifest: dict[str, Any], key: str, value: str, day_number: int) -> None:
    files = manifest.setdefault("files", {})
    values = list(files.get(key) or [])
    index = day_number - 1
    while len(values) <= index:
        values.append("")
    values[index] = value
    files[key] = values


def _has_transparency(image) -> bool:
    alpha = image.getchannel("A")
    return alpha.getextrema()[0] < 255


def _load_font(image_font_module, size: int):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return image_font_module.truetype(candidate, size)
            except OSError:
                continue
    return image_font_module.load_default()


def _canvas_from_source(source):
    from PIL import Image

    target_size = (1200, 675)
    image = source.copy()
    image.thumbnail(target_size)
    canvas = Image.new("RGB", target_size, (28, 28, 28))
    x = (target_size[0] - image.width) // 2
    y = (target_size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas.convert("RGBA")


def _draw_visual_tags(draw, tags: list[str], font_large, font_small) -> None:
    x = 54
    y = 56
    orange = (245, 158, 11, 255)
    shadow = (0, 0, 0, 180)
    draw.text((x + 2, y + 2), "Advantage", font=font_large, fill=shadow)
    draw.text((x, y), "Advantage", font=font_large, fill=orange)
    line_y = y + 50
    for tag in tags:
        text = f"◇ {tag}"
        draw.text((x + 1, line_y + 1), text, font=font_small, fill=shadow)
        draw.text((x, line_y), text, font=font_small, fill=orange)
        line_y += 34


def _paste_logo(image, logo) -> None:
    max_width = 270
    resized = logo.copy()
    if resized.width > max_width:
        ratio = max_width / resized.width
        resized = resized.resize((max_width, max(1, int(resized.height * ratio))))
    margin = 48
    x = image.width - resized.width - margin
    y = 42
    image.alpha_composite(resized, (x, y))


def _upsert_daily_image_reference(daily_path: Path, image_path: Path) -> None:
    if not daily_path.exists():
        return
    text = daily_path.read_text(encoding="utf-8")
    section = "\n## Publishing Image\n\n" + str(image_path) + "\n"
    marker = "\n## Publishing Image\n"
    if marker not in text:
        daily_path.write_text(text.rstrip() + section, encoding="utf-8")
        return
    before, _marker, after = text.partition(marker)
    next_section_index = after.find("\n## ")
    if next_section_index == -1:
        replacement = section
        tail = ""
    else:
        replacement = section.rstrip() + "\n"
        tail = after[next_section_index:]
    daily_path.write_text(before.rstrip() + replacement + tail, encoding="utf-8")


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    return safe or "linkedin_campaign"
