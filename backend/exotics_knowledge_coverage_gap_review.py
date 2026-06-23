# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

EXOTICS_KNOWLEDGE_COVERAGE_GAP_REVIEW_MODE = "exotics_knowledge_coverage_gap_review_v1"

# This review is intentionally a coverage/gap review. It is not a diagnostic,
# treatment, prescription, or dosing engine.
EXPECTED_COVERAGE_ROWS: List[Dict[str, str]] = [
    {
        "species_group": "lagomorph",
        "species_or_taxon": "rabbit",
        "current_rule": "rabbit",
        "coverage_status": "triage_scaffold_ready_needs_deepening",
        "covered_presentations": "anorexia; feces_down; no_feces; abdominal_distension; dental_signs; respiratory_distress; head_tilt; urinary_or_reproductive_issue",
        "critical_gaps": "E cuniculi, uterine disease, urolithiasis, pododermatitis, dental imaging details, species-specific lab interpretation, analgesia/anesthesia risk boundaries",
        "priority": "P0",
        "next_stage": "Exotics Rabbit Deepening V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "avian",
        "species_or_taxon": "bird_general",
        "current_rule": "bird",
        "coverage_status": "triage_scaffold_ready_needs_species_split",
        "covered_presentations": "respiratory_distress; ruffled_feathers; egg_binding; regurgitation; appetite_down; collapse",
        "critical_gaps": "parrot, passerine, pigeon, raptor, poultry/waterfowl split; PBFD/PDD/aspergillosis/heavy metal/toxicosis depth; low-stress handling protocols; avian lab interpretation",
        "priority": "P0",
        "next_stage": "Exotics Avian Deepening V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "reptile",
        "species_or_taxon": "reptile_general",
        "current_rule": "reptile",
        "coverage_status": "triage_scaffold_ready_needs_split",
        "covered_presentations": "husbandry_problem; uvb_issue; temperature_issue; humidity_issue; mbd_signs; dysecdysis; respiratory_distress; vent_prolapse; neurologic_signs",
        "critical_gaps": "species-specific husbandry tables; turtle/tortoise/lizard/snake/amphibian split; UVB index and basking gradients; reptile lab and imaging interpretation",
        "priority": "P0",
        "next_stage": "Exotics Reptile Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "chelonians",
        "species_or_taxon": "turtle_tortoise",
        "current_rule": "reptile",
        "coverage_status": "mapped_to_reptile_needs_dedicated_rule",
        "covered_presentations": "shell_skin_issue; husbandry_problem; respiratory_distress; appetite_down",
        "critical_gaps": "aquatic vs terrestrial husbandry split; shell rot/abscess/ear disease; brumation risk; water quality; species-specific diet and UVB",
        "priority": "P1",
        "next_stage": "Exotics Reptile Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "squamate",
        "species_or_taxon": "lizard",
        "current_rule": "reptile",
        "coverage_status": "mapped_to_reptile_needs_dedicated_rule",
        "covered_presentations": "mbd_signs; uvb_issue; dysecdysis; appetite_down; respiratory_distress",
        "critical_gaps": "bearded dragon/leopard gecko/iguana/chameleon split; species-specific temperature, humidity, UVB, diet and parasite patterns",
        "priority": "P1",
        "next_stage": "Exotics Reptile Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "squamate",
        "species_or_taxon": "snake",
        "current_rule": "reptile",
        "coverage_status": "mapped_to_reptile_needs_dedicated_rule",
        "covered_presentations": "respiratory_distress; dysecdysis; appetite_down; neurologic_signs",
        "critical_gaps": "ball python/corn snake/boa split; prey history; regurgitation timing; mite/IBD risk; enclosure gradient and shedding parameters",
        "priority": "P1",
        "next_stage": "Exotics Reptile Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "amphibian",
        "species_or_taxon": "amphibian_general",
        "current_rule": "reptile",
        "coverage_status": "mapped_to_reptile_inadequate_needs_rule",
        "covered_presentations": "husbandry_problem; humidity_issue; skin_issue; appetite_down",
        "critical_gaps": "water quality, substrate/toxin exposure, chytrid risk, species-specific humidity/temperature, amphibian handling and medication sensitivity",
        "priority": "P2",
        "next_stage": "Exotics Amphibian/Aquatic Readiness V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "aquatic",
        "species_or_taxon": "fish_general",
        "current_rule": "reptile",
        "coverage_status": "mapped_to_reptile_inadequate_needs_rule",
        "covered_presentations": "water_quality_placeholder; appetite_down; skin_gill_issue_placeholder",
        "critical_gaps": "water chemistry, tank cycling, gill disease, parasites, temperature/salinity, species-specific aquatics triage and diagnostics",
        "priority": "P2",
        "next_stage": "Exotics Amphibian/Aquatic Readiness V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "mustelid",
        "species_or_taxon": "ferret",
        "current_rule": "ferret",
        "coverage_status": "triage_scaffold_ready_needs_deepening",
        "covered_presentations": "hypoglycemia_signs; weakness; drooling; vomiting; foreign_body_risk; respiratory_distress; urinary_issue",
        "critical_gaps": "insulinoma, adrenal disease, ECE, lymphoma, vaccine reactions, cardiopulmonary disease, surgical/anesthesia risk boundaries",
        "priority": "P1",
        "next_stage": "Exotics Ferret Deepening V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "caviomorph",
        "species_or_taxon": "guinea_pig",
        "current_rule": "rodent",
        "coverage_status": "mapped_to_rodent_needs_species_rule",
        "covered_presentations": "dental_signs; anorexia; feces_down; diarrhea; respiratory_distress; weight_loss",
        "critical_gaps": "vitamin C deficiency, urolithiasis, ovarian cysts, pododermatitis, dental radiography, pregnancy/toxemia risk, antibiotic safety flags",
        "priority": "P1",
        "next_stage": "Exotics Small Mammal Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "rodent",
        "species_or_taxon": "hamster",
        "current_rule": "rodent",
        "coverage_status": "mapped_to_rodent_needs_species_rule",
        "covered_presentations": "anorexia; diarrhea; respiratory_distress; skin_issue; trauma",
        "critical_gaps": "wet-tail triage, cheek pouch disease, pyometra, tumor patterns, torpor vs illness, species-specific handling and anesthesia risk",
        "priority": "P2",
        "next_stage": "Exotics Small Mammal Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "caviomorph",
        "species_or_taxon": "chinchilla",
        "current_rule": "rodent",
        "coverage_status": "mapped_to_rodent_needs_species_rule",
        "covered_presentations": "dental_signs; weight_loss; feces_down; diarrhea; respiratory_distress",
        "critical_gaps": "dental elongation depth, fur slip/dermatology, GI stasis, heat stress, dust bath/environment review",
        "priority": "P2",
        "next_stage": "Exotics Small Mammal Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "rodent",
        "species_or_taxon": "rat_mouse",
        "current_rule": "rodent",
        "coverage_status": "mapped_to_rodent_needs_species_rule",
        "covered_presentations": "respiratory_distress; skin_issue; anorexia; weight_loss; trauma",
        "critical_gaps": "mycoplasma/chronic respiratory disease, mammary tumors, abscesses, aging comorbidity, species-specific analgesia/anesthesia risk",
        "priority": "P2",
        "next_stage": "Exotics Small Mammal Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "insectivore",
        "species_or_taxon": "hedgehog",
        "current_rule": "rodent",
        "coverage_status": "taxonomy_mapping_needs_review_and_dedicated_rule",
        "covered_presentations": "anorexia; skin_issue; low_energy; weight_loss_placeholder",
        "critical_gaps": "wobbly hedgehog syndrome, mites/dermatology, dental disease, obesity, neoplasia, hibernation/temperature risk",
        "priority": "P2",
        "next_stage": "Exotics Small Mammal Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "marsupial",
        "species_or_taxon": "sugar_glider",
        "current_rule": "rodent",
        "coverage_status": "taxonomy_mapping_needs_review_and_dedicated_rule",
        "covered_presentations": "low_energy; appetite_down; husbandry_placeholder; dental_placeholder",
        "critical_gaps": "hindlimb paresis/nutrition, calcium/phosphorus balance, self-mutilation, pouch/reproductive disease, social/husbandry stress",
        "priority": "P2",
        "next_stage": "Exotics Small Mammal Split V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
    {
        "species_group": "invertebrate",
        "species_or_taxon": "tarantula_scorpion_invertebrate",
        "current_rule": "",
        "coverage_status": "not_covered",
        "covered_presentations": "none",
        "critical_gaps": "molting, dehydration, enclosure parameters, trauma, toxicity, owner safety, species-specific no-handle guidance",
        "priority": "P3",
        "next_stage": "Exotics Scope Decision V1",
        "drug_dose_status": "not_reviewed_not_enabled",
        "source_review_status": "required_not_started",
    },
]

SAFETY_FLAGS: Dict[str, Any] = {
    "read_only": True,
    "dry_run": True,
    "writes_database": False,
    "creates_case": False,
    "updates_case": False,
    "creates_diagnostic_report": False,
    "updates_diagnostic_report": False,
    "creates_observation": False,
    "updates_observation": False,
    "creates_imaging_study": False,
    "updates_imaging_study": False,
    "writes_ai_summary": False,
    "writes_abnormal_summary": False,
    "writes_audit_log": False,
    "persists_reasoning_trace": False,
    "generates_final_diagnosis": False,
    "generates_diagnostic_conclusion": False,
    "creates_treatment_plan": False,
    "writes_prescription": False,
    "returns_drug_dose": False,
    "returns_drug_route": False,
    "returns_drug_frequency": False,
    "calls_external_ai": False,
    "calls_external_provider": False,
    "executes_real_import": False,
    "executes_real_lab_ingest": False,
    "executes_real_dicom_ingest": False,
    "executes_real_device_ingest": False,
    "requires_human_review": True,
    "clinician_signoff_required": True,
    "not_client_facing": True,
}


def exotics_knowledge_coverage_safety_flags() -> Dict[str, Any]:
    return dict(SAFETY_FLAGS)


def _repo_root(root: Optional[Path] = None) -> Path:
    if root is not None:
        return Path(root)
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ValueError("missing JSON file: %s" % path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("JSON file must contain an object: %s" % path)
    return data


def _kb_dir(root: Optional[Path] = None) -> Path:
    return _repo_root(root) / "knowledge-base" / "exotics"


def _load_kb_index(root: Optional[Path] = None) -> Dict[str, Any]:
    return _load_json(_kb_dir(root) / "index.json")


def _load_rule(root: Optional[Path], rule_key: str) -> Dict[str, Any]:
    return _load_json(_kb_dir(root) / (rule_key + ".json"))


def _rule_summary(rule: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "key": rule.get("key"),
        "label": rule.get("label"),
        "red_flag_count": len(rule.get("red_flags") or []),
        "disease_count": len(rule.get("diseases") or []),
        "check_count": len(rule.get("checks") or []),
        "question_count": len(rule.get("questions") or []),
        "has_actions": bool(rule.get("actions")),
    }


def _priority_counts(rows: List[Dict[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        key = row.get("priority") or "unclassified"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _status_counts(rows: List[Dict[str, str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        key = row.get("coverage_status") or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_exotics_knowledge_coverage_gap_review(root: Optional[Path] = None) -> Dict[str, Any]:
    """Build a read-only coverage gap review for the current exotics KB.

    This does not change knowledge files, call external providers, write database
    rows, emit diagnoses, create treatment plans, or produce medication doses.
    """
    index = _load_kb_index(root)
    rule_keys = list(index.get("rules") or [])
    if not rule_keys:
        raise ValueError("exotics index has no rules")

    rule_summaries = []
    missing_rule_files = []
    for key in rule_keys:
        try:
            rule_summaries.append(_rule_summary(_load_rule(root, str(key))))
        except Exception:
            missing_rule_files.append(str(key))

    mapped_species = sorted((index.get("species_to_rule") or {}).keys())
    mapped_groups = sorted((index.get("group_to_rule") or {}).keys())
    rows = [dict(row) for row in EXPECTED_COVERAGE_ROWS]
    row_taxa = {row["species_or_taxon"] for row in rows}

    required_next_stages = [
        "Exotics Rabbit Deepening V1",
        "Exotics Avian Deepening V1",
        "Exotics Reptile Split V1",
        "Exotics Small Mammal Split V1",
        "Exotics Ferret Deepening V1",
        "Exotics Amphibian/Aquatic Readiness V1",
        "Exotics Drug Dose Source Review Pack V1",
    ]

    source_review_not_started = [
        row["species_or_taxon"] for row in rows
        if row.get("source_review_status") != "reviewed"
    ]
    dose_not_ready = [
        row["species_or_taxon"] for row in rows
        if row.get("drug_dose_status") != "reviewed_enabled"
    ]
    taxonomy_needs_review = [
        row["species_or_taxon"] for row in rows
        if "taxonomy_mapping_needs_review" in row.get("coverage_status", "")
        or "inadequate" in row.get("coverage_status", "")
    ]

    quality_gate = {
        "status": "PASS",
        "decision": "coverage_gap_review_complete",
        "kb_version": index.get("version"),
        "current_rule_count": len(rule_keys),
        "expected_taxa_count": len(rows),
        "missing_rule_file_count": len(missing_rule_files),
        "priority_counts": _priority_counts(rows),
        "coverage_status_counts": _status_counts(rows),
        "source_review_required_count": len(source_review_not_started),
        "drug_dose_source_review_required_count": len(dose_not_ready),
        "taxonomy_mapping_review_required_count": len(taxonomy_needs_review),
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "blocks_drug_dose_output": True,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
    }

    return {
        "mode": EXOTICS_KNOWLEDGE_COVERAGE_GAP_REVIEW_MODE,
        "kb_version": index.get("version"),
        "schema_version": index.get("schema_version"),
        "current_rule_keys": rule_keys,
        "mapped_species": mapped_species,
        "mapped_groups": mapped_groups,
        "rule_summaries": rule_summaries,
        "missing_rule_files": missing_rule_files,
        "coverage_matrix": rows,
        "coverage_matrix_taxa": sorted(row_taxa),
        "gap_summary": {
            "is_comprehensive": False,
            "current_level": "triage_scaffold_not_comprehensive_clinical_kb",
            "priority_counts": _priority_counts(rows),
            "coverage_status_counts": _status_counts(rows),
            "needs_species_split_or_deepening": [
                row["species_or_taxon"] for row in rows
                if "needs" in row.get("coverage_status", "") or row.get("priority") in ("P0", "P1")
            ],
            "taxonomy_mapping_needs_review": taxonomy_needs_review,
            "source_review_not_started": source_review_not_started,
            "drug_dose_source_review_not_started": dose_not_ready,
        },
        "required_next_stages": required_next_stages,
        "decision": "GO_TO_EXOTICS_RABBIT_DEEPENING_V1",
        "quality_gate": quality_gate,
        "safety": exotics_knowledge_coverage_safety_flags(),
        **exotics_knowledge_coverage_safety_flags(),
    }


def write_coverage_matrix_csv(path: Path, rows: Optional[List[Dict[str, str]]] = None) -> None:
    rows = rows if rows is not None else [dict(row) for row in EXPECTED_COVERAGE_ROWS]
    fieldnames = [
        "species_group",
        "species_or_taxon",
        "current_rule",
        "coverage_status",
        "covered_presentations",
        "critical_gaps",
        "priority",
        "next_stage",
        "drug_dose_status",
        "source_review_status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
