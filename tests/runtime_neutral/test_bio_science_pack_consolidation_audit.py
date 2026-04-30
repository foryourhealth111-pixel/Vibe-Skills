from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_CORE_SRC = REPO_ROOT / "packages" / "verification-core" / "src"
if str(VERIFICATION_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(VERIFICATION_CORE_SRC))

from vgo_verify.bio_science_pack_consolidation_audit import (
    BIO_SCIENCE_MERGE_DELETE_SKILLS,
    BIO_SCIENCE_ROUTE_AUTHORITIES,
    BIO_SCIENCE_STAGE_ASSISTANTS,
    audit_bio_science_problem_map,
    write_bio_science_problem_artifacts,
)


BIO_SCIENCE_DIRECT_OWNERS = [
    "biopython",
    "scanpy",
    "pydeseq2",
    "bio-database-evidence",
]

PRUNED_DIRECT_SKILLS = [
    "anndata",
    "scvi-tools",
    "pysam",
    "deeptools",
    "esm",
    "cobrapy",
    "geniml",
    "arboreto",
    "flowio",
]

MERGED_DATABASE_SKILLS = [
    "alphafold-database",
    "bioservices",
    "cellxgene-census",
    "clinvar-database",
    "cosmic-database",
    "ensembl-database",
    "gene-database",
    "gget",
    "gwas-database",
    "kegg-database",
    "opentargets-database",
    "pdb-database",
    "reactome-database",
    "string-database",
]

REMOVED_BIO_SCIENCE_SKILLS = MERGED_DATABASE_SKILLS + PRUNED_DIRECT_SKILLS

BIO_SCIENCE_DIRECT_ROUTE_OWNERS = BIO_SCIENCE_DIRECT_OWNERS


class BioSciencePackConsolidationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write_fixture_repo()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative_path: str, content: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _write_json(self, relative_path: str, payload: object) -> None:
        self._write(relative_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    def _write_skill(
        self,
        skill_id: str,
        *,
        scripts: bool = False,
        references: bool = False,
        assets: bool = False,
    ) -> None:
        self._write(
            f"bundled/skills/{skill_id}/SKILL.md",
            "---\n"
            f"name: {skill_id}\n"
            f"description: Fixture skill for {skill_id}.\n"
            "---\n\n"
            f"# {skill_id}\n\n"
            f"Use {skill_id} for its explicit bio-science workflow.\n",
        )
        if scripts:
            self._write(f"bundled/skills/{skill_id}/scripts/run.py", "print('ok')\n")
        if references:
            self._write(f"bundled/skills/{skill_id}/references/guide.md", "# Guide\n\nConcrete guidance.\n")
        if assets:
            self._write(f"bundled/skills/{skill_id}/assets/example.txt", "asset\n")

    def _write_fixture_repo(self) -> None:
        self._write_json(
            "config/pack-manifest.json",
            {
                "packs": [
                    {
                        "id": "bio-science",
                        "skill_candidates": BIO_SCIENCE_DIRECT_OWNERS,
                        "route_authority_candidates": BIO_SCIENCE_DIRECT_ROUTE_OWNERS,
                        "stage_assistant_candidates": [],
                        "defaults_by_task": {
                            "planning": "biopython",
                            "coding": "biopython",
                            "research": "scanpy",
                        },
                    },
                    {
                        "id": "science-chem-drug",
                        "skill_candidates": ["rdkit"],
                        "defaults_by_task": {"coding": "rdkit"},
                    },
                ]
            },
        )
        self._write_json("config/skill-keyword-index.json", {"skills": {}})
        self._write_json("config/skill-routing-rules.json", {"skills": {}})
        for skill_id in BIO_SCIENCE_DIRECT_OWNERS + REMOVED_BIO_SCIENCE_SKILLS:
            self._write_skill(
                skill_id,
                scripts=skill_id in {"scanpy", "pysam", "cobrapy", "flowio"},
                references=skill_id.endswith("-database") or skill_id in {"biopython", "esm", "bio-database-evidence"},
                assets=skill_id in {"cellxgene-census", "pdb-database", "deeptools"},
            )

    def test_problem_map_covers_all_candidates_and_target_roles(self) -> None:
        artifact = audit_bio_science_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual(set(BIO_SCIENCE_DIRECT_OWNERS + REMOVED_BIO_SCIENCE_SKILLS), set(rows))
        self.assertEqual(BIO_SCIENCE_DIRECT_ROUTE_OWNERS, BIO_SCIENCE_ROUTE_AUTHORITIES)
        self.assertEqual(REMOVED_BIO_SCIENCE_SKILLS, BIO_SCIENCE_MERGE_DELETE_SKILLS)
        self.assertEqual([], BIO_SCIENCE_STAGE_ASSISTANTS)
        self.assertEqual(set(BIO_SCIENCE_DIRECT_ROUTE_OWNERS), {row.skill_id for row in artifact.rows if row.target_role == "keep"})
        self.assertEqual(set(), {row.skill_id for row in artifact.rows if row.target_role == "stage-assistant"})
        self.assertEqual(4, artifact.to_dict()["summary"]["target_route_authority_count"])
        self.assertEqual(0, artifact.to_dict()["summary"]["target_stage_assistant_count"])
        self.assertEqual(23, artifact.to_dict()["summary"]["target_merge_delete_count"])

    def test_problem_map_records_primary_problem_owners(self) -> None:
        artifact = audit_bio_science_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        self.assertEqual("single_cell_rnaseq", rows["scanpy"].primary_problem_id)
        self.assertEqual("bulk_rnaseq_differential_expression", rows["pydeseq2"].primary_problem_id)
        self.assertEqual("sequence_io_entrez", rows["biopython"].primary_problem_id)
        self.assertEqual("biological_database_evidence", rows["bio-database-evidence"].primary_problem_id)
        self.assertEqual("single_cell_data_container", rows["anndata"].primary_problem_id)
        self.assertEqual("single_cell_latent_models", rows["scvi-tools"].primary_problem_id)
        self.assertEqual("alignment_variant_files", rows["pysam"].primary_problem_id)
        self.assertEqual("protein_language_models", rows["esm"].primary_problem_id)
        self.assertEqual("metabolic_flux_modeling", rows["cobrapy"].primary_problem_id)

    def test_removed_skills_are_merge_delete_rows(self) -> None:
        artifact = audit_bio_science_problem_map(self.root)
        rows = {row.skill_id: row for row in artifact.rows}

        for skill_id in REMOVED_BIO_SCIENCE_SKILLS:
            self.assertEqual("merge-delete-after-migration", rows[skill_id].target_role)
            self.assertTrue(rows[skill_id].delete_allowed_after_migration)

        self.assertEqual("scanpy", rows["anndata"].target_owner)
        self.assertEqual("scanpy", rows["scvi-tools"].target_owner)
        self.assertEqual("bio-database-evidence", rows["clinvar-database"].target_owner)

    def test_artifact_writer_outputs_json_csv_and_markdown(self) -> None:
        artifact = audit_bio_science_problem_map(self.root)
        output_dir = self.root / "outputs" / "skills-audit"
        written = write_bio_science_problem_artifacts(self.root, artifact, output_dir)

        self.assertTrue(written["json"].exists())
        self.assertTrue(written["csv"].exists())
        self.assertTrue(written["markdown"].exists())
        self.assertIn("bio-science-problem-map", written["json"].name)

        csv_text = written["csv"].read_text(encoding="utf-8")
        self.assertIn("skill_id,problem_ids,primary_problem_id", csv_text)
        self.assertIn("scanpy", csv_text)
        self.assertIn("pydeseq2", csv_text)

        markdown_text = written["markdown"].read_text(encoding="utf-8")
        self.assertIn("# Bio-Science Problem-First Consolidation", markdown_text)
        self.assertIn("## Route Authorities", markdown_text)
        self.assertIn("Stage assistants: 0", markdown_text)
        self.assertNotIn("## Stage Assistants", markdown_text)

    def test_audit_and_writer_do_not_modify_live_config(self) -> None:
        config_paths = [
            self.root / "config" / "pack-manifest.json",
            self.root / "config" / "skill-keyword-index.json",
            self.root / "config" / "skill-routing-rules.json",
        ]
        before = {path: path.read_text(encoding="utf-8") for path in config_paths}

        artifact = audit_bio_science_problem_map(self.root)
        write_bio_science_problem_artifacts(self.root, artifact, self.root / "outputs" / "skills-audit")

        after = {path: path.read_text(encoding="utf-8") for path in config_paths}
        self.assertEqual(before, after)

    def test_real_bio_science_pack_has_target_role_split(self) -> None:
        manifest = json.loads((REPO_ROOT / "config" / "pack-manifest.json").read_text(encoding="utf-8-sig"))
        bio_pack = next(pack for pack in manifest["packs"] if pack["id"] == "bio-science")

        self.assertEqual(BIO_SCIENCE_DIRECT_OWNERS, bio_pack["skill_candidates"])
        self.assertEqual(BIO_SCIENCE_DIRECT_ROUTE_OWNERS, bio_pack["skill_candidates"])
        self.assertNotIn("route_authority_candidates", bio_pack)
        self.assertNotIn("stage_assistant_candidates", bio_pack)
        self.assertEqual(
            {
                "planning": "biopython",
                "coding": "biopython",
                "research": "scanpy",
            },
            bio_pack["defaults_by_task"],
        )

    def test_runtime_neutral_wrapper_exposes_main(self) -> None:
        wrapper = REPO_ROOT / "scripts" / "verify" / "runtime_neutral" / "bio_science_pack_consolidation_audit.py"
        text = wrapper.read_text(encoding="utf-8")
        self.assertIn("from vgo_verify.bio_science_pack_consolidation_audit import", text)
        self.assertIn("raise SystemExit(main())", text)


if __name__ == "__main__":
    unittest.main()
