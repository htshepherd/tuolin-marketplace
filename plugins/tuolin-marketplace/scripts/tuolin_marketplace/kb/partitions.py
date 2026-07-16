from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .card_validator import parse_frontmatter
from ..shared.project_layout import ProjectPaths


PARTITION_STATUSES = {
    "not_started",
    "ready",
    "needs_update",
    "pending_review",
    "incomplete_materials",
}

RECOMMENDED_NEXT_ACTIONS = {
    "update_first",
    "organize_usable",
    "continue_reading",
    "review_required",
    "use_existing",
    "prepare_raw",
}

IGNORED_FILE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
PDF_SUFFIXES = {".pdf"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
PRODUCT_MATERIAL_SUBFOLDERS = (
    "01_检测报告与认证",
    "02_产品图片",
    "03_产品视频",
    "04_应用场景素材",
    "05_测试验证素材",
)


@dataclass(frozen=True)
class ProductMaterialProgress:
    name: str
    raw_path: str
    status: str
    total_file_count: int
    registered_file_count: int
    pending_registration_count: int
    pending_processing_count: int
    pdf_progress: str
    video_progress: str


@dataclass(frozen=True)
class PartitionDefinition:
    name: str
    slug: str
    partition_type: str
    primary_raw_path: str
    fingerprint_raw_paths: tuple[str, ...]
    generates_official_cards: bool = True


@dataclass(frozen=True)
class RawFingerprint:
    fingerprint: str
    file_count: int
    latest_mtime: float | None


@dataclass(frozen=True)
class PartitionSummary:
    name: str
    slug: str
    partition_type: str
    raw_path: str
    status: str
    pending_material_count: int
    pending_processing_count: int
    pdf_total_count: int
    pdf_processed_count: int
    pdf_pending_count: int
    video_total_count: int
    video_processed_count: int
    video_pending_count: int
    product_material_status: str
    product_pending_subfolder_count: int
    product_pending_registration_count: int
    product_material_progress: tuple[ProductMaterialProgress, ...]
    recognized_unapplied_count: int
    review_item_count: int
    last_raw_changed_at: str | None
    last_organized_at: str | None
    recommended_next_action: str
    raw_file_count: int
    fingerprint: str | None


PARTITIONS: tuple[PartitionDefinition, ...] = (
    PartitionDefinition(
        name="陶瓷纤维隔热带",
        slug="ceramic_fiber_tape",
        partition_type="product",
        primary_raw_path="01_产品/01_陶瓷纤维隔热带",
        fingerprint_raw_paths=("00_知识库核心资料", "01_产品/01_陶瓷纤维隔热带"),
    ),
    PartitionDefinition(
        name="石英纤维隔热带",
        slug="quartz_fiber_tape",
        partition_type="product",
        primary_raw_path="01_产品/02_石英纤维隔热带",
        fingerprint_raw_paths=("00_知识库核心资料", "01_产品/02_石英纤维隔热带"),
    ),
    PartitionDefinition(
        name="玄武岩纤维隔热带",
        slug="basalt_fiber_tape",
        partition_type="product",
        primary_raw_path="01_产品/03_玄武岩纤维隔热带",
        fingerprint_raw_paths=("00_知识库核心资料", "01_产品/03_玄武岩纤维隔热带"),
    ),
    PartitionDefinition(
        name="高硅氧纤维隔热带_有背胶",
        slug="high_silica_fiber_tape_adhesive",
        partition_type="product",
        primary_raw_path="01_产品/04_高硅氧纤维隔热带_有背胶",
        fingerprint_raw_paths=("00_知识库核心资料", "01_产品/04_高硅氧纤维隔热带_有背胶"),
    ),
    PartitionDefinition(
        name="高硅氧纤维隔热带_无背胶",
        slug="high_silica_fiber_tape_non_adhesive",
        partition_type="product",
        primary_raw_path="01_产品/05_高硅氧纤维隔热带_无背胶",
        fingerprint_raw_paths=("00_知识库核心资料", "01_产品/05_高硅氧纤维隔热带_无背胶"),
    ),
    PartitionDefinition(
        name="公司能力",
        slug="company_capability",
        partition_type="domain",
        primary_raw_path="02_公司能力",
        fingerprint_raw_paths=("02_公司能力",),
    ),
    PartitionDefinition(
        name="标准法规",
        slug="standards",
        partition_type="domain",
        primary_raw_path="03_标准法规",
        fingerprint_raw_paths=("03_标准法规",),
    ),
    PartitionDefinition(
        name="市场情报",
        slug="market_intelligence",
        partition_type="domain",
        primary_raw_path="04_市场情报",
        fingerprint_raw_paths=("04_市场情报",),
    ),
    PartitionDefinition(
        name="销售物料",
        slug="sales_material",
        partition_type="domain",
        primary_raw_path="05_销售物料",
        fingerprint_raw_paths=("05_销售物料",),
    ),
    PartitionDefinition(
        name="客户问题/客服反馈",
        slug="customer_questions",
        partition_type="domain",
        primary_raw_path="06_客户问题与客服反馈",
        fingerprint_raw_paths=("06_客户问题与客服反馈",),
    ),
    PartitionDefinition(
        name="待迁移素材暂存区",
        slug="migration_buffer",
        partition_type="migration_buffer",
        primary_raw_path="90_待迁移素材暂存区",
        fingerprint_raw_paths=("90_待迁移素材暂存区",),
        generates_official_cards=False,
    ),
)


def scan_all_partitions(paths: ProjectPaths) -> list[PartitionSummary]:
    return [scan_partition(paths, definition) for definition in PARTITIONS]


def scan_partition(paths: ProjectPaths, definition: PartitionDefinition) -> PartitionSummary:
    primary_raw_dir = paths.raw_dir / definition.primary_raw_path
    primary_files = list(_iter_files(primary_raw_dir)) if primary_raw_dir.exists() else []
    fingerprint = build_fingerprint(paths, definition) if primary_raw_dir.exists() else None
    previous = load_partition_snapshot(paths, definition.slug)
    processing = _processing_counts(paths, primary_files)
    product_progress = _product_material_progress(paths, definition) if definition.partition_type == "product" else ()
    product_pending_registration_count = sum(item.pending_registration_count for item in product_progress)
    product_pending_subfolder_count = sum(1 for item in product_progress if item.status != "complete")
    product_material_status = _product_material_status(product_progress)

    recognized_unapplied_count = _count_json_files(paths.generated_dir / "cache" / "recognized-unapplied" / definition.slug)
    review_item_count = _count_json_files(paths.generated_dir / "cache" / "review-items" / definition.slug)
    review_item_count += _count_open_review_markdown_files(paths.knowledge_dir / "复核项" / definition.slug)

    if not primary_raw_dir.exists():
        status = "not_started"
        pending_material_count = 0
    elif not primary_files:
        status = "incomplete_materials"
        pending_material_count = 0
    elif previous is None:
        status = "not_started"
        pending_material_count = len(primary_files)
    elif fingerprint and previous.get("fingerprint") != fingerprint.fingerprint:
        status = "needs_update"
        pending_material_count = len(primary_files)
    elif review_item_count > 0:
        status = "pending_review"
        pending_material_count = 0
    else:
        status = "ready"
        pending_material_count = product_pending_registration_count

    recommended_next_action = recommend_next_action(
        status=status,
        pending_material_count=pending_material_count,
        pending_processing_count=processing["pending_processing_count"],
        product_pending_subfolder_count=product_pending_subfolder_count,
        recognized_unapplied_count=recognized_unapplied_count,
        review_item_count=review_item_count,
    )

    last_organized_at = previous.get("organized_at") if previous else None
    return PartitionSummary(
        name=definition.name,
        slug=definition.slug,
        partition_type=definition.partition_type,
        raw_path=str(primary_raw_dir),
        status=status,
        pending_material_count=pending_material_count,
        pending_processing_count=processing["pending_processing_count"],
        pdf_total_count=processing["pdf_total_count"],
        pdf_processed_count=processing["pdf_processed_count"],
        pdf_pending_count=processing["pdf_pending_count"],
        video_total_count=processing["video_total_count"],
        video_processed_count=processing["video_processed_count"],
        video_pending_count=processing["video_pending_count"],
        product_material_status=product_material_status,
        product_pending_subfolder_count=product_pending_subfolder_count,
        product_pending_registration_count=product_pending_registration_count,
        product_material_progress=product_progress,
        recognized_unapplied_count=recognized_unapplied_count,
        review_item_count=review_item_count,
        last_raw_changed_at=_format_timestamp(fingerprint.latest_mtime) if fingerprint else None,
        last_organized_at=last_organized_at,
        recommended_next_action=recommended_next_action,
        raw_file_count=len(primary_files),
        fingerprint=fingerprint.fingerprint if fingerprint else None,
    )


def recommend_next_action(
    status: str,
    pending_material_count: int,
    recognized_unapplied_count: int = 0,
    review_item_count: int = 0,
    pending_processing_count: int = 0,
    product_pending_subfolder_count: int = 0,
) -> str:
    if status == "needs_update":
        return "update_first"
    if status in {"not_started", "incomplete_materials"} and pending_material_count == 0:
        return "prepare_raw"
    if recognized_unapplied_count > 0:
        return "organize_usable"
    if review_item_count > 0:
        return "review_required"
    if pending_processing_count > 0:
        return "continue_reading"
    if pending_material_count > 0:
        return "continue_reading"
    if product_pending_subfolder_count > 0:
        return "prepare_raw"
    if status == "ready":
        return "use_existing"
    return "prepare_raw"


def mark_partition_organized(paths: ProjectPaths, definition: PartitionDefinition) -> Path:
    fingerprint = build_fingerprint(paths, definition)
    snapshot = {
        "name": definition.name,
        "slug": definition.slug,
        "fingerprint": fingerprint.fingerprint,
        "file_count": fingerprint.file_count,
        "latest_mtime": fingerprint.latest_mtime,
        "organized_at": datetime.now(timezone.utc).isoformat(),
    }
    path = partition_snapshot_path(paths, definition.slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_partition_snapshot(paths: ProjectPaths, slug: str) -> dict | None:
    path = partition_snapshot_path(paths, slug)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def partition_snapshot_path(paths: ProjectPaths, slug: str) -> Path:
    return paths.generated_dir / "cache" / "partition-fingerprints" / f"{slug}.json"


def build_fingerprint(paths: ProjectPaths, definition: PartitionDefinition) -> RawFingerprint:
    hasher = hashlib.sha256()
    file_count = 0
    latest_mtime: float | None = None
    for file_path in _iter_fingerprint_files(paths, definition):
        relative = file_path.relative_to(paths.raw_dir).as_posix()
        stat = file_path.stat()
        hasher.update(relative.encode("utf-8"))
        hasher.update(str(stat.st_size).encode("ascii"))
        hasher.update(str(stat.st_mtime_ns).encode("ascii"))
        file_count += 1
        latest_mtime = stat.st_mtime if latest_mtime is None else max(latest_mtime, stat.st_mtime)
    return RawFingerprint(fingerprint=hasher.hexdigest(), file_count=file_count, latest_mtime=latest_mtime)


def find_partition(query: str) -> PartitionDefinition | None:
    normalized = query.strip()
    for definition in PARTITIONS:
        if normalized in {definition.name, definition.slug}:
            return definition
    if normalized == "高硅氧纤维隔热带":
        return None
    return None


def summaries_to_json(summaries: Iterable[PartitionSummary]) -> list[dict]:
    return [asdict(summary) for summary in summaries]


def _iter_fingerprint_files(paths: ProjectPaths, definition: PartitionDefinition) -> Iterable[Path]:
    for relative_dir in definition.fingerprint_raw_paths:
        yield from _iter_files(paths.raw_dir / relative_dir)


def _iter_files(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        return
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name not in IGNORED_FILE_NAMES:
            yield path


def _processing_counts(paths: ProjectPaths, primary_files: list[Path]) -> dict[str, int]:
    pdf_files = [path for path in primary_files if path.suffix.lower() in PDF_SUFFIXES]
    video_files = [path for path in primary_files if path.suffix.lower() in VIDEO_SUFFIXES]
    pdf_processed = sum(1 for path in pdf_files if _pdf_text_available(paths, path))
    video_processed = sum(1 for path in video_files if _valid_video_profile_available(paths, path))
    pdf_pending = len(pdf_files) - pdf_processed
    video_pending = len(video_files) - video_processed
    return {
        "pending_processing_count": pdf_pending + video_pending,
        "pdf_total_count": len(pdf_files),
        "pdf_processed_count": pdf_processed,
        "pdf_pending_count": pdf_pending,
        "video_total_count": len(video_files),
        "video_processed_count": video_processed,
        "video_pending_count": video_pending,
    }


def _product_material_progress(
    paths: ProjectPaths,
    definition: PartitionDefinition,
) -> tuple[ProductMaterialProgress, ...]:
    product_dir = paths.raw_dir / definition.primary_raw_path
    registered_sources = _registered_source_paths(paths, definition)
    progress: list[ProductMaterialProgress] = []
    for subfolder in PRODUCT_MATERIAL_SUBFOLDERS:
        subfolder_dir = product_dir / subfolder
        files = list(_iter_files(subfolder_dir)) if subfolder_dir.exists() else []
        processing = _processing_counts(paths, files)
        registered_count = sum(1 for path in files if _raw_relative(path, paths) in registered_sources)
        pending_registration_count = len(files) - registered_count
        if not files:
            status = "not_started"
        elif pending_registration_count > 0 or processing["pending_processing_count"] > 0:
            status = "in_progress"
        else:
            status = "complete"
        progress.append(
            ProductMaterialProgress(
                name=subfolder,
                raw_path=str(subfolder_dir),
                status=status,
                total_file_count=len(files),
                registered_file_count=registered_count,
                pending_registration_count=pending_registration_count,
                pending_processing_count=processing["pending_processing_count"],
                pdf_progress=f"{processing['pdf_processed_count']}/{processing['pdf_total_count']}",
                video_progress=f"{processing['video_processed_count']}/{processing['video_total_count']}",
            )
        )
    return tuple(progress)


def _product_material_status(progress: tuple[ProductMaterialProgress, ...]) -> str:
    if not progress:
        return "not_applicable"
    if all(item.status == "complete" for item in progress):
        return "complete"
    if any(item.total_file_count > 0 for item in progress):
        return "in_progress"
    return "not_started"


def _registered_source_paths(paths: ProjectPaths, definition: PartitionDefinition) -> set[str]:
    evidence_dir = paths.knowledge_dir / "证据" / definition.slug
    if not evidence_dir.exists():
        return set()
    sources: set[str] = set()
    for card_path in evidence_dir.rglob("*.md"):
        if not card_path.is_file():
            continue
        try:
            frontmatter = parse_frontmatter(card_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for source_path in frontmatter.get("source_paths", []):
            if isinstance(source_path, str) and source_path.startswith("raw/"):
                sources.add(source_path[4:])
    return sources


def _raw_relative(path: Path, paths: ProjectPaths) -> str:
    try:
        return path.relative_to(paths.raw_dir).as_posix()
    except ValueError:
        return path.resolve().relative_to(paths.raw_dir.resolve()).as_posix()


def _pdf_text_available(paths: ProjectPaths, pdf_path: Path) -> bool:
    if pdf_path.with_suffix(".md").exists():
        return True
    try:
        relative = pdf_path.resolve().relative_to(paths.raw_dir).with_suffix("")
    except ValueError:
        return False
    cache_dir = paths.generated_dir / "cache" / "pdf-markdown" / relative
    return cache_dir.exists() and any(path.is_file() and path.suffix.lower() == ".md" for path in cache_dir.rglob("*"))


def _valid_video_profile_available(paths: ProjectPaths, video_path: Path) -> bool:
    try:
        relative = video_path.resolve().relative_to(paths.raw_dir).as_posix()
    except ValueError:
        return False
    registry_path = paths.generated_dir / "cache" / "video-assets" / "registry.json"
    if not registry_path.is_file():
        return False
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    source_fingerprint = _file_sha256(video_path)
    asset = next(
        (
            item
            for item in registry.get("assets", [])
            if item.get("source_relative_path") == relative
            and item.get("source_fingerprint") == source_fingerprint
        ),
        None,
    )
    if asset is None:
        return False
    product_id = str(asset.get("product_id", ""))
    if "/" not in product_id:
        return False
    product_slug = product_id.split("/", 1)[1]
    asset_id = str(asset.get("asset_id", ""))
    profile_dir = paths.knowledge_dir / "视频档案" / product_slug
    markdown_path = profile_dir / f"{asset_id}.md"
    structured_path = profile_dir / f"{asset_id}.json"
    if not markdown_path.is_file() or not structured_path.is_file():
        return False
    try:
        profile = json.loads(structured_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return (
        profile.get("video_asset_id") == asset_id
        and profile.get("source_revision") == source_fingerprint
        and profile.get("processing_state") == "valid"
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_json_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.glob("*.json") if path.is_file())


def _count_open_review_markdown_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    count = 0
    for path in directory.glob("*.md"):
        if not path.is_file():
            continue
        try:
            frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
        except ValueError:
            count += 1
            continue
        if frontmatter.get("status") != "archived":
            count += 1
    return count


def _format_timestamp(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
