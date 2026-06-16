from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .card_validator import parse_frontmatter
from .project_layout import ProjectPaths


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
        pending_material_count = 0

    recommended_next_action = recommend_next_action(
        status=status,
        pending_material_count=pending_material_count,
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
    recognized_unapplied_count: int,
    review_item_count: int,
) -> str:
    if status == "needs_update":
        return "update_first"
    if status in {"not_started", "incomplete_materials"} and pending_material_count == 0:
        return "prepare_raw"
    if recognized_unapplied_count > 0:
        return "organize_usable"
    if review_item_count > 0:
        return "review_required"
    if pending_material_count > 0:
        return "continue_reading"
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
