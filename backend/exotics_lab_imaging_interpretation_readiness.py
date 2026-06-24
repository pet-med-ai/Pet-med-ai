# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MODE = "exotics_lab_imaging_interpretation_readiness_v1"

# This stage is a readiness review only. It is deliberately not an
# interpretation engine and does not produce diagnoses, treatment plans,
# prescriptions, drug doses, client-facing summaries, or external provider calls.
MATRIX_FILENAME = "EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MATRIX_V1.csv"

CRITICAL_SPECIES_KEYS = [
    "rabbit",
    "bird",
    "ferret",
    "turtle",
    "lizard",
    "snake",
    "amphibian",
    "fish",
    "guinea_pig",
    "hamster",
    "chinchilla",
    "rat_mouse",
    "hedgehog",
    "sugar_glider",
]

LEGACY_FALLBACK_KEYS = [
    "reptile",
    "rodent",
]

READINESS_MATRIX: List[Dict[str, str]] = [
    {
        "rule_key": "rabbit",
        "species_scope": "rabbit",
        "lab_reference_range_status": "missing_species_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; glucose; electrolytes; renal; liver; urinalysis",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "abdominal radiographs for gas/obstruction; skull/dental radiographs; thoracic radiographs",
        "observation_mapping_status": "needs_exotic_reference_ranges_and_units",
        "diagnostic_report_mapping_status": "needs reviewed lab panel and imaging report templates",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "rabbit lab ranges and imaging pattern source pack before interpretation",
    },
    {
        "rule_key": "bird",
        "species_scope": "avian general",
        "lab_reference_range_status": "missing_species_and_order_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; bile acids; uric acid; calcium; protein; pathogen tests",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "whole-body radiographs; coelomic/egg binding evaluation; respiratory/air sac patterns",
        "observation_mapping_status": "needs avian analyte vocabulary and sample quality flags",
        "diagnostic_report_mapping_status": "needs low-stress avian diagnostic report boundary",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "avian source pack split by psittacine/passerine/pigeon where possible",
    },
    {
        "rule_key": "ferret",
        "species_scope": "ferret",
        "lab_reference_range_status": "missing_ferret_specific_ranges",
        "priority_lab_domains": "glucose; CBC; chemistry; electrolytes; urinalysis; endocrine screening placeholders",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "abdominal radiographs/ultrasound for foreign body; thoracic imaging; adrenal/abdominal review",
        "observation_mapping_status": "needs ferret reference ranges and hypoglycemia safety flags",
        "diagnostic_report_mapping_status": "needs foreign body and endocrine review templates",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "ferret lab/imaging source review before diagnostic interpretation",
    },
    {
        "rule_key": "turtle",
        "species_scope": "turtle/tortoise/terrapin",
        "lab_reference_range_status": "missing_species_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; calcium/phosphorus; uric acid; hydration; water quality context",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "shell/bone; lungs; GI; reproductive/egg retention; buoyancy context",
        "observation_mapping_status": "needs chelonian reference range and husbandry-linked interpretation metadata",
        "diagnostic_report_mapping_status": "needs chelonian imaging report template",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "chelonian lab/imaging readiness pack",
    },
    {
        "rule_key": "lizard",
        "species_scope": "lizard including bearded dragon/gecko/iguana/chameleon",
        "lab_reference_range_status": "missing_species_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; calcium/phosphorus; uric acid; hydration; nutrition",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "MBD/bone; GI impaction; reproductive; respiratory; trauma",
        "observation_mapping_status": "needs species and husbandry metadata for any interpretation",
        "diagnostic_report_mapping_status": "needs lizard imaging pattern checklist",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "lizard source pack split by common pet taxa",
    },
    {
        "rule_key": "snake",
        "species_scope": "snake",
        "lab_reference_range_status": "missing_species_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; uric acid; hydration; pathogen/fecal tests",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "respiratory; GI foreign body/retained meal; reproductive; skeletal/trauma",
        "observation_mapping_status": "needs snake-specific reference range metadata",
        "diagnostic_report_mapping_status": "needs snake imaging report and regurgitation/respiratory context",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "snake lab/imaging readiness pack",
    },
    {
        "rule_key": "amphibian",
        "species_scope": "amphibian including frog/toad/salamander/newt/axolotl",
        "lab_reference_range_status": "mostly_missing_species_specific_ranges",
        "priority_lab_domains": "water quality; cytology; skin scrape; infectious testing; limited bloodwork readiness",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "coelomic fluid; skeletal; foreign body; buoyancy/axolotl aquatic context",
        "observation_mapping_status": "needs water quality/device observations before lab interpretation",
        "diagnostic_report_mapping_status": "needs amphibian husbandry and dermatologic report templates",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "amphibian source pack with water quality observation model",
    },
    {
        "rule_key": "fish",
        "species_scope": "ornamental fish",
        "lab_reference_range_status": "not_applicable_or_specialized_for_common_clinic_flow",
        "priority_lab_domains": "water quality; microscopy; cytology; parasite exam; bacterial culture readiness",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "generally limited; radiographs/ultrasound only in selected cases",
        "observation_mapping_status": "needs water quality Observation mapping as first-class diagnostic data",
        "diagnostic_report_mapping_status": "needs tank/population-level report model before individual interpretation",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "fish water-quality/device observation readiness before medical interpretation",
    },
    {
        "rule_key": "guinea_pig",
        "species_scope": "guinea pig",
        "lab_reference_range_status": "missing_guinea_pig_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; glucose; calcium; urinalysis; vitamin C/nutrition context",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "dental skull; urinary stones; GI gas; thoracic respiratory",
        "observation_mapping_status": "needs guinea pig reference ranges and dental/urinary flags",
        "diagnostic_report_mapping_status": "needs guinea pig dental/urinary/GI imaging report template",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "guinea pig lab/imaging source pack",
    },
    {
        "rule_key": "hamster",
        "species_scope": "hamster",
        "lab_reference_range_status": "missing_hamster_specific_ranges",
        "priority_lab_domains": "limited bloodwork readiness; hydration; glucose; fecal/parasite; cytology",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "cheek pouch; GI; masses; respiratory; trauma",
        "observation_mapping_status": "needs hamster-specific feasibility and sample-volume flags",
        "diagnostic_report_mapping_status": "needs small-patient sampling limitations in report template",
        "source_review_status": "required_not_started",
        "gap_level": "medium_high",
        "next_stage_requirement": "hamster diagnostic feasibility and source review",
    },
    {
        "rule_key": "chinchilla",
        "species_scope": "chinchilla",
        "lab_reference_range_status": "missing_chinchilla_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; glucose; hydration; fecal/parasite; dental context",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "dental skull; GI gas/stasis; thoracic; trauma",
        "observation_mapping_status": "needs chinchilla reference ranges and heat-stress context flags",
        "diagnostic_report_mapping_status": "needs dental/GI imaging report template",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "chinchilla lab/imaging source pack",
    },
    {
        "rule_key": "rat_mouse",
        "species_scope": "rat/mouse",
        "lab_reference_range_status": "missing_rat_mouse_specific_ranges",
        "priority_lab_domains": "CBC/chemistry feasibility; cytology; respiratory pathogen context; urinalysis",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "thoracic respiratory; masses; dental; skeletal/trauma",
        "observation_mapping_status": "needs rat/mouse sample-feasibility metadata",
        "diagnostic_report_mapping_status": "needs respiratory/mass report template",
        "source_review_status": "required_not_started",
        "gap_level": "medium_high",
        "next_stage_requirement": "rat/mouse source review and imaging pattern checklist",
    },
    {
        "rule_key": "hedgehog",
        "species_scope": "hedgehog",
        "lab_reference_range_status": "missing_hedgehog_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; glucose; urinalysis; cytology; infectious/skin tests",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "oral/dental; abdominal/thoracic masses; skeletal/neuro; respiratory",
        "observation_mapping_status": "needs hedgehog reference ranges and anesthesia/stress context flags",
        "diagnostic_report_mapping_status": "needs oral/mass/neuro imaging report template",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "hedgehog lab/imaging source pack",
    },
    {
        "rule_key": "sugar_glider",
        "species_scope": "sugar glider",
        "lab_reference_range_status": "missing_sugar_glider_specific_ranges",
        "priority_lab_domains": "CBC; chemistry; calcium/phosphorus; glucose; hydration; nutrition context",
        "imaging_interpretation_status": "readiness_only_no_ai_interpretation",
        "priority_imaging_domains": "skeletal/MBD; dental/oral; pouch/reproductive; trauma",
        "observation_mapping_status": "needs sugar glider reference ranges and nutrition metadata",
        "diagnostic_report_mapping_status": "needs nutrition/MBD/self-trauma report template",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "sugar glider source pack and nutrition diagnostic context",
    },
    {
        "rule_key": "reptile",
        "species_scope": "legacy generic reptile fallback",
        "lab_reference_range_status": "fallback_only_do_not_use_for_species_specific_interpretation",
        "priority_lab_domains": "route to turtle/lizard/snake/amphibian/fish when possible",
        "imaging_interpretation_status": "fallback_only_no_ai_interpretation",
        "priority_imaging_domains": "species split required",
        "observation_mapping_status": "fallback only",
        "diagnostic_report_mapping_status": "fallback only",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "replace with split rule whenever species is known",
    },
    {
        "rule_key": "rodent",
        "species_scope": "legacy generic small mammal fallback",
        "lab_reference_range_status": "fallback_only_do_not_use_for_species_specific_interpretation",
        "priority_lab_domains": "route to guinea_pig/hamster/chinchilla/rat_mouse/hedgehog/sugar_glider when possible",
        "imaging_interpretation_status": "fallback_only_no_ai_interpretation",
        "priority_imaging_domains": "species split required",
        "observation_mapping_status": "fallback only",
        "diagnostic_report_mapping_status": "fallback only",
        "source_review_status": "required_not_started",
        "gap_level": "high",
        "next_stage_requirement": "replace with split rule whenever species is known",
    },
]


def exotics_lab_imaging_interpretation_readiness_safety_flags() -> Dict[str, Any]:
    return {
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
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
        "lab_reference_ranges_enabled": False,
        "imaging_ai_interpretation_enabled": False,
    }


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def _repo_root(root: Optional[Path] = None) -> Path:
    return Path(root).resolve() if root else Path(__file__).resolve().parents[1]


def _existing_rule_keys(root: Path) -> List[str]:
    index_path = root / "knowledge-base" / "exotics" / "index.json"
    index = _read_json(index_path)
    rules = index.get("rules")
    if isinstance(rules, list):
        return [str(item) for item in rules if str(item).strip()]
    return []


def write_readiness_matrix_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rule_key",
        "species_scope",
        "lab_reference_range_status",
        "priority_lab_domains",
        "imaging_interpretation_status",
        "priority_imaging_domains",
        "observation_mapping_status",
        "diagnostic_report_mapping_status",
        "source_review_status",
        "gap_level",
        "next_stage_requirement",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in READINESS_MATRIX:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def build_exotics_lab_imaging_interpretation_readiness_review(
    *,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    repo_root = _repo_root(root)
    existing_rules = _existing_rule_keys(repo_root)
    matrix_keys = [row["rule_key"] for row in READINESS_MATRIX]
    missing_critical_rules = [key for key in CRITICAL_SPECIES_KEYS if key not in existing_rules]

    quality_gate = {
        "status": "PASS",
        "decision": "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1",
        "current_level": "exotics_lab_imaging_readiness_only_not_interpretation_engine",
        "is_interpretation_engine": False,
        "is_comprehensive_clinical_kb": False,
        "species_rows": len(READINESS_MATRIX),
        "critical_species_count": len(CRITICAL_SPECIES_KEYS),
        "legacy_fallback_count": len(LEGACY_FALLBACK_KEYS),
        "missing_critical_rules": missing_critical_rules,
        "requires_source_review": True,
        "lab_reference_ranges_enabled": False,
        "imaging_ai_interpretation_enabled": False,
        "drug_dose_status": "not_reviewed_not_enabled",
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    safety = exotics_lab_imaging_interpretation_readiness_safety_flags()
    return {
        "mode": EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MODE,
        "matrix_filename": MATRIX_FILENAME,
        "matrix": list(READINESS_MATRIX),
        "matrix_keys": matrix_keys,
        "existing_rule_keys": existing_rules,
        "critical_species_keys": list(CRITICAL_SPECIES_KEYS),
        "legacy_fallback_keys": list(LEGACY_FALLBACK_KEYS),
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }


__all__ = [
    "EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MODE",
    "MATRIX_FILENAME",
    "CRITICAL_SPECIES_KEYS",
    "LEGACY_FALLBACK_KEYS",
    "READINESS_MATRIX",
    "build_exotics_lab_imaging_interpretation_readiness_review",
    "exotics_lab_imaging_interpretation_readiness_safety_flags",
    "write_readiness_matrix_csv",
]
