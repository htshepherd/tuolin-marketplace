from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ..shared.downstream_context import build_downstream_context
from ..shared.project_layout import ProjectPaths


INTERNAL_PRODUCT_ID = "product/quartz_fiber_tape"
INTERNAL_PRODUCT_NAME = "石英纤维隔热带"
RUN_DIR_PRODUCT_SLUG = "quartz_fiber_tape"
VIDEO_CREATION_PRODUCT_ALIAS_IDS = ["product/quartz_fiber_exhaust_wrap"]
SUPPORTED_LANGUAGE_VERSIONS = {"zh", "en"}
SUPPORTED_DURATIONS = {60, 90, 120}
SUPPORTED_PLATFORMS = {"youtube_shorts", "tiktok"}
DEFAULT_VIDEO_DURATION_SECONDS = 60
DEFAULT_DREAMINA_MODEL = "seedance2.0_vip"
DEFAULT_RESOLUTION = "1080P"
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_DREAMINA_CAPABILITY_PROFILE = {
    "model": DEFAULT_DREAMINA_MODEL,
    "resolution": DEFAULT_RESOLUTION,
    "aspect_ratio": DEFAULT_ASPECT_RATIO,
    "min_duration_seconds": 4,
    "max_duration_seconds": 15,
    "max_images": 9,
    "max_videos": 3,
    "max_audios": 3,
    "max_total_files": 12,
    "max_image_mb": 30,
    "max_video_mb": 50,
    "max_audio_mb": 15,
    "min_video_reference_duration_seconds": 2,
    "max_video_reference_duration_seconds": 15,
    "max_audio_reference_duration_seconds": 15,
}
Runner = Callable[..., subprocess.CompletedProcess[str]]


VIDEO_CREATIVE_DIRECTIONS = [
    {"id": "product_overview", "name": "产品总览型", "description": "用短时间介绍产品是什么、核心特点和适合的工业客户"},
    {"id": "single_core_benefit", "name": "单一核心卖点型", "description": "聚焦一个核心优势，例如耐高温、隔热、不刺痒或不冒烟"},
    {"id": "multiple_benefit_overview", "name": "多卖点概览型", "description": "同时呈现多个已确认卖点，适合首次触达和平台日常内容"},
    {"id": "product_detail", "name": "产品细节型", "description": "强调织纹、厚度、卷装、边缘、柔软度等真实产品细节"},
    {"id": "application_demonstration", "name": "应用演示型", "description": "展示产品在已确认应用场景中的使用方式"},
    {"id": "customer_pain_point_solution", "name": "客户痛点解决型", "description": "围绕客户痛点组织叙事，例如烟雾、刺痒、施工麻烦、隔热不足"},
    {"id": "installation_demonstration", "name": "安装演示型", "description": "说明裁切、缠绕、固定、收尾等施工过程"},
    {"id": "usage_precautions", "name": "使用注意事项型", "description": "说明适用边界、施工注意和选型提示，避免过度承诺"},
    {"id": "technical_education", "name": "技术科普型", "description": "用通俗方式解释材料、耐温、隔热或选择逻辑"},
    {"id": "performance_test", "name": "性能测试型", "description": "展示火焰、高温或热源等测试视觉，但必须避免夸大测试结论"},
    {"id": "faq", "name": "FAQ 问答型", "description": "用常见问题引出产品特点和采购关注点"},
    {"id": "material_comparison_selection", "name": "材料对比与选型型", "description": "与其他材料或方案做中性选择说明，不攻击竞品，不制造无证据结论"},
    {"id": "specification_customization", "name": "规格与定制型", "description": "展示宽度、厚度、卷长、包装和定制能力等已确认规格"},
    {"id": "procurement_guide", "name": "采购指南型", "description": "面向采购/OEM/分销商，说明询价前需要确认的关键事项"},
    {"id": "real_case_study", "name": "真实案例型", "description": "基于已有正式案例或可公开素材展示应用，不得把 AI 模拟场景表述为真实案例"},
    {"id": "inquiry_conversion", "name": "询盘转化型", "description": "以联系、索样、获取规格或报价为核心目标，必须包含 CTA"},
]

EXTERNAL_VIDEO_SKILL_ABSORPTION = [
    {
        "source": "dexhunter/seedance2-skill",
        "absorbed_as": "Seedance/Dreamina prompt structure and material-reference grammar",
    },
    {
        "source": "songguoxs/seedance-prompt-skill",
        "absorbed_as": "prompt workflow patterns for text-to-video, image-to-video, sound-aware planning, and shot timing",
    },
    {
        "source": "zhanghaonan777/Seedance2-skill",
        "absorbed_as": "CLI/API execution awareness, creative quality gate, and multimodal task parameters",
    },
    {
        "source": "op7418/Seedance-Product-Video",
        "absorbed_as": "product-video style matrix, adapted to Tuolin industrial B2B videos",
    },
    {
        "source": "woodfantasy/Seedance2.0-ShotDesign-Skills",
        "absorbed_as": "shot-design validation and Dreamina task-type mapping",
    },
    {
        "source": "smixs/visual-skills",
        "absorbed_as": "lean skill body with load-on-demand references and concrete visual-detail requirements",
    },
    {
        "source": "MapleShaw/seedance2.0-prompt-skill",
        "absorbed_as": "reference-library organization, production logs, and prompt vocabulary discipline",
    },
    {
        "source": "AKCodez/higgsfield-claude-skills",
        "absorbed_as": "execution automation failure-mode handling without making browser automation the primary path",
    },
    {
        "source": "liangdabiao/Seedance2-Storyboard-Generator",
        "absorbed_as": "multi-shot continuity discipline without absorbing short-drama story categories",
    },
    {
        "source": "rediumvex/ai-video-generator-claude + beshuaxian/higgsfield-seedance2-jineng",
        "absorbed_as": "short-video hook and retention checks adapted to industrial product communication",
    },
]

INDUSTRIAL_VIDEO_STYLE_MATRIX = {
    "industrial_professional": {
        "name": "工业专业型",
        "visual_language": "clean factory-adjacent industrial visuals, neutral lighting, credible B2B product framing",
        "best_for": {"product_overview", "multiple_benefit_overview", "customer_pain_point_solution", "usage_precautions"},
    },
    "minimal_product": {
        "name": "极简产品型",
        "visual_language": "simple background, strong product silhouette, controlled negative space, clear material texture",
        "best_for": {"single_core_benefit", "product_detail", "inquiry_conversion"},
    },
    "technical_explainer": {
        "name": "技术说明型",
        "visual_language": "subtle engineering annotations, measured pacing, parameter cards only when facts are official",
        "best_for": {"technical_education", "performance_test", "material_comparison_selection", "usage_precautions"},
    },
    "application_scene": {
        "name": "应用场景型",
        "visual_language": "confirmed industrial use context, installation movement, no fake customer-site claim",
        "best_for": {"application_demonstration", "installation_demonstration", "real_case_study"},
    },
    "procurement_decision": {
        "name": "采购决策型",
        "visual_language": "buyer checklist rhythm, specification-oriented cuts, restrained CTA and contact logic",
        "best_for": {"procurement_guide", "specification_customization", "faq", "inquiry_conversion"},
    },
}

INDUSTRIAL_CAMERA_LANGUAGE = {
    "opening_environment": "稳定慢推，前两秒建立工业隔热语境，不使用快速摇镜。",
    "product_hero": "产品卷装 hero 慢推，轻微环绕，保持产品形态稳定。",
    "product_detail": "织纹微距和局部特写，轻微横移展示边缘、厚度和柔性。",
    "benefit_visual": "克制说明型镜头，轻微滑动或后拉，不做夸张测试结果。",
    "application_context": "包覆动作跟随镜头，展示已确认应用逻辑，不伪装真实客户现场。",
    "closing_cta": "干净收束镜头，产品定格，CTA 安全留白，避开平台 UI 区域。",
}

PRODUCT_DISPLAY_TEMPLATES = {
    "opening_environment": "industrial need setup, no specific product claim unless product reference is provided",
    "product_hero": "quartz fiber tape roll hero display, stable product silhouette, clean edge and woven surface visible",
    "product_detail": "woven texture macro, edge thickness detail, flexible tape form, no itchy handling claim beyond confirmed narration",
    "benefit_visual": "controlled industrial benefit visual, no exaggerated flame result, no fake certification",
    "application_context": "wrapping or sealing application explanation based only on confirmed use context, AI scenes labeled as visual explanation",
    "closing_cta": "product freeze-frame style closing, light B2B CTA composition, no generated subtitles or platform UI",
}

FORBIDDEN_ENTERTAINMENT_PROMPT_PATTERNS = [
    "short drama",
    "dance",
    "xianxia",
    "fantasy battle",
    "emotional acting",
    "medical cgi",
]

PROMPT_CONFLICT_RULES = [
    {
        "code": "fixed_camera_conflicts_with_dynamic_camera",
        "left_terms": ["fixed camera", "static camera", "locked-off camera", "tripod locked"],
        "right_terms": ["orbit", "surround", "360", "fast pan", "whip pan", "tracking shot", "follow shot"],
        "message": "Prompt 同时要求固定镜头和明显动态运镜。",
    },
    {
        "code": "no_text_conflicts_with_generated_text",
        "left_terms": ["no subtitles", "no readable subtitles", "no generated subtitles", "no karaoke text", "no text overlay"],
        "right_terms": ["add text overlay", "show text overlay", "display text overlay", "text overlay appears", "onscreen text", "on-screen text", "large text appears", "words appear", "title card", "caption appears"],
        "message": "Prompt 同时禁止字幕/文字，又要求生成画面文字。",
    },
    {
        "code": "no_fake_customer_site_conflicts_with_real_site_claim",
        "left_terms": ["no fake customer site", "not a real case claim", "visual explanation"],
        "right_terms": ["at a real customer site", "at an actual customer site", "real factory case", "authentic customer case"],
        "message": "Prompt 同时禁止伪装真实现场，又要求真实客户现场表达。",
    },
    {
        "code": "no_exaggerated_test_conflicts_with_proof_claim",
        "left_terms": ["no exaggerated test", "no exaggerated testing", "no unsupported temperature result", "no fake certification"],
        "right_terms": ["prove 1000", "certified result", "official certification", "guaranteed performance", "will not fail"],
        "message": "Prompt 同时禁止夸大测试/认证，又要求未经确认的证明性表达。",
    },
]

PROMPT_DURATION_COMPLEXITY_POLICY = {
    "max_time_segments_for_5s": 3,
    "max_time_segments_for_8s": 4,
    "max_time_segments_for_15s": 5,
    "max_scene_change_terms_for_5s": 3,
    "max_scene_change_terms_for_8s": 4,
    "max_scene_change_terms_for_15s": 6,
    "scene_change_terms": [
        "cut to",
        "then cut",
        "scene changes",
        "new scene",
        "montage",
        "split screen",
        "rapid transition",
        "fast transition",
        "whip pan",
        "explosion",
    ],
}

CREATIVE_DIRECTION_QUALITY_MATRIX = {
    "product_overview": {
        "hook": "前 2 秒必须讲清这是工业隔热带产品，不做抽象品牌开场。",
        "visual_focus": "产品卷装、织带表面和典型工业背景必须快速出现。",
        "message_focus": "说明产品是什么、适合什么客户、解决什么基本问题。",
        "cta_rule": "结尾使用轻量 CTA，不压过产品理解。",
    },
    "single_core_benefit": {
        "hook": "前 2 秒直接点出单一核心卖点。",
        "visual_focus": "所有镜头围绕同一卖点强化，不堆叠过多标签。",
        "message_focus": "只解释一个已确认优势，避免扩展成多卖点介绍。",
        "cta_rule": "CTA 与该卖点相关，例如索取规格或样品。",
    },
    "multiple_benefit_overview": {
        "hook": "前 2 秒建立高温隔热/施工痛点，再快速进入产品。",
        "visual_focus": "用短镜头轮换展示产品、细节、应用和已确认卖点。",
        "message_focus": "耐高温、隔热、不刺痒、不冒烟等信息只能来自正式知识。",
        "cta_rule": "允许轻量 CTA，重点仍是首次触达教育。",
    },
    "product_detail": {
        "hook": "前 2 秒展示织纹、边缘或厚度细节。",
        "visual_focus": "微距、手持、卷装边缘、柔性形态和材料质感。",
        "message_focus": "强调可见材料细节，不用细节画面证明未经确认的性能。",
        "cta_rule": "CTA 可提示索取规格或样品。",
    },
    "application_demonstration": {
        "hook": "前 2 秒出现明确应用场景或安装动作。",
        "visual_focus": "管道、炉门、设备保温等已确认场景；AI 场景必须标记为模拟。",
        "message_focus": "说明可用在哪里，不承诺具体工况结果。",
        "cta_rule": "CTA 引导客户提供应用环境。",
    },
    "customer_pain_point_solution": {
        "hook": "前 2 秒提出客户痛点，例如烟雾、刺痒、施工麻烦或隔热不足。",
        "visual_focus": "痛点与解决方案形成清晰前后关系，但不攻击竞品。",
        "message_focus": "围绕问题解决组织叙事。",
        "cta_rule": "CTA 引导客户描述现有痛点。",
    },
    "installation_demonstration": {
        "hook": "前 2 秒进入裁切、缠绕或固定动作。",
        "visual_focus": "手部动作、施工路径、收尾细节和材料柔性。",
        "message_focus": "说明施工流程和注意点，不替代正式安装说明书。",
        "cta_rule": "CTA 可引导索取安装建议。",
    },
    "usage_precautions": {
        "hook": "前 2 秒提出选型或使用边界问题。",
        "visual_focus": "用清晰卡片和示意镜头降低误用风险。",
        "message_focus": "强调适用边界、确认工况、避免过度承诺。",
        "cta_rule": "CTA 引导客户先确认温度、尺寸和应用环境。",
    },
    "technical_education": {
        "hook": "前 2 秒提出一个材料或选型问题。",
        "visual_focus": "工程说明、结构示意和产品实拍结合。",
        "message_focus": "用通俗语言解释材料逻辑。",
        "cta_rule": "CTA 可提示获取 datasheet。",
    },
    "performance_test": {
        "hook": "前 2 秒出现受控热源或测试视觉。",
        "visual_focus": "测试画面必须克制，不伪造检测结果。",
        "message_focus": "只表达已确认测试事实，不把演示当认证。",
        "cta_rule": "CTA 引导索取正式测试资料。",
    },
    "faq": {
        "hook": "前 2 秒显示或提出一个真实采购问题。",
        "visual_focus": "问题卡片与产品/应用镜头交替。",
        "message_focus": "每个回答短、具体、可追溯。",
        "cta_rule": "CTA 引导继续提问或索取规格。",
    },
    "material_comparison_selection": {
        "hook": "前 2 秒提出材料选型困惑。",
        "visual_focus": "中性对比，不做攻击性竞品画面。",
        "message_focus": "说明选择逻辑和边界，不制造无证据优劣结论。",
        "cta_rule": "CTA 引导客户给出工况后推荐选型。",
    },
    "specification_customization": {
        "hook": "前 2 秒展示宽度、厚度、卷长或包装信息。",
        "visual_focus": "规格卡、卷装、不同尺寸组合；没有真实多规格素材时不得伪造。",
        "message_focus": "围绕已确认规格和定制能力。",
        "cta_rule": "CTA 引导发送尺寸需求。",
    },
    "procurement_guide": {
        "hook": "前 2 秒出现 buyer checklist 或询价前确认项。",
        "visual_focus": "清晰列表、产品图、规格信息和采购判断路径。",
        "message_focus": "帮助采购/OEM/分销商减少沟通成本。",
        "cta_rule": "CTA 引导发送应用、温度、尺寸和数量。",
    },
    "real_case_study": {
        "hook": "前 2 秒出现真实案例或明确说明是示意场景。",
        "visual_focus": "必须基于正式可公开案例素材；无案例时不伪装真实客户现场。",
        "message_focus": "讲清应用背景和可公开事实。",
        "cta_rule": "CTA 引导索取类似应用建议。",
    },
    "inquiry_conversion": {
        "hook": "前 2 秒直接说明客户可以获得什么信息或样品。",
        "visual_focus": "产品可信展示、规格/应用提示和联系方式节奏清晰。",
        "message_focus": "围绕联系、索样、报价或规格确认收口。",
        "cta_rule": "必须有明确 CTA，且联系方式来自正式知识或配置。",
    },
}


@dataclass(frozen=True)
class ProjectValidation:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class VideoCreationRunResult:
    run_dir: str
    requirements_path: str
    workflow_state_path: str
    context_id: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VideoCreationStepResult:
    run_dir: str
    workflow_state_path: str
    status: str
    phase: str
    output_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_video_creation_request(text: str) -> bool:
    utterance = text.strip().lower()
    if not utterance:
        return False
    mentions_video = any(token in utterance for token in ["视频", "短视频", "video", "tiktok", "youtube shorts", "shorts"])
    mentions_quartz = any(token in utterance for token in ["石英纤维", "隔热带", "quartz", "fiberglass tape", "glass fiber tape"])
    return mentions_video and mentions_quartz


def validate_video_creation_project(paths: ProjectPaths) -> ProjectValidation:
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


def create_video_creation_run(
    paths: ProjectPaths,
    request_text: str,
    language_version: str,
    platforms: list[str] | tuple[str, ...],
    duration_seconds: int = DEFAULT_VIDEO_DURATION_SECONDS,
    target_audience: str = "",
    core_objective: str = "",
    primary_direction: str = "",
    supporting_direction: str | None = None,
    now: datetime | None = None,
) -> VideoCreationRunResult:
    validation = validate_video_creation_project(paths)
    if not validation.valid:
        raise ValueError("当前目录不是可用于视频创作 Agent 的知识库项目目录：" + "；".join(validation.errors))

    language = normalize_language_version(language_version)
    platform_values = normalize_platforms(platforms)
    duration = normalize_duration(duration_seconds)
    primary = normalize_creative_direction(primary_direction)
    supporting = normalize_creative_direction(supporting_direction) if supporting_direction else None
    if supporting and supporting["id"] == primary["id"]:
        raise ValueError("辅助创意方向不能与主创意方向相同")

    context = build_downstream_context(
        paths,
        "video_creation",
        product_id=INTERNAL_PRODUCT_ID,
        query=request_text,
        include_review_items=True,
    )
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_dir = paths.generated_dir / "reports" / "video-creation" / f"{timestamp}_{RUN_DIR_PRODUCT_SLUG}_{language}"
    _ensure_run_dirs(run_dir)

    recommendations = recommend_creative_directions(request_text, platform_values, target_audience, core_objective, context)
    requirements_path = run_dir / "requirements.md"
    workflow_state_path = run_dir / "workflow_state.json"
    change_log_path = run_dir / "change_log.md"
    context_path = paths.generated_dir / "agent-interface" / "contexts" / f"{context['context_id']}.json"
    requirements = {
        "request_text": request_text,
        "language_version": language,
        "platforms": platform_values,
        "duration_seconds": duration,
        "target_audience": target_audience,
        "core_objective": core_objective,
        "primary_direction": primary,
        "supporting_direction": supporting,
        "recommendations": recommendations,
        "fixed_directions": VIDEO_CREATIVE_DIRECTIONS,
        "context": {
            "context_id": context["context_id"],
            "product_id": context["product_id"],
            "canonical_product_id": context.get("canonical_product_id", INTERNAL_PRODUCT_ID),
            "product_alias_ids": context.get("product_alias_ids", []),
            "raw_access": context["raw_access"],
            "policy": context["policy"],
        },
    }
    requirements_path.write_text(_render_requirements(requirements), encoding="utf-8")
    workflow_state = _initial_workflow_state(
        run_dir,
        requirements,
        context,
        paths.config or {},
        requirements_path,
        context_path,
        change_log_path,
        timestamp,
    )
    workflow_state_path.write_text(json.dumps(workflow_state, ensure_ascii=False, indent=2), encoding="utf-8")
    change_log_path.write_text(
        f"# 视频创作变更记录\n\n- {timestamp}: 创建视频创作运行，等待生成视频策划。\n",
        encoding="utf-8",
    )
    return VideoCreationRunResult(
        run_dir=str(run_dir),
        requirements_path=str(requirements_path),
        workflow_state_path=str(workflow_state_path),
        context_id=context["context_id"],
        status=workflow_state["status"],
    )


def generate_video_plan(run_dir: Path, overwrite: bool = False, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_video_plan", "awaiting_video_plan_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能生成视频策划。")

    plan_md_path = run_dir / "video_plan.md"
    plan_json_path = run_dir / "video_plan.json"
    if (plan_md_path.exists() or plan_json_path.exists()) and not overwrite:
        raise FileExistsError(f"视频策划已存在，未覆盖：{plan_md_path}")

    context = _load_context_for_state(run_dir, state)
    plan = _build_video_plan_payload(state, context, now or datetime.now())
    plan_md_path.write_text(_render_video_plan(plan), encoding="utf-8")
    plan_json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "video_plan_ready"
    state["phase"] = "awaiting_video_plan_confirmation"
    state["current_pending_confirmation"] = "确认策划"
    state["updated_at"] = timestamp
    state["confirmations"]["video_plan"] = False
    _clear_downstream_confirmations(state, after="video_plan")
    state.setdefault("files", {})["video_plan_md"] = str(plan_md_path)
    state.setdefault("files", {})["video_plan_json"] = str(plan_json_path)
    _append_status_history(state, "video_plan_ready", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "生成视频策划，等待确认策划。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(plan_md_path), str(plan_json_path)),
    )


def confirm_video_plan(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    plan_md_path = Path(state.get("files", {}).get("video_plan_md", run_dir / "video_plan.md"))
    plan_json_path = Path(state.get("files", {}).get("video_plan_json", run_dir / "video_plan.json"))
    if not plan_md_path.exists() or not plan_json_path.exists():
        raise ValueError("找不到可确认的视频策划，请先生成 video_plan.md 和 video_plan.json。")
    if state.get("phase") != "awaiting_video_plan_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认策划。")

    timestamp = _timestamp(now)
    state["status"] = "video_plan_confirmed"
    state["phase"] = "ready_for_storyboard"
    state["current_pending_confirmation"] = "生成分镜"
    state["updated_at"] = timestamp
    state["confirmations"]["video_plan"] = True
    _append_status_history(state, "video_plan_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "确认视频策划，进入分镜生成阶段。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(plan_md_path), str(plan_json_path)),
    )


def generate_storyboard(run_dir: Path, overwrite: bool = False, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_storyboard", "awaiting_storyboard_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能生成分镜。")
    if not state.get("confirmations", {}).get("video_plan"):
        raise ValueError("视频策划尚未确认，不能生成分镜。")

    storyboard_md_path = run_dir / "storyboard.md"
    storyboard_json_path = run_dir / "storyboard.json"
    prompts_md_path = run_dir / "prompts.md"
    prompts_json_path = run_dir / "prompts.json"
    existing = [path for path in [storyboard_md_path, storyboard_json_path, prompts_md_path, prompts_json_path] if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"分镜或 Prompt 已存在，未覆盖：{existing[0]}")

    plan_path = Path(state.get("files", {}).get("video_plan_json", run_dir / "video_plan.json"))
    if not plan_path.exists():
        raise ValueError("找不到 video_plan.json，请先生成并确认视频策划。")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    storyboard = _build_storyboard_payload(state, plan, now or datetime.now())
    prompts = _build_prompts_payload(storyboard, plan, now or datetime.now())

    storyboard_md_path.write_text(_render_storyboard(storyboard), encoding="utf-8")
    storyboard_json_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    prompts_md_path.write_text(_render_prompts(prompts), encoding="utf-8")
    prompts_json_path.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "storyboard_ready"
    state["phase"] = "awaiting_storyboard_confirmation"
    state["current_pending_confirmation"] = "确认分镜"
    state["updated_at"] = timestamp
    state["confirmations"]["storyboard"] = False
    _clear_downstream_confirmations(state, after="storyboard")
    files = state.setdefault("files", {})
    files["storyboard_md"] = str(storyboard_md_path)
    files["storyboard_json"] = str(storyboard_json_path)
    files["prompts_md"] = str(prompts_md_path)
    files["prompts_json"] = str(prompts_json_path)
    _append_status_history(state, "storyboard_ready", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "生成视频分镜和即梦 Prompt，等待确认分镜。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(storyboard_md_path), str(storyboard_json_path), str(prompts_md_path), str(prompts_json_path)),
    )


def confirm_storyboard(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    files = state.get("files", {})
    required = [
        Path(files.get("storyboard_md", run_dir / "storyboard.md")),
        Path(files.get("storyboard_json", run_dir / "storyboard.json")),
        Path(files.get("prompts_md", run_dir / "prompts.md")),
        Path(files.get("prompts_json", run_dir / "prompts.json")),
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise ValueError(f"找不到可确认的分镜或 Prompt：{missing[0]}")
    if state.get("phase") != "awaiting_storyboard_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认分镜。")

    timestamp = _timestamp(now)
    state["status"] = "storyboard_confirmed"
    state["phase"] = "ready_for_narration_script"
    state["current_pending_confirmation"] = "生成旁白文案"
    state["updated_at"] = timestamp
    state["confirmations"]["storyboard"] = True
    _append_status_history(state, "storyboard_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "确认视频分镜，进入旁白文案阶段。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=tuple(str(path) for path in required),
    )


def generate_narration_script(run_dir: Path, overwrite: bool = False, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_narration_script", "awaiting_narration_script_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能生成旁白文案。")
    if not state.get("confirmations", {}).get("storyboard"):
        raise ValueError("分镜尚未确认，不能生成旁白文案。")

    script_md_path = run_dir / "narration" / "script.md"
    script_json_path = run_dir / "narration" / "script.json"
    if (script_md_path.exists() or script_json_path.exists()) and not overwrite:
        raise FileExistsError(f"旁白文案已存在，未覆盖：{script_md_path}")

    plan = _load_json_file(Path(state["files"]["video_plan_json"]), "video_plan.json")
    storyboard = _load_json_file(Path(state["files"]["storyboard_json"]), "storyboard.json")
    narration = _build_narration_script_payload(state, plan, storyboard, now or datetime.now())
    script_md_path.write_text(_render_narration_script(narration), encoding="utf-8")
    script_json_path.write_text(json.dumps(narration, ensure_ascii=False, indent=2), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "narration_script_ready"
    state["phase"] = "awaiting_narration_script_confirmation"
    state["current_pending_confirmation"] = "确认旁白文案"
    state["updated_at"] = timestamp
    state["confirmations"]["narration_script"] = False
    _clear_downstream_confirmations(state, after="narration_script")
    state.setdefault("files", {})["narration_script_md"] = str(script_md_path)
    state.setdefault("files", {})["narration_script_json"] = str(script_json_path)
    _append_status_history(state, "narration_script_ready", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "生成完整旁白文案，等待确认旁白文案。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(script_md_path), str(script_json_path)),
    )


def confirm_narration_script(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    script_md_path = Path(state.get("files", {}).get("narration_script_md", run_dir / "narration" / "script.md"))
    script_json_path = Path(state.get("files", {}).get("narration_script_json", run_dir / "narration" / "script.json"))
    if not script_md_path.exists() or not script_json_path.exists():
        raise ValueError("找不到可确认的旁白文案，请先生成 narration/script.md。")
    if state.get("phase") != "awaiting_narration_script_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认旁白文案。")

    timestamp = _timestamp(now)
    state["status"] = "narration_script_confirmed"
    state["phase"] = "ready_for_voice_samples"
    state["current_pending_confirmation"] = "生成声音样本"
    state["updated_at"] = timestamp
    state["confirmations"]["narration_script"] = True
    _append_status_history(state, "narration_script_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "确认旁白文案，进入声音样本阶段。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(script_md_path), str(script_json_path)),
    )


def generate_voice_samples(run_dir: Path, overwrite: bool = False, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_voice_samples", "awaiting_voice_selection"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能生成声音样本。")
    if not state.get("confirmations", {}).get("narration_script"):
        raise ValueError("旁白文案尚未确认，不能生成声音样本。")

    script = _load_json_file(Path(state["files"]["narration_script_json"]), "narration/script.json")
    samples_dir = run_dir / "narration" / "voice_samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    samples_json_path = run_dir / "narration" / "voice_samples.json"
    if samples_json_path.exists() and not overwrite:
        raise FileExistsError(f"声音样本已存在，未覆盖：{samples_json_path}")
    excerpt = _voice_sample_excerpt(script)
    samples = []
    for index, profile in enumerate(_voice_profiles(state["language_version"]), start=1):
        sample_path = samples_dir / f"sample_{index}.wav"
        if sample_path.exists() and not overwrite:
            raise FileExistsError(f"声音样本已存在，未覆盖：{sample_path}")
        _write_mock_wav(sample_path, duration_seconds=2.0 + index * 0.15)
        samples.append(
            {
                "sample_id": index,
                "voice_profile": profile,
                "excerpt": excerpt,
                "audio_path": str(sample_path),
                "provider": "mock_narration_provider",
            }
        )
    samples_json_path.write_text(json.dumps({"samples": samples, "excerpt": excerpt}, ensure_ascii=False, indent=2), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "voice_samples_ready"
    state["phase"] = "awaiting_voice_selection"
    state["current_pending_confirmation"] = "声音选 1/2/3"
    state["updated_at"] = timestamp
    state["confirmations"]["voice"] = False
    _clear_downstream_confirmations(state, after="voice")
    state.setdefault("files", {})["voice_samples_json"] = str(samples_json_path)
    _append_status_history(state, "voice_samples_ready", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "生成 3 个声音样本，等待选择声音。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=tuple(sample["audio_path"] for sample in samples) + (str(samples_json_path),),
    )


def select_voice(run_dir: Path, sample_id: int, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "awaiting_voice_selection":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能选择声音。")
    samples_path = Path(state.get("files", {}).get("voice_samples_json", run_dir / "narration" / "voice_samples.json"))
    samples = _load_json_file(samples_path, "voice_samples.json")
    selected = next((item for item in samples.get("samples", []) if int(item["sample_id"]) == int(sample_id)), None)
    if not selected:
        raise ValueError("声音样本只能选择 1、2 或 3")

    timestamp = _timestamp(now)
    state["status"] = "voice_selected"
    state["phase"] = "ready_for_full_narration"
    state["current_pending_confirmation"] = "生成完整旁白"
    state["updated_at"] = timestamp
    state["confirmations"]["voice"] = True
    state["selected_voice"] = selected
    _append_status_history(state, "voice_selected", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"选择声音样本 {sample_id}，进入完整旁白生成阶段。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(selected["audio_path"], str(samples_path)),
    )


def generate_full_narration(run_dir: Path, overwrite: bool = False, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_full_narration", "awaiting_narration_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能生成完整旁白。")
    if not state.get("confirmations", {}).get("voice"):
        raise ValueError("尚未选择声音，不能生成完整旁白。")

    script = _load_json_file(Path(state["files"]["narration_script_json"]), "narration/script.json")
    narration_path = run_dir / "narration" / "narration.wav"
    timing_path = run_dir / "narration" / "timing.json"
    preview_path = run_dir / "narration" / "narration_preview.md"
    if (narration_path.exists() or timing_path.exists()) and not overwrite:
        raise FileExistsError(f"完整旁白已存在，未覆盖：{narration_path}")
    duration = int(state["duration_seconds"])
    _write_mock_wav(narration_path, duration_seconds=float(duration))
    timing = _build_sentence_timing(script, duration, state.get("selected_voice", {}), now or datetime.now())
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    preview_path.write_text(_render_narration_preview(script, timing, state.get("selected_voice", {})), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "narration_ready"
    state["phase"] = "awaiting_narration_confirmation"
    state["current_pending_confirmation"] = "确认旁白"
    state["updated_at"] = timestamp
    state["confirmations"]["narration"] = False
    _clear_downstream_confirmations(state, after="narration")
    files = state.setdefault("files", {})
    files["narration_audio"] = str(narration_path)
    files["narration_timing"] = str(timing_path)
    files["narration_preview"] = str(preview_path)
    _append_status_history(state, "narration_ready", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "生成完整旁白音频和句级时间轴，等待确认旁白。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(narration_path), str(timing_path), str(preview_path)),
    )


def confirm_narration(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    files = state.get("files", {})
    narration_path = Path(files.get("narration_audio", run_dir / "narration" / "narration.wav"))
    timing_path = Path(files.get("narration_timing", run_dir / "narration" / "timing.json"))
    if not narration_path.exists() or not timing_path.exists():
        raise ValueError("找不到可确认的完整旁白，请先生成 narration.wav 和 timing.json。")
    if state.get("phase") != "awaiting_narration_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认旁白。")

    timestamp = _timestamp(now)
    state["status"] = "narration_confirmed"
    state["phase"] = "ready_for_dreamina_jobs"
    state["current_pending_confirmation"] = "规划即梦任务"
    state["updated_at"] = timestamp
    state["confirmations"]["narration"] = True
    _append_status_history(state, "narration_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "确认旁白，进入即梦任务规划阶段。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(narration_path), str(timing_path)),
    )


def generate_dreamina_jobs(run_dir: Path, overwrite: bool = False, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_dreamina_jobs", "awaiting_dreamina_generation_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能规划即梦任务。")
    if not state.get("confirmations", {}).get("narration"):
        raise ValueError("旁白尚未确认，不能规划即梦任务。")

    jobs_md_path = run_dir / "dreamina_generation" / "dreamina_jobs.md"
    jobs_json_path = run_dir / "dreamina_generation" / "dreamina_jobs.json"
    if (jobs_md_path.exists() or jobs_json_path.exists()) and not overwrite:
        raise FileExistsError(f"即梦任务计划已存在，未覆盖：{jobs_md_path}")

    plan = _load_json_file(Path(state["files"]["video_plan_json"]), "video_plan.json")
    storyboard = _load_json_file(Path(state["files"]["storyboard_json"]), "storyboard.json")
    prompts = _load_json_file(Path(state["files"]["prompts_json"]), "prompts.json")
    timing = _load_json_file(Path(state["files"]["narration_timing"]), "narration/timing.json")
    jobs = _build_dreamina_jobs_payload(state, plan, storyboard, prompts, timing, now or datetime.now())
    jobs_md_path.write_text(_render_dreamina_jobs(jobs), encoding="utf-8")
    jobs_json_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "dreamina_jobs_ready"
    state["phase"] = "awaiting_dreamina_generation_confirmation"
    state["current_pending_confirmation"] = "确认即梦生成"
    state["updated_at"] = timestamp
    state["confirmations"]["dreamina_generation"] = False
    _clear_downstream_confirmations(state, after="dreamina_generation")
    files = state.setdefault("files", {})
    files["dreamina_jobs_md"] = str(jobs_md_path)
    files["dreamina_jobs_json"] = str(jobs_json_path)
    _append_status_history(state, "dreamina_jobs_ready", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "生成即梦任务计划，等待确认即梦生成。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(jobs_md_path), str(jobs_json_path)),
    )


def confirm_dreamina_generation(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    jobs_md_path = Path(state.get("files", {}).get("dreamina_jobs_md", run_dir / "dreamina_generation" / "dreamina_jobs.md"))
    jobs_json_path = Path(state.get("files", {}).get("dreamina_jobs_json", run_dir / "dreamina_generation" / "dreamina_jobs.json"))
    if not jobs_md_path.exists() or not jobs_json_path.exists():
        raise ValueError("找不到可确认的即梦任务计划，请先生成 dreamina_jobs.md 和 dreamina_jobs.json。")
    if state.get("phase") != "awaiting_dreamina_generation_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认即梦生成。")
    jobs = _load_json_file(jobs_json_path, "dreamina_jobs.json")
    if any(job.get("job_type") == "blocked" or job.get("status") == "blocked" or job.get("validation", {}).get("status") == "blocked" for job in jobs.get("jobs", [])):
        raise ValueError("存在 blocked 即梦任务，不能确认即梦生成。请先修改分镜或补充素材。")

    timestamp = _timestamp(now)
    state["status"] = "dreamina_generation_confirmed"
    state["phase"] = "ready_for_dreamina_submission"
    state["current_pending_confirmation"] = "提交即梦任务"
    state["updated_at"] = timestamp
    state["confirmations"]["dreamina_generation"] = True
    state["dreamina_authorization"] = {
        "confirmed_at": timestamp,
        "estimated_total_credits": jobs["estimated_total_credits"],
        "note": "用户已确认可以提交即梦生成；本步骤不实际提交任务。",
    }
    _append_status_history(state, "dreamina_generation_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "确认即梦生成授权，等待提交即梦任务。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(jobs_md_path), str(jobs_json_path)),
    )


def submit_dreamina_jobs(
    run_dir: Path,
    execute: bool = False,
    dreamina_command: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "ready_for_dreamina_submission":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能提交即梦任务。")
    if not state.get("confirmations", {}).get("dreamina_generation"):
        raise ValueError("即梦生成尚未确认，不能提交任务。")

    jobs_json_path = Path(state.get("files", {}).get("dreamina_jobs_json", run_dir / "dreamina_generation" / "dreamina_jobs.json"))
    jobs_payload = _load_json_file(jobs_json_path, "dreamina_jobs.json")
    if any(job.get("job_type") == "blocked" for job in jobs_payload.get("jobs", [])):
        raise ValueError("存在 blocked 即梦任务，不能提交即梦生成。")

    command = dreamina_command or _state_adapter_command(state, "dreamina_command", "dreamina")
    submission = _submit_dreamina_jobs_payload(jobs_payload, execute, command, runner, now or datetime.now())
    submission_json_path = run_dir / "dreamina_generation" / "dreamina_submission.json"
    submission_md_path = run_dir / "dreamina_generation" / "dreamina_submission.md"
    submission_json_path.write_text(json.dumps(submission, ensure_ascii=False, indent=2), encoding="utf-8")
    submission_md_path.write_text(_render_dreamina_submission(submission), encoding="utf-8")

    timestamp = _timestamp(now)
    failed = [item for item in submission["submissions"] if item["status"] == "submission_failed"]
    state["status"] = "dreamina_submission_failed" if failed else "dreamina_jobs_submitted"
    state["phase"] = "ready_for_dreamina_submission" if failed else "awaiting_dreamina_results"
    state["current_pending_confirmation"] = "修复即梦提交失败" if failed else "查询即梦结果"
    state["updated_at"] = timestamp
    files = state.setdefault("files", {})
    files["dreamina_submission_md"] = str(submission_md_path)
    files["dreamina_submission_json"] = str(submission_json_path)
    _append_status_history(state, state["status"], timestamp)
    _write_state(state_path, state)
    mode = "真实提交" if execute else "dry-run 提交记录"
    _append_change(run_dir, timestamp, f"生成即梦{mode}，状态：{state['status']}。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(submission_md_path), str(submission_json_path)),
    )


def query_dreamina_results(
    run_dir: Path,
    execute: bool = False,
    dreamina_command: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"awaiting_dreamina_results", "awaiting_shot_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能查询即梦结果。")

    submission_json_path = Path(state.get("files", {}).get("dreamina_submission_json", run_dir / "dreamina_generation" / "dreamina_submission.json"))
    submission = _load_json_file(submission_json_path, "dreamina_submission.json")
    command = dreamina_command or _state_adapter_command(state, "dreamina_command", "dreamina")
    results = _query_dreamina_results_payload(submission, execute, command, runner, now or datetime.now())
    results_json_path = run_dir / "dreamina_generation" / "dreamina_results.json"
    results_md_path = run_dir / "dreamina_generation" / "dreamina_results.md"
    results_json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    results_md_path.write_text(_render_dreamina_results(results), encoding="utf-8")

    timestamp = _timestamp(now)
    all_succeeded = all(item["status"] == "succeeded" for item in results["results"])
    state["status"] = "dreamina_results_ready" if all_succeeded else "dreamina_results_pending"
    state["phase"] = "awaiting_shot_confirmation" if all_succeeded else "awaiting_dreamina_results"
    state["current_pending_confirmation"] = "确认镜头或重做镜头 XX" if all_succeeded else "继续查询即梦结果"
    state["updated_at"] = timestamp
    state["confirmations"]["shots"] = False
    files = state.setdefault("files", {})
    files["dreamina_results_md"] = str(results_md_path)
    files["dreamina_results_json"] = str(results_json_path)
    _append_status_history(state, state["status"], timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"查询即梦结果，状态：{state['status']}。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(results_md_path), str(results_json_path)),
    )


def confirm_shots(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "awaiting_shot_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认镜头。")
    results_json_path = Path(state.get("files", {}).get("dreamina_results_json", run_dir / "dreamina_generation" / "dreamina_results.json"))
    results = _load_json_file(results_json_path, "dreamina_results.json")
    if any(item.get("status") != "succeeded" for item in results.get("results", [])):
        raise ValueError("存在未成功的镜头结果，不能确认镜头。")
    shot_preview = _build_shot_preview_manifest(run_dir, state, results, now or datetime.now())
    shot_preview_json_path = run_dir / "dreamina_generation" / "shot_preview_manifest.json"
    shot_preview_md_path = run_dir / "dreamina_generation" / "shot_preview_manifest.md"
    shot_preview_json_path.write_text(json.dumps(shot_preview, ensure_ascii=False, indent=2), encoding="utf-8")
    shot_preview_md_path.write_text(_render_shot_preview_manifest(shot_preview), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "shots_confirmed"
    state["phase"] = "ready_for_final_assembly"
    state["current_pending_confirmation"] = "生成成片预览"
    state["updated_at"] = timestamp
    state["confirmations"]["shots"] = True
    state.setdefault("files", {})["shot_preview_manifest_json"] = str(shot_preview_json_path)
    state.setdefault("files", {})["shot_preview_manifest_md"] = str(shot_preview_md_path)
    state.setdefault("files", {})["shot_preview_mp4"] = str(run_dir / "dreamina_generation" / "shot_preview.mp4")
    _append_status_history(state, "shots_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "确认全部镜头，进入成片组装阶段。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(results_json_path), str(shot_preview_md_path), str(shot_preview_json_path)),
    )


def plan_shot_retry(run_dir: Path, shot_id: str, reason: str = "", now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    normalized_shot_id = _normalize_shot_id(shot_id)
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "awaiting_shot_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能规划单镜头重做。")
    jobs = _load_json_file(Path(state["files"]["dreamina_jobs_json"]), "dreamina_jobs.json")
    original_job = next((job for job in jobs.get("jobs", []) if job["shot_id"] == normalized_shot_id), None)
    if not original_job:
        raise ValueError(f"找不到镜头 {normalized_shot_id} 的即梦任务。")
    if original_job.get("job_type") in {"blocked", "reuse_video", "reuse_image"}:
        raise ValueError(f"镜头 {normalized_shot_id} 的任务类型是 {original_job.get('job_type')}，不适合提交即梦重做。")

    timestamp = _timestamp(now)
    retry_dir = run_dir / "dreamina_generation" / "retry_plans"
    retry_dir.mkdir(parents=True, exist_ok=True)
    retry_json_path = retry_dir / f"retry_shot_{normalized_shot_id}_{timestamp}.json"
    retry_md_path = retry_dir / f"retry_shot_{normalized_shot_id}_{timestamp}.md"
    retry = {
        "schema_version": "dreamina-shot-retry-plan-v1",
        "generated_at": (now or datetime.now()).isoformat(),
        "status": "planned_pending_user_confirmation",
        "shot_id": normalized_shot_id,
        "reason": reason,
        "original_job": original_job,
        "estimated_credits": original_job["estimated_credits"],
        "submit_requires_confirmation": f"确认重做镜头 {normalized_shot_id}",
        "policy": {
            "retry_only_one_shot": True,
            "do_not_resubmit_accepted_shots": True,
            "requires_user_confirmation": True,
        },
    }
    retry_json_path.write_text(json.dumps(retry, ensure_ascii=False, indent=2), encoding="utf-8")
    retry_md_path.write_text(_render_shot_retry_plan(retry), encoding="utf-8")

    state["status"] = "shot_retry_planned"
    state["phase"] = "awaiting_shot_retry_confirmation"
    state["current_pending_confirmation"] = f"确认重做镜头 {normalized_shot_id}"
    state["updated_at"] = timestamp
    state["pending_shot_retry"] = {
        "shot_id": normalized_shot_id,
        "retry_plan_md": str(retry_md_path),
        "retry_plan_json": str(retry_json_path),
        "estimated_credits": original_job["estimated_credits"],
    }
    _append_status_history(state, "shot_retry_planned", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"规划重做镜头 {normalized_shot_id}，等待确认重做。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(retry_md_path), str(retry_json_path)),
    )


def confirm_shot_retry(run_dir: Path, shot_id: str, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    normalized_shot_id = _normalize_shot_id(shot_id)
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "awaiting_shot_retry_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认单镜头重做。")
    pending = state.get("pending_shot_retry") or {}
    if pending.get("shot_id") != normalized_shot_id:
        raise ValueError(f"当前等待确认的是镜头 {pending.get('shot_id')}，不是 {normalized_shot_id}。")

    timestamp = _timestamp(now)
    state["status"] = "shot_retry_confirmed"
    state["phase"] = "ready_for_shot_retry_submission"
    state["current_pending_confirmation"] = f"提交重做镜头 {normalized_shot_id}"
    state["updated_at"] = timestamp
    pending["confirmed_at"] = timestamp
    state["pending_shot_retry"] = pending
    _append_status_history(state, "shot_retry_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"确认重做镜头 {normalized_shot_id}，等待提交单镜头重做。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(pending["retry_plan_md"], pending["retry_plan_json"]),
    )


def submit_shot_retry(
    run_dir: Path,
    execute: bool = False,
    dreamina_command: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    expected_shot_id: str | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "ready_for_shot_retry_submission":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能提交单镜头重做。")

    pending = state.get("pending_shot_retry") or {}
    shot_id = pending.get("shot_id")
    retry_plan_json = pending.get("retry_plan_json")
    if not shot_id or not retry_plan_json:
        raise ValueError("找不到已确认的单镜头重做计划。")
    if expected_shot_id and _normalize_shot_id(expected_shot_id) != shot_id:
        raise ValueError(f"当前等待提交的是镜头 {shot_id}，不是 {_normalize_shot_id(expected_shot_id)}。")

    retry_plan = _load_json_file(Path(retry_plan_json), "retry shot plan")
    original_job = retry_plan.get("original_job") or {}
    if original_job.get("shot_id") != shot_id:
        raise ValueError(f"重做计划镜头 {original_job.get('shot_id')} 与等待提交镜头 {shot_id} 不一致。")
    if original_job.get("job_type") in {"blocked", "reuse_video", "reuse_image"}:
        raise ValueError(f"镜头 {shot_id} 的任务类型是 {original_job.get('job_type')}，不能提交即梦重做。")

    timestamp = _timestamp(now)
    retry_job = dict(original_job)
    retry_job["job_id"] = f"retry_{original_job['job_id']}_{timestamp}"
    retry_job["retry_of_job_id"] = original_job["job_id"]
    retry_job["retry_reason"] = retry_plan.get("reason", "")
    jobs_payload = {
        "schema_version": "dreamina-jobs-v1",
        "generated_at": (now or datetime.now()).isoformat(),
        "run_dir": str(run_dir),
        "estimated_total_credits": retry_plan["estimated_credits"],
        "jobs": [retry_job],
        "policy": {
            "submitted_only_after_user_confirmation": True,
            "retry_only_one_shot": True,
            "do_not_resubmit_accepted_shots": True,
        },
    }
    command = dreamina_command or _state_adapter_command(state, "dreamina_command", "dreamina")
    submission = _submit_dreamina_jobs_payload(jobs_payload, execute, command, runner, now or datetime.now())

    retry_dir = run_dir / "dreamina_generation" / "retry_submissions"
    retry_dir.mkdir(parents=True, exist_ok=True)
    submission_json_path = retry_dir / f"retry_shot_{shot_id}_{timestamp}.json"
    submission_md_path = retry_dir / f"retry_shot_{shot_id}_{timestamp}.md"
    submission_json_path.write_text(json.dumps(submission, ensure_ascii=False, indent=2), encoding="utf-8")
    submission_md_path.write_text(_render_dreamina_submission(submission), encoding="utf-8")

    failed = [item for item in submission["submissions"] if item["status"] == "submission_failed"]
    state["status"] = "shot_retry_submission_failed" if failed else "shot_retry_submitted"
    state["phase"] = "ready_for_shot_retry_submission" if failed else "awaiting_shot_retry_results"
    state["current_pending_confirmation"] = f"修复重做镜头 {shot_id} 提交失败" if failed else f"查询重做镜头 {shot_id}"
    state["updated_at"] = timestamp
    pending["retry_submission_md"] = str(submission_md_path)
    pending["retry_submission_json"] = str(submission_json_path)
    pending["submitted_at"] = timestamp
    pending["execute_mode"] = "execute" if execute else "dry_run"
    state["pending_shot_retry"] = pending
    _append_status_history(state, state["status"], timestamp)
    _write_state(state_path, state)
    mode = "真实提交" if execute else "dry-run 提交记录"
    _append_change(run_dir, timestamp, f"生成镜头 {shot_id} 重做{mode}，状态：{state['status']}。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(submission_md_path), str(submission_json_path)),
    )


def query_shot_retry_results(
    run_dir: Path,
    execute: bool = False,
    dreamina_command: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    expected_shot_id: str | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"awaiting_shot_retry_results", "awaiting_shot_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能查询单镜头重做结果。")

    pending = state.get("pending_shot_retry") or {}
    shot_id = pending.get("shot_id")
    retry_submission_json = pending.get("retry_submission_json")
    if not shot_id or not retry_submission_json:
        raise ValueError("找不到已提交的单镜头重做记录。")
    if expected_shot_id and _normalize_shot_id(expected_shot_id) != shot_id:
        raise ValueError(f"当前等待查询的是镜头 {shot_id}，不是 {_normalize_shot_id(expected_shot_id)}。")

    submission = _load_json_file(Path(retry_submission_json), "retry submission")
    command = dreamina_command or _state_adapter_command(state, "dreamina_command", "dreamina")
    retry_results = _query_dreamina_results_payload(submission, execute, command, runner, now or datetime.now())

    timestamp = _timestamp(now)
    retry_dir = run_dir / "dreamina_generation" / "retry_results"
    retry_dir.mkdir(parents=True, exist_ok=True)
    retry_results_json_path = retry_dir / f"retry_shot_{shot_id}_{timestamp}.json"
    retry_results_md_path = retry_dir / f"retry_shot_{shot_id}_{timestamp}.md"
    retry_results_json_path.write_text(json.dumps(retry_results, ensure_ascii=False, indent=2), encoding="utf-8")
    retry_results_md_path.write_text(_render_dreamina_results(retry_results), encoding="utf-8")

    all_succeeded = all(item["status"] == "succeeded" for item in retry_results["results"])
    if all_succeeded:
        full_results_json_path = Path(state["files"]["dreamina_results_json"])
        full_results = _load_json_file(full_results_json_path, "dreamina_results.json")
        retry_result = retry_results["results"][0]
        replaced = False
        for index, item in enumerate(full_results.get("results", [])):
            if item.get("shot_id") == shot_id:
                updated_item = dict(retry_result)
                updated_item["replaces_previous_result"] = True
                updated_item["retry_result_json"] = str(retry_results_json_path)
                updated_item["previous_result"] = item
                full_results["results"][index] = updated_item
                replaced = True
                break
        if not replaced:
            raise ValueError(f"找不到镜头 {shot_id} 的原始结果，不能回填重做结果。")
        full_results["status"] = "ready" if all(item["status"] == "succeeded" for item in full_results["results"]) else "pending"
        full_results["last_retry_applied_at"] = (now or datetime.now()).isoformat()
        full_results_json_path.write_text(json.dumps(full_results, ensure_ascii=False, indent=2), encoding="utf-8")
        full_results_md_path = Path(state["files"]["dreamina_results_md"])
        full_results_md_path.write_text(_render_dreamina_results(full_results), encoding="utf-8")

    state["status"] = "shot_retry_results_ready" if all_succeeded else "shot_retry_results_pending"
    state["phase"] = "awaiting_shot_confirmation" if all_succeeded else "awaiting_shot_retry_results"
    state["current_pending_confirmation"] = "确认镜头或重做镜头 XX" if all_succeeded else f"继续查询重做镜头 {shot_id}"
    state["updated_at"] = timestamp
    pending["retry_results_md"] = str(retry_results_md_path)
    pending["retry_results_json"] = str(retry_results_json_path)
    pending["results_status"] = retry_results["status"]
    pending["queried_at"] = timestamp
    history = state.setdefault("shot_retry_history", [])
    history.append(dict(pending))
    if all_succeeded:
        state.pop("pending_shot_retry", None)
    else:
        state["pending_shot_retry"] = pending
    state["confirmations"]["shots"] = False
    _append_status_history(state, state["status"], timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"查询镜头 {shot_id} 重做结果，状态：{state['status']}。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(retry_results_md_path), str(retry_results_json_path)),
    )


def assemble_final_preview(
    run_dir: Path,
    execute: bool = False,
    ffmpeg_command: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_final_assembly", "ready_for_quality_gate"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能生成成片预览。")
    if not state.get("confirmations", {}).get("shots"):
        raise ValueError("镜头尚未确认，不能生成成片预览。")

    timing = _load_json_file(Path(state["files"]["narration_timing"]), "narration/timing.json")
    results = _load_json_file(Path(state["files"]["dreamina_results_json"]), "dreamina_results.json")
    subtitles_path = run_dir / "subtitles" / "final_subtitles.srt"
    bgm_license_path = run_dir / "audio" / "bgm_license.json"
    bgm_brief_path = run_dir / "audio" / "bgm_brief.md"
    manifest_json_path = run_dir / "dreamina_generation" / "final_preview_manifest.json"
    manifest_md_path = run_dir / "dreamina_generation" / "final_preview_manifest.md"
    preview_path = run_dir / "dreamina_generation" / "final_preview.mp4"
    concat_path = run_dir / "dreamina_generation" / "shot_concat.txt"

    subtitles = _build_srt_subtitles(timing)
    subtitles_path.write_text(subtitles, encoding="utf-8")
    bgm_license = (
        _load_json_file(bgm_license_path, "bgm_license.json")
        if bgm_license_path.exists()
        else _build_bgm_license_payload(state, now or datetime.now())
    )
    bgm_license_path.write_text(json.dumps(bgm_license, ensure_ascii=False, indent=2), encoding="utf-8")
    bgm_brief_path.write_text(_render_bgm_brief(bgm_license), encoding="utf-8")
    command = ffmpeg_command or _state_adapter_command(state, "ffmpeg_command", "ffmpeg")
    manifest = _build_final_preview_manifest(
        state,
        results,
        subtitles_path,
        bgm_license_path,
        preview_path,
        concat_path,
        execute,
        command,
        runner,
        now or datetime.now(),
    )
    manifest_json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_md_path.write_text(_render_final_preview_manifest(manifest), encoding="utf-8")

    timestamp = _timestamp(now)
    state["status"] = "final_preview_ready" if manifest["status"] in {"dry_run_ready", "assembled"} else "final_preview_blocked"
    state["phase"] = "ready_for_quality_gate"
    state["current_pending_confirmation"] = "运行质量门禁"
    state["updated_at"] = timestamp
    files = state.setdefault("files", {})
    files["final_subtitles_srt"] = str(subtitles_path)
    files["bgm_license_json"] = str(bgm_license_path)
    files["bgm_brief_md"] = str(bgm_brief_path)
    files["final_preview_manifest_json"] = str(manifest_json_path)
    files["final_preview_manifest_md"] = str(manifest_md_path)
    files["final_preview_mp4"] = str(preview_path)
    _append_status_history(state, state["status"], timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"生成成片预览组装清单，状态：{state['status']}。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(manifest_md_path), str(manifest_json_path), str(subtitles_path), str(bgm_license_path)),
    )


def select_bgm_track(
    run_dir: Path,
    title: str,
    source: str,
    license_name: str,
    local_path: Path,
    license_url: str = "",
    now: datetime | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_quality_gate", "awaiting_manual_quality_check"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能记录 BGM 授权。")
    if not title.strip() or not source.strip() or not license_name.strip():
        raise ValueError("BGM 必须填写 title、source 和 license。")
    audio_path = local_path.expanduser().resolve()
    if not audio_path.exists():
        raise ValueError(f"找不到 BGM 本地文件：{audio_path}")

    bgm_license_path = Path(state.get("files", {}).get("bgm_license_json", run_dir / "audio" / "bgm_license.json"))
    payload = _load_json_file(bgm_license_path, "bgm_license.json") if bgm_license_path.exists() else _build_bgm_license_payload(state, now or datetime.now())
    payload["status"] = "selected"
    payload["selected_at"] = (now or datetime.now()).isoformat()
    payload["selected_track"] = {
        "title": title.strip(),
        "source": source.strip(),
        "license": license_name.strip(),
        "license_url": license_url.strip(),
        "local_path": str(audio_path),
    }
    bgm_license_path.parent.mkdir(parents=True, exist_ok=True)
    bgm_license_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    bgm_brief_path = run_dir / "audio" / "bgm_brief.md"
    bgm_brief_path.write_text(_render_bgm_brief(payload), encoding="utf-8")

    timestamp = _timestamp(now)
    state["updated_at"] = timestamp
    state.setdefault("files", {})["bgm_license_json"] = str(bgm_license_path)
    state.setdefault("files", {})["bgm_brief_md"] = str(bgm_brief_path)
    state["selected_bgm"] = payload["selected_track"]
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"记录 BGM 授权：{title.strip()}。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(bgm_license_path), str(bgm_brief_path)),
    )


def run_quality_gate(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_quality_gate", "awaiting_manual_quality_check"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能运行质量门禁。")
    report = _build_quality_report(run_dir, state, now or datetime.now())
    report_json_path = run_dir / "quality_report.json"
    report_md_path = run_dir / "quality_report.md"
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_render_quality_report(report), encoding="utf-8")

    timestamp = _timestamp(now)
    blockers = report["blocking_defects"]
    state["status"] = "quality_gate_failed" if blockers else "quality_gate_passed"
    state["phase"] = "ready_for_quality_gate" if blockers else "awaiting_manual_quality_check"
    state["current_pending_confirmation"] = "修复质量门禁问题" if blockers else "记录人工音视频检查"
    state["updated_at"] = timestamp
    state.setdefault("files", {})["quality_report_json"] = str(report_json_path)
    state.setdefault("files", {})["quality_report_md"] = str(report_md_path)
    state["quality_gate"] = {
        "status": report["status"],
        "blocking_defect_count": len(blockers),
        "checked_at": timestamp,
    }
    _append_status_history(state, state["status"], timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"运行质量门禁，阻塞问题 {len(blockers)} 个。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(report_md_path), str(report_json_path)),
    )


def record_manual_quality_check(
    run_dir: Path,
    audio_ok: bool,
    visual_ok: bool,
    notes: str = "",
    now: datetime | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "awaiting_manual_quality_check":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能记录人工音视频检查。")
    if not audio_ok or not visual_ok:
        raise ValueError("人工音视频检查未通过，不能进入确认成片。")

    timestamp = _timestamp(now)
    check = {
        "checked_at": timestamp,
        "audio_ok": bool(audio_ok),
        "visual_ok": bool(visual_ok),
        "notes": notes,
        "method": "人工打开视频剪辑软件或播放器检查音频、画面、字幕同步和整体节奏。",
    }
    check_path = run_dir / "manual_quality_check.json"
    check_path.write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8")

    state["status"] = "manual_quality_check_confirmed"
    state["phase"] = "awaiting_final_video_confirmation"
    state["current_pending_confirmation"] = "确认成片"
    state["updated_at"] = timestamp
    state["manual_quality_check"] = check
    state.setdefault("files", {})["manual_quality_check_json"] = str(check_path)
    _append_status_history(state, "manual_quality_check_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "记录人工音视频检查通过，等待确认成片。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(check_path),),
    )


def confirm_final_video(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") != "awaiting_final_video_confirmation":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能确认成片。")
    if not state.get("manual_quality_check", {}).get("audio_ok") or not state.get("manual_quality_check", {}).get("visual_ok"):
        raise ValueError("缺少已通过的人工音视频检查，不能确认成片。")
    preview_path = Path(state.get("files", {}).get("final_preview_mp4", run_dir / "dreamina_generation" / "final_preview.mp4"))
    if not preview_path.exists():
        raise ValueError(f"找不到成片预览文件，不能确认成片：{preview_path}")

    final_path = run_dir / state["outputs"]["final_filename"]
    shutil.copyfile(preview_path, final_path)
    timestamp = _timestamp(now)
    state["status"] = "final_video_confirmed"
    state["phase"] = "completed"
    state["current_pending_confirmation"] = None
    state["updated_at"] = timestamp
    state["confirmations"]["final_video"] = True
    state.setdefault("files", {})["final_video"] = str(final_path)
    _append_status_history(state, "final_video_confirmed", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"确认成片并输出最终视频：{final_path.name}。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(final_path),),
    )


def inspect_video_creation_adapters(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    report = _build_adapter_inspection_report(run_dir, state, now or datetime.now())
    report_json_path = run_dir / "adapter_inspection.json"
    report_md_path = run_dir / "adapter_inspection.md"
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_render_adapter_inspection(report), encoding="utf-8")

    timestamp = _timestamp(now)
    state["updated_at"] = timestamp
    state.setdefault("files", {})["adapter_inspection_json"] = str(report_json_path)
    state.setdefault("files", {})["adapter_inspection_md"] = str(report_md_path)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "检查视频创作适配器配置。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(report_md_path), str(report_json_path)),
    )


def resume_video_creation_run(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    status = _build_workflow_status(run_dir, state, now or datetime.now())
    status_json_path = run_dir / "workflow_status.json"
    status_md_path = run_dir / "workflow_status.md"
    status_json_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    status_md_path.write_text(_render_workflow_status(status), encoding="utf-8")

    timestamp = _timestamp(now)
    state["updated_at"] = timestamp
    state.setdefault("files", {})["workflow_status_json"] = str(status_json_path)
    state.setdefault("files", {})["workflow_status_md"] = str(status_md_path)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "恢复视频创作运行，生成当前待确认项摘要。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(status_md_path), str(status_json_path)),
    )


def handle_video_creation_reply(run_dir: Path, reply: str, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    normalized = _normalize_user_reply(reply)
    if not normalized:
        raise ValueError("没有识别到有效回复。")

    plan_revision = _parse_plan_revision_request(normalized, reply)
    if plan_revision:
        return revise_video_plan(run_dir, plan_revision, now=now)
    storyboard_revision = _parse_storyboard_revision_request(normalized, reply)
    if storyboard_revision:
        return revise_storyboard(run_dir, storyboard_revision, now=now)
    shot_revision = _parse_shot_revision_request(normalized, reply)
    if shot_revision:
        shot_id, request = shot_revision
        return revise_storyboard_shot(run_dir, shot_id, request, now=now)
    if normalized in {"生成视频策划", "生成策划"}:
        return generate_video_plan(run_dir, now=now)
    if normalized == "确认策划":
        return confirm_video_plan(run_dir, now=now)
    if normalized == "生成分镜":
        return generate_storyboard(run_dir, now=now)
    if normalized == "确认分镜":
        return confirm_storyboard(run_dir, now=now)
    if normalized == "生成旁白文案":
        return generate_narration_script(run_dir, now=now)
    if normalized == "确认旁白文案":
        return confirm_narration_script(run_dir, now=now)
    if normalized == "生成声音样本":
        return generate_voice_samples(run_dir, now=now)
    voice_id = _parse_voice_selection(normalized)
    if voice_id is not None:
        return select_voice(run_dir, voice_id, now=now)
    if normalized in {"生成完整旁白", "生成旁白音频"}:
        return generate_full_narration(run_dir, now=now)
    if normalized == "确认旁白":
        return confirm_narration(run_dir, now=now)
    if normalized == "规划即梦任务":
        return generate_dreamina_jobs(run_dir, now=now)
    if normalized == "确认即梦生成":
        return confirm_dreamina_generation(run_dir, now=now)
    if normalized == "提交即梦任务":
        return submit_dreamina_jobs(run_dir, now=now)
    if normalized in {"查询即梦结果", "继续查询即梦结果"}:
        return query_dreamina_results(run_dir, now=now)
    shot_retry_id = _parse_shot_retry_confirmation(normalized)
    if shot_retry_id:
        return confirm_shot_retry(run_dir, shot_retry_id, now=now)
    shot_retry_submission_id = _parse_shot_retry_submission(normalized)
    if shot_retry_submission_id:
        return submit_shot_retry(run_dir, now=now, expected_shot_id=shot_retry_submission_id)
    shot_retry_query_id = _parse_shot_retry_query(normalized)
    if shot_retry_query_id:
        return query_shot_retry_results(run_dir, now=now, expected_shot_id=shot_retry_query_id)
    shot_retry_request_id = _parse_shot_retry_request(normalized)
    if shot_retry_request_id:
        return plan_shot_retry(run_dir, shot_retry_request_id, reason=reply, now=now)
    if normalized == "确认镜头":
        return confirm_shots(run_dir, now=now)
    if normalized == "生成成片预览":
        return assemble_final_preview(run_dir, now=now)
    if normalized == "运行质量门禁":
        return run_quality_gate(run_dir, now=now)
    if _is_manual_quality_pass_reply(normalized):
        return record_manual_quality_check(run_dir, audio_ok=True, visual_ok=True, notes=reply, now=now)
    if normalized == "确认成片":
        return confirm_final_video(run_dir, now=now)
    if normalized in {"更换背景音乐", "换背景音乐", "更换bgm", "换bgm"}:
        return request_bgm_replacement(run_dir, now=now)
    raise ValueError(f"未支持的视频创作回复：{reply}")


def request_bgm_replacement(run_dir: Path, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") not in {"ready_for_quality_gate", "awaiting_manual_quality_check", "awaiting_final_video_confirmation"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能更换背景音乐。")

    timestamp = _timestamp(now)
    state["status"] = "bgm_replacement_requested"
    state["phase"] = "ready_for_quality_gate"
    state["current_pending_confirmation"] = "选择新的可商用 BGM 并重新生成成片预览"
    state["updated_at"] = timestamp
    state["confirmations"]["final_video"] = False
    state.pop("manual_quality_check", None)
    for key in ["manual_quality_check_json", "quality_report_json", "quality_report_md"]:
        state.setdefault("files", {}).pop(key, None)
    _append_status_history(state, "bgm_replacement_requested", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, "用户要求更换背景音乐；保留已确认策划、分镜、镜头和旁白，等待选择新的 BGM。")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(state_path),),
    )


def revise_video_plan(run_dir: Path, change_request: str, now: datetime | None = None) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    if not change_request.strip():
        raise ValueError("修改策划必须提供具体修改要求。")
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") == "completed":
        raise ValueError("视频已完成，不能直接修改策划；请新建一次视频创作运行。")

    files = state.get("files", {})
    plan_json_path = Path(files.get("video_plan_json", run_dir / "video_plan.json"))
    plan_md_path = Path(files.get("video_plan_md", run_dir / "video_plan.md"))
    if not plan_json_path.exists() or not plan_md_path.exists():
        raise ValueError("找不到可修改的视频策划，请先生成 video_plan.md 和 video_plan.json。")

    timestamp = _timestamp(now)
    revision = _build_revision_record("video_plan", change_request, timestamp)
    plan = _load_json_file(plan_json_path, "video_plan.json")
    plan["status"] = "revised_pending_confirmation"
    plan.setdefault("change_requests", []).append(revision)
    plan_json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    _append_revision_to_markdown(plan_md_path, "策划修改要求", revision)

    state["status"] = "video_plan_revised"
    state["phase"] = "awaiting_video_plan_confirmation"
    state["current_pending_confirmation"] = "确认策划"
    state["updated_at"] = timestamp
    state["confirmations"]["video_plan"] = False
    _clear_downstream_confirmations(state, after="video_plan")
    _clear_downstream_file_references(state, after="video_plan")
    _clear_transient_review_state(state)
    _append_status_history(state, "video_plan_revised", timestamp)
    _write_state(state_path, state)
    _append_change(run_dir, timestamp, f"用户修改视频策划，清除分镜及后续确认：{change_request.strip()}")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(plan_md_path), str(plan_json_path)),
    )


def revise_storyboard(run_dir: Path, change_request: str, now: datetime | None = None) -> VideoCreationStepResult:
    return _revise_storyboard_scope(run_dir, change_request, shot_id=None, now=now)


def revise_storyboard_shot(run_dir: Path, shot_id: str, change_request: str, now: datetime | None = None) -> VideoCreationStepResult:
    return _revise_storyboard_scope(run_dir, change_request, shot_id=_normalize_shot_id(shot_id), now=now)


def _revise_storyboard_scope(
    run_dir: Path,
    change_request: str,
    shot_id: str | None,
    now: datetime | None = None,
) -> VideoCreationStepResult:
    run_dir = run_dir.expanduser().resolve()
    if not change_request.strip():
        raise ValueError("修改分镜必须提供具体修改要求。")
    state_path = run_dir / "workflow_state.json"
    state = _load_state(state_path)
    if state.get("phase") == "completed":
        raise ValueError("视频已完成，不能直接修改分镜；请新建一次视频创作运行。")

    files = state.get("files", {})
    storyboard_json_path = Path(files.get("storyboard_json", run_dir / "storyboard.json"))
    storyboard_md_path = Path(files.get("storyboard_md", run_dir / "storyboard.md"))
    prompts_json_path = Path(files.get("prompts_json", run_dir / "prompts.json"))
    prompts_md_path = Path(files.get("prompts_md", run_dir / "prompts.md"))
    missing = [path for path in [storyboard_json_path, storyboard_md_path, prompts_json_path, prompts_md_path] if not path.exists()]
    if missing:
        raise ValueError(f"找不到可修改的分镜或 Prompt：{missing[0]}")

    timestamp = _timestamp(now)
    scope = f"shot_{shot_id}" if shot_id else "storyboard"
    revision = _build_revision_record(scope, change_request, timestamp)
    storyboard = _load_json_file(storyboard_json_path, "storyboard.json")
    prompts = _load_json_file(prompts_json_path, "prompts.json")
    storyboard["status"] = "revised_pending_confirmation"
    prompts["status"] = "revised_pending_storyboard_confirmation"
    if shot_id:
        shot = next((item for item in storyboard.get("shots", []) if item.get("shot_id") == shot_id), None)
        if not shot:
            raise ValueError(f"找不到镜头 {shot_id}，不能修改。")
        prompt_item = next((item for item in prompts.get("prompts", []) if item.get("shot_id") == shot_id), None)
        if not prompt_item:
            raise ValueError(f"找不到镜头 {shot_id} 的 Prompt，不能修改。")
        shot.setdefault("change_requests", []).append(revision)
        prompt_item.setdefault("change_requests", []).append(revision)
    else:
        storyboard.setdefault("change_requests", []).append(revision)
        prompts.setdefault("change_requests", []).append(revision)
    storyboard_json_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    prompts_json_path.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")
    title = f"镜头 {shot_id} 修改要求" if shot_id else "分镜修改要求"
    _append_revision_to_markdown(storyboard_md_path, title, revision)
    _append_revision_to_markdown(prompts_md_path, title, revision)

    state["status"] = "storyboard_revised"
    state["phase"] = "awaiting_storyboard_confirmation"
    state["current_pending_confirmation"] = "确认分镜"
    state["updated_at"] = timestamp
    state["confirmations"]["storyboard"] = False
    _clear_downstream_confirmations(state, after="storyboard")
    _clear_downstream_file_references(state, after="storyboard")
    _clear_transient_review_state(state)
    _append_status_history(state, "storyboard_revised", timestamp)
    _write_state(state_path, state)
    if shot_id:
        _append_change(run_dir, timestamp, f"用户修改镜头 {shot_id}，清除旁白及后续确认：{change_request.strip()}")
    else:
        _append_change(run_dir, timestamp, f"用户修改视频分镜，清除旁白及后续确认：{change_request.strip()}")

    return VideoCreationStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(storyboard_md_path), str(storyboard_json_path), str(prompts_md_path), str(prompts_json_path)),
    )


def normalize_language_version(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "中文": "zh",
        "中文版": "zh",
        "chinese": "zh",
        "zh-cn": "zh",
        "zh": "zh",
        "英文": "en",
        "英文版": "en",
        "english": "en",
        "en-us": "en",
        "en": "en",
    }
    result = aliases.get(normalized)
    if result not in SUPPORTED_LANGUAGE_VERSIONS:
        raise ValueError("视频语言版本只支持中文版或英文版")
    return result


def normalize_platforms(values: list[str] | tuple[str, ...]) -> list[str]:
    if not values:
        raise ValueError("视频平台只支持 YouTube Shorts、TikTok 或两者同时")
    normalized = []
    aliases = {
        "youtube": "youtube_shorts",
        "youtube_shorts": "youtube_shorts",
        "youtube shorts": "youtube_shorts",
        "shorts": "youtube_shorts",
        "油管 shorts": "youtube_shorts",
        "tiktok": "tiktok",
        "tik tok": "tiktok",
        "抖音海外版": "tiktok",
    }
    for value in values:
        item = aliases.get(value.strip().lower())
        if item not in SUPPORTED_PLATFORMS:
            raise ValueError("视频平台只支持 YouTube Shorts、TikTok 或两者同时")
        if item not in normalized:
            normalized.append(item)
    return normalized


def normalize_duration(value: int) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("视频时长只支持 60、90 或 120 秒") from exc
    if duration not in SUPPORTED_DURATIONS:
        raise ValueError("视频时长只支持 60、90 或 120 秒")
    return duration


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def normalize_creative_direction(value: str | None) -> dict[str, str]:
    if not value:
        raise ValueError("必须选择 1 个视频主创意方向")
    cleaned = value.strip().lower()
    by_id = {item["id"]: item for item in VIDEO_CREATIVE_DIRECTIONS}
    by_name = {item["name"].lower(): item for item in VIDEO_CREATIVE_DIRECTIONS}
    if cleaned.isdigit():
        index = int(cleaned)
        if 1 <= index <= len(VIDEO_CREATIVE_DIRECTIONS):
            return VIDEO_CREATIVE_DIRECTIONS[index - 1]
    if cleaned in by_id:
        return by_id[cleaned]
    if cleaned in by_name:
        return by_name[cleaned]
    raise ValueError("创意方向必须从固定 16 个视频创意方向中选择")


def recommend_creative_directions(
    request_text: str,
    platforms: list[str],
    target_audience: str,
    core_objective: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    text = " ".join([request_text, " ".join(platforms), target_audience, core_objective]).lower()
    product_assets = context.get("cards_by_type", {}).get("content_asset", [])
    material_coverage = "已有石英纤维隔热带关联内容素材" if product_assets else "暂无已关联内容素材"
    base = [
        ("multiple_benefit_overview", "product_detail", "适合在短视频首触达中同时讲清产品、卖点和真实细节。"),
        ("customer_pain_point_solution", "application_demonstration", "适合围绕采购和使用痛点解释产品价值。"),
        ("procurement_guide", "specification_customization", "适合面向工业采购/OEM/分销商，降低询盘沟通成本。"),
    ]
    if any(token in text for token in ["询盘", "inquiry", "contact", "报价", "样品"]):
        base[0] = ("inquiry_conversion", "procurement_guide", "当前目标包含询盘或转化，优先收口到 CTA。")
    elif any(token in text for token in ["安装", "施工", "wrap", "缠绕"]):
        base[0] = ("installation_demonstration", "product_detail", "当前目标包含安装施工，优先展示裁切、缠绕和细节。")
    elif any(token in text for token in ["测试", "火焰", "高温", "1000"]):
        base[0] = ("performance_test", "technical_education", "当前目标包含高温或测试表达，需同时控制证据和夸大风险。")

    direction_by_id = {item["id"]: item for item in VIDEO_CREATIVE_DIRECTIONS}
    recommendations = []
    seen = set()
    for primary_id, supporting_id, reason in base:
        if primary_id in seen:
            continue
        seen.add(primary_id)
        primary = direction_by_id[primary_id]
        supporting = direction_by_id.get(supporting_id)
        recommendations.append(
            {
                "primary_direction": primary,
                "supporting_direction": supporting,
                "rationale": reason,
                "material_coverage": material_coverage,
                "missing_materials": "真实应用视频、真实测试视频需按内容素材卡确认；缺失时只能标记为 AI 模拟或改用产品图转视频。",
                "ai_generation_risk": "不得把 AI 模拟场景表述为真实案例、真实测试或客户现场。",
            }
        )
    return recommendations[:3]


def _ensure_run_dirs(run_dir: Path) -> None:
    for relative in [
        ".",
        "narration/voice_samples",
        "dreamina_generation/generated_shots",
        "audio",
        "subtitles",
    ]:
        (run_dir / relative).mkdir(parents=True, exist_ok=True)


def _initial_workflow_state(
    run_dir: Path,
    requirements: dict[str, Any],
    context: dict[str, Any],
    config: dict[str, Any],
    requirements_path: Path,
    context_path: Path,
    change_log_path: Path,
    timestamp: str,
) -> dict[str, Any]:
    capability_profile = _dreamina_capability_profile(config)
    return {
        "schema_version": "video-creation-workflow-v1",
        "status": "requirements_confirmed",
        "phase": "ready_for_video_plan",
        "current_pending_confirmation": "生成视频策划",
        "created_at": timestamp,
        "updated_at": timestamp,
        "run_dir": str(run_dir),
        "product": {
            "internal_id": context.get("product_id") or INTERNAL_PRODUCT_ID,
            "canonical_id": INTERNAL_PRODUCT_ID,
            "compatible_alias_ids": VIDEO_CREATION_PRODUCT_ALIAS_IDS,
            "internal_name": INTERNAL_PRODUCT_NAME,
        },
        "language_version": requirements["language_version"],
        "platforms": requirements["platforms"],
        "duration_seconds": requirements["duration_seconds"],
        "target_audience": requirements["target_audience"],
        "core_objective": requirements["core_objective"],
        "creative_direction": {
            "primary": requirements["primary_direction"],
            "supporting": requirements["supporting_direction"],
        },
        "confirmations": {
            "language_version": True,
            "platform_duration_audience_objective": True,
            "creative_direction": True,
            "video_plan": False,
            "storyboard": False,
            "narration_script": False,
            "voice": False,
            "narration": False,
            "dreamina_generation": False,
            "shots": False,
            "final_video": False,
        },
        "context": {
            "context_id": context["context_id"],
            "task_type": context["task_type"],
            "product_id": context["product_id"],
            "canonical_product_id": context.get("canonical_product_id", INTERNAL_PRODUCT_ID),
            "product_alias_ids": context.get("product_alias_ids", []),
            "raw_access": context["raw_access"],
            "policy": context["policy"],
        },
        "files": {
            "requirements": str(requirements_path),
            "context": str(context_path),
            "change_log": str(change_log_path),
        },
        "status_history": [{"status": "requirements_confirmed", "at": timestamp}],
        "outputs": {
            "final_filename": f"{RUN_DIR_PRODUCT_SLUG}_{requirements['language_version']}_9x16.mp4",
            "aspect_ratio": capability_profile["aspect_ratio"],
            "resolution": "1080x1920",
            "dreamina_model": capability_profile["model"],
            "dreamina_resolution": capability_profile["resolution"],
        },
        "dreamina_capability_profile": capability_profile,
        "adapters": _video_adapter_config(config),
    }


def _render_requirements(requirements: dict[str, Any]) -> str:
    platforms = ", ".join(requirements["platforms"])
    primary = requirements["primary_direction"]
    supporting = requirements["supporting_direction"]
    lines = [
        "# 视频创作需求确认",
        "",
        f"- 产品：{INTERNAL_PRODUCT_NAME}",
        f"- 语言版本：{requirements['language_version']}",
        f"- 平台：{platforms}",
        f"- 时长：{requirements['duration_seconds']} 秒",
        f"- 受众：{requirements['target_audience'] or '未填写'}",
        f"- 核心目标：{requirements['core_objective'] or '未填写'}",
        f"- 主创意方向：{primary['name']}（{primary['id']}）",
        f"- 辅助创意方向：{supporting['name'] + '（' + supporting['id'] + '）' if supporting else '无'}",
        "",
        "## 原始需求",
        "",
        requirements["request_text"],
        "",
        "## 动态推荐",
        "",
    ]
    for index, item in enumerate(requirements["recommendations"], start=1):
        supporting_item = item["supporting_direction"]
        lines.extend(
            [
                f"### 推荐 {index}",
                "",
                f"- 主方向：{item['primary_direction']['name']}",
                f"- 辅助方向：{supporting_item['name'] if supporting_item else '无'}",
                f"- 推荐理由：{item['rationale']}",
                f"- 素材覆盖：{item['material_coverage']}",
                f"- 缺失素材：{item['missing_materials']}",
                f"- AI 生成风险：{item['ai_generation_risk']}",
                "",
            ]
        )
    lines.extend(["## 固定视频创意方向全集", ""])
    for index, item in enumerate(VIDEO_CREATIVE_DIRECTIONS, start=1):
        lines.append(f"{index}. **{item['name']}**（{item['id']}）：{item['description']}")
    lines.extend(
        [
            "",
            "## 边界",
            "",
            "- 本运行只使用 `video_creation` 上下文，不扫描 raw。",
            "- 本运行不写回 `knowledge/okf/`。",
            "- 本运行不使用“母版”概念，输出文件名不得包含 `master`。",
            "- 即梦生成和单镜头重做必须先展示预计额度并等待确认。",
        ]
    )
    return "\n".join(lines) + "\n"


def _video_adapter_config(config: dict[str, Any]) -> dict[str, Any]:
    video_config = config.get("video_creation", {}) if isinstance(config.get("video_creation", {}), dict) else {}
    return {
        "dreamina_command": str(video_config.get("dreamina_command") or config.get("dreamina_command") or "dreamina"),
        "dreamina_execute_default": bool(video_config.get("dreamina_execute_default", False)),
        "ffmpeg_command": str(video_config.get("ffmpeg_command") or config.get("ffmpeg_path") or "ffmpeg"),
        "tts_provider": str(video_config.get("tts_provider") or "mock"),
        "tts_command": str(video_config.get("tts_command") or ""),
        "bgm_provider": str(video_config.get("bgm_provider") or "manual_licensed_file"),
        "bgm_library_dir": str(video_config.get("bgm_library_dir") or ""),
        "logo_path": str(video_config.get("logo_path") or config.get("linkedin", {}).get("transparent_logo_path", "")),
    }


def _dreamina_capability_profile(config: dict[str, Any]) -> dict[str, Any]:
    video_config = config.get("video_creation", {}) if isinstance(config.get("video_creation", {}), dict) else {}
    configured = video_config.get("dreamina_capability_profile")
    if not isinstance(configured, dict):
        configured = config.get("dreamina_capability_profile")
    if not isinstance(configured, dict):
        configured = {}
    return _normalize_dreamina_capability_profile(configured)


def _state_dreamina_capability_profile(state: dict[str, Any]) -> dict[str, Any]:
    configured = state.get("dreamina_capability_profile")
    return _normalize_dreamina_capability_profile(configured if isinstance(configured, dict) else {})


def _normalize_dreamina_capability_profile(configured: dict[str, Any]) -> dict[str, Any]:
    profile = dict(DEFAULT_DREAMINA_CAPABILITY_PROFILE)
    profile.update({key: value for key, value in configured.items() if value not in (None, "")})
    for key in ["max_images", "max_videos", "max_audios", "max_total_files"]:
        profile[key] = _non_negative_int(profile.get(key), int(DEFAULT_DREAMINA_CAPABILITY_PROFILE[key]))
    for key in [
        "min_duration_seconds",
        "max_duration_seconds",
        "max_image_mb",
        "max_video_mb",
        "max_audio_mb",
        "min_video_reference_duration_seconds",
        "max_video_reference_duration_seconds",
        "max_audio_reference_duration_seconds",
    ]:
        profile[key] = _positive_int(profile.get(key), int(DEFAULT_DREAMINA_CAPABILITY_PROFILE[key]))
    for key in ["model", "resolution", "aspect_ratio"]:
        profile[key] = str(profile.get(key) or DEFAULT_DREAMINA_CAPABILITY_PROFILE[key])
    return profile


def _state_adapter_command(state: dict[str, Any], key: str, default: str) -> str:
    value = state.get("adapters", {}).get(key)
    return str(value).strip() if value else default


def _build_video_plan_payload(state: dict[str, Any], context: dict[str, Any], now: datetime) -> dict[str, Any]:
    product_cards = context.get("cards_by_type", {}).get("product", [])
    if not product_cards:
        raise ValueError("video_creation 上下文缺少石英纤维隔热带产品卡。")
    product = product_cards[0]
    content_assets = context.get("cards_by_type", {}).get("content_asset", [])
    language = state["language_version"]
    duration = state["duration_seconds"]
    duration_min, duration_max = _duration_tolerance(duration)
    capability_profile = _state_dreamina_capability_profile(state)
    external_names = _external_names_from_product(product)
    primary = state["creative_direction"]["primary"]
    supporting = state["creative_direction"].get("supporting")
    plan = {
        "schema_version": "video-plan-v1",
        "generated_at": now.isoformat(),
        "status": "draft_pending_confirmation",
        "product": {
            "internal_id": product.get("id") or context.get("product_id") or INTERNAL_PRODUCT_ID,
            "canonical_id": INTERNAL_PRODUCT_ID,
            "compatible_alias_ids": VIDEO_CREATION_PRODUCT_ALIAS_IDS,
            "internal_name": INTERNAL_PRODUCT_NAME,
            "external_name_zh": external_names["zh"],
            "external_name_en": external_names["en"],
            "usage_scope": product.get("usage_scope", ""),
            "status": product.get("status", ""),
        },
        "language_version": language,
        "platforms": state["platforms"],
        "format": {
            "aspect_ratio": capability_profile["aspect_ratio"],
            "resolution": "1080x1920",
            "duration_seconds": duration,
            "duration_tolerance_seconds": {"min": duration_min, "max": duration_max},
            "single_deliverable_for_multiple_platforms": len(state["platforms"]) > 1,
        },
        "audience": state.get("target_audience", ""),
        "core_objective": state.get("core_objective", ""),
        "creative_direction": {
            "primary": primary,
            "supporting": supporting,
        },
        "knowledge_boundary": {
            "context_id": context["context_id"],
            "task_type": "video_creation",
            "raw_access": False,
            "official_only": True,
            "content_assets_prove_product_facts": False,
            "no_keyword_expansion": True,
            "no_write_back_to_knowledge": True,
            "canonical_product_id": context.get("canonical_product_id", INTERNAL_PRODUCT_ID),
            "resolved_product_id": product.get("id") or context.get("product_id"),
            "product_usage_scope": product.get("usage_scope", ""),
            "external_publication_ready": product.get("usage_scope") == "external_allowed",
            "draft_only_until_external_review": product.get("usage_scope") == "review_before_external",
            "review_before_external_rule": "可用于内部策划和 dry-run 草稿；正式外发成片前必须复核为 external_allowed，或删除高风险 claim。",
        },
        "usable_product_knowledge": _usable_product_knowledge(product),
        "content_assets": [_content_asset_summary(card) for card in content_assets],
        "visual_strategy": _visual_strategy(primary, supporting, content_assets),
        "production_style": _production_style_profile(primary, supporting),
        "creative_quality": _direction_quality_profile(primary),
        "external_skill_absorption": EXTERNAL_VIDEO_SKILL_ABSORPTION,
        "dreamina_capability_profile": capability_profile,
        "prompt_policy": {
            "structure": [
                "timebox",
                "subject",
                "reference_material",
                "time_segments",
                "motion_and_camera",
                "environment",
                "material_texture",
                "product_display_template",
                "safety_and_negative_constraints",
            ],
            "visible_product_requires_real_reference": True,
            "no_subtitles_in_generation_prompt": True,
            "no_unverified_claims": True,
            "industrial_camera_language_required": True,
            "product_display_template_required": True,
            "forbidden_entertainment_patterns": FORBIDDEN_ENTERTAINMENT_PROMPT_PATTERNS,
            "conflict_rules": PROMPT_CONFLICT_RULES,
            "duration_complexity_policy": PROMPT_DURATION_COMPLEXITY_POLICY,
            "sources_absorbed": [
                "dexhunter/seedance2-skill",
                "songguoxs/seedance-prompt-skill",
                "MapleShaw/seedance2.0-prompt-skill",
            ],
        },
        "music_brief": _music_brief(primary, language),
        "subtitle_policy": {
            "burned_in": True,
            "language_matches_narration": True,
            "max_lines_per_screen": 2,
            "sentence_level_timing": True,
            "no_word_by_word_karaoke": True,
            "safe_area": "TikTok 与 YouTube Shorts 顶部/底部 UI 安全区交集",
        },
        "overlay_policy": {
            "allowed": ["标题", "正式确认参数", "短卖点标签", "CTA"],
            "source": "正式知识或项目配置",
            "inquiry_conversion_requires_cta": primary["id"] == "inquiry_conversion",
        },
        "audio_policy": {
            "narration_required": True,
            "bgm_required": True,
            "dreamina_does_not_generate_audio": True,
            "music_must_be_commercially_usable": True,
        },
        "generation_policy": {
            "dreamina_model": DEFAULT_DREAMINA_MODEL,
            "dreamina_resolution": DEFAULT_RESOLUTION,
            "shot_duration_default_seconds": 5,
            "shot_duration_range_seconds": {"min": 4, "max": 15},
            "paid_generation_requires_confirmation": "确认即梦生成",
        },
        "forbidden": [
            "不得扫描 raw",
            "不得写回 knowledge/okf",
            "不得使用 video_script 任务上下文",
            "不得使用母版/master 作为交付概念或文件名",
            "不得引入正式知识中没有的设备、参数、应用、性能结论或认证承诺",
            "不得把 AI 模拟场景表述为真实案例、真实测试或客户现场",
            "不得生成平台标题、发布文案、描述或 hashtags",
        ],
        "next_step": "确认策划后生成 storyboard.md、storyboard.json、prompts.md 和 prompts.json。",
    }
    return plan


def _render_video_plan(plan: dict[str, Any]) -> str:
    product = plan["product"]
    duration = plan["format"]["duration_seconds"]
    tolerance = plan["format"]["duration_tolerance_seconds"]
    primary = plan["creative_direction"]["primary"]
    supporting = plan["creative_direction"].get("supporting")
    lines = [
        "# 视频策划",
        "",
        "## 基本信息",
        "",
        f"- 内部产品：{product['internal_name']}（{product['internal_id']}）",
        f"- 对外中文名：{product['external_name_zh'] or '未在知识卡中找到'}",
        f"- 对外英文名：{product['external_name_en'] or '未在知识卡中找到'}",
        f"- 语言版本：{plan['language_version']}",
        f"- 平台：{', '.join(plan['platforms'])}",
        f"- 画幅/分辨率：{plan['format']['aspect_ratio']}，{plan['format']['resolution']}",
        f"- 时长：{duration} 秒（允许 {tolerance['min']}-{tolerance['max']} 秒）",
        f"- 受众：{plan['audience'] or '未填写'}",
        f"- 核心目标：{plan['core_objective'] or '未填写'}",
        "",
        "## 创意方向",
        "",
        f"- 主方向：{primary['name']}（{primary['id']}）",
        f"- 辅助方向：{supporting['name'] + '（' + supporting['id'] + '）' if supporting else '无'}",
        "",
        "## 可使用产品知识",
        "",
    ]
    for item in plan["usable_product_knowledge"]:
        lines.append(f"- {item}")
    if not plan["usable_product_knowledge"]:
        lines.append("- 暂无可摘要的产品正文；后续生成不得补造产品事实。")
    lines.extend(["", "## 可用内容素材", ""])
    if plan["content_assets"]:
        for asset in plan["content_assets"]:
            media = ", ".join(asset["media_types"]) or "unknown"
            lines.append(f"- {asset['id']}｜{asset['title']}｜媒体类型：{media}｜用途：仅用于画面/素材参考，不证明产品事实")
    else:
        lines.append("- 暂无正式关联内容素材；后续分镜应降低真实素材覆盖预期。")
    lines.extend(
        [
            "",
            "## 画面策略",
            "",
            f"- {plan['visual_strategy']['summary']}",
            f"- 素材优先级：{plan['visual_strategy']['material_priority']}",
            f"- AI 风险控制：{plan['visual_strategy']['ai_risk_control']}",
            f"- 产品视频风格：{plan['production_style']['name']}｜{plan['production_style']['visual_language']}",
            "",
            "## 创意质量矩阵",
            "",
            f"- 前 2 秒吸引点：{plan['creative_quality']['hook']}",
            f"- 视觉重点：{plan['creative_quality']['visual_focus']}",
            f"- 信息重点：{plan['creative_quality']['message_focus']}",
            f"- CTA 规则：{plan['creative_quality']['cta_rule']}",
            "",
            "## 即梦 Prompt 规则",
            "",
            "- Prompt 使用结构化英文写法：时间段、主体、参考素材、动作/运镜、环境、材质细节、禁止项。",
            "- 产品可见镜头必须使用真实产品图或视频参考；纯 text2video 只能用于环境或过渡镜头。",
            "- Prompt 不生成字幕、不生成平台 UI、不引入知识卡之外的认证、参数或测试结论。",
            "",
            "## 音乐 brief",
            "",
            f"- 情绪：{plan['music_brief']['mood']}",
            f"- 节奏：{plan['music_brief']['pace']}",
            f"- 强度：{plan['music_brief']['intensity']}",
            f"- 授权要求：{plan['music_brief']['license_requirement']}",
            "",
            "## 字幕与叠加层",
            "",
            "- 字幕：烧录字幕，与旁白同语言，每屏 1-2 行，按句级时间轴同步，不做逐字卡拉 OK。",
            "- 叠加层：只允许标题、正式确认参数、短卖点标签和 CTA，必须来自正式知识或配置。",
            "",
            "## 禁止事项",
            "",
        ]
    )
    for item in plan["forbidden"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            plan["next_step"],
            "",
            "请确认策划后继续生成分镜。",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_storyboard_payload(state: dict[str, Any], plan: dict[str, Any], now: datetime) -> dict[str, Any]:
    duration = int(plan["format"]["duration_seconds"])
    shot_duration = 5
    shot_count = max(1, duration // shot_duration)
    content_assets = plan.get("content_assets", [])
    product_asset = content_assets[0] if content_assets else None
    primary = plan["creative_direction"]["primary"]
    external_name = _display_product_name(plan)
    shots = []
    for index in range(1, shot_count + 1):
        shot_id = f"{index:02d}"
        role = _shot_role(index, shot_count)
        product_visible = role not in {"opening_environment", "closing_cta"} or bool(product_asset)
        material_mode = _shot_material_mode(role, product_asset, product_visible)
        selected_material = product_asset if material_mode in {"image2video", "reuse_image"} else None
        ai_generated = material_mode in {"image2video", "text2video", "ai_simulated_scene"}
        shot = {
            "shot_id": shot_id,
            "duration_seconds": shot_duration,
            "role": role,
            "visual_description": _shot_visual_description(role, external_name, primary, bool(product_asset)),
            "message": _shot_message(role, primary, external_name),
            "product_visible": product_visible,
            "material_mode": material_mode,
            "selected_material": selected_material,
            "ai_generated": ai_generated,
            "requires_real_product_reference": product_visible and ai_generated,
            "first_frame_reference_id": _first_frame_reference_id(role, selected_material),
            "last_frame_reference_id": _last_frame_reference_id(role, selected_material),
            "frame_control_risk": _frame_control_risk(role, product_visible, selected_material),
            "human_face_risk": _material_human_face_risk(selected_material),
            "human_face_policy": "allow_partial_hands_or_back_view_only",
            "risk_notes": _shot_risk_notes(material_mode, product_visible, bool(product_asset)),
            "narration_intent": _shot_narration_intent(role, external_name),
            "creative_quality_checks": _shot_creative_quality_checks(role, primary, plan["creative_quality"]),
        }
        shot["shot_design_validation"] = _validate_shot_design(shot)
        shots.append(shot)
    return {
        "schema_version": "storyboard-v1",
        "generated_at": now.isoformat(),
        "status": "draft_pending_confirmation",
        "language_version": plan["language_version"],
        "platforms": plan["platforms"],
        "format": plan["format"],
        "creative_direction": plan["creative_direction"],
        "material_priority": plan["visual_strategy"]["material_priority"],
        "production_style": plan["production_style"],
        "creative_quality": plan["creative_quality"],
        "shots": shots,
        "policy": {
            "text_prompts_are_not_subtitles": True,
            "product_shots_require_real_product_reference": True,
            "text2video_only_for_environment_or_transition": True,
            "ai_scenes_not_real_cases_or_tests": True,
        },
        "next_step": "确认分镜后生成完整旁白文案。",
    }


def _build_prompts_payload(storyboard: dict[str, Any], plan: dict[str, Any], now: datetime) -> dict[str, Any]:
    capability_profile = _normalize_dreamina_capability_profile(plan.get("dreamina_capability_profile", {}))
    material_reference_map = _build_material_reference_map(storyboard, capability_profile)
    prompts = []
    for shot in storyboard["shots"]:
        material_reference = _material_reference_for_shot(shot, material_reference_map)
        components = _dreamina_prompt_components_for_shot(shot, plan, material_reference)
        prompt = _render_dreamina_prompt_components(components)
        prompt_item = {
            "shot_id": shot["shot_id"],
            "duration_seconds": shot["duration_seconds"],
            "material_mode": shot["material_mode"],
            "prompt_language": "en",
            "prompt_standard": "tuolin-industrial-seedance-v2",
            "prompt_components": components,
            "prompt": prompt,
            "negative_prompt": "No unsupported certifications, no exaggerated test claims, no fake customer site, no readable subtitles, no karaoke text, no watermark.",
            "reference_required": bool(shot["requires_real_product_reference"]),
            "reference_material_id": shot["selected_material"]["id"] if shot.get("selected_material") else None,
            "numbered_reference_label": material_reference.get("label"),
            "reference_usage": material_reference.get("usage"),
            "first_frame_reference_id": shot.get("first_frame_reference_id"),
            "last_frame_reference_id": shot.get("last_frame_reference_id"),
            "frame_control_risk": shot.get("frame_control_risk", ""),
            "human_face_risk": shot.get("human_face_risk", "none"),
            "human_face_policy": shot.get("human_face_policy", "allow_partial_hands_or_back_view_only"),
        }
        prompt_item["prompt_quality_checks"] = _prompt_quality_checks(prompt_item)
        prompts.append(prompt_item)
    return {
        "schema_version": "dreamina-prompts-v1",
        "generated_at": now.isoformat(),
        "status": "draft_pending_storyboard_confirmation",
        "model": capability_profile["model"],
        "resolution": capability_profile["resolution"],
        "aspect_ratio": capability_profile["aspect_ratio"],
        "prompts_are_subtitles": False,
        "prompt_policy": plan["prompt_policy"],
        "dreamina_capability_profile": capability_profile,
        "material_reference_map": material_reference_map,
        "prompts": prompts,
    }


def _render_storyboard(storyboard: dict[str, Any]) -> str:
    lines = [
        "# 视频分镜",
        "",
        f"- 语言版本：{storyboard['language_version']}",
        f"- 平台：{', '.join(storyboard['platforms'])}",
        f"- 画幅/分辨率：{storyboard['format']['aspect_ratio']}，{storyboard['format']['resolution']}",
        f"- 镜头数：{len(storyboard['shots'])}",
        "",
        "## 素材优先级",
        "",
        storyboard["material_priority"],
        "",
        "## 镜头列表",
        "",
    ]
    for shot in storyboard["shots"]:
        material = shot["selected_material"]["id"] if shot.get("selected_material") else "无"
        lines.extend(
            [
                f"### 镜头 {shot['shot_id']}（{shot['duration_seconds']} 秒）",
                "",
                f"- 画面：{shot['visual_description']}",
                f"- 信息目标：{shot['message']}",
                f"- 素材模式：{shot['material_mode']}",
                f"- 匹配素材：{material}",
                f"- 需要真实产品参考：{'是' if shot['requires_real_product_reference'] else '否'}",
                f"- 首帧参考：{shot.get('first_frame_reference_id') or '无'}",
                f"- 尾帧参考：{shot.get('last_frame_reference_id') or '无'}",
                f"- 帧控制风险：{shot.get('frame_control_risk') or '无'}",
                f"- 人脸风险：{shot.get('human_face_risk') or 'none'}｜策略：{shot.get('human_face_policy') or 'allow_partial_hands_or_back_view_only'}",
                f"- AI 生成：{'是' if shot['ai_generated'] else '否'}",
                f"- 风险提示：{shot['risk_notes']}",
                f"- 创意质量要求：{'; '.join(shot['creative_quality_checks'])}",
                f"- 镜头验证：{shot['shot_design_validation']['status']}｜{'; '.join(shot['shot_design_validation']['messages'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## 边界",
            "",
            "- Prompt 是给即梦使用，不是字幕。",
            "- 展示具体产品的 AI 镜头必须使用真实产品图/视频作参考。",
            "- AI 模拟场景不能表述为真实案例、真实测试或客户现场。",
            "",
            "请确认分镜后继续生成旁白文案。",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_prompts(prompts: dict[str, Any]) -> str:
    lines = [
        "# 即梦 Prompts",
        "",
        f"- 模型：{prompts['model']}",
        f"- 分辨率：{prompts['resolution']}",
        f"- 画幅：{prompts['aspect_ratio']}",
        "- 说明：以下英文 Prompt 是给即梦使用，不是视频字幕。",
        "",
        "## 素材编号引用",
        "",
    ]
    references = prompts.get("material_reference_map", {}).get("references", [])
    if references:
        for reference in references:
            usages = "；".join(reference.get("usages", []))
            paths = "；".join(reference.get("local_paths", [])) or "未记录本地路径"
            lines.append(f"- {reference['label']}｜{reference['material_id']}｜用途：{usages}｜路径：{paths}")
    else:
        lines.append("- 无")
    lines.append("")
    for item in prompts["prompts"]:
        lines.extend(
            [
                f"## 镜头 {item['shot_id']}",
                "",
                f"- 时长：{item['duration_seconds']} 秒",
                f"- 素材模式：{item['material_mode']}",
                f"- 需要参考素材：{'是' if item['reference_required'] else '否'}",
                f"- 参考素材 ID：{item['reference_material_id'] or '无'}",
                f"- 编号引用：{item.get('numbered_reference_label') or '无'}",
                f"- 引用用途：{item.get('reference_usage') or '无'}",
                f"- 首帧参考：{item.get('first_frame_reference_id') or '无'}",
                f"- 尾帧参考：{item.get('last_frame_reference_id') or '无'}",
                f"- 帧控制风险：{item.get('frame_control_risk') or '无'}",
                f"- 人脸风险：{item.get('human_face_risk') or 'none'}｜策略：{item.get('human_face_policy') or 'allow_partial_hands_or_back_view_only'}",
                f"- Prompt 标准：{item['prompt_standard']}",
                "",
                "Prompt:",
                "",
                item["prompt"],
                "",
                "Negative Prompt:",
                "",
                item["negative_prompt"],
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _display_product_name(plan: dict[str, Any]) -> str:
    product = plan["product"]
    if plan["language_version"] == "en" and product.get("external_name_en"):
        return product["external_name_en"]
    return product.get("external_name_zh") or product["internal_name"]


def _shot_role(index: int, total: int) -> str:
    if index == 1:
        return "opening_environment"
    if index == total:
        return "closing_cta"
    cycle = ["product_hero", "product_detail", "benefit_visual", "application_context"]
    return cycle[(index - 2) % len(cycle)]


def _shot_material_mode(role: str, product_asset: dict[str, Any] | None, product_visible: bool) -> str:
    if product_asset:
        media_types = set(product_asset.get("media_types", []))
        if "video" in media_types:
            return "reuse_video"
        if "image" in media_types:
            return "image2video" if product_visible else "reuse_image"
    if product_visible:
        return "blocked"
    if role == "application_context":
        return "ai_simulated_scene"
    return "text2video"


def _shot_visual_description(role: str, product_name: str, primary: dict[str, str], has_asset: bool) -> str:
    if role == "opening_environment":
        return f"Vertical industrial short-video opening for {product_name}, clean high-temperature insulation context, no text subtitles."
    if role == "product_hero":
        return f"Hero shot of {product_name} roll or tape surface, clean lighting, industrial B2B product look."
    if role == "product_detail":
        return f"Close-up of {product_name} texture, edge, thickness and flexible woven detail, realistic product material."
    if role == "benefit_visual":
        return f"Visual metaphor for {primary['name']} using controlled heat-insulation industrial imagery, no exaggerated test result."
    if role == "application_context":
        return f"Confirmed industrial application context for {product_name}, simulated only if no real application material exists."
    return f"Closing product and inquiry-oriented shot for {product_name}, clean industrial background, no platform UI conflict."


def _shot_message(role: str, primary: dict[str, str], product_name: str) -> str:
    if role == "opening_environment":
        return "开场建立工业高温隔热需求。"
    if role == "product_hero":
        return f"展示 {product_name} 是本视频主角。"
    if role == "product_detail":
        return "展示真实织纹、边缘和材料细节。"
    if role == "benefit_visual":
        return f"围绕{primary['name']}呈现核心价值。"
    if role == "application_context":
        return "呈现已确认应用方向，避免虚构真实案例。"
    return "收束到品牌记忆和轻量 CTA。"


def _shot_risk_notes(material_mode: str, product_visible: bool, has_asset: bool) -> str:
    if material_mode == "blocked":
        return "缺少真实产品参考素材，不能生成展示具体产品的 AI 镜头。"
    if product_visible and material_mode in {"image2video", "ai_simulated_scene"}:
        return "必须使用真实产品参考，且不得夸大性能或表述为真实测试/案例。"
    if not has_asset:
        return "缺少真实素材，视觉一致性风险较高。"
    return "按内容素材卡使用；素材不证明产品性能事实。"


def _first_frame_reference_id(role: str, selected_material: dict[str, Any] | None) -> str | None:
    if not selected_material:
        return None
    if role in {"product_hero", "product_detail", "application_context"}:
        return str(selected_material.get("id") or "")
    return None


def _last_frame_reference_id(role: str, selected_material: dict[str, Any] | None) -> str | None:
    if not selected_material:
        return None
    if role == "closing_cta":
        return str(selected_material.get("id") or "")
    return None


def _frame_control_risk(role: str, product_visible: bool, selected_material: dict[str, Any] | None) -> str:
    if not product_visible:
        return ""
    if not selected_material:
        return "产品可见镜头缺少真实素材，无法指定首帧或尾帧。"
    if role in {"product_hero", "product_detail", "application_context"}:
        return "" if _first_frame_reference_id(role, selected_material) else "产品镜头未指定首帧，产品形态一致性风险较高。"
    if role == "closing_cta":
        return "" if _last_frame_reference_id(role, selected_material) else "CTA 镜头未指定尾帧，结尾产品定格一致性风险较高。"
    return ""


def _material_human_face_risk(material: dict[str, Any] | None) -> str:
    if not material:
        return "none"
    value = str(material.get("human_face_risk") or "none").strip().lower()
    return value if value in {"none", "unclear", "clear_face"} else "unclear"


def _shot_narration_intent(role: str, product_name: str) -> str:
    if role == "opening_environment":
        return "用一句话提出工业隔热或施工痛点。"
    if role == "product_hero":
        return f"介绍 {product_name}。"
    if role == "product_detail":
        return "说明材料细节和使用友好性，但不新增无证据参数。"
    if role == "benefit_visual":
        return "表达已确认核心卖点。"
    if role == "application_context":
        return "说明产品可用于已确认应用场景。"
    return "提示联系或索取规格信息。"


def _build_material_reference_map(storyboard: dict[str, Any], capability_profile: dict[str, Any]) -> dict[str, Any]:
    counters = {"image": 0, "video": 0, "audio": 0}
    references_by_material_id: dict[str, dict[str, Any]] = {}
    references: list[dict[str, Any]] = []
    for shot in storyboard.get("shots", []):
        material = shot.get("selected_material") or {}
        material_id = str(material.get("id") or "")
        if not material_id:
            continue
        media_kind = _seedance_media_kind(material)
        if media_kind not in counters:
            continue
        usage = _material_reference_usage(shot, media_kind)
        if material_id in references_by_material_id:
            existing = references_by_material_id[material_id]
            if usage not in existing["usages"]:
                existing["usages"].append(usage)
            continue
        counters[media_kind] += 1
        label_prefix = {"image": "@图片", "video": "@视频", "audio": "@音频"}[media_kind]
        reference = {
            "label": f"{label_prefix}{counters[media_kind]}",
            "material_id": material_id,
            "title": material.get("title", ""),
            "media_kind": media_kind,
            "media_types": material.get("media_types", []),
            "asset_category": material.get("asset_category", ""),
            "local_paths": _material_local_paths(material),
            "usages": [usage],
            "product_visible": bool(shot.get("product_visible")),
            "human_face_risk": _material_human_face_risk(material),
            "human_face_policy": "allow_partial_hands_or_back_view_only",
            "execution_strategy": _material_reference_execution_strategy(media_kind),
        }
        references_by_material_id[material_id] = reference
        references.append(reference)
    counts = {
        "images": counters["image"],
        "videos": counters["video"],
        "audios": counters["audio"],
        "total_files": sum(counters.values()),
    }
    return {
        "schema_version": "seedance-material-reference-map-v1",
        "capability_limits": {
            "max_images": capability_profile["max_images"],
            "max_videos": capability_profile["max_videos"],
            "max_audios": capability_profile["max_audios"],
            "max_total_files": capability_profile["max_total_files"],
        },
        "counts": counts,
        "references": references,
    }


def _material_reference_for_shot(shot: dict[str, Any], material_reference_map: dict[str, Any]) -> dict[str, Any]:
    material = shot.get("selected_material") or {}
    material_id = str(material.get("id") or "")
    if not material_id:
        return {}
    for reference in material_reference_map.get("references", []):
        if reference.get("material_id") == material_id:
            usage = _material_reference_usage(shot, str(reference.get("media_kind") or "image"))
            return {
                "label": reference.get("label"),
                "usage": usage,
                "reference": reference,
            }
    return {}


def _seedance_media_kind(material: dict[str, Any]) -> str:
    media_types = {str(item).lower() for item in material.get("media_types", [])}
    if "video" in media_types:
        return "video"
    if "audio" in media_types:
        return "audio"
    return "image"


def _material_reference_usage(shot: dict[str, Any], media_kind: str) -> str:
    role = str(shot.get("role") or "")
    if media_kind == "video":
        return "真实产品视频参考，用于产品外观、动作和运镜节奏"
    if media_kind == "audio":
        return "音频节奏或 BGM 参考；当前流程优先作为后处理音乐策略记录"
    if role == "product_hero":
        return "真实产品首帧参考"
    if role == "product_detail":
        return "织纹、边缘和材料细节参考"
    if role == "closing_cta":
        return "产品定格或尾帧参考"
    if role == "application_context":
        return "已确认应用场景中的产品外观参考"
    return "真实产品外观参考"


def _material_reference_execution_strategy(media_kind: str) -> str:
    if media_kind == "audio":
        return "record_for_bgm_or_future_audio_reference"
    return "pass_to_dreamina_cli_input"


def _material_local_paths(material: dict[str, Any]) -> list[str]:
    values = material.get("files") or material.get("file_paths") or material.get("paths") or material.get("raw_partitions") or []
    if isinstance(values, str):
        return [values]
    return [str(item) for item in values if str(item).strip()]


def _material_reference_limit_blockers(material_reference_map: dict[str, Any], capability_profile: dict[str, Any]) -> list[str]:
    counts = material_reference_map.get("counts", {})
    checks = [
        ("images", "图片", "max_images"),
        ("videos", "视频", "max_videos"),
        ("audios", "音频", "max_audios"),
        ("total_files", "总文件数", "max_total_files"),
    ]
    blockers = []
    for count_key, label, limit_key in checks:
        count = int(counts.get(count_key, 0))
        limit = int(capability_profile.get(limit_key, DEFAULT_DREAMINA_CAPABILITY_PROFILE[limit_key]))
        if count > limit:
            blockers.append(f"Seedance 多模态输入超限：{label} {count} 个，配置上限 {limit} 个。")
    for reference in material_reference_map.get("references", []):
        if not reference.get("label"):
            blockers.append(f"素材 {reference.get('material_id')} 缺少编号引用。")
        if not reference.get("usages"):
            blockers.append(f"素材 {reference.get('material_id')} 缺少用途说明。")
    return blockers


def _forbidden_entertainment_terms_in_prompt(prompt: str) -> list[str]:
    normalized = prompt.lower()
    return [term for term in FORBIDDEN_ENTERTAINMENT_PROMPT_PATTERNS if term in normalized]


def _prompt_quality_checks(prompt_item: dict[str, Any]) -> dict[str, Any]:
    components = prompt_item.get("prompt_components", {})
    prompt_text = _prompt_quality_text(prompt_item)
    blockers = _prompt_instruction_conflict_issues(prompt_text)
    blockers.extend(_prompt_duration_complexity_issues(prompt_item, prompt_text))
    warnings: list[dict[str, str]] = []
    duration = int(prompt_item.get("duration_seconds") or 0)
    metrics = {
        "duration_seconds": duration,
        "time_segment_count": _time_segment_count(str(components.get("time_segments") or "")),
        "scene_change_term_count": _scene_change_term_count(prompt_text),
        "reference_count": len(set(re.findall(r"@(?:图片|视频|音频)\d+", prompt_text))),
    }
    return {
        "status": "blocked" if blockers else "warning" if warnings else "ok",
        "blockers": blockers,
        "warnings": warnings,
        "metrics": metrics,
    }


def _prompt_quality_text(prompt_item: dict[str, Any]) -> str:
    components = prompt_item.get("prompt_components", {})
    values = [str(prompt_item.get("prompt") or ""), str(prompt_item.get("negative_prompt") or "")]
    values.extend(str(value) for value in components.values())
    return " ".join(values).lower()


def _prompt_instruction_conflict_issues(prompt_text: str) -> list[dict[str, str]]:
    issues = []
    for rule in PROMPT_CONFLICT_RULES:
        left = _matched_terms(prompt_text, rule["left_terms"])
        right = _matched_terms(prompt_text, rule["right_terms"])
        if left and right:
            issues.append(
                {
                    "code": str(rule["code"]),
                    "message": f"{rule['message']} 冲突词：{', '.join(left + right)}",
                }
            )
    return issues


def _prompt_duration_complexity_issues(prompt_item: dict[str, Any], prompt_text: str) -> list[dict[str, str]]:
    duration = int(prompt_item.get("duration_seconds") or 0)
    components = prompt_item.get("prompt_components", {})
    segment_count = _time_segment_count(str(components.get("time_segments") or ""))
    scene_change_count = _scene_change_term_count(prompt_text)
    max_segments = _max_time_segments_for_duration(duration)
    max_scene_changes = _max_scene_change_terms_for_duration(duration)
    issues = []
    if segment_count > max_segments:
        issues.append(
            {
                "code": "time_segment_count_exceeds_duration",
                "message": f"{duration} 秒镜头包含 {segment_count} 个分时段，超过建议上限 {max_segments} 个。",
            }
        )
    if scene_change_count > max_scene_changes:
        issues.append(
            {
                "code": "scene_change_complexity_exceeds_duration",
                "message": f"{duration} 秒镜头包含 {scene_change_count} 个场景/转场复杂度词，超过建议上限 {max_scene_changes} 个。",
            }
        )
    return issues


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def _time_segment_count(text: str) -> int:
    return len(re.findall(r"\b\d+\s*-\s*\d+\s*s", text.lower()))


def _scene_change_term_count(text: str) -> int:
    return sum(text.count(term) for term in PROMPT_DURATION_COMPLEXITY_POLICY["scene_change_terms"])


def _max_time_segments_for_duration(duration: int) -> int:
    if duration <= 5:
        return int(PROMPT_DURATION_COMPLEXITY_POLICY["max_time_segments_for_5s"])
    if duration <= 8:
        return int(PROMPT_DURATION_COMPLEXITY_POLICY["max_time_segments_for_8s"])
    return int(PROMPT_DURATION_COMPLEXITY_POLICY["max_time_segments_for_15s"])


def _max_scene_change_terms_for_duration(duration: int) -> int:
    if duration <= 5:
        return int(PROMPT_DURATION_COMPLEXITY_POLICY["max_scene_change_terms_for_5s"])
    if duration <= 8:
        return int(PROMPT_DURATION_COMPLEXITY_POLICY["max_scene_change_terms_for_8s"])
    return int(PROMPT_DURATION_COMPLEXITY_POLICY["max_scene_change_terms_for_15s"])


def _prompt_frame_control_instruction(shot: dict[str, Any], reference_label: str | None) -> str:
    if not reference_label:
        return ""
    if shot.get("first_frame_reference_id"):
        return f"Use {reference_label} as the first-frame reference to keep the product shape consistent."
    if shot.get("last_frame_reference_id"):
        return f"Use {reference_label} as the last-frame reference for a stable product freeze-frame ending."
    return ""


def _dreamina_prompt_for_shot(shot: dict[str, Any], plan: dict[str, Any]) -> str:
    material_reference_map = _build_material_reference_map({"shots": [shot]}, _normalize_dreamina_capability_profile(plan.get("dreamina_capability_profile", {})))
    return _render_dreamina_prompt_components(_dreamina_prompt_components_for_shot(shot, plan, _material_reference_for_shot(shot, material_reference_map)))


def _dreamina_prompt_components_for_shot(shot: dict[str, Any], plan: dict[str, Any], material_reference: dict[str, Any] | None = None) -> dict[str, str]:
    product_name = _display_product_name(plan)
    style = plan.get("production_style", {})
    material_reference = material_reference or {}
    reference_label = material_reference.get("label")
    reference_usage = material_reference.get("usage")
    if shot["material_mode"] in {"image2video", "reuse_image"}:
        reference = f"Use {reference_label} as {reference_usage}; preserve product identity, tape shape, woven surface, and material texture." if reference_label and reference_usage else "BLOCKED: this image-based product shot needs a numbered real product reference and usage."
    elif shot["material_mode"] == "reuse_video":
        reference = f"Use {reference_label} as {reference_usage}; keep product identity unchanged." if reference_label and reference_usage else "BLOCKED: this video-based product shot needs a numbered real footage reference and usage."
    elif shot["material_mode"] == "blocked":
        reference = "BLOCKED: this shot needs a real product reference before generation."
    else:
        reference = "No specific Tuolin product depiction unless a real product reference is provided."
    frame_control = _prompt_frame_control_instruction(shot, reference_label)
    if frame_control:
        reference = f"{reference} {frame_control}"
    return {
        "timebox": f"0-{int(shot['duration_seconds'])} seconds, one continuous vertical 9:16 short-video shot.",
        "subject": f"{shot['visual_description']} Product context: {product_name}.",
        "reference_material": reference,
        "time_segments": _prompt_time_segments_for_shot(shot, product_name),
        "motion_and_camera": _prompt_motion_for_role(shot["role"]),
        "environment": f"{style.get('visual_language', 'credible industrial B2B product framing')}. Avoid platform UI areas.",
        "material_texture": "Show realistic woven fiber tape texture, clean edges, flexible tape form, and industrial product credibility when the product is visible.",
        "product_display_template": PRODUCT_DISPLAY_TEMPLATES.get(shot["role"], PRODUCT_DISPLAY_TEMPLATES["product_hero"]),
        "safety_and_negative_constraints": "No subtitles, no karaoke text, no watermark, no fake certification, no unsupported temperature result, no fake customer site, no competitor attack.",
    }


def _render_dreamina_prompt_components(components: dict[str, str]) -> str:
    order = [
        "timebox",
        "subject",
        "reference_material",
        "time_segments",
        "motion_and_camera",
        "environment",
        "material_texture",
        "product_display_template",
        "safety_and_negative_constraints",
    ]
    labels = {
        "timebox": "Timebox",
        "subject": "Subject",
        "reference_material": "Reference material",
        "time_segments": "Time segments",
        "motion_and_camera": "Motion and camera",
        "environment": "Environment",
        "material_texture": "Material texture",
        "product_display_template": "Product display template",
        "safety_and_negative_constraints": "Safety and negative constraints",
    }
    return " ".join(f"{labels[key]}: {components[key]}" for key in order if components.get(key))


def _prompt_time_segments_for_shot(shot: dict[str, Any], product_name: str) -> str:
    duration = int(shot.get("duration_seconds", 5))
    role = str(shot.get("role") or "product_hero")
    if duration <= 5:
        ranges = [("0-2s", _segment_opening_action(role, product_name)), ("2-4s", _segment_detail_action(role, product_name)), (f"4-{duration}s", _segment_closing_action(role, product_name))]
    elif duration <= 8:
        midpoint = max(3, duration // 2)
        ranges = [("0-2s", _segment_opening_action(role, product_name)), (f"2-{midpoint}s", _segment_detail_action(role, product_name)), (f"{midpoint}-{duration}s", _segment_closing_action(role, product_name))]
    else:
        first = 3
        second = max(6, duration - 4)
        ranges = [("0-3s", _segment_opening_action(role, product_name)), (f"3-{second}s", _segment_detail_action(role, product_name)), (f"{second}-{duration}s", _segment_closing_action(role, product_name))]
    return " ".join(f"{label}: {text}" for label, text in ranges if label.split("-")[0] != label.split("-")[-1])


def _segment_opening_action(role: str, product_name: str) -> str:
    if role == "opening_environment":
        return "show a clean industrial insulation problem context without text overlays"
    if role == "product_detail":
        return f"start from a stable macro view of {product_name} woven surface"
    if role == "application_context":
        return "start with a confirmed wrapping or sealing context, no fake customer-site claim"
    if role == "closing_cta":
        return f"bring {product_name} into a clean product closing composition"
    return f"reveal {product_name} as the main product with stable shape"


def _segment_detail_action(role: str, product_name: str) -> str:
    if role == "product_detail":
        return "move laterally across texture, edge thickness, and flexible tape form"
    if role == "benefit_visual":
        return "show one controlled industrial benefit visual without exaggerated testing"
    if role == "application_context":
        return "follow a simple wrapping or installation motion using only confirmed application logic"
    if role == "closing_cta":
        return "hold product clearly with safe blank space for later CTA overlay"
    return "slowly push in to show product silhouette, clean edge, and woven material credibility"


def _segment_closing_action(role: str, product_name: str) -> str:
    if role == "opening_environment":
        return f"transition visually toward {product_name} as the material solution"
    if role == "product_detail":
        return "end on a sharp close-up of clean edge and woven fiber detail"
    if role == "application_context":
        return "end with the application remaining clearly illustrative, not a real case claim"
    if role == "closing_cta":
        return "end on a product freeze-frame style composition with no generated subtitles"
    return "end with a stable product-focused frame ready for the next shot"


def _prompt_motion_for_role(role: str) -> str:
    industrial_language = INDUSTRIAL_CAMERA_LANGUAGE.get(role)
    if role == "opening_environment":
        return f"{industrial_language} Fast but stable opening move, subtle push-in, immediate industrial context within the first two seconds."
    if role == "product_hero":
        return f"{industrial_language} Slow push-in around the product roll or tape surface, smooth B2B product reveal."
    if role == "product_detail":
        return f"{industrial_language} Macro close-up with slight lateral movement to reveal woven texture, edge, and thickness."
    if role == "benefit_visual":
        return f"{industrial_language} Controlled explanatory motion, light camera slide, no exaggerated flame or test outcome."
    if role == "application_context":
        return f"{industrial_language} Practical installation-context camera move, show application logic without claiming a real customer site."
    return f"{industrial_language or ''} Clean closing movement with product and CTA-safe composition, leave room away from TikTok and Shorts UI zones."


def _build_narration_script_payload(state: dict[str, Any], plan: dict[str, Any], storyboard: dict[str, Any], now: datetime) -> dict[str, Any]:
    product_name = _display_product_name(plan)
    language = state["language_version"]
    sentences = []
    for shot in storyboard["shots"]:
        text = _narration_sentence_for_shot(shot, plan, product_name, language)
        sentences.append(
            {
                "shot_id": shot["shot_id"],
                "duration_seconds": shot["duration_seconds"],
                "text": text,
                "intent": shot.get("narration_intent", ""),
            }
        )
    return {
        "schema_version": "narration-script-v1",
        "generated_at": now.isoformat(),
        "status": "draft_pending_confirmation",
        "language_version": language,
        "voice_requirement": _voice_requirement(language),
        "sentences": sentences,
        "full_text": " ".join(item["text"] for item in sentences),
        "policy": {
            "same_language_as_video": True,
            "no_new_product_facts": True,
            "confirm_before_voice_samples": True,
            "voice_samples_same_excerpt": True,
        },
        "next_step": "确认旁白文案后生成 3 个声音样本。",
    }


def _render_narration_script(script: dict[str, Any]) -> str:
    lines = [
        "# 旁白文案",
        "",
        f"- 语言版本：{script['language_version']}",
        f"- 声音要求：{script['voice_requirement']}",
        "",
        "## 完整旁白",
        "",
        script["full_text"],
        "",
        "## 分句脚本",
        "",
    ]
    for item in script["sentences"]:
        lines.extend(
            [
                f"### 镜头 {item['shot_id']}",
                "",
                f"- 建议时长：{item['duration_seconds']} 秒",
                f"- 旁白：{item['text']}",
                f"- 意图：{item['intent']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 边界",
            "",
            "- 旁白语言必须与视频语言版本一致。",
            "- 旁白不得引入正式知识中没有的新事实、参数、性能结论或认证承诺。",
            "- 确认旁白文案后，才能生成 3 个同文本声音样本。",
            "",
            "请确认旁白文案后继续生成声音样本。",
        ]
    )
    return "\n".join(lines) + "\n"


def _narration_sentence_for_shot(shot: dict[str, Any], plan: dict[str, Any], product_name: str, language: str) -> str:
    role = shot["role"]
    primary_name = plan["creative_direction"]["primary"]["name"]
    if language == "en":
        if role == "opening_environment":
            return "High-temperature insulation work needs materials that are reliable, clean, and easy to handle."
        if role == "product_hero":
            return f"{product_name} is designed for industrial heat-insulation wrapping and sealing applications."
        if role == "product_detail":
            return "Its woven surface and flexible tape form help installers handle detailed wrapping work more consistently."
        if role == "benefit_visual":
            return f"This video focuses on the confirmed product value behind {primary_name}, without overstating test results."
        if role == "application_context":
            return "Use it only in confirmed application scenarios, and treat any simulated scene as a visual explanation."
        return "For specifications, samples, or purchasing details, contact Tuolin with your application requirements."
    if role == "opening_environment":
        return "高温隔热和包覆施工，需要可靠、干净、易操作的材料。"
    if role == "product_hero":
        return f"{product_name} 面向工业隔热包覆和密封应用。"
    if role == "product_detail":
        return "织带表面和柔性形态，有助于施工人员处理细节包覆。"
    if role == "benefit_visual":
        return f"本视频围绕{primary_name}表达已确认价值，不夸大测试结果。"
    if role == "application_context":
        return "应用画面只基于已确认场景，AI 模拟画面仅用于解释。"
    return "如需规格、样品或采购信息，请把具体应用需求发给拓霖。"


def _voice_requirement(language: str) -> str:
    if language == "en":
        return "natural, credible middle-aged Western male voice"
    return "自然、流畅的中年男声中文，不刻意使用外国口音"


def _voice_profiles(language: str) -> list[dict[str, str]]:
    if language == "en":
        return [
            {"voice_id": "en_middle_aged_western_male_1", "description": "Natural, credible middle-aged Western male voice, steady pace."},
            {"voice_id": "en_middle_aged_western_male_2", "description": "Warmer middle-aged Western male voice, slightly slower and reassuring."},
            {"voice_id": "en_middle_aged_western_male_3", "description": "Clear industrial narrator, middle-aged Western male, concise delivery."},
        ]
    return [
        {"voice_id": "zh_middle_aged_male_1", "description": "自然、流畅的中年男声中文，语速中等。"},
        {"voice_id": "zh_middle_aged_male_2", "description": "稳重可信的中年男声中文，语速略慢。"},
        {"voice_id": "zh_middle_aged_male_3", "description": "清晰干净的工业产品讲解男声中文。"},
    ]


def _voice_sample_excerpt(script: dict[str, Any]) -> str:
    text = script.get("full_text", "").strip()
    if not text:
        return ""
    sentences = [item["text"] for item in script.get("sentences", [])]
    if len(sentences) >= 2:
        return " ".join(sentences[:2])
    return text[:220]


def _write_mock_wav(path: Path, duration_seconds: float = 1.0, sample_rate: int = 8000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(duration_seconds * sample_rate))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)


def _build_sentence_timing(script: dict[str, Any], total_duration: int, selected_voice: dict[str, Any], now: datetime) -> dict[str, Any]:
    sentences = script.get("sentences", [])
    total_script_duration = sum(float(item.get("duration_seconds", 0)) for item in sentences) or float(total_duration)
    cursor = 0.0
    timed = []
    for index, item in enumerate(sentences, start=1):
        ratio = float(item.get("duration_seconds", 0)) / total_script_duration if total_script_duration else 0
        duration = round(total_duration * ratio, 3)
        if index == len(sentences):
            end = float(total_duration)
        else:
            end = round(cursor + duration, 3)
        timed.append(
            {
                "index": index,
                "shot_id": item["shot_id"],
                "start_seconds": round(cursor, 3),
                "end_seconds": round(end, 3),
                "text": item["text"],
            }
        )
        cursor = end
    return {
        "schema_version": "narration-timing-v1",
        "generated_at": now.isoformat(),
        "language_version": script["language_version"],
        "total_duration_seconds": total_duration,
        "voice": selected_voice,
        "sentence_timing": timed,
    }


def _render_narration_preview(script: dict[str, Any], timing: dict[str, Any], selected_voice: dict[str, Any]) -> str:
    lines = [
        "# 旁白预览",
        "",
        f"- 语言版本：{script['language_version']}",
        f"- 声音：{selected_voice.get('voice_profile', {}).get('description', '未选择')}",
        f"- 总时长：{timing['total_duration_seconds']} 秒",
        "",
        "## 句级时间轴",
        "",
    ]
    for item in timing["sentence_timing"]:
        lines.append(f"- {item['start_seconds']:.3f}s–{item['end_seconds']:.3f}s｜镜头 {item['shot_id']}｜{item['text']}")
    lines.extend(
        [
            "",
            "请检查旁白文案、声音、语速、发音和节奏。确认后回复：确认旁白。",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_dreamina_jobs_payload(
    state: dict[str, Any],
    plan: dict[str, Any],
    storyboard: dict[str, Any],
    prompts: dict[str, Any],
    timing: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    prompt_by_shot = {item["shot_id"]: item for item in prompts.get("prompts", [])}
    timing_by_shot = {item["shot_id"]: item for item in timing.get("sentence_timing", [])}
    capability_profile = _state_dreamina_capability_profile(state)
    material_reference_map = prompts.get("material_reference_map") or _build_material_reference_map(storyboard, capability_profile)
    material_limit_blockers = _material_reference_limit_blockers(material_reference_map, capability_profile)
    jobs = []
    for shot in storyboard.get("shots", []):
        prompt = prompt_by_shot.get(shot["shot_id"], {})
        sentence_timing = timing_by_shot.get(shot["shot_id"], {})
        job_type = _dreamina_job_type_for_shot(shot)
        blocked_reason = _dreamina_blocked_reason(shot, job_type)
        validation = _validate_dreamina_job(shot, prompt, job_type, blocked_reason, capability_profile, material_limit_blockers)
        estimated_credits = _estimate_dreamina_credits(job_type, int(shot["duration_seconds"]))
        job_status = "blocked" if job_type == "blocked" or validation.get("status") == "blocked" else "planned"
        jobs.append(
            {
                "job_id": f"shot_{shot['shot_id']}",
                "shot_id": shot["shot_id"],
                "job_type": job_type,
                "status": job_status,
                "duration_seconds": int(shot["duration_seconds"]),
                "model": capability_profile["model"],
                "resolution": capability_profile["resolution"],
                "aspect_ratio": capability_profile["aspect_ratio"],
                "prompt": prompt.get("prompt", ""),
                "negative_prompt": prompt.get("negative_prompt", ""),
                "reference_required": bool(prompt.get("reference_required")),
                "reference_material_id": prompt.get("reference_material_id"),
                "numbered_reference_label": prompt.get("numbered_reference_label"),
                "reference_usage": prompt.get("reference_usage"),
                "first_frame_reference_id": prompt.get("first_frame_reference_id"),
                "last_frame_reference_id": prompt.get("last_frame_reference_id"),
                "frame_control_risk": prompt.get("frame_control_risk", ""),
                "human_face_risk": prompt.get("human_face_risk", "none"),
                "human_face_policy": prompt.get("human_face_policy", "allow_partial_hands_or_back_view_only"),
                "prompt_quality_checks": prompt.get("prompt_quality_checks") or _prompt_quality_checks(prompt),
                "selected_material": shot.get("selected_material"),
                "product_visible": bool(shot.get("product_visible")),
                "ai_generated": bool(shot.get("ai_generated")),
                "narration_timing": sentence_timing,
                "estimated_credits": estimated_credits,
                "risk_notes": shot.get("risk_notes", ""),
                "blocked_reason": blocked_reason,
                "validation": validation,
            }
        )
    estimated_total = sum(int(job["estimated_credits"]) for job in jobs)
    return {
        "schema_version": "dreamina-jobs-v1",
        "generated_at": now.isoformat(),
        "status": "planned_pending_user_confirmation",
        "run_dir": state["run_dir"],
        "language_version": state["language_version"],
        "platforms": state["platforms"],
        "format": {
            "aspect_ratio": capability_profile["aspect_ratio"],
            "resolution": "1080x1920",
            "dreamina_resolution": capability_profile["resolution"],
            "model": capability_profile["model"],
            "capability_profile": capability_profile,
        },
        "source_files": {
            "storyboard_json": state["files"]["storyboard_json"],
            "prompts_json": state["files"]["prompts_json"],
            "narration_timing": state["files"]["narration_timing"],
        },
        "material_reference_map": material_reference_map,
        "estimated_total_credits": estimated_total,
        "submit_requires_confirmation": "确认即梦生成",
        "jobs": jobs,
        "policy": {
            "do_not_submit_before_confirmation": True,
            "product_shots_require_real_reference": True,
            "text2video_not_allowed_for_visible_product": True,
            "blocked_jobs_prevent_confirmation": True,
            "job_validation_required": True,
        },
    }


def _render_dreamina_jobs(jobs_payload: dict[str, Any]) -> str:
    lines = [
        "# 即梦任务计划",
        "",
        f"- 状态：{jobs_payload['status']}",
        f"- 模型：{jobs_payload['format']['model']}",
        f"- 分辨率：{jobs_payload['format']['dreamina_resolution']}（最终 1080×1920）",
        f"- 画幅：{jobs_payload['format']['aspect_ratio']}",
        f"- 预计总额度：{jobs_payload['estimated_total_credits']}",
        "- 提交条件：用户明确回复 `确认即梦生成`",
        "",
        "## 任务列表",
        "",
    ]
    for job in jobs_payload["jobs"]:
        lines.extend(
            [
                f"### 镜头 {job['shot_id']}｜{job['job_type']}",
                "",
                f"- 状态：{job['status']}",
                f"- 时长：{job['duration_seconds']} 秒",
                f"- 预计额度：{job['estimated_credits']}",
                f"- 参考素材：{job['reference_material_id'] or '无'}",
                f"- 编号引用：{job.get('numbered_reference_label') or '无'}",
                f"- 引用用途：{job.get('reference_usage') or '无'}",
                f"- 首帧参考：{job.get('first_frame_reference_id') or '无'}",
                f"- 尾帧参考：{job.get('last_frame_reference_id') or '无'}",
                f"- 帧控制风险：{job.get('frame_control_risk') or '无'}",
                f"- 人脸风险：{job.get('human_face_risk') or 'none'}｜策略：{job.get('human_face_policy') or 'allow_partial_hands_or_back_view_only'}",
                f"- 展示产品：{'是' if job['product_visible'] else '否'}",
                f"- AI 生成：{'是' if job['ai_generated'] else '否'}",
                f"- 风险提示：{job['risk_notes'] or '无'}",
                f"- 任务验证：{job['validation']['status']}｜{'; '.join(job['validation']['messages'])}",
            ]
        )
        if job["blocked_reason"]:
            lines.append(f"- 阻塞原因：{job['blocked_reason']}")
        lines.extend(["", "Prompt:", "", job["prompt"] or "无", ""])
    lines.extend(
        [
            "## 边界",
            "",
            "- 本文件只是任务计划，不会提交即梦任务。",
            "- 存在 blocked 任务时不能确认即梦生成。",
            "- 展示具体产品的 AI 镜头必须使用真实产品素材作为参考。",
            "- `text2video` 只能用于环境或过渡镜头，不能用于可见产品镜头。",
            "",
            "请检查任务类型、素材、时长、预计额度和风险。确认消耗额度后回复：确认即梦生成。",
        ]
    )
    return "\n".join(lines) + "\n"


def _submit_dreamina_jobs_payload(
    jobs_payload: dict[str, Any],
    execute: bool,
    dreamina_command: str,
    runner: Runner,
    now: datetime,
) -> dict[str, Any]:
    generated_dir = Path(jobs_payload["run_dir"]) / "dreamina_generation" / "generated_shots"
    generated_dir.mkdir(parents=True, exist_ok=True)
    submissions = []
    for job in jobs_payload.get("jobs", []):
        output_path = generated_dir / f"shot_{job['shot_id']}.mp4"
        command = _dreamina_submit_command(job, dreamina_command, output_path)
        if job["job_type"] in {"reuse_video", "reuse_image"}:
            submissions.append(
                {
                    "job_id": job["job_id"],
                    "shot_id": job["shot_id"],
                    "job_type": job["job_type"],
                    "status": "reused",
                    "provider_task_id": None,
                    "command": command,
                    "expected_output_path": str(output_path),
                    "error": None,
                }
            )
            continue
        if not execute:
            submissions.append(
                {
                    "job_id": job["job_id"],
                    "shot_id": job["shot_id"],
                    "job_type": job["job_type"],
                    "status": "dry_run_submitted",
                    "provider_task_id": f"dryrun_{job['job_id']}",
                    "command": command,
                    "expected_output_path": str(output_path),
                    "error": None,
                }
            )
            continue
        completed = runner(command, capture_output=True, text=True, check=False)
        parsed = _parse_dreamina_json_output(completed.stdout)
        provider_task_id = parsed.get("task_id") or parsed.get("id") or parsed.get("job_id")
        submissions.append(
            {
                "job_id": job["job_id"],
                "shot_id": job["shot_id"],
                "job_type": job["job_type"],
                "status": "submitted" if completed.returncode == 0 else "submission_failed",
                "provider_task_id": provider_task_id,
                "command": command,
                "expected_output_path": str(output_path),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "error": None if completed.returncode == 0 else _completed_error(completed),
            }
        )
    return {
        "schema_version": "dreamina-submission-v1",
        "submitted_at": now.isoformat(),
        "mode": "execute" if execute else "dry_run",
        "status": "submitted" if all(item["status"] != "submission_failed" for item in submissions) else "partial_failure",
        "run_dir": jobs_payload["run_dir"],
        "estimated_total_credits": jobs_payload["estimated_total_credits"],
        "submissions": submissions,
        "policy": {
            "submitted_only_after_user_confirmation": True,
            "dry_run_does_not_consume_credits": not execute,
        },
    }


def _render_dreamina_submission(submission: dict[str, Any]) -> str:
    lines = [
        "# 即梦提交记录",
        "",
        f"- 模式：{submission['mode']}",
        f"- 状态：{submission['status']}",
        f"- 预计额度：{submission['estimated_total_credits']}",
        "",
        "## 提交明细",
        "",
    ]
    for item in submission["submissions"]:
        lines.extend(
            [
                f"### 镜头 {item['shot_id']}｜{item['job_type']}",
                "",
                f"- 状态：{item['status']}",
                f"- 即梦任务 ID：{item['provider_task_id'] or '无'}",
                f"- 预期输出：{item['expected_output_path']}",
                f"- 错误：{item.get('error') or '无'}",
                f"- 命令预览：`{' '.join(str(part) for part in item['command'])}`",
                "",
            ]
        )
    lines.extend(["下一步：查询即梦结果。", ""])
    return "\n".join(lines)


def _query_dreamina_results_payload(
    submission: dict[str, Any],
    execute: bool,
    dreamina_command: str,
    runner: Runner,
    now: datetime,
) -> dict[str, Any]:
    results = []
    for item in submission.get("submissions", []):
        command = _dreamina_status_command(dreamina_command, item.get("provider_task_id"))
        if item["status"] == "reused":
            results.append(
                {
                    "job_id": item["job_id"],
                    "shot_id": item["shot_id"],
                    "job_type": item["job_type"],
                    "status": "succeeded",
                    "provider_task_id": item.get("provider_task_id"),
                    "output_path": item["expected_output_path"],
                    "command": command,
                    "error": None,
                }
            )
            continue
        if item["status"] == "dry_run_submitted" or not execute:
            results.append(
                {
                    "job_id": item["job_id"],
                    "shot_id": item["shot_id"],
                    "job_type": item["job_type"],
                    "status": "succeeded",
                    "provider_task_id": item.get("provider_task_id"),
                    "output_path": item["expected_output_path"],
                    "command": command,
                    "error": None,
                    "note": "dry-run 查询结果，用于验证工作流状态和文件契约；不会生成真实视频文件。",
                }
            )
            continue
        completed = runner(command, capture_output=True, text=True, check=False)
        parsed = _parse_dreamina_json_output(completed.stdout)
        provider_status = str(parsed.get("status") or parsed.get("state") or "").lower()
        status = "succeeded" if provider_status in {"succeeded", "success", "completed", "done"} else "pending"
        if completed.returncode != 0:
            status = "query_failed"
        results.append(
            {
                "job_id": item["job_id"],
                "shot_id": item["shot_id"],
                "job_type": item["job_type"],
                "status": status,
                "provider_task_id": item.get("provider_task_id"),
                "output_path": parsed.get("output_path") or parsed.get("video_path") or parsed.get("url") or item["expected_output_path"],
                "command": command,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "error": None if completed.returncode == 0 else _completed_error(completed),
            }
        )
    return {
        "schema_version": "dreamina-results-v1",
        "queried_at": now.isoformat(),
        "mode": "execute" if execute else "dry_run",
        "status": "ready" if all(item["status"] == "succeeded" for item in results) else "pending",
        "run_dir": submission["run_dir"],
        "results": results,
        "policy": {
            "confirm_shots_before_final_assembly": True,
            "retry_failed_or_unsatisfactory_shots_only": True,
        },
    }


def _render_dreamina_results(results: dict[str, Any]) -> str:
    lines = [
        "# 即梦结果",
        "",
        f"- 模式：{results['mode']}",
        f"- 状态：{results['status']}",
        "",
        "## 镜头结果",
        "",
    ]
    for item in results["results"]:
        lines.extend(
            [
                f"### 镜头 {item['shot_id']}｜{item['job_type']}",
                "",
                f"- 状态：{item['status']}",
                f"- 即梦任务 ID：{item.get('provider_task_id') or '无'}",
                f"- 输出：{item.get('output_path') or '无'}",
                f"- 错误：{item.get('error') or '无'}",
                "",
            ]
        )
    lines.extend(
        [
            "## 下一步",
            "",
            "- 如果镜头可用，回复：确认镜头。",
            "- 如果单个镜头需要重做，回复：重做镜头 03，并说明原因。",
            "",
        ]
    )
    return "\n".join(lines)


def _build_shot_preview_manifest(run_dir: Path, state: dict[str, Any], results: dict[str, Any], now: datetime) -> dict[str, Any]:
    timing_path = Path(state["files"]["narration_timing"])
    return {
        "schema_version": "shot-preview-manifest-v1",
        "generated_at": now.isoformat(),
        "status": "dry_run_ready",
        "run_dir": str(run_dir),
        "shot_outputs": [item.get("output_path", "") for item in results.get("results", [])],
        "narration_audio": state["files"]["narration_audio"],
        "temporary_subtitles_source": str(timing_path),
        "preview_path": str(run_dir / "dreamina_generation" / "shot_preview.mp4"),
        "contains_confirmed_narration": True,
        "contains_temporary_subtitles": True,
        "contains_final_bgm": False,
        "policy": {
            "used_for_shot_review_only": True,
            "final_bgm_not_included": True,
            "confirmed_shots_not_resubmitted": True,
        },
    }


def _render_shot_preview_manifest(manifest: dict[str, Any]) -> str:
    lines = [
        "# 镜头预览组装清单",
        "",
        f"- 状态：{manifest['status']}",
        f"- 镜头数量：{len(manifest['shot_outputs'])}",
        f"- 旁白：{manifest['narration_audio']}",
        f"- 临时字幕来源：{manifest['temporary_subtitles_source']}",
        f"- 预览输出：{manifest['preview_path']}",
        f"- 包含最终 BGM：{'是' if manifest['contains_final_bgm'] else '否'}",
        "",
        "该预览只用于确认镜头；最终 BGM 在确认镜头后再加入。",
        "",
    ]
    return "\n".join(lines)


def _render_shot_retry_plan(retry: dict[str, Any]) -> str:
    job = retry["original_job"]
    lines = [
        f"# 重做镜头 {retry['shot_id']} 计划",
        "",
        f"- 状态：{retry['status']}",
        f"- 原任务类型：{job['job_type']}",
        f"- 预计额度：{retry['estimated_credits']}",
        f"- 重做原因：{retry['reason'] or '未填写'}",
        f"- 提交条件：`{retry['submit_requires_confirmation']}`",
        "",
        "## 原 Prompt",
        "",
        job.get("prompt") or "无",
        "",
        "## 边界",
        "",
        "- 只重做当前镜头，不重新提交已接受镜头。",
        "- 展示产品时仍必须使用真实产品参考素材。",
        "- 确认重做后才允许提交，避免误消耗额度。",
        "",
    ]
    return "\n".join(lines)


def _dreamina_submit_command(job: dict[str, Any], dreamina_command: str, output_path: Path) -> list[str]:
    base = [
        dreamina_command,
        "video",
        job["job_type"],
        "--model",
        job["model"],
        "--resolution",
        job["resolution"],
        "--aspect-ratio",
        job["aspect_ratio"],
        "--duration",
        str(job["duration_seconds"]),
        "--prompt",
        job.get("prompt", ""),
        "--negative-prompt",
        job.get("negative_prompt", ""),
        "--output",
        str(output_path),
        "--json",
    ]
    material_path = _reference_material_path(job)
    if material_path:
        base.extend(["--input", material_path])
    return base


def _dreamina_status_command(dreamina_command: str, provider_task_id: str | None) -> list[str]:
    command = [dreamina_command, "task", "status", provider_task_id or "", "--json"]
    return [part for part in command if part != ""]


def _reference_material_path(job: dict[str, Any]) -> str | None:
    selected = job.get("selected_material") or {}
    files = selected.get("files") or selected.get("file_paths") or selected.get("paths") or []
    if isinstance(files, str):
        return files
    if files:
        return str(files[0])
    return None


def _parse_dreamina_json_output(output: str) -> dict[str, Any]:
    if not output.strip():
        return {}
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _completed_error(completed: subprocess.CompletedProcess[str]) -> str:
    return (completed.stderr or completed.stdout or f"command failed with exit code {completed.returncode}").strip()


def _normalize_shot_id(shot_id: str) -> str:
    value = str(shot_id).strip().lower().replace("shot_", "")
    if value.isdigit():
        return f"{int(value):02d}"
    if len(value) == 2 and value[0].isdigit() and value[1].isdigit():
        return value
    raise ValueError("镜头编号必须是 01、02、03 这类格式，或数字 1、2、3。")


def _build_srt_subtitles(timing: dict[str, Any]) -> str:
    blocks = []
    for index, item in enumerate(timing.get("sentence_timing", []), start=1):
        text = _subtitle_text(str(item.get("text", "")))
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{_srt_timestamp(float(item['start_seconds']))} --> {_srt_timestamp(float(item['end_seconds']))}",
                    text,
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def _subtitle_text(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return ""
    if _contains_cjk(cleaned):
        if len(cleaned) <= 18:
            return cleaned
        split_at = min(len(cleaned) - 1, max(1, len(cleaned) // 2))
        return cleaned[:split_at] + "\n" + cleaned[split_at:]
    words = cleaned.split()
    if len(words) <= 7:
        return cleaned
    split_at = max(1, min(len(words) - 1, len(words) // 2))
    return " ".join(words[:split_at]) + "\n" + " ".join(words[split_at:])


def _srt_timestamp(value: float) -> str:
    milliseconds = int(round(value * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _build_bgm_license_payload(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    return {
        "schema_version": "bgm-license-v1",
        "generated_at": now.isoformat(),
        "status": "metadata_required_before_real_publish",
        "music_policy": {
            "commercially_usable_required": True,
            "do_not_use_tiktok_trending_song": True,
            "must_not_cover_narration": True,
        },
        "selection_brief": {
            "language_version": state["language_version"],
            "mood": "modern industrial, clean, trustworthy",
            "pace": "short-video medium tempo",
            "vocal": "instrumental preferred; no lyrics competing with narration",
        },
        "selected_track": {
            "title": "",
            "source": "",
            "license": "",
            "license_url": "",
            "local_path": "",
        },
    }


def _render_bgm_brief(payload: dict[str, Any]) -> str:
    brief = payload["selection_brief"]
    lines = [
        "# BGM 选择与授权记录",
        "",
        f"- 状态：{payload['status']}",
        f"- 情绪：{brief['mood']}",
        f"- 节奏：{brief['pace']}",
        f"- 人声：{brief['vocal']}",
        "",
        "## 必填授权元数据",
        "",
        "- title",
        "- source",
        "- license",
        "- license_url",
        "- local_path",
        "",
        "## 边界",
        "",
        "- 必须可商用。",
        "- 不使用 TikTok 热门歌曲替代授权音乐。",
        "- 音乐不得压过旁白。",
        "",
    ]
    return "\n".join(lines)


def _build_final_preview_manifest(
    state: dict[str, Any],
    results: dict[str, Any],
    subtitles_path: Path,
    bgm_license_path: Path,
    preview_path: Path,
    concat_path: Path,
    execute: bool,
    ffmpeg_command: str,
    runner: Runner,
    now: datetime,
) -> dict[str, Any]:
    shot_paths = [str(item.get("output_path", "")) for item in results.get("results", [])]
    local_shot_paths = [Path(path) for path in shot_paths if path and not path.startswith(("http://", "https://"))]
    missing = [str(path) for path in local_shot_paths if not path.exists()]
    bgm = _load_json_file(bgm_license_path, "bgm_license.json") if bgm_license_path.exists() else {}
    selected_bgm = bgm.get("selected_track", {})
    selected_bgm_path = str(selected_bgm.get("local_path", "")).strip()
    logo_path = _resolve_logo_path(str(state.get("adapters", {}).get("logo_path", "")), Path(state["run_dir"]))
    logo_status = "available" if logo_path and logo_path.exists() else "missing_or_not_configured"
    command: list[str] = []
    ffmpeg_result: dict[str, Any] | None = None
    status = "dry_run_ready"
    if execute:
        if missing:
            status = "missing_inputs"
        else:
            concat_path.write_text("".join(f"file '{path}'\n" for path in local_shot_paths), encoding="utf-8")
            command = [
                ffmpeg_command,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-i",
                state["files"]["narration_audio"],
            ]
            if selected_bgm_path:
                command.extend(["-i", selected_bgm_path])
            command.extend(
                [
                    "-vf",
                    f"subtitles={subtitles_path}",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    str(preview_path),
                ]
            )
            completed = runner(command, capture_output=True, text=True, check=False)
            status = "assembled" if completed.returncode == 0 else "assembly_failed"
            ffmpeg_result = {
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "error": None if completed.returncode == 0 else _completed_error(completed),
            }
    return {
        "schema_version": "final-preview-manifest-v1",
        "generated_at": now.isoformat(),
        "status": status,
        "mode": "execute" if execute else "dry_run",
        "run_dir": state["run_dir"],
        "language_version": state["language_version"],
        "platforms": state["platforms"],
        "shot_outputs": shot_paths,
        "missing_inputs": missing,
        "narration_audio": state["files"]["narration_audio"],
        "subtitles_srt": str(subtitles_path),
        "subtitles_burned_in": True,
        "bgm_license": str(bgm_license_path),
        "selected_bgm_audio": selected_bgm_path,
        "bgm_embedded": bool(selected_bgm_path),
        "logo_path": str(logo_path) if logo_path else "",
        "logo_status": logo_status,
        "logo_end_only": True,
        "preview_path": str(preview_path),
        "final_output_filename": state["outputs"]["final_filename"],
        "expected_duration_seconds": int(state["duration_seconds"]),
        "duration_tolerance_seconds": {
            "min": _duration_tolerance(int(state["duration_seconds"]))[0],
            "max": _duration_tolerance(int(state["duration_seconds"]))[1],
        },
        "ffmpeg_command": command,
        "ffmpeg_result": ffmpeg_result,
        "policy": {
            "short_sentence_subtitles": True,
            "subtitle_safe_area_required": True,
            "manual_audio_visual_check_required": True,
            "no_master_filename": True,
        },
    }


def _render_final_preview_manifest(manifest: dict[str, Any]) -> str:
    lines = [
        "# 成片预览组装清单",
        "",
        f"- 状态：{manifest['status']}",
        f"- 模式：{manifest['mode']}",
        f"- 语言版本：{manifest['language_version']}",
        f"- 平台：{', '.join(manifest['platforms'])}",
        f"- 预览输出：{manifest['preview_path']}",
        f"- 最终文件名：{manifest['final_output_filename']}",
        "",
        "## 组成",
        "",
        f"- 镜头数量：{len(manifest['shot_outputs'])}",
        f"- 旁白：{manifest['narration_audio']}",
        f"- 字幕：{manifest['subtitles_srt']}（烧录：{'是' if manifest.get('subtitles_burned_in') else '否'}）",
        f"- BGM 授权记录：{manifest['bgm_license']}",
        f"- BGM 音频：{manifest.get('selected_bgm_audio') or '未选择'}（嵌入：{'是' if manifest.get('bgm_embedded') else '否'}）",
        f"- 结尾 logo：{manifest.get('logo_path') or '未配置'}（{manifest.get('logo_status')}）",
        f"- 预期时长：{manifest.get('expected_duration_seconds')} 秒，容差 {manifest.get('duration_tolerance_seconds', {}).get('min')}-{manifest.get('duration_tolerance_seconds', {}).get('max')} 秒",
        "",
    ]
    if manifest["missing_inputs"]:
        lines.extend(["## 缺失输入", ""])
        lines.extend(f"- {item}" for item in manifest["missing_inputs"])
        lines.append("")
    lines.extend(
        [
            "## 下一步",
            "",
            "运行质量门禁；门禁通过后人工打开视频剪辑软件或播放器检查音频和画面。",
            "",
        ]
    )
    return "\n".join(lines)


def _build_quality_report(run_dir: Path, state: dict[str, Any], now: datetime) -> dict[str, Any]:
    files = state.get("files", {})
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    preview_path = Path(files.get("final_preview_mp4", run_dir / "dreamina_generation" / "final_preview.mp4"))
    subtitles_path = Path(files.get("final_subtitles_srt", run_dir / "subtitles" / "final_subtitles.srt"))
    bgm_license_path = Path(files.get("bgm_license_json", run_dir / "audio" / "bgm_license.json"))
    manifest_path = Path(files.get("final_preview_manifest_json", run_dir / "dreamina_generation" / "final_preview_manifest.json"))
    manifest = _load_json_file(manifest_path, "final_preview_manifest.json") if manifest_path.exists() else {}

    if "master" in state["outputs"]["final_filename"].lower() or "母版" in state["outputs"]["final_filename"]:
        blockers.append({"code": "forbidden_master_filename", "message": "最终文件名不能包含 master 或母版。"})
    if not preview_path.exists():
        blockers.append({"code": "missing_final_preview_mp4", "message": "缺少可人工检查的 final_preview.mp4。"})
    if not subtitles_path.exists():
        blockers.append({"code": "missing_subtitles", "message": "缺少短句字幕 SRT。"})
    else:
        subtitle_issues = _subtitle_quality_issues(subtitles_path)
        blockers.extend(subtitle_issues)
    if not bgm_license_path.exists():
        blockers.append({"code": "missing_bgm_license", "message": "缺少 BGM 授权元数据。"})
    else:
        bgm = _load_json_file(bgm_license_path, "bgm_license.json")
        selected = bgm.get("selected_track", {})
        required_bgm_fields = ["title", "source", "license", "local_path"]
        missing_bgm_fields = [field for field in required_bgm_fields if not str(selected.get(field, "")).strip()]
        if missing_bgm_fields:
            blockers.append(
                {
                    "code": "bgm_track_not_selected",
                    "message": "BGM 必须选择真实曲目并记录 title、source、license 和 local_path。",
                }
            )
        else:
            bgm_path = Path(str(selected["local_path"])).expanduser()
            if not bgm_path.exists():
                blockers.append({"code": "missing_bgm_file", "message": f"找不到 BGM 本地文件：{bgm_path}"})
    if manifest.get("status") == "dry_run_ready" and not preview_path.exists():
        blockers.append({"code": "dry_run_preview_only", "message": "当前只是 dry-run 组装清单，尚未生成真实 final_preview.mp4。"})
    if manifest and not manifest.get("contains_final_bgm", True) and manifest.get("schema_version") == "shot-preview-manifest-v1":
        blockers.append({"code": "shot_preview_used_as_final", "message": "镜头预览不能作为最终成片预览。"})
    if manifest and not manifest.get("subtitles_burned_in"):
        blockers.append({"code": "subtitles_not_burned_in", "message": "最终成片必须烧录字幕。"})
    if manifest and not manifest.get("bgm_embedded"):
        blockers.append({"code": "bgm_not_embedded", "message": "最终成片必须嵌入已授权 BGM。"})
    if manifest and not manifest.get("logo_end_only"):
        blockers.append({"code": "logo_policy_missing", "message": "透明 logo 必须按结尾一次策略记录。"})
    if manifest and manifest.get("logo_status") != "available":
        warnings.append({"code": "logo_missing_or_not_configured", "message": "透明 logo 缺失或未配置；按 PRD 记录警告，不阻塞成片。"})
    if manifest and "duration_tolerance_seconds" in manifest:
        expected = int(manifest.get("expected_duration_seconds", 0))
        tolerance = manifest["duration_tolerance_seconds"]
        if not (int(tolerance["min"]) <= expected <= int(tolerance["max"])):
            blockers.append({"code": "duration_out_of_tolerance", "message": "成片预期时长不在对应容差内。"})
    if not state.get("confirmations", {}).get("shots"):
        blockers.append({"code": "shots_not_confirmed", "message": "镜头尚未确认。"})
    planning_issues = _video_creation_planning_quality_issues(state)
    blockers.extend(planning_issues["blockers"])
    warnings.extend(planning_issues["warnings"])

    return {
        "schema_version": "video-quality-report-v1",
        "checked_at": now.isoformat(),
        "status": "failed" if blockers else "passed",
        "run_dir": str(run_dir),
        "blocking_defects": blockers,
        "warnings": warnings,
        "manual_check_required": True,
        "checks": {
            "preview_exists": preview_path.exists(),
            "subtitles_exist": subtitles_path.exists(),
            "bgm_license_exists": bgm_license_path.exists(),
            "shots_confirmed": bool(state.get("confirmations", {}).get("shots")),
            "final_filename": state["outputs"]["final_filename"],
            "bgm_embedded": bool(manifest.get("bgm_embedded")),
            "subtitles_burned_in": bool(manifest.get("subtitles_burned_in")),
            "logo_status": manifest.get("logo_status", ""),
            "creative_quality_matrix_checked": planning_issues["creative_quality_matrix_checked"],
            "prompt_standard_checked": planning_issues["prompt_standard_checked"],
            "dreamina_job_validation_checked": planning_issues["dreamina_job_validation_checked"],
        },
    }


def _video_creation_planning_quality_issues(state: dict[str, Any]) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    files = state.get("files", {})
    plan = _optional_json_file(files.get("video_plan_json"))
    storyboard = _optional_json_file(files.get("storyboard_json"))
    prompts = _optional_json_file(files.get("prompts_json"))
    jobs = _optional_json_file(files.get("dreamina_jobs_json"))

    if plan:
        if not plan.get("creative_quality"):
            blockers.append({"code": "missing_creative_quality_matrix", "message": "视频策划缺少按创意方向切换的质量矩阵。"})
        if not plan.get("production_style"):
            blockers.append({"code": "missing_product_video_style", "message": "视频策划缺少工业产品视频风格矩阵映射。"})
        boundary = plan.get("knowledge_boundary", {})
        if boundary.get("draft_only_until_external_review"):
            blockers.append(
                {
                    "code": "product_requires_external_review",
                    "message": "产品知识卡 usage_scope 为 review_before_external；可做内部策划/dry-run，但正式成片外发前必须复核为 external_allowed 或删除高风险 claim。",
                }
            )
        absorbed = {item.get("source") for item in plan.get("external_skill_absorption", [])}
        if "dexhunter/seedance2-skill" not in absorbed:
            warnings.append({"code": "seedance_prompt_reference_not_recorded", "message": "策划未记录 dexhunter/seedance2-skill 的 Prompt 规则吸收来源。"})
    if storyboard:
        for shot in storyboard.get("shots", []):
            validation = shot.get("shot_design_validation", {})
            if validation.get("status") == "blocked":
                blockers.append({"code": "blocked_shot_design", "message": f"镜头 {shot.get('shot_id')} 设计验证未通过：{'; '.join(validation.get('messages', []))}"})
            if not shot.get("creative_quality_checks"):
                blockers.append({"code": "missing_shot_creative_quality", "message": f"镜头 {shot.get('shot_id')} 缺少创意质量要求。"})
            if shot.get("frame_control_risk"):
                warnings.append({"code": "frame_control_risk", "message": f"镜头 {shot.get('shot_id')}：{shot.get('frame_control_risk')}"})
            if shot.get("human_face_risk") == "clear_face":
                blockers.append({"code": "clear_human_face_reference", "message": f"镜头 {shot.get('shot_id')} 使用了清晰可辨识真人脸部素材。"})
            elif shot.get("human_face_risk") == "unclear":
                warnings.append({"code": "unclear_human_face_reference", "message": f"镜头 {shot.get('shot_id')} 素材人脸风险不明确，建议裁切、打码或替换。"})
    if prompts:
        for item in prompts.get("prompts", []):
            if item.get("prompt_standard") not in {"tuolin-industrial-seedance-v1", "tuolin-industrial-seedance-v2"}:
                blockers.append({"code": "invalid_prompt_standard", "message": f"镜头 {item.get('shot_id')} 未使用拓霖工业即梦 Prompt 标准。"})
            components = item.get("prompt_components", {})
            required = set(prompts.get("prompt_policy", {}).get("structure", []))
            missing = [key for key in required if not str(components.get(key, "")).strip()]
            if missing:
                blockers.append({"code": "missing_prompt_components", "message": f"镜头 {item.get('shot_id')} Prompt 组件缺失：{', '.join(missing)}"})
            if item.get("reference_required") and not item.get("reference_material_id"):
                blockers.append({"code": "missing_prompt_reference", "message": f"镜头 {item.get('shot_id')} 需要真实参考素材但未绑定素材 ID。"})
            if item.get("reference_required") and not item.get("numbered_reference_label"):
                blockers.append({"code": "missing_numbered_prompt_reference", "message": f"镜头 {item.get('shot_id')} 需要真实参考素材但缺少 @图片/@视频 编号引用。"})
            if item.get("reference_required") and not str(item.get("reference_usage") or "").strip():
                blockers.append({"code": "missing_prompt_reference_usage", "message": f"镜头 {item.get('shot_id')} 需要真实参考素材但缺少用途说明。"})
            if item.get("prompt_standard") == "tuolin-industrial-seedance-v2":
                if not str(components.get("time_segments") or "").strip():
                    blockers.append({"code": "missing_prompt_time_segments", "message": f"镜头 {item.get('shot_id')} 缺少分时段 Prompt。"})
                if not str(components.get("product_display_template") or "").strip():
                    blockers.append({"code": "missing_product_display_template", "message": f"镜头 {item.get('shot_id')} 缺少工业产品展示模板。"})
                forbidden = _forbidden_entertainment_terms_in_prompt(item.get("prompt", ""))
                if forbidden:
                    blockers.append({"code": "forbidden_entertainment_prompt_pattern", "message": f"镜头 {item.get('shot_id')} Prompt 包含不允许的娱乐化表达：{', '.join(forbidden)}"})
            quality_checks = item.get("prompt_quality_checks") or _prompt_quality_checks(item)
            for issue in quality_checks.get("blockers", []):
                blockers.append({"code": str(issue.get("code", "prompt_quality_blocker")), "message": f"镜头 {item.get('shot_id')}：{issue.get('message', '')}"})
            for issue in quality_checks.get("warnings", []):
                warnings.append({"code": str(issue.get("code", "prompt_quality_warning")), "message": f"镜头 {item.get('shot_id')}：{issue.get('message', '')}"})
    if jobs:
        for job in jobs.get("jobs", []):
            validation = job.get("validation", {})
            if validation.get("status") == "blocked":
                blockers.append({"code": "blocked_dreamina_job_validation", "message": f"镜头 {job.get('shot_id')} 即梦任务验证未通过：{'; '.join(validation.get('messages', []))}"})
    return {
        "blockers": blockers,
        "warnings": warnings,
        "creative_quality_matrix_checked": bool(plan and plan.get("creative_quality")),
        "prompt_standard_checked": bool(prompts and prompts.get("prompt_policy")),
        "dreamina_job_validation_checked": bool(jobs and jobs.get("policy", {}).get("job_validation_required")),
    }


def _optional_json_file(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _subtitle_quality_issues(path: Path) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    content = path.read_text(encoding="utf-8")
    for block in [item for item in content.split("\n\n") if item.strip()]:
        lines = block.splitlines()
        text_lines = lines[2:]
        if len(text_lines) > 2:
            issues.append({"code": "subtitle_too_many_lines", "message": f"字幕块超过 2 行：{lines[0]}"})
    return issues


def _render_quality_report(report: dict[str, Any]) -> str:
    lines = [
        "# 视频质量门禁报告",
        "",
        f"- 状态：{report['status']}",
        f"- 阻塞问题：{len(report['blocking_defects'])}",
        f"- 警告：{len(report['warnings'])}",
        f"- 需要人工检查：{'是' if report['manual_check_required'] else '否'}",
        "",
        "## 阻塞问题",
        "",
    ]
    if report["blocking_defects"]:
        for item in report["blocking_defects"]:
            lines.append(f"- {item['code']}：{item['message']}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 警告", ""])
    if report["warnings"]:
        for item in report["warnings"]:
            lines.append(f"- {item['code']}：{item['message']}")
    else:
        lines.append("- 无")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "阻塞问题为 0 后，人工打开视频剪辑软件或播放器检查音频、画面、字幕同步和整体节奏。",
            "",
        ]
    )
    return "\n".join(lines)


def _build_adapter_inspection_report(run_dir: Path, state: dict[str, Any], now: datetime) -> dict[str, Any]:
    adapters = state.get("adapters", {})
    capability_profile = _state_dreamina_capability_profile(state)
    dreamina_command = str(adapters.get("dreamina_command") or "dreamina")
    ffmpeg_command = str(adapters.get("ffmpeg_command") or "ffmpeg")
    tts_provider = str(adapters.get("tts_provider") or "mock")
    tts_command = str(adapters.get("tts_command") or "")
    bgm_library_dir = str(adapters.get("bgm_library_dir") or "")
    logo_path = str(adapters.get("logo_path") or "")
    checks = [
        _command_check("dreamina_command", dreamina_command, required=False),
        _command_check("ffmpeg_command", ffmpeg_command, required=True),
        _command_check("tts_command", tts_command, required=tts_provider == "external_command"),
        _optional_path_check("bgm_library_dir", bgm_library_dir, must_be_dir=True),
        _optional_project_path_check("logo_path", logo_path, run_dir),
        _capability_profile_check(capability_profile),
    ]
    blocking = [item for item in checks if item["severity"] == "blocking" and item["status"] != "ok"]
    warnings = [item for item in checks if item["severity"] == "warning" and item["status"] != "ok"]
    return {
        "schema_version": "video-adapter-inspection-v1",
        "checked_at": now.isoformat(),
        "run_dir": str(run_dir),
        "status": "failed" if blocking else "passed_with_warnings" if warnings else "passed",
        "adapters": adapters,
        "dreamina_capability_profile": capability_profile,
        "checks": checks,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "note": "该检查只验证本地配置可解析，不提交即梦任务、不生成付费内容。",
    }


def _render_adapter_inspection(report: dict[str, Any]) -> str:
    lines = [
        "# 视频创作适配器检查",
        "",
        f"- 状态：{report['status']}",
        f"- 阻塞项：{report['blocking_count']}",
        f"- 警告项：{report['warning_count']}",
        "- 说明：只检查配置，不提交即梦任务、不消耗额度。",
        "",
        "## Seedance 能力配置",
        "",
    ]
    profile = report.get("dreamina_capability_profile", {})
    for key in [
        "model",
        "resolution",
        "aspect_ratio",
        "min_duration_seconds",
        "max_duration_seconds",
        "max_images",
        "max_videos",
        "max_audios",
        "max_total_files",
    ]:
        lines.append(f"- {key}: {profile.get(key)}")
    lines.extend(
        [
            "",
        "## 检查项",
        "",
        ]
    )
    for item in report["checks"]:
        lines.append(f"- {item['name']}：{item['status']}｜{item['message']}")
    lines.append("")
    return "\n".join(lines)


def _build_workflow_status(run_dir: Path, state: dict[str, Any], now: datetime) -> dict[str, Any]:
    available_outputs = []
    for label, path_value in state.get("files", {}).items():
        path = Path(str(path_value))
        available_outputs.append({"key": label, "path": str(path), "exists": path.exists()})
    return {
        "schema_version": "video-workflow-status-v1",
        "generated_at": now.isoformat(),
        "run_dir": str(run_dir),
        "status": state.get("status"),
        "phase": state.get("phase"),
        "current_pending_confirmation": state.get("current_pending_confirmation"),
        "product": state.get("product", {}),
        "language_version": state.get("language_version"),
        "platforms": state.get("platforms", []),
        "duration_seconds": state.get("duration_seconds"),
        "creative_direction": state.get("creative_direction", {}),
        "confirmations": state.get("confirmations", {}),
        "suggested_replies": _suggested_replies_for_state(state),
        "available_outputs": available_outputs,
        "policy": {
            "resume_from_current_phase_only": True,
            "do_not_repeat_confirmed_paid_actions": True,
            "ordinary_user_uses_tuolin_video_workflow_only": True,
        },
    }


def _render_workflow_status(status: dict[str, Any]) -> str:
    direction = status.get("creative_direction", {})
    primary = direction.get("primary") or {}
    supporting = direction.get("supporting") or {}
    lines = [
        "# 视频创作当前状态",
        "",
        f"- 状态：{status.get('status')}",
        f"- 阶段：{status.get('phase')}",
        f"- 当前待确认项：{status.get('current_pending_confirmation') or '无'}",
        f"- 语言版本：{status.get('language_version')}",
        f"- 平台：{', '.join(status.get('platforms', []))}",
        f"- 时长：{status.get('duration_seconds')} 秒",
        f"- 主创意方向：{primary.get('name', '未记录')}",
        f"- 辅助创意方向：{supporting.get('name', '无') if supporting else '无'}",
        "",
        "## 建议回复",
        "",
    ]
    suggestions = status.get("suggested_replies", [])
    if suggestions:
        for item in suggestions:
            lines.append(f"- {item}")
    else:
        lines.append("- 当前没有需要回复的确认项。")
    lines.extend(["", "## 已生成文件", ""])
    for item in status.get("available_outputs", []):
        exists = "存在" if item.get("exists") else "缺失"
        lines.append(f"- {item['key']}：{exists}｜{item['path']}")
    lines.extend(
        [
            "",
            "## 恢复规则",
            "",
            "- 只从当前阶段继续，不重复已确认步骤。",
            "- 已确认的付费即梦动作不会因为恢复状态而自动重新提交。",
            "- 普通员工继续通过 `$tuolin-video-workflow` 或自然语言回复操作。",
            "",
        ]
    )
    return "\n".join(lines)


def _suggested_replies_for_state(state: dict[str, Any]) -> list[str]:
    pending = str(state.get("current_pending_confirmation") or "")
    phase = str(state.get("phase") or "")
    if pending.startswith(("确认重做镜头", "提交重做镜头", "查询重做镜头", "继续查询重做镜头")):
        return [pending]
    if pending == "确认策划":
        return ["确认策划", "修改策划，开场更突出客户痛点"]
    if pending == "确认分镜":
        return ["确认分镜", "修改分镜，减少泛泛介绍", "修改镜头03，突出产品细节"]
    if pending in {
        "确认旁白文案",
        "确认旁白",
        "确认即梦生成",
        "确认成片",
    }:
        return [pending]
    if phase == "awaiting_voice_selection":
        return ["声音选 1", "声音选 2", "声音选 3"]
    if phase == "awaiting_shot_confirmation":
        return ["确认镜头", "重做镜头 03"]
    if phase == "awaiting_manual_quality_check":
        return ["人工音视频检查通过", "更换背景音乐"]
    if phase in {"ready_for_quality_gate", "awaiting_final_video_confirmation"}:
        return ["更换背景音乐", "确认成片"]
    if pending:
        return [pending]
    return []


def _normalize_user_reply(reply: str) -> str:
    return re.sub(r"\s+", " ", reply.strip()).lower().replace("ｂｇｍ", "bgm")


def _parse_voice_selection(reply: str) -> int | None:
    match = re.search(r"(?:声音|voice)\s*(?:选|选择|choose)?\s*([123])", reply)
    if match:
        return int(match.group(1))
    return None


def _parse_plan_revision_request(normalized_reply: str, original_reply: str) -> str | None:
    if re.match(r"^(修改|调整|改)(视频)?策划", normalized_reply):
        return original_reply.strip()
    return None


def _parse_storyboard_revision_request(normalized_reply: str, original_reply: str) -> str | None:
    if re.match(r"^(修改|调整|改)(视频)?分镜", normalized_reply):
        return original_reply.strip()
    return None


def _parse_shot_revision_request(normalized_reply: str, original_reply: str) -> tuple[str, str] | None:
    match = re.match(r"^(修改|调整|改)镜头\s*0?(\d{1,2})", normalized_reply)
    if match:
        return _normalize_shot_id(match.group(2)), original_reply.strip()
    return None


def _parse_shot_retry_confirmation(reply: str) -> str | None:
    match = re.search(r"确认(?:重做|重新生成)?镜头\s*0?(\d{1,2})", reply)
    if match and "重做" in reply:
        return _normalize_shot_id(match.group(1))
    return None


def _parse_shot_retry_submission(reply: str) -> str | None:
    match = re.search(r"提交(?:重做|重新生成)镜头\s*0?(\d{1,2})", reply)
    if match:
        return _normalize_shot_id(match.group(1))
    return None


def _parse_shot_retry_query(reply: str) -> str | None:
    match = re.search(r"(?:查询|继续查询)(?:重做|重新生成)镜头\s*0?(\d{1,2})", reply)
    if match:
        return _normalize_shot_id(match.group(1))
    return None


def _parse_shot_retry_request(reply: str) -> str | None:
    match = re.search(r"(?:重做|重新生成)镜头\s*0?(\d{1,2})", reply)
    if match and not reply.startswith("确认"):
        return _normalize_shot_id(match.group(1))
    return None


def _is_manual_quality_pass_reply(reply: str) -> bool:
    pass_tokens = ["人工音视频检查通过", "人工检查通过", "音视频检查通过", "音画检查通过", "音频画面正常"]
    return any(token in reply for token in pass_tokens)


def _command_check(name: str, command: str, required: bool) -> dict[str, str]:
    if not command.strip():
        return {
            "name": name,
            "status": "missing",
            "severity": "blocking" if required else "warning",
            "message": "未配置命令。",
        }
    command_path = Path(command).expanduser()
    if command_path.is_absolute():
        ok = command_path.exists()
        resolved = str(command_path)
    else:
        found = shutil.which(command)
        ok = bool(found)
        resolved = found or command
    return {
        "name": name,
        "status": "ok" if ok else "not_found",
        "severity": "blocking" if required else "warning",
        "message": f"resolved={resolved}",
    }


def _optional_path_check(name: str, value: str, must_be_dir: bool = False) -> dict[str, str]:
    if not value.strip():
        return {"name": name, "status": "not_configured", "severity": "warning", "message": "未配置，可由人工选择文件。"}
    path = Path(value).expanduser()
    ok = path.is_dir() if must_be_dir else path.exists()
    return {"name": name, "status": "ok" if ok else "not_found", "severity": "warning", "message": str(path)}


def _optional_project_path_check(name: str, value: str, run_dir: Path) -> dict[str, str]:
    if not value.strip():
        return {"name": name, "status": "not_configured", "severity": "warning", "message": "未配置，结尾 logo 将作为警告处理。"}
    path = Path(value).expanduser()
    if not path.is_absolute():
        project_dir = _project_dir_from_run_dir(run_dir)
        path = project_dir / path
    return {"name": name, "status": "ok" if path.exists() else "not_found", "severity": "warning", "message": str(path)}


def _capability_profile_check(profile: dict[str, Any]) -> dict[str, str]:
    min_duration = int(profile.get("min_duration_seconds", 0))
    max_duration = int(profile.get("max_duration_seconds", 0))
    max_total_files = int(profile.get("max_total_files", 0))
    max_images = int(profile.get("max_images", 0))
    max_videos = int(profile.get("max_videos", 0))
    max_audios = int(profile.get("max_audios", 0))
    issues: list[str] = []
    if min_duration > max_duration:
        issues.append(f"min_duration_seconds {min_duration} 大于 max_duration_seconds {max_duration}")
    if max_total_files < max(max_images, max_videos, max_audios):
        issues.append("max_total_files 小于单类素材上限")
    if not str(profile.get("model", "")).strip():
        issues.append("model 为空")
    if not str(profile.get("resolution", "")).strip():
        issues.append("resolution 为空")
    if not str(profile.get("aspect_ratio", "")).strip():
        issues.append("aspect_ratio 为空")
    return {
        "name": "dreamina_capability_profile",
        "status": "invalid" if issues else "ok",
        "severity": "blocking",
        "message": "；".join(issues) if issues else "Seedance 能力配置可用。",
    }


def _resolve_logo_path(value: str, run_dir: Path) -> Path | None:
    if not value.strip():
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return _project_dir_from_run_dir(run_dir) / path


def _project_dir_from_run_dir(run_dir: Path) -> Path:
    try:
        return run_dir.parents[3]
    except IndexError:
        return run_dir


def _dreamina_job_type_for_shot(shot: dict[str, Any]) -> str:
    material_mode = shot.get("material_mode")
    product_visible = bool(shot.get("product_visible"))
    if material_mode == "blocked":
        return "blocked"
    if material_mode == "reuse_video":
        return "reuse_video"
    if material_mode == "reuse_image":
        return "reuse_image"
    if material_mode == "image2video":
        return "image2video"
    if material_mode == "text2video" and not product_visible:
        return "text2video"
    if material_mode == "ai_simulated_scene":
        return "text2video" if not product_visible else "blocked"
    if product_visible and not shot.get("selected_material"):
        return "blocked"
    return "text2video"


def _dreamina_blocked_reason(shot: dict[str, Any], job_type: str) -> str | None:
    if job_type != "blocked":
        return None
    if shot.get("product_visible") and not shot.get("selected_material"):
        return "该镜头展示具体产品，但没有真实产品图片或视频参考。"
    if shot.get("material_mode") == "ai_simulated_scene" and shot.get("product_visible"):
        return "AI 模拟场景不能在无真实产品参考时展示具体产品。"
    return "素材缺失或当前规则不允许生成。"


def _validate_dreamina_job(
    shot: dict[str, Any],
    prompt: dict[str, Any],
    job_type: str,
    blocked_reason: str | None,
    capability_profile: dict[str, Any] | None = None,
    material_limit_blockers: list[str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    profile = _normalize_dreamina_capability_profile(capability_profile or {})
    duration = int(shot.get("duration_seconds", 0))
    min_duration = int(profile["min_duration_seconds"])
    max_duration = int(profile["max_duration_seconds"])
    if blocked_reason:
        blockers.append(blocked_reason)
    blockers.extend(material_limit_blockers or [])
    human_face_risk = str(shot.get("human_face_risk") or "none")
    if human_face_risk == "clear_face":
        blockers.append("素材包含清晰可辨识真人脸部，不能作为真实即梦参考。")
    elif human_face_risk == "unclear":
        warnings.append("素材人脸风险不明确，建议裁切、打码或替换为手部/设备局部素材。")
    if not min_duration <= duration <= max_duration:
        blockers.append(f"镜头时长 {duration} 秒超出 Seedance 能力配置范围 {min_duration}-{max_duration} 秒。")
    if shot.get("product_visible") and job_type == "text2video":
        blockers.append("可见产品镜头不能规划为 text2video。")
    if prompt.get("reference_required") and not prompt.get("reference_material_id"):
        blockers.append("Prompt 要求参考素材，但任务缺少 reference_material_id。")
    if prompt.get("reference_required") and not prompt.get("numbered_reference_label"):
        blockers.append("Prompt 要求参考素材，但缺少 @图片/@视频 编号引用。")
    if prompt.get("reference_required") and not str(prompt.get("reference_usage") or "").strip():
        blockers.append("Prompt 要求参考素材，但缺少素材用途说明。")
    if prompt.get("prompt_standard") not in {"tuolin-industrial-seedance-v1", "tuolin-industrial-seedance-v2"}:
        warnings.append("Prompt 未声明拓霖工业即梦标准。")
    components = prompt.get("prompt_components", {})
    required_components = [
        "timebox",
        "subject",
        "reference_material",
        "time_segments",
        "motion_and_camera",
        "environment",
        "material_texture",
        "product_display_template",
        "safety_and_negative_constraints",
    ]
    missing = [key for key in required_components if not str(components.get(key, "")).strip()]
    if missing:
        blockers.append("Prompt 结构缺少字段：" + ", ".join(missing))
    forbidden = _forbidden_entertainment_terms_in_prompt(prompt.get("prompt", ""))
    if forbidden:
        blockers.append("Prompt 包含不允许的娱乐化表达：" + ", ".join(forbidden))
    prompt_quality_checks = prompt.get("prompt_quality_checks") or _prompt_quality_checks(prompt)
    blockers.extend(str(issue.get("message", "")) for issue in prompt_quality_checks.get("blockers", []))
    warnings.extend(str(issue.get("message", "")) for issue in prompt_quality_checks.get("warnings", []))
    messages = blockers or warnings or ["任务类型、素材引用和 Prompt 结构可执行。"]
    return {
        "status": "blocked" if blockers else "warning" if warnings else "ok",
        "messages": messages,
        "blockers": blockers,
        "warnings": warnings,
    }


def _estimate_dreamina_credits(job_type: str, duration_seconds: int) -> int:
    if job_type in {"reuse_video", "reuse_image", "blocked"}:
        return 0
    unit = max(1, round(duration_seconds / 5))
    if job_type == "image2video":
        return unit * 8
    if job_type == "text2video":
        return unit * 10
    return unit * 10


def _duration_tolerance(duration: int) -> tuple[int, int]:
    if duration == 60:
        return 55, 65
    if duration == 90:
        return 85, 95
    if duration == 120:
        return 115, 125
    raise ValueError("视频时长只支持 60、90 或 120 秒")


def _external_names_from_product(product: dict[str, Any]) -> dict[str, str]:
    aliases = [str(item) for item in product.get("aliases", [])]
    title = str(product.get("title", ""))
    zh = next((item for item in aliases if _contains_cjk(item) and item != INTERNAL_PRODUCT_NAME), "")
    en = next((item for item in aliases if not _contains_cjk(item) and any(ch.isalpha() for ch in item)), "")
    return {"zh": zh or title, "en": en}


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in value)


def _usable_product_knowledge(product: dict[str, Any]) -> list[str]:
    items = []
    body = str(product.get("body_excerpt", "")).strip()
    if body:
        items.append(body)
    aliases = product.get("aliases", [])
    if aliases:
        items.append("知识卡别名/对外名：" + "、".join(str(item) for item in aliases))
    return items[:5]


def _content_asset_summary(card: dict[str, Any]) -> dict[str, Any]:
    frontmatter = card.get("frontmatter", {})
    raw_partitions = card.get("raw_partitions", [])
    files = frontmatter.get("files") or frontmatter.get("file_paths") or frontmatter.get("paths") or raw_partitions
    return {
        "id": card["id"],
        "title": card.get("title", ""),
        "media_types": frontmatter.get("media_types", []),
        "asset_category": frontmatter.get("asset_category", ""),
        "raw_partitions": raw_partitions,
        "files": files,
        "human_face_risk": str(frontmatter.get("human_face_risk") or "none"),
        "usage_note": "内容素材只用于素材选择、画面描述、Prompt 参考和镜头生成约束，不能证明产品事实。",
    }


def _visual_strategy(primary: dict[str, str], supporting: dict[str, str] | None, content_assets: list[dict[str, Any]]) -> dict[str, str]:
    support_text = f"，辅助方向为{supporting['name']}" if supporting else ""
    coverage = "优先使用已整理内容素材" if content_assets else "当前缺少已整理内容素材，后续分镜需谨慎使用 AI 模拟"
    return {
        "summary": f"围绕{primary['name']}组织叙事{support_text}；{coverage}。",
        "material_priority": "真实产品视频 > 真实应用视频 > 真实产品图片转视频 > 真实应用图片转视频 > AI 模拟场景 > 纯文本生成视频",
        "ai_risk_control": "任何展示具体产品的 AI 镜头必须使用真实产品图/视频作参考；模拟场景必须标记为 AI 生成。",
    }


def _direction_quality_profile(primary: dict[str, str]) -> dict[str, str]:
    return CREATIVE_DIRECTION_QUALITY_MATRIX.get(primary["id"], CREATIVE_DIRECTION_QUALITY_MATRIX["product_overview"])


def _production_style_profile(primary: dict[str, str], supporting: dict[str, str] | None) -> dict[str, str]:
    candidate_ids = {primary["id"]}
    if supporting:
        candidate_ids.add(supporting["id"])
    for style_id, profile in INDUSTRIAL_VIDEO_STYLE_MATRIX.items():
        if candidate_ids & set(profile["best_for"]):
            return {
                "id": style_id,
                "name": profile["name"],
                "visual_language": profile["visual_language"],
                "matched_direction_ids": sorted(candidate_ids & set(profile["best_for"])),
            }
    fallback = INDUSTRIAL_VIDEO_STYLE_MATRIX["industrial_professional"]
    return {
        "id": "industrial_professional",
        "name": fallback["name"],
        "visual_language": fallback["visual_language"],
        "matched_direction_ids": [primary["id"]],
    }


def _shot_creative_quality_checks(role: str, primary: dict[str, str], quality: dict[str, str]) -> list[str]:
    checks = []
    if role == "opening_environment":
        checks.append(quality["hook"])
    elif role == "product_detail":
        checks.append(quality["visual_focus"])
    elif role == "closing_cta":
        checks.append(quality["cta_rule"])
    else:
        checks.append(quality["message_focus"])
    if primary["id"] == "inquiry_conversion" and role == "closing_cta":
        checks.append("询盘转化型结尾必须包含明确 CTA。")
    if primary["id"] == "performance_test":
        checks.append("性能测试型不得把演示视觉表述为正式检测结果。")
    if primary["id"] == "real_case_study":
        checks.append("真实案例型必须基于可公开真实案例素材；缺失时应降级为应用示意。")
    return checks


def _validate_shot_design(shot: dict[str, Any]) -> dict[str, Any]:
    messages: list[str] = []
    blockers: list[str] = []
    duration = int(shot.get("duration_seconds", 0))
    if not 4 <= duration <= 15:
        blockers.append("镜头时长必须在 4-15 秒之间。")
    if shot.get("product_visible") and shot.get("material_mode") == "text2video":
        blockers.append("展示具体产品的镜头不能使用纯 text2video。")
    if shot.get("product_visible") and shot.get("ai_generated") and not shot.get("selected_material"):
        blockers.append("展示具体产品的 AI 镜头必须有真实产品参考素材。")
    if shot.get("material_mode") == "blocked":
        blockers.append("当前镜头素材缺失，必须补充素材或改分镜。")
    if shot.get("human_face_risk") == "clear_face":
        blockers.append("素材包含清晰可辨识真人脸部，不能作为即梦参考。")
    if not blockers:
        messages.append("镜头可进入即梦任务规划。")
    else:
        messages.extend(blockers)
    return {
        "status": "blocked" if blockers else "ok",
        "messages": messages,
        "blockers": blockers,
    }


def _music_brief(primary: dict[str, str], language: str) -> dict[str, str]:
    if primary["id"] in {"performance_test", "technical_education"}:
        mood = "克制、专业、技术感"
        pace = "中等偏快"
    elif primary["id"] in {"inquiry_conversion", "procurement_guide"}:
        mood = "可信、稳重、商务感"
        pace = "中等"
    else:
        mood = "现代工业、干净、可信"
        pace = "短视频中等节奏"
    return {
        "mood": mood,
        "pace": pace,
        "intensity": "背景存在感适中，不压过旁白",
        "language_context": language,
        "license_requirement": "必须可商用，记录来源和授权元数据，不使用 TikTok 热门歌曲。",
    }


def _load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        raise ValueError(f"找不到视频创作 workflow_state.json：{state_path}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def _load_json_file(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"找不到 {label}：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_context_for_state(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    context_path_value = state.get("files", {}).get("context")
    if context_path_value:
        context_path = Path(context_path_value)
    else:
        generated_dir = run_dir.parents[2]
        context_path = generated_dir / "agent-interface" / "contexts" / f"{state['context']['context_id']}.json"
    if not context_path.exists():
        raise ValueError(f"找不到 video_creation 上下文文件：{context_path}")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    if context.get("task_type") != "video_creation":
        raise ValueError("当前上下文不是 video_creation。")
    return context


def _append_status_history(state: dict[str, Any], status: str, timestamp: str) -> None:
    state.setdefault("status_history", []).append({"status": status, "at": timestamp})


def _append_change(run_dir: Path, timestamp: str, message: str) -> None:
    change_log = run_dir / "change_log.md"
    with change_log.open("a", encoding="utf-8") as handle:
        handle.write(f"- {timestamp}: {message}\n")


def _clear_downstream_confirmations(state: dict[str, Any], after: str) -> None:
    order = [
        "video_plan",
        "storyboard",
        "narration_script",
        "voice",
        "narration",
        "dreamina_generation",
        "shots",
        "final_video",
    ]
    if after not in order:
        return
    for key in order[order.index(after) + 1 :]:
        state["confirmations"][key] = False


def _clear_downstream_file_references(state: dict[str, Any], after: str) -> None:
    order = [
        "video_plan",
        "storyboard",
        "narration_script",
        "voice",
        "narration",
        "dreamina_generation",
        "shots",
        "final_video",
    ]
    keys_by_stage = {
        "video_plan": {"video_plan_md", "video_plan_json"},
        "storyboard": {"storyboard_md", "storyboard_json", "prompts_md", "prompts_json"},
        "narration_script": {"narration_script_md", "narration_script_json"},
        "voice": {"voice_samples_md", "voice_samples_json"},
        "narration": {"narration_audio", "narration_timing", "narration_manifest"},
        "dreamina_generation": {
            "dreamina_jobs_md",
            "dreamina_jobs_json",
            "dreamina_submission_md",
            "dreamina_submission_json",
            "dreamina_results_md",
            "dreamina_results_json",
        },
        "shots": {
            "shot_preview_manifest_json",
            "shot_preview_manifest_md",
            "shot_preview_mp4",
            "final_subtitles_srt",
            "bgm_license_json",
            "bgm_brief_md",
            "final_preview_manifest_json",
            "final_preview_manifest_md",
            "final_preview_mp4",
            "quality_report_json",
            "quality_report_md",
            "manual_quality_check_json",
            "final_video_mp4",
        },
        "final_video": {"final_video_mp4"},
    }
    if after not in order:
        return
    files = state.setdefault("files", {})
    invalidated = state.setdefault("invalidated_file_references", [])
    for stage in order[order.index(after) + 1 :]:
        for key in keys_by_stage.get(stage, set()):
            if key in files:
                invalidated.append({"key": key, "path": files[key], "invalidated_after": after})
                files.pop(key, None)


def _clear_transient_review_state(state: dict[str, Any]) -> None:
    for key in [
        "dreamina_authorization",
        "pending_shot_retry",
        "quality_gate",
        "manual_quality_check",
        "final_video",
    ]:
        state.pop(key, None)


def _build_revision_record(scope: str, change_request: str, timestamp: str) -> dict[str, str]:
    return {
        "scope": scope,
        "requested_at": timestamp,
        "request": change_request.strip(),
        "status": "pending_user_confirmation",
    }


def _append_revision_to_markdown(path: Path, title: str, revision: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n"
            f"## {title}\n\n"
            f"- 时间：{revision['requested_at']}\n"
            f"- 范围：{revision['scope']}\n"
            f"- 要求：{revision['request']}\n"
            "- 状态：待重新确认\n"
        )


def _timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d_%H%M%S")


def _display_path(project_dir: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return str(path)
