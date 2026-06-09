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
    from backend.models import Case
except ModuleNotFoundError:
    from auth_jwt import get_current_user
    from db import get_db
    from models import Case


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


def _render_docx(template_path: Path, context: Dict[str, str]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(template_path, "r") as zin:
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                raw = zin.read(item.filename)
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
    }

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type=DOCX_MEDIA_TYPE,
        headers=headers,
    )
