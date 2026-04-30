from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "runtime-core" / "src"))

from vgo_runtime.router_contract_runtime import route_prompt  # noqa: E402


def route(prompt: str, task_type: str = "research", grade: str = "M") -> dict[str, object]:
    return route_prompt(prompt=prompt, grade=grade, task_type=task_type, repo_root=REPO_ROOT)


def selected(result: dict[str, object]) -> tuple[str, str]:
    selected_row = result.get("selected")
    assert isinstance(selected_row, dict), result
    return str(selected_row.get("pack_id") or ""), str(selected_row.get("skill") or "")


def ranked_summary(result: dict[str, object]) -> list[tuple[str, str, float, str]]:
    ranked = result.get("ranked")
    assert isinstance(ranked, list), result
    rows: list[tuple[str, str, float, str]] = []
    for row in ranked[:8]:
        assert isinstance(row, dict), row
        rows.append(
            (
                str(row.get("pack_id") or ""),
                str(row.get("selected_candidate") or ""),
                float(row.get("score") or 0.0),
                str(row.get("candidate_selection_reason") or ""),
            )
        )
    return rows


def load_pack(pack_id: str) -> dict[str, object]:
    manifest = json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))
    return next(pack for pack in manifest["packs"] if pack["id"] == pack_id)


class ZeroRouteAuthorityPackConsolidationTests(unittest.TestCase):
    def assert_selected(
        self,
        prompt: str,
        expected_pack: str,
        expected_skill: str,
        *,
        task_type: str = "research",
        grade: str = "M",
    ) -> None:
        result = route(prompt, task_type=task_type, grade=grade)
        self.assertEqual((expected_pack, expected_skill), selected(result), ranked_summary(result))

    def test_manifest_makes_medical_imaging_direct_owners(self) -> None:
        pack = load_pack("science-medical-imaging")
        expected = ["pydicom", "imaging-data-commons", "histolab", "omero-integration", "pathml"]
        self.assertEqual(expected, pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

    def test_manifest_makes_finance_direct_owners(self) -> None:
        pack = load_pack("finance-edgar-macro")
        expected = [
            "edgartools",
            "alpha-vantage",
            "fred-economic-data",
            "usfiscaldata",
            "hedgefundmonitor",
            "market-research-reports",
            "datacommons-client",
        ]
        self.assertEqual(expected, pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

    def test_manifest_removes_tiledbvcf_from_zarr_polars_and_assigns_single_owner(self) -> None:
        zarr_pack = load_pack("science-zarr-polars")
        tiledb_pack = load_pack("science-tiledbvcf")
        self.assertEqual(["polars", "vaex", "zarr-python"], zarr_pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", zarr_pack)
        self.assertNotIn("stage_assistant_candidates", zarr_pack)
        self.assertEqual(["tiledbvcf"], tiledb_pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", tiledb_pack)
        self.assertNotIn("stage_assistant_candidates", tiledb_pack)

    def test_manifest_removes_geo_database_from_geospatial(self) -> None:
        pack = load_pack("science-geospatial")
        self.assertEqual(["geopandas", "geomaster"], pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)
        self.assertNotEqual("geo-database", pack["defaults_by_task"]["research"])

    def test_manifest_makes_web_scraping_direct_owners(self) -> None:
        pack = load_pack("web-scraping")
        self.assertEqual(["scrapling", "playwright"], pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", pack)
        self.assertNotIn("stage_assistant_candidates", pack)

    def test_medical_imaging_routes_to_direct_owners(self) -> None:
        self.assert_selected(
            "用 pydicom 读取 DICOM tags 并匿名化患者字段",
            "science-medical-imaging",
            "pydicom",
            task_type="coding",
        )
        self.assert_selected(
            "从 Imaging Data Commons 查询 TCIA cancer imaging cohort 并下载 DICOMWeb 样例",
            "science-medical-imaging",
            "imaging-data-commons",
        )
        self.assert_selected(
            "用 histolab 对 whole slide image 做 tissue detection 和 tile extraction",
            "science-medical-imaging",
            "histolab",
            task_type="coding",
        )
        self.assert_selected(
            "用 OMERO 读取 microscopy image server 里的 ROI annotations",
            "science-medical-imaging",
            "omero-integration",
            task_type="coding",
        )
        self.assert_selected(
            "用 PathML 构建 digital pathology WSI 分析流程",
            "science-medical-imaging",
            "pathml",
            task_type="planning",
        )

    def test_finance_routes_to_direct_owners(self) -> None:
        self.assert_selected(
            "用 EDGAR 拉取 AAPL 10-K 并解析 XBRL financial statements",
            "finance-edgar-macro",
            "edgartools",
        )
        self.assert_selected(
            "用 Alpha Vantage 获取 AAPL stock price 日线行情并输出 CSV",
            "finance-edgar-macro",
            "alpha-vantage",
            task_type="coding",
        )
        self.assert_selected(
            "用 FRED 获取 CPI unemployment federal funds rate 时间序列",
            "finance-edgar-macro",
            "fred-economic-data",
        )
        self.assert_selected(
            "用 U.S. Treasury Fiscal Data 查询 national debt 和 federal spending",
            "finance-edgar-macro",
            "usfiscaldata",
        )
        self.assert_selected(
            "查询 OFR Hedge Fund Monitor 和 Form PF aggregate statistics",
            "finance-edgar-macro",
            "hedgefundmonitor",
        )
        self.assert_selected(
            "生成 consulting-style market research report 和 competitive analysis",
            "finance-edgar-macro",
            "market-research-reports",
            task_type="planning",
        )
        self.assert_selected(
            "用 Data Commons 查询 public statistical data 和人口经济指标",
            "finance-edgar-macro",
            "datacommons-client",
        )

    def test_zarr_polars_and_tiledbvcf_have_separate_owners(self) -> None:
        self.assert_selected(
            "用 Polars 读取 Parquet 并做 lazy groupby aggregation",
            "science-zarr-polars",
            "polars",
            task_type="coding",
        )
        self.assert_selected(
            "用 Vaex 做 out-of-core big dataframe filtering",
            "science-zarr-polars",
            "vaex",
            task_type="coding",
        )
        self.assert_selected(
            "用 Zarr 存储 chunked N-D array 到 S3 并并行读取",
            "science-zarr-polars",
            "zarr-python",
            task_type="coding",
        )
        self.assert_selected(
            "用 TileDB-VCF 管理大规模 VCF BCF 并查询基因区域 variant",
            "science-tiledbvcf",
            "tiledbvcf",
            task_type="coding",
        )

    def test_geospatial_routes_and_blocks_ncbi_geo(self) -> None:
        self.assert_selected(
            "用 GeoPandas 读取 Shapefile 并导出 GeoJSON，做 spatial join",
            "science-geospatial",
            "geopandas",
            task_type="coding",
        )
        self.assert_selected(
            "做 remote sensing earth observation workflow，包含投影和经纬度坐标转换",
            "science-geospatial",
            "geomaster",
            task_type="planning",
        )
        result = route("查询 NCBI GEO 的 GSE 和 GSM gene expression dataset")
        self.assertNotEqual("science-geospatial", selected(result)[0], ranked_summary(result))

    def test_web_scraping_routes_to_direct_owners_and_blocks_generic_research(self) -> None:
        self.assert_selected(
            "用 scrapling 抓取网页并用 CSS selector 提取 #main a 链接",
            "web-scraping",
            "scrapling",
            task_type="coding",
        )
        self.assert_selected(
            "用 Playwright 做 browser automation，登录表单并截图调试动态页面",
            "web-scraping",
            "playwright",
            task_type="debug",
        )
        result = route("检索 PubMed website 上的文献并整理 citation references")
        self.assertNotEqual("web-scraping", selected(result)[0], ranked_summary(result))


if __name__ == "__main__":
    unittest.main()
