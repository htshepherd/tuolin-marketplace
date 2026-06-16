from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


KNOWLEDGE_DIRS = [
    "产品",
    "应用场景",
    "标准法规",
    "公司能力",
    "市场情报",
    "销售物料",
    "客户问题",
    "内容素材",
    "证据",
    "复核项",
]

GENERATED_DIRS = [
    "indexes",
    "agent-interface",
    "agent-interface/cards",
    "agent-interface/contexts",
    "reports",
    "cache",
    "cache/pdf-markdown",
    "cache/video-frames",
]

RAW_TEMPLATE_DIRS = [
    "00_知识库核心资料/01_产品核心资料",
    "00_知识库核心资料/02_产品对比资料",
    "00_知识库核心资料/03_客服常用回答",
    "00_知识库核心资料/04_公共内容素材",
    "01_产品/01_陶瓷纤维隔热带/01_检测报告与认证",
    "01_产品/01_陶瓷纤维隔热带/02_产品图片",
    "01_产品/01_陶瓷纤维隔热带/03_产品视频",
    "01_产品/01_陶瓷纤维隔热带/04_应用场景素材",
    "01_产品/01_陶瓷纤维隔热带/05_测试验证素材",
    "01_产品/02_石英纤维隔热带/01_检测报告与认证",
    "01_产品/02_石英纤维隔热带/02_产品图片",
    "01_产品/02_石英纤维隔热带/03_产品视频",
    "01_产品/02_石英纤维隔热带/04_应用场景素材",
    "01_产品/02_石英纤维隔热带/05_测试验证素材",
    "01_产品/03_玄武岩纤维隔热带/01_检测报告与认证",
    "01_产品/03_玄武岩纤维隔热带/02_产品图片",
    "01_产品/03_玄武岩纤维隔热带/03_产品视频",
    "01_产品/03_玄武岩纤维隔热带/04_应用场景素材",
    "01_产品/03_玄武岩纤维隔热带/05_测试验证素材",
    "01_产品/04_高硅氧纤维隔热带_有背胶/01_检测报告与认证",
    "01_产品/04_高硅氧纤维隔热带_有背胶/02_产品图片",
    "01_产品/04_高硅氧纤维隔热带_有背胶/03_产品视频",
    "01_产品/04_高硅氧纤维隔热带_有背胶/04_应用场景素材",
    "01_产品/04_高硅氧纤维隔热带_有背胶/05_测试验证素材",
    "01_产品/05_高硅氧纤维隔热带_无背胶/01_检测报告与认证",
    "01_产品/05_高硅氧纤维隔热带_无背胶/02_产品图片",
    "01_产品/05_高硅氧纤维隔热带_无背胶/03_产品视频",
    "01_产品/05_高硅氧纤维隔热带_无背胶/04_应用场景素材",
    "01_产品/05_高硅氧纤维隔热带_无背胶/05_测试验证素材",
    "02_公司能力/01_公司介绍",
    "02_公司能力/02_生产车间/陶瓷纤维生产车间",
    "02_公司能力/02_生产车间/纺纱",
    "02_公司能力/02_生产车间/织带",
    "02_公司能力/02_生产车间/织布",
    "02_公司能力/02_生产车间/混棉",
    "02_公司能力/02_生产车间/包装",
    "02_公司能力/03_企业资质",
    "02_公司能力/04_实验室",
    "03_标准法规/01_中国标准",
    "03_标准法规/02_国际标准",
    "04_市场情报/01_市场现状与平台调研",
    "04_市场情报/02_竞争对手",
    "04_市场情报/03_潜在客户/00_客户名录",
    "04_市场情报/04_网页价格资料库",
    "04_市场情报/05_历史调研资料",
    "05_销售物料/01_Datasheet",
    "05_销售物料/02_报价资料/报价原则",
    "05_销售物料/02_报价资料/报价单",
    "05_销售物料/03_开发信与跟进",
    "05_销售物料/04_产品手册与说明文档",
    "05_销售物料/05_多语言销售资料/英文",
    "05_销售物料/05_多语言销售资料/日文",
    "05_销售物料/05_多语言销售资料/中英日对照",
    "06_客户问题与客服反馈/01_原始客服记录/抖店2023",
    "06_客户问题与客服反馈/01_原始客服记录/淘宝2024",
    "06_客户问题与客服反馈/02_已归类问题素材/产品规格与配件",
    "06_客户问题与客服反馈/02_已归类问题素材/材料对比与选型",
    "06_客户问题与客服反馈/02_已归类问题素材/冒烟异味",
    "06_客户问题与客服反馈/02_已归类问题素材/扎手掉毛",
    "06_客户问题与客服反馈/02_已归类问题素材/安装长度",
    "06_客户问题与客服反馈/02_已归类问题素材/耐温与安全",
    "06_客户问题与客服反馈/02_已归类问题素材/防锈腐蚀",
    "06_客户问题与客服反馈/02_已归类问题素材/购买与本地自取",
    "90_待迁移素材暂存区/01_待归入产品素材",
    "90_待迁移素材暂存区/02_待归入公共内容素材",
    "90_待迁移素材暂存区/03_待归入公司能力素材",
    "90_待迁移素材暂存区/04_历史成片与项目文件",
    "90_待迁移素材暂存区/90_待人工判定",
]


@dataclass(frozen=True)
class ProjectPaths:
    project_dir: Path
    raw_dir: Path
    knowledge_dir: Path
    generated_dir: Path


def load_config(config_path: Path | None) -> dict[str, Any]:
    if config_path is None or not config_path.exists():
        return {
            "raw_dir": "raw",
            "knowledge_dir": "knowledge/okf",
            "generated_dir": "generated",
        }
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_paths(project_dir: Path, config: dict[str, Any]) -> ProjectPaths:
    root = project_dir.expanduser().resolve()
    raw_dir = _resolve_configured_path(root, config.get("raw_dir", "raw"))
    knowledge_dir = _resolve_configured_path(root, config.get("knowledge_dir", "knowledge/okf"))
    generated_dir = _resolve_configured_path(root, config.get("generated_dir", "generated"))
    paths = ProjectPaths(
        project_dir=root,
        raw_dir=raw_dir,
        knowledge_dir=knowledge_dir,
        generated_dir=generated_dir,
    )
    validate_path_boundaries(paths)
    return paths


def _resolve_configured_path(project_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_dir / path
    return path.resolve()


def validate_path_boundaries(paths: ProjectPaths) -> None:
    pairs = [
        ("raw_dir", paths.raw_dir, "knowledge_dir", paths.knowledge_dir),
        ("raw_dir", paths.raw_dir, "generated_dir", paths.generated_dir),
        ("knowledge_dir", paths.knowledge_dir, "generated_dir", paths.generated_dir),
    ]
    for left_name, left, right_name, right in pairs:
        if left == right:
            raise ValueError(f"{left_name} and {right_name} must not point to the same directory")
        if _is_relative_to(left, right):
            raise ValueError(f"{left_name} must not be inside {right_name}")
        if _is_relative_to(right, left):
            raise ValueError(f"{right_name} must not be inside {left_name}")


def initialize_project(paths: ProjectPaths, include_raw_template: bool = True) -> list[Path]:
    created: list[Path] = []
    created.extend(_ensure_profile_config(paths.project_dir / "config" / "tuolin-okf-profile"))
    if include_raw_template:
        for relative in RAW_TEMPLATE_DIRS:
            created.extend(_ensure_dir(paths.raw_dir / relative))

    for relative in KNOWLEDGE_DIRS:
        created.extend(_ensure_dir(paths.knowledge_dir / relative))
    created.extend(_ensure_file(paths.knowledge_dir / "首页.md", "# 拓霖知识库\n\n这是知识卡片导航页。\n"))
    created.extend(_ensure_file(paths.knowledge_dir / "变更记录.md", "# 变更记录\n\n"))

    for relative in GENERATED_DIRS:
        created.extend(_ensure_dir(paths.generated_dir / relative))
    return created


def inspect_project(paths: ProjectPaths) -> dict[str, Any]:
    return {
        "project_dir": str(paths.project_dir),
        "raw_dir": str(paths.raw_dir),
        "knowledge_dir": str(paths.knowledge_dir),
        "generated_dir": str(paths.generated_dir),
        "raw_exists": paths.raw_dir.exists(),
        "knowledge_exists": paths.knowledge_dir.exists(),
        "generated_exists": paths.generated_dir.exists(),
        "knowledge_navigation_files": {
            "首页.md": (paths.knowledge_dir / "首页.md").exists(),
            "变更记录.md": (paths.knowledge_dir / "变更记录.md").exists(),
        },
        "profile_config": {
            "profile.yaml": (paths.project_dir / "config" / "tuolin-okf-profile" / "profile.yaml").exists(),
            "card_templates": {
                name: (
                    paths.project_dir
                    / "config"
                    / "tuolin-okf-profile"
                    / "card-templates"
                    / f"{name}.yaml"
                ).exists()
                for name in [
                    "product",
                    "application_scenario",
                    "standard",
                    "company_capability",
                    "market_intelligence",
                    "sales_material",
                    "customer_question",
                    "content_asset",
                    "evidence",
                    "review_item",
                ]
            },
        },
        "knowledge_card_dirs": {
            name: (paths.knowledge_dir / name).is_dir() for name in KNOWLEDGE_DIRS
        },
        "generated_dirs": {
            name: (paths.generated_dir / name).is_dir() for name in GENERATED_DIRS
        },
    }


def _ensure_dir(path: Path) -> list[Path]:
    if path.exists():
        return []
    path.mkdir(parents=True, exist_ok=True)
    return [path]


def _ensure_file(path: Path, content: str) -> list[Path]:
    if path.exists():
        return []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return [path]


def _ensure_profile_config(target_dir: Path) -> list[Path]:
    source_dir = Path(__file__).resolve().parents[2] / "config" / "tuolin-okf-profile"
    if not source_dir.exists():
        return []

    created: list[Path] = []
    for source_path in sorted(source_dir.rglob("*")):
        relative = source_path.relative_to(source_dir)
        target_path = target_dir / relative
        if source_path.is_dir():
            created.extend(_ensure_dir(target_path))
            continue
        if target_path.exists():
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        created.append(target_path)
    return created


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
