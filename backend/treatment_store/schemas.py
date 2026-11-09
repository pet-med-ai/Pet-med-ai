"""Strict payloads. Clinical identity and provenance never come from typed names."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Diagnosis(Strict):
    label: str = Field(min_length=1, max_length=500)
    code_system: str | None = Field(default=None, max_length=100)
    code: str | None = Field(default=None, max_length=100)


class Treatment(Strict):
    goals: list[Annotated[str, Field(max_length=1000)]] = Field(
        default_factory=list, max_length=50
    )
    management_text: str = Field(max_length=30000)
    monitoring_text: str = Field(default="", max_length=10000)
    followup_text: str = Field(default="", max_length=10000)


class Provenance(Strict):
    ai_generation_ids: list[str] = Field(default_factory=list, max_length=0)
    voice_transcript_revision_ids: list[str] = Field(default_factory=list, max_length=0)


class Content(Strict):
    schema: Literal["treatment-content-v1"] = "treatment-content-v1"
    diagnoses: list[Diagnosis] = Field(max_length=50)
    assessment: str = Field(default="", max_length=30000)
    treatment: Treatment
    linked_orders: list = Field(default_factory=list, max_length=0)
    provenance: Provenance = Field(default_factory=Provenance)


class Draft(Strict):
    content: Content


class Freeze(Strict):
    draft_version: int = Field(ge=1)
    expected_source_epoch: int = Field(ge=1)


class Review(Strict):
    decision: Literal["approve", "request_revision", "reject"]
    reason: str = Field(min_length=1, max_length=2000)


class Sign(Strict):
    review_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    challenge_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )


class Amend(Strict):
    base_signature_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    reason: str = Field(min_length=1, max_length=2000)


class Revoke(Strict):
    challenge_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    reason: str = Field(min_length=1, max_length=2000)


class Reauthenticate(Strict):
    org_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    clinic_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    case_id: int = Field(ge=1)
    revision_id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: Literal["sign", "revoke"]
    target_signature_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    password: str = Field(min_length=1, max_length=1024, repr=False)


class Cancel(Strict):
    operation: Literal[
        "draft.save", "revision.freeze", "review", "sign", "amend", "revoke"
    ]
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str = Field(min_length=1, max_length=2000)
