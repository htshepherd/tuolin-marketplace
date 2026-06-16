from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.card_validator import validate_card_file
from scripts.tuolin_marketplace.partition_organizer import organize_partition
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class PartitionOrganizerTests(unittest.TestCase):
    def test_all_product_partitions_generate_separate_product_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            product_dirs = {
                "陶瓷纤维隔热带": "01_产品/01_陶瓷纤维隔热带/01_检测报告与认证/report.pdf",
                "石英纤维隔热带": "01_产品/02_石英纤维隔热带/01_检测报告与认证/report.pdf",
                "玄武岩纤维隔热带": "01_产品/03_玄武岩纤维隔热带/01_检测报告与认证/report.pdf",
                "高硅氧纤维隔热带_有背胶": "01_产品/04_高硅氧纤维隔热带_有背胶/01_检测报告与认证/report.pdf",
                "高硅氧纤维隔热带_无背胶": "01_产品/05_高硅氧纤维隔热带_无背胶/01_检测报告与认证/report.pdf",
            }
            for product_name, relative in product_dirs.items():
                (paths.raw_dir / relative).write_text("fake report", encoding="utf-8")
                organize_partition(paths, product_name)

            product_cards = sorted(path.name for path in (paths.knowledge_dir / "产品").glob("*.md"))
            self.assertEqual(
                product_cards,
                [
                    "玄武岩纤维隔热带.md",
                    "石英纤维隔热带.md",
                    "陶瓷纤维隔热带.md",
                    "高硅氧纤维隔热带_无背胶.md",
                    "高硅氧纤维隔热带_有背胶.md",
                ],
            )

    def test_domain_partitions_generate_expected_card_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixtures = {
                "公司能力": "02_公司能力/01_公司介绍/company.md",
                "标准法规": "03_标准法规/01_中国标准/gb_t_3003.pdf",
                "市场情报": "04_市场情报/02_竞争对手/BrandA/price.png",
                "销售物料": "05_销售物料/01_Datasheet/石英_datasheet.md",
                "客户问题/客服反馈": "06_客户问题与客服反馈/02_已归类问题素材/冒烟异味/石英冒烟.md",
            }
            for partition, relative in fixtures.items():
                (paths.raw_dir / relative).parent.mkdir(parents=True, exist_ok=True)
                (paths.raw_dir / relative).write_text("fixture", encoding="utf-8")
                organize_partition(paths, partition)

            self.assertTrue(list((paths.knowledge_dir / "公司能力").glob("*.md")))
            self.assertTrue(list((paths.knowledge_dir / "标准法规").glob("*.md")))
            self.assertTrue(list((paths.knowledge_dir / "市场情报").glob("*.md")))
            self.assertTrue(list((paths.knowledge_dir / "销售物料").glob("*.md")))
            self.assertTrue(list((paths.knowledge_dir / "客户问题").glob("*.md")))

            invalid = [path for path in paths.knowledge_dir.rglob("*.md") if not validate_card_file(path).valid]
            self.assertEqual(invalid, [])

            cards = json.loads((paths.generated_dir / "indexes" / "cards.json").read_text(encoding="utf-8"))
            card_types = {card["type"] for card in cards}
            self.assertTrue(
                {
                    "company_capability",
                    "standard",
                    "market_intelligence",
                    "sales_material",
                    "customer_question",
                    "evidence",
                    "review_item",
                }.issubset(card_types)
            )

    def test_ten_card_types_can_be_generated_from_sample_materials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixtures = {
                "石英纤维隔热带": [
                    "01_产品/02_石英纤维隔热带/01_检测报告与认证/report.pdf",
                    "01_产品/02_石英纤维隔热带/02_产品图片/product.jpg",
                    "01_产品/02_石英纤维隔热带/04_应用场景素材/scene.png",
                ],
                "公司能力": ["02_公司能力/01_公司介绍/company.md"],
                "标准法规": ["03_标准法规/01_中国标准/gb_t_3003.pdf"],
                "市场情报": ["04_市场情报/02_竞争对手/BrandA/price.png"],
                "销售物料": ["05_销售物料/01_Datasheet/石英_datasheet.md"],
                "客户问题/客服反馈": ["06_客户问题与客服反馈/02_已归类问题素材/冒烟异味/石英冒烟.md"],
            }
            for partition, relatives in fixtures.items():
                for relative in relatives:
                    (paths.raw_dir / relative).parent.mkdir(parents=True, exist_ok=True)
                    (paths.raw_dir / relative).write_text("fixture", encoding="utf-8")
                organize_partition(paths, partition)

            summary = json.loads((paths.generated_dir / "agent-interface" / "manifest_summary.json").read_text(encoding="utf-8"))
            for card_type, count in summary["counts_by_type"].items():
                self.assertGreater(count, 0, card_type)

    def test_market_sales_and_customer_materials_do_not_create_product_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixtures = {
                "市场情报": "04_市场情报/02_竞争对手/BrandA/石英_price.png",
                "销售物料": "05_销售物料/01_Datasheet/石英_datasheet.md",
                "客户问题/客服反馈": "06_客户问题与客服反馈/02_已归类问题素材/冒烟异味/石英冒烟.md",
            }
            for partition, relative in fixtures.items():
                (paths.raw_dir / relative).parent.mkdir(parents=True, exist_ok=True)
                (paths.raw_dir / relative).write_text("fixture", encoding="utf-8")
                organize_partition(paths, partition)

            self.assertEqual(list((paths.knowledge_dir / "产品").glob("*.md")), [])
            self.assertTrue(list((paths.knowledge_dir / "复核项").rglob("*.md")))

    def test_manual_review_buffer_only_generates_report_and_review_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = paths.raw_dir / "90_待迁移素材暂存区" / "04_历史成片与项目文件" / "old_project.mp4"
            source.write_text("video", encoding="utf-8")

            result = organize_partition(paths, "待迁移素材暂存区")

            self.assertEqual(result.cards, ())
            self.assertEqual(result.evidence_cards, ())
            self.assertTrue(result.report_path.endswith("MANUAL_REVIEW_BUFFER_REPORT.md"))
            self.assertTrue((paths.generated_dir / "reports" / "MANUAL_REVIEW_BUFFER_REPORT.md").exists())
            self.assertTrue(list((paths.knowledge_dir / "复核项" / "migration_buffer").glob("*.md")))

    def test_empty_partition_generates_no_fake_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            result = organize_partition(paths, "公司能力")

            self.assertEqual(result.cards, ())
            self.assertEqual(result.evidence_cards, ())
            self.assertEqual(result.review_item_cards, ())
            self.assertEqual(list((paths.knowledge_dir / "公司能力").glob("*.md")), [])


if __name__ == "__main__":
    unittest.main()
