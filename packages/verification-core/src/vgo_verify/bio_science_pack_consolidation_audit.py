#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROBLEM_MAP_CSV_FIELDS = [
    "skill_id",
    "problem_ids",
    "primary_problem_id",
    "current_role",
    "target_role",
    "target_owner",
    "overlap_with",
    "unique_assets",
    "routing_change",
    "delete_allowed_after_migration",
    "risk_level",
    "rationale",
]

BIO_SCIENCE_ROUTE_AUTHORITIES = [
    "alphafold-database",
    "anndata",
    "biopython",
    "bioservices",
    "cellxgene-census",
    "clinvar-database",
    "cosmic-database",
    "deeptools",
    "ensembl-database",
    "gene-database",
    "gget",
    "gwas-database",
    "kegg-database",
    "opentargets-database",
    "pdb-database",
    "pydeseq2",
    "pysam",
    "reactome-database",
    "scanpy",
    "scvi-tools",
    "arboreto",
    "cobrapy",
    "esm",
    "flowio",
    "geniml",
    "string-database",
]

BIO_SCIENCE_STAGE_ASSISTANTS: list[str] = []

BIO_SCIENCE_PROBLEM_DECISIONS: dict[str, dict[str, Any]] = {
    "scanpy": {
        "problem_ids": ["single_cell_rnaseq"],
        "primary_problem_id": "single_cell_rnaseq",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "anndata; scvi-tools; cellxgene-census; pydeseq2",
        "routing_change": "keep as route authority for single-cell RNA-seq clustering, annotation, marker genes, and h5ad/10X workflows",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Single-cell RNA-seq is a distinct high-value user problem and scanpy is the clearest owner.",
    },
    "pydeseq2": {
        "problem_ids": ["bulk_rnaseq_differential_expression"],
        "primary_problem_id": "bulk_rnaseq_differential_expression",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "scanpy; statistical-analysis",
        "routing_change": "keep as route authority for bulk RNA-seq differential expression, DESeq2-style statistics, MA plots, and volcano plots",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Bulk RNA-seq differential expression must not be absorbed by scanpy or biopython.",
    },
    "pysam": {
        "problem_ids": ["alignment_variant_files"],
        "primary_problem_id": "alignment_variant_files",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "biopython; tiledbvcf",
        "routing_change": "keep as route authority for BAM/SAM/CRAM/VCF parsing, pileup, coverage, and variant-file handling",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Alignment and variant files are concrete coding/research tasks with a dedicated Python owner.",
    },
    "biopython": {
        "problem_ids": ["sequence_io_entrez"],
        "primary_problem_id": "sequence_io_entrez",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "gget; pysam; database assistants",
        "routing_change": "keep as route authority and planning/coding default for sequence IO, FASTA, GenBank, SeqIO, Entrez, and sequence conversion",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "Biopython is broad and useful, but negative routing boundaries must stop it from swallowing single-cell, DESeq2, BAM/VCF, ESM, COBRApy, and flow cytometry prompts.",
    },
    "gget": {
        "problem_ids": ["gene_symbol_lookup"],
        "primary_problem_id": "gene_symbol_lookup",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "biopython; bioservices; ensembl-database; gene-database",
        "routing_change": "keep as route authority for quick gene, transcript, Ensembl, BLAST, and symbol lookup",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Quick lookup is a separate user intent from full single-cell or differential-expression workflows.",
    },
    "esm": {
        "problem_ids": ["protein_language_models"],
        "primary_problem_id": "protein_language_models",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "alphafold-database; pdb-database; string-database",
        "routing_change": "keep as route authority for ESM, protein language models, and protein embeddings",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Protein embedding tasks are bio-ML tasks and should not be routed to generic sequence handling.",
    },
    "cobrapy": {
        "problem_ids": ["metabolic_flux_modeling"],
        "primary_problem_id": "metabolic_flux_modeling",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "kegg-database; reactome-database; bioservices",
        "routing_change": "keep as route authority for COBRApy, FBA, flux balance, and constraint-based metabolic models",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Metabolic flux modeling is a problem owner, not a generic pathway lookup.",
    },
    "flowio": {
        "problem_ids": ["flow_cytometry_fcs_io"],
        "primary_problem_id": "flow_cytometry_fcs_io",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "anndata",
        "routing_change": "keep as route authority for FCS and flow cytometry channel matrix handling",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "FCS/flow cytometry file IO is a specific task that should not fall back to biopython.",
    },
    "arboreto": {
        "problem_ids": ["gene_regulatory_networks"],
        "primary_problem_id": "gene_regulatory_networks",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "scanpy; geniml",
        "routing_change": "keep as route authority for pySCENIC, GRN, gene regulatory network, and transcription-factor network tasks",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Gene regulatory network inference is distinct from ordinary single-cell clustering.",
    },
    "geniml": {
        "problem_ids": ["genomic_ml_embeddings"],
        "primary_problem_id": "genomic_ml_embeddings",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "esm; data-ml",
        "routing_change": "keep as route authority for genomic ML and genome embedding tasks",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Genome embeddings are a bio-specific ML surface and need a precise owner.",
    },
    "anndata": {
        "problem_ids": ["single_cell_data_container"],
        "primary_problem_id": "single_cell_data_container",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "scanpy; scvi-tools; cellxgene-census",
        "routing_change": "keep as route authority for AnnData/h5ad containers, annotated matrices, metadata, backed mode, and sparse single-cell data handling",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "AnnData is a data structure layer used inside single-cell workflows.",
    },
    "scvi-tools": {
        "problem_ids": ["single_cell_latent_models"],
        "primary_problem_id": "single_cell_latent_models",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "scanpy; anndata",
        "routing_change": "keep as route authority for scVI/scANVI, batch correction, latent models, transfer learning, and multimodal single-cell modeling",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "scVI is useful inside single-cell workflows but should not absorb broad single-cell prompts in the first split.",
    },
    "deeptools": {
        "problem_ids": ["genomics_track_processing"],
        "primary_problem_id": "genomics_track_processing",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "pysam",
        "routing_change": "keep as route authority for deepTools, BAM to bigWig conversion, genomics signal tracks, QC, heatmaps, and profile plots",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "deepTools is a genomics processing helper with a narrower route surface than pysam.",
    },
    "bioservices": {
        "problem_ids": ["cross_database_aggregation"],
        "primary_problem_id": "cross_database_aggregation",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "kegg-database; reactome-database; uniprot-like services",
        "routing_change": "keep as route authority for BioServices cross-database workflows, UniProt/KEGG/Reactome service access, and ID mapping",
        "delete_allowed_after_migration": False,
        "risk_level": "medium",
        "rationale": "Cross-service lookup is valuable but must not override a more specific workflow owner.",
    },
    "alphafold-database": {
        "problem_ids": ["protein_structure_evidence"],
        "primary_problem_id": "protein_structure_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "pdb-database; esm",
        "routing_change": "keep as route authority for AlphaFold Database predicted structures, UniProt lookup, mmCIF/PDB downloads, pLDDT, and PAE",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Structure evidence supports protein workflows but does not own the main task.",
    },
    "clinvar-database": {
        "problem_ids": ["variant_clinical_evidence"],
        "primary_problem_id": "variant_clinical_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "cosmic-database; gwas-database",
        "routing_change": "keep as route authority for ClinVar clinical significance, pathogenicity, VUS, review status, and variant annotation evidence",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "ClinVar lookup is evidence retrieval inside a variant interpretation workflow.",
    },
    "cosmic-database": {
        "problem_ids": ["cancer_variant_evidence"],
        "primary_problem_id": "cancer_variant_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "clinvar-database; gwas-database",
        "routing_change": "keep as route authority for COSMIC cancer mutations, Cancer Gene Census, mutational signatures, and cancer variant evidence",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "COSMIC is supporting evidence for cancer variant work.",
    },
    "ensembl-database": {
        "problem_ids": ["ensembl_annotation_evidence"],
        "primary_problem_id": "ensembl_annotation_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "gget; gene-database",
        "routing_change": "keep as route authority for Ensembl REST, gene/transcript lookup, VEP, orthologs, comparative genomics, and coordinate conversion",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Ensembl lookup should support gget and sequence workflows.",
    },
    "gene-database": {
        "problem_ids": ["gene_annotation_evidence"],
        "primary_problem_id": "gene_annotation_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "ensembl-database; opentargets-database",
        "routing_change": "keep as route authority for NCBI Gene search, gene symbols, RefSeqs, GO annotations, and gene metadata",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Gene lookup supports annotation but should not own whole workflows.",
    },
    "gwas-database": {
        "problem_ids": ["gwas_trait_evidence"],
        "primary_problem_id": "gwas_trait_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "clinvar-database; opentargets-database",
        "routing_change": "keep as route authority for GWAS Catalog SNP-trait associations, rs IDs, p-values, summary statistics, and genetic epidemiology evidence",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "GWAS evidence is supporting context for genetics workflows.",
    },
    "kegg-database": {
        "problem_ids": ["pathway_metabolism_evidence"],
        "primary_problem_id": "pathway_metabolism_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "reactome-database; bioservices",
        "routing_change": "keep as route authority for KEGG REST, pathway mapping, ID conversion, metabolic pathways, and KEGG-specific control",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "KEGG is useful evidence for pathway and metabolism workflows.",
    },
    "opentargets-database": {
        "problem_ids": ["target_disease_evidence"],
        "primary_problem_id": "target_disease_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "gene-database; gwas-database",
        "routing_change": "keep as route authority for Open Targets target-disease associations, tractability, safety, genetics evidence, and known drugs",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "OpenTargets supports target evidence, not the main computational workflow.",
    },
    "pdb-database": {
        "problem_ids": ["protein_structure_evidence"],
        "primary_problem_id": "protein_structure_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "alphafold-database; string-database",
        "routing_change": "keep as route authority for RCSB PDB structure search, sequence similarity, structure metadata, and coordinate downloads",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "PDB lookup supports structural interpretation but is not the primary route for protein embeddings.",
    },
    "reactome-database": {
        "problem_ids": ["pathway_evidence"],
        "primary_problem_id": "pathway_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "kegg-database; bioservices",
        "routing_change": "keep as route authority for Reactome pathway enrichment, gene-pathway mapping, reactions, and disease pathways",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Reactome supports pathway interpretation inside larger workflows.",
    },
    "string-database": {
        "problem_ids": ["protein_interaction_evidence"],
        "primary_problem_id": "protein_interaction_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "pdb-database; alphafold-database",
        "routing_change": "keep as route authority for STRING protein-protein interaction networks, enrichment, interaction partners, and hub proteins",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "STRING lookup is supporting evidence for protein workflows.",
    },
    "cellxgene-census": {
        "problem_ids": ["single_cell_reference_evidence"],
        "primary_problem_id": "single_cell_reference_evidence",
        "target_role": "keep",
        "target_owner": "",
        "overlap_with": "scanpy; anndata",
        "routing_change": "keep as route authority for CZ CELLxGENE Census queries, cell/tissue/disease filters, expression data, metadata, and census-scale single-cell access",
        "delete_allowed_after_migration": False,
        "risk_level": "low",
        "rationale": "Cellxgene Census supports single-cell reference lookup inside scanpy workflows.",
    },
}


@dataclass(frozen=True)
class ProblemMapRow:
    skill_id: str
    problem_ids: str
    primary_problem_id: str
    current_role: str
    target_role: str
    target_owner: str
    overlap_with: str
    unique_assets: str
    routing_change: str
    delete_allowed_after_migration: bool
    risk_level: str
    rationale: str


@dataclass(frozen=True)
class ProblemMapArtifact:
    generated_at: str
    repo_root: str
    rows: list[ProblemMapRow]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "summary": {
                "bio_science_skill_count": len(self.rows),
                "target_route_authority_count": sum(1 for row in self.rows if row.target_role == "keep"),
                "target_stage_assistant_count": sum(1 for row in self.rows if row.target_role == "stage-assistant"),
                "target_manual_review_count": sum(1 for row in self.rows if row.target_role == "manual-review"),
                "target_merge_delete_count": sum(1 for row in self.rows if row.target_role == "merge-delete-after-migration"),
            },
            "target_route_authority_candidates": BIO_SCIENCE_ROUTE_AUTHORITIES,
            "target_stage_assistant_candidates": BIO_SCIENCE_STAGE_ASSISTANTS,
            "rows": [asdict(row) for row in self.rows],
        }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _bio_science_pack(pack_manifest: dict[str, Any]) -> dict[str, Any]:
    for pack in _as_list(pack_manifest.get("packs")):
        if isinstance(pack, dict) and str(pack.get("id", "")).strip() == "bio-science":
            return pack
    return {}


def _pack_index(pack_manifest: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    index: dict[str, dict[str, set[str]]] = {}
    for pack in _as_list(pack_manifest.get("packs")):
        if not isinstance(pack, dict):
            continue
        pack_id = str(pack.get("id", "")).strip()
        if not pack_id:
            continue
        for role_key in ("skill_candidates", "route_authority_candidates", "stage_assistant_candidates"):
            for value in _as_list(pack.get(role_key)):
                skill_id = str(value).strip()
                if not skill_id:
                    continue
                record = index.setdefault(
                    skill_id,
                    {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
                )
                record["packs"].add(pack_id)
                if role_key == "route_authority_candidates":
                    record["route_authority"].add(pack_id)
                if role_key == "stage_assistant_candidates":
                    record["stage_assistant"].add(pack_id)
        defaults_by_task = pack.get("defaults_by_task")
        if isinstance(defaults_by_task, dict):
            for value in defaults_by_task.values():
                skill_id = str(value).strip()
                if not skill_id:
                    continue
                record = index.setdefault(
                    skill_id,
                    {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
                )
                record["packs"].add(pack_id)
                record["defaults"].add(pack_id)
    return index


def _current_role(record: dict[str, set[str]]) -> str:
    if record["route_authority"]:
        return "route_authority"
    if record["stage_assistant"]:
        return "stage_assistant"
    if record["defaults"]:
        return "default"
    return "candidate"


def _file_count(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for item in directory.rglob("*") if item.is_file())


def _asset_summary(skill_dir: Path) -> str:
    return "; ".join(
        [
            f"scripts={_file_count(skill_dir / 'scripts')}",
            f"references={_file_count(skill_dir / 'references')}",
            f"assets={_file_count(skill_dir / 'assets')}",
        ]
    )


def _decision_for(skill_id: str) -> dict[str, Any]:
    return BIO_SCIENCE_PROBLEM_DECISIONS.get(
        skill_id,
        {
            "problem_ids": ["manual_review"],
            "primary_problem_id": "manual_review",
            "target_role": "manual-review",
            "target_owner": "",
            "overlap_with": "",
            "routing_change": "manual review required before changing bio-science membership",
            "delete_allowed_after_migration": False,
            "risk_level": "high",
            "rationale": "Skill is not registered in the bio-science problem decision table.",
        },
    )


def audit_bio_science_problem_map(repo_root: Path) -> ProblemMapArtifact:
    repo_root = repo_root.resolve()
    pack_manifest = _read_json(repo_root / "config" / "pack-manifest.json")
    pack_index = _pack_index(pack_manifest)
    bio_pack = _bio_science_pack(pack_manifest)
    candidates = [str(item).strip() for item in _as_list(bio_pack.get("skill_candidates")) if str(item).strip()]
    skill_ids = list(dict.fromkeys(candidates + list(BIO_SCIENCE_PROBLEM_DECISIONS)))
    rows: list[ProblemMapRow] = []

    for skill_id in skill_ids:
        record = pack_index.get(
            skill_id,
            {"packs": set(), "route_authority": set(), "stage_assistant": set(), "defaults": set()},
        )
        decision = _decision_for(skill_id)
        skill_dir = repo_root / "bundled" / "skills" / skill_id
        rows.append(
            ProblemMapRow(
                skill_id=skill_id,
                problem_ids="; ".join(_as_list(decision.get("problem_ids"))),
                primary_problem_id=str(decision.get("primary_problem_id", "")),
                current_role=_current_role(record),
                target_role=str(decision.get("target_role", "manual-review")),
                target_owner=str(decision.get("target_owner", "")),
                overlap_with=str(decision.get("overlap_with", "")),
                unique_assets=_asset_summary(skill_dir),
                routing_change=str(decision.get("routing_change", "")),
                delete_allowed_after_migration=bool(decision.get("delete_allowed_after_migration", False)),
                risk_level=str(decision.get("risk_level", "high")),
                rationale=str(decision.get("rationale", "")),
            )
        )
    return ProblemMapArtifact(generated_at=datetime.now(timezone.utc).isoformat(), repo_root=str(repo_root), rows=rows)


def _markdown_table(rows: list[ProblemMapRow], fields: list[str]) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        data = asdict(row)
        values = [str(data[field]).replace("\n", " ").replace("|", "\\|") for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def _write_problem_markdown(path: Path, artifact: ProblemMapArtifact) -> None:
    route_rows = [row for row in artifact.rows if row.target_role == "keep"]
    stage_rows = [row for row in artifact.rows if row.target_role == "stage-assistant"]
    manual_rows = [row for row in artifact.rows if row.target_role == "manual-review"]
    merge_rows = [row for row in artifact.rows if row.target_role == "merge-delete-after-migration"]
    lines: list[str] = [
        "# Bio-Science Problem-First Consolidation",
        "",
        f"- Generated At: `{artifact.generated_at}`",
        f"- Current Bio-Science Skills: {len(artifact.rows)}",
        f"- Target Route Authorities: {len(route_rows)}",
        f"- Stage assistants: {len(stage_rows)}",
        f"- Manual Review: {len(manual_rows)}",
        f"- Merge/Delete After Migration: {len(merge_rows)}",
        "",
        "## Route Authorities",
        "",
    ]
    lines.extend(_markdown_table(route_rows, ["skill_id", "primary_problem_id", "current_role", "overlap_with", "rationale"]))
    if stage_rows:
        lines.extend(["", "## Stage Assistants", ""])
        lines.extend(_markdown_table(stage_rows, ["skill_id", "primary_problem_id", "target_owner", "unique_assets", "rationale"]))
    lines.extend(["", "## Manual Review", ""])
    if manual_rows:
        lines.extend(_markdown_table(manual_rows, ["skill_id", "primary_problem_id", "unique_assets", "rationale"]))
    else:
        lines.append("- none")
    lines.extend(["", "## Merge/Delete After Migration", ""])
    if merge_rows:
        lines.extend(_markdown_table(merge_rows, ["skill_id", "target_owner", "unique_assets", "rationale"]))
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_bio_science_problem_artifacts(
    repo_root: Path,
    artifact: ProblemMapArtifact,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    repo_root = repo_root.resolve()
    output_dir = output_dir or repo_root / "outputs" / "skills-audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "bio-science-problem-map.json"
    csv_path = output_dir / "bio-science-problem-map.csv"
    markdown_path = output_dir / "bio-science-problem-consolidation.md"

    json_path.write_text(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROBLEM_MAP_CSV_FIELDS)
        writer.writeheader()
        for row in artifact.rows:
            writer.writerow(asdict(row))
    _write_problem_markdown(markdown_path, artifact)
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit bio-science pack problem ownership before consolidation.")
    parser.add_argument("--repo-root", help="Optional repository root. Defaults to the current working directory.")
    parser.add_argument("--write-artifacts", action="store_true", help="Write JSON/CSV/Markdown artifacts.")
    parser.add_argument("--output-directory", help="Optional output directory for artifacts.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    artifact = audit_bio_science_problem_map(repo_root)
    if args.write_artifacts:
        output_dir = Path(args.output_directory).resolve() if args.output_directory else None
        write_bio_science_problem_artifacts(repo_root, artifact, output_dir)
    print(json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
