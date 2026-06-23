# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, Optional
import zipfile
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

try:
    from backend.auth_jwt import get_current_user
    from backend.db import get_db
    from backend.models import Case, DiagnosticReport, Observation, ImagingStudy
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import Case, DiagnosticReport, Observation, ImagingStudy

try:
    from backend.clinical_docs_diagnostic_data_merge import (
        CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE,
        build_clinical_docs_diagnostic_data_merge,
        clinical_docs_diagnostic_data_merge_safety_flags,
    )
except ModuleNotFoundError:
    from clinical_docs_diagnostic_data_merge import (
        CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE,
        build_clinical_docs_diagnostic_data_merge,
        clinical_docs_diagnostic_data_merge_safety_flags,
    )

router = APIRouter(prefix="/api/clinical-docs", tags=["clinical-docs"])

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates" / "clinical_docs"

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "admission_hospitalization_record_bilingual": {
        "file": "admission_hospitalization_record_bilingual.docx",
        "label": "入院 / 住院记录 Admission / Hospitalization Record",
        "output_filename_prefix": "petmed-admission-record",
        "required_keys": [
            "case_id",
            "pet.name",
            "species",
            "admission_reason",
            "clinician.name",
            "generator",
            "clinician_id",
            "timestamp",
            "hash",
        ],
    },
    "discharge_summary_bilingual": {
        "file": "discharge_summary_bilingual.docx",
        "label": "出院小结 Discharge Summary",
        "output_filename_prefix": "petmed-discharge-summary",
        "required_keys": [
            "case_id",
            "pet.name",
            "species",
            "hospital_course",
            "clinician.name",
            "generator",
            "clinician_id",
            "timestamp",
            "hash",
        ],
    },
}


class ClinicalDocRenderIn(BaseModel):
    case_id: int = Field(..., ge=1)
    template_id: str = Field(..., min_length=1, max_length=120)
    output: str = Field(default="docx", max_length=20)
    clinician_name: Optional[str] = Field(default=None, max_length=120)
    clinician_id: Optional[str] = Field(default=None, max_length=120)
    generator: Optional[str] = Field(default=None, max_length=120)
    include_preview_context: bool = Field(default=False)
    include_diagnostic_data: bool = Field(default=False)


def _text(value: Any, fallback: str = "") -> str:
    raw = str(value if value is not None else "").strip()
    return raw or fallback


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _template_meta(template_id: str) -> Dict[str, Any]:
    template_id = _text(template_id)
    meta = TEMPLATES.get(template_id)
    if not meta:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "unsupported clinical document template",
                "template_id": template_id,
                "allowed_templates": sorted(TEMPLATES.keys()),
            },
        )

    path = TEMPLATE_DIR / str(meta["file"])
    if not path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"clinical document template asset missing: {meta['file']}",
        )

    return {**meta, "template_id": template_id, "path": path}


def _case_or_404(db: Session, case_id: int, user) -> Case:
    case = db.get(Case, int(case_id))
    user_id = getattr(user, "id", None)
    if not case or getattr(case, "owner_id", None) != user_id:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


def _canonical_hash(context: Dict[str, Any]) -> str:
    canonical = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]



# --- Clinical Docs Diagnostic Data Merge V1 helpers: start ---
def _clinical_docs_diagnostic_data_merge_for_case(db: Session, case: Case, *, include: bool) -> Dict[str, Any]:
    case_context = {
        "case_id": int(getattr(case, "id")),
        "patient_name": getattr(case, "patient_name", None),
        "species": getattr(case, "species", None),
    }
    if not include:
        safety = clinical_docs_diagnostic_data_merge_safety_flags()
        return {
            "mode": CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE,
            "case_id": int(getattr(case, "id")),
            "case_context": case_context,
            "diagnostic_data_merge": {
                "reports": [],
                "observations": [],
                "imaging_studies": [],
                "section_text": "",
                "not_a_diagnosis": True,
                "not_a_treatment_plan": True,
                "not_a_prescription": True,
                "not_client_facing": True,
            },
            "document_context": {
                "diagnostic.reports.summary": "Diagnostic data merge not requested.",
                "diagnostic.observations.summary": "Diagnostic data merge not requested.",
                "diagnostic.imaging.summary": "Diagnostic data merge not requested.",
                "diagnostic.data.safety": "read_only=true; writes_database=false; merge_not_requested=true",
                "__diagnostic_data_section": "",
            },
            "quality_gate": {
                "status": "PASS",
                "decision": "diagnostic_data_merge_not_requested",
                "writes_database": False,
                "requires_human_review": True,
                "clinician_signoff_required": True,
            },
            "safety": safety,
            **safety,
        }

    reports = (
        db.query(DiagnosticReport)
        .filter(DiagnosticReport.case_id == int(getattr(case, "id")))
        .order_by(DiagnosticReport.created_at.desc(), DiagnosticReport.id.desc())
        .limit(20)
        .all()
    )
    observations = (
        db.query(Observation)
        .filter(Observation.case_id == int(getattr(case, "id")))
        .order_by(Observation.created_at.desc(), Observation.id.desc())
        .limit(50)
        .all()
    )
    imaging_studies = (
        db.query(ImagingStudy)
        .filter(ImagingStudy.case_id == int(getattr(case, "id")))
        .order_by(ImagingStudy.created_at.desc(), ImagingStudy.id.desc())
        .limit(20)
        .all()
    )
    return build_clinical_docs_diagnostic_data_merge(
        reports,
        observations,
        imaging_studies,
        case_id=int(getattr(case, "id")),
        case_context=case_context,
    )


def _apply_diagnostic_data_context_to_clinical_doc_context(context: Dict[str, str], merge: Dict[str, Any]) -> Dict[str, str]:
    document_context = merge.get("document_context") if isinstance(merge, dict) else None
    if isinstance(document_context, dict):
        for key, value in document_context.items():
            context[str(key)] = str(value if value is not None else "")
    context["diagnostic.data.merge.mode"] = CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE
    context["diagnostic.data.merge.enabled"] = "true" if context.get("__diagnostic_data_section") else "false"
    return context
# --- Clinical Docs Diagnostic Data Merge V1 helpers: end ---

def _build_context(case: Case, *, data: ClinicalDocRenderIn, user, template_id: str) -> Dict[str, str]:
    timestamp = _utc_timestamp()
    clinician_id = _text(data.clinician_id) or _text(getattr(user, "id", None), "unknown")
    clinician_name = _text(data.clinician_name) or _text(getattr(user, "email", None), "临床医生 / Clinician")

    context: Dict[str, str] = {
        "case_id": _text(getattr(case, "id", None), "unknown"),
        "pet.name": _text(getattr(case, "patient_name", None), "未命名病例"),
        "species": _text(getattr(case, "species", None), "other"),
        "dob": _text(getattr(case, "age_info", None)),
        "owner.name": _text(getattr(case, "owner_name", None)),
        "contact": _text(getattr(case, "owner_phone", None)),
        "vitals": _text(getattr(case, "exam_findings", None)),
        "admission_reason": _text(getattr(case, "chief_complaint", None)),
        "provisional_dx": _text(getattr(case, "analysis", None)),
        "treatment_plan": _text(getattr(case, "treatment", None)),
        "meds": _text(getattr(case, "treatment", None)),
        "hospital_course": _text(getattr(case, "history", None)),
        "final_dx": _text(getattr(case, "analysis", None)),
        "discharge_instructions": _text(getattr(case, "prognosis", None)),
        "home_meds": _text(getattr(case, "treatment", None)),
        "follow_up_plan": _text(getattr(case, "prognosis", None)),
        "clinician.name": clinician_name,
        "generator": _text(data.generator, "Pet-Med-AI Clinical Docs Export API V1"),
        "clinician_id": clinician_id,
        "timestamp": timestamp,
        "hash": "",
        # Template-level operational placeholders.
        # These are safe defaults; no real official stamp or secret value is embedded.
        "clinic.name": "瀚森宠物医院 / Hanson Veterinary Clinic",
        "clinic.address": "地址待填写 / Address TBD",
        "clinic.phone": "电话待填写 / Phone TBD",
        "clinic.hours": "营业时间待填写 / Hours TBD",
        "stamp.image": "电子章位 / Stamp placeholder",
    }

    hash_input = {
        **context,
        "template_id": template_id,
        "case_id": context["case_id"],
        "hash": "",
    }
    context["hash"] = _canonical_hash(hash_input)
    return context


def _replace_placeholders_in_xml(xml_bytes: bytes, context: Dict[str, str]) -> bytes:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes

    placeholders = {f"{{{{{key}}}}}": value for key, value in context.items()}

    changed_any = False
    for paragraph in root.iter():
        if not paragraph.tag.endswith("}p"):
            continue

        text_nodes = [node for node in paragraph.iter() if node.tag.endswith("}t")]
        if not text_nodes:
            continue

        combined = "".join(node.text or "" for node in text_nodes)
        if "{{" not in combined:
            continue

        replaced = combined
        for placeholder, value in placeholders.items():
            replaced = replaced.replace(placeholder, value)

        if replaced != combined:
            text_nodes[0].text = replaced
            for node in text_nodes[1:]:
                node.text = ""
            changed_any = True

    if not changed_any:
        return xml_bytes

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)



# --- Clinical Docs Diagnostic Data Merge V1 DOCX append: start ---
def _append_diagnostic_data_section_to_document_xml(xml_bytes: bytes, context: Dict[str, str]) -> bytes:
    section_text = str(context.get("__diagnostic_data_section") or "").strip()
    if not section_text:
        return xml_bytes
    try:
        ET.register_namespace("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes

    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    body = root.find(w + "body")
    if body is None:
        return xml_bytes

    existing_text = "".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
    if "Diagnostic data merge / 诊断数据合并" in existing_text:
        return xml_bytes

    def paragraph(text: str, *, bold: bool = False):
        p = ET.Element(w + "p")
        r = ET.SubElement(p, w + "r")
        if bold:
            rpr = ET.SubElement(r, w + "rPr")
            ET.SubElement(rpr, w + "b")
        t = ET.SubElement(r, w + "t")
        t.text = text
        return p

    insert_at = len(body)
    if len(body) and body[-1].tag == w + "sectPr":
        insert_at -= 1

    body.insert(insert_at, paragraph("Diagnostic data merge / 诊断数据合并（医生复核）", bold=True))
    insert_at += 1
    for raw_line in section_text.splitlines()[:90]:
        line = raw_line.strip()
        if not line:
            continue
        body.insert(insert_at, paragraph(line))
        insert_at += 1

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
# --- Clinical Docs Diagnostic Data Merge V1 DOCX append: end ---

def _render_docx(template_path: Path, context: Dict[str, str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(template_path, "r") as zin:
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                raw = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    raw = _append_diagnostic_data_section_to_document_xml(raw, context)
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    raw = _replace_placeholders_in_xml(raw, context)
                zout.writestr(item, raw)
    return out.getvalue()


def _unreplaced_placeholders(docx_bytes: bytes) -> list[str]:
    found: set[str] = set()
    with zipfile.ZipFile(io.BytesIO(docx_bytes), "r") as zf:
        for name in zf.namelist():
            if not (name.startswith("word/") and name.endswith(".xml")):
                continue
            text = zf.read(name).decode("utf-8", errors="ignore")
            for chunk in text.split("{{")[1:]:
                key = chunk.split("}}", 1)[0].strip()
                if key:
                    found.add("{{" + key + "}}")
    return sorted(found)


@router.get("/templates", response_model=dict)
def list_clinical_doc_templates():
    templates = []
    for template_id, meta in TEMPLATES.items():
        path = TEMPLATE_DIR / str(meta["file"])
        templates.append({
            "template_id": template_id,
            "label": meta["label"],
            "filename": meta["file"],
            "exists": path.exists(),
            "required_keys": meta["required_keys"],
        })

    return {
        "message": "clinical_doc_templates",
        "mode": "clinical_docs_export_api_v1",
        "templates": templates,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "executes_real_import": False,
    }


@router.post("/render-preview", response_model=dict)
def preview_clinical_doc_context(
    data: ClinicalDocRenderIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    meta = _template_meta(data.template_id)
    case = _case_or_404(db, data.case_id, user)
    context = _build_context(case, data=data, user=user, template_id=str(meta["template_id"]))
    diagnostic_data_merge = _clinical_docs_diagnostic_data_merge_for_case(
        db,
        case,
        include=bool(data.include_diagnostic_data),
    )
    context = _apply_diagnostic_data_context_to_clinical_doc_context(context, diagnostic_data_merge)

    missing_required = [
        key for key in meta["required_keys"]
        if not _text(context.get(key))
    ]

    return {
        "message": "clinical_doc_render_preview",
        "mode": "clinical_docs_export_api_v1",
        "template_id": meta["template_id"],
        "case_id": data.case_id,
        "document_hash": context["hash"],
        "missing_required_keys": missing_required,
        "context": context,
        "diagnostic_data_merge": diagnostic_data_merge,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "executes_real_import": False,
    }


@router.post("/render", response_class=StreamingResponse)
def render_clinical_doc(
    data: ClinicalDocRenderIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if data.output.lower() != "docx":
        raise HTTPException(status_code=422, detail="Clinical Docs Export API V1 supports output=docx only")

    meta = _template_meta(data.template_id)
    case = _case_or_404(db, data.case_id, user)
    context = _build_context(case, data=data, user=user, template_id=str(meta["template_id"]))
    diagnostic_data_merge = _clinical_docs_diagnostic_data_merge_for_case(
        db,
        case,
        include=bool(data.include_diagnostic_data),
    )
    context = _apply_diagnostic_data_context_to_clinical_doc_context(context, diagnostic_data_merge)

    missing_required = [
        key for key in meta["required_keys"]
        if not _text(context.get(key))
    ]
    if missing_required:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "missing required clinical document context keys",
                "missing_required_keys": missing_required,
            },
        )

    docx_bytes = _render_docx(Path(meta["path"]), context)
    unreplaced = _unreplaced_placeholders(docx_bytes)
    if unreplaced:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "clinical document template still contains unreplaced placeholders",
                "unreplaced_placeholders": unreplaced,
            },
        )

    filename = f"{meta['output_filename_prefix']}-case-{case.id}-{context['hash']}.docx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-PMAI-Document-Hash": context["hash"],
        "X-PMAI-Template-Id": str(meta["template_id"]),
        "X-PMAI-Writes-Database": "false",
        "X-PMAI-Creates-Case": "false",
        "X-PMAI-Diagnostic-Data-Merge": "true" if data.include_diagnostic_data else "false",
        "X-PMAI-Diagnostic-Data-Mode": CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE if data.include_diagnostic_data else "not_requested",
    }

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type=DOCX_MEDIA_TYPE,
        headers=headers,
    )
