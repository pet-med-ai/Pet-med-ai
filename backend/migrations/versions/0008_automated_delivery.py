"""add automated reminder delivery data model

Revision ID: 0008_auto_delivery
Revises: 0007_preventive_care
Create Date: 2026-06-12 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008_auto_delivery"
down_revision = "0007_preventive_care"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automated_reminder_delivery_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("template_version", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("clinical_safety_text", sa.Text(), nullable=True),
        sa.Column("opt_out_text", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "template_key", "template_version", "channel", "language", "category", "review_status", "approved_by", "approved_at", "created_at"):
        op.create_index(f"ix_automated_reminder_delivery_templates_{column}", "automated_reminder_delivery_templates", [column], unique=False)
    op.create_index("ux_automated_delivery_template_version", "automated_reminder_delivery_templates", ["template_key", "template_version", "channel"], unique=True)
    op.create_index("ix_automated_delivery_template_review", "automated_reminder_delivery_templates", ["review_status", "channel", "category"], unique=False)

    op.create_table(
        "automated_reminder_delivery_attempts",
        sa.Column("delivery_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("reminder_id", sa.String(length=64), nullable=True),
        sa.Column("notification_id", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=True),
        sa.Column("template_version", sa.String(length=50), nullable=True),
        sa.Column("eligibility_result", sa.String(length=50), nullable=False),
        sa.Column("blocked_reason", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("manual_review_required", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("auto_send", sa.Boolean(), nullable=False),
        sa.Column("sends_external_message", sa.Boolean(), nullable=False),
        sa.Column("consent_snapshot", sa.JSON(), nullable=True),
        sa.Column("opt_out_snapshot", sa.JSON(), nullable=True),
        sa.Column("contact_destination_hash", sa.String(length=128), nullable=True),
        sa.Column("message_hash", sa.String(length=128), nullable=True),
        sa.Column("provider_name", sa.String(length=100), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["preventive_care_notification_queue.notification_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reminder_id"], ["preventive_care_reminders.reminder_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("delivery_id"),
    )
    for column in (
        "owner_id", "reminder_id", "notification_id", "channel", "template_key", "template_version",
        "eligibility_result", "blocked_reason", "status", "manual_review_required", "approved_by",
        "approved_at", "dry_run", "auto_send", "sends_external_message", "contact_destination_hash",
        "message_hash", "provider_name", "provider_message_id", "queued_at", "sent_at",
        "delivered_at", "failed_at", "canceled_at", "created_at",
    ):
        op.create_index(f"ix_automated_reminder_delivery_attempts_{column}", "automated_reminder_delivery_attempts", [column], unique=False)
    op.create_index("ix_automated_delivery_owner_status_channel", "automated_reminder_delivery_attempts", ["owner_id", "status", "channel"], unique=False)
    op.create_index("ix_automated_delivery_reminder_status", "automated_reminder_delivery_attempts", ["reminder_id", "status"], unique=False)
    op.create_index("ix_automated_delivery_notification_status", "automated_reminder_delivery_attempts", ["notification_id", "status"], unique=False)
    op.create_index("ix_automated_delivery_safety", "automated_reminder_delivery_attempts", ["dry_run", "auto_send", "sends_external_message"], unique=False)

    op.create_table(
        "automated_reminder_delivery_receipts",
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("delivery_id", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("raw_payload_hash", sa.String(length=128), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["automated_reminder_delivery_attempts.delivery_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("receipt_id"),
    )
    for column in ("delivery_id", "provider_name", "provider_message_id", "event_type", "status", "received_at", "signature_verified", "idempotency_key", "failure_code", "created_at"):
        op.create_index(f"ix_automated_reminder_delivery_receipts_{column}", "automated_reminder_delivery_receipts", [column], unique=False)
    op.create_index("ix_automated_receipts_delivery_status", "automated_reminder_delivery_receipts", ["delivery_id", "status"], unique=False)
    op.create_index("ix_automated_receipts_provider_event", "automated_reminder_delivery_receipts", ["provider_name", "event_type", "received_at"], unique=False)

    op.create_table(
        "automated_reminder_delivery_suppression_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("reminder_id", sa.String(length=64), nullable=True),
        sa.Column("notification_id", sa.String(length=64), nullable=True),
        sa.Column("pet_id", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["notification_id"], ["preventive_care_notification_queue.notification_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reminder_id"], ["preventive_care_reminders.reminder_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "owner_id", "reminder_id", "notification_id", "pet_id", "category", "channel", "reason", "active", "starts_at", "ends_at", "created_by", "created_at"):
        op.create_index(f"ix_automated_reminder_delivery_suppression_rules_{column}", "automated_reminder_delivery_suppression_rules", [column], unique=False)
    op.create_index("ix_automated_suppression_owner_channel_active", "automated_reminder_delivery_suppression_rules", ["owner_id", "channel", "active"], unique=False)
    op.create_index("ix_automated_suppression_category_active", "automated_reminder_delivery_suppression_rules", ["category", "active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_automated_suppression_category_active", table_name="automated_reminder_delivery_suppression_rules")
    op.drop_index("ix_automated_suppression_owner_channel_active", table_name="automated_reminder_delivery_suppression_rules")
    for column in ("created_at", "created_by", "ends_at", "starts_at", "active", "reason", "channel", "category", "pet_id", "notification_id", "reminder_id", "owner_id", "id"):
        op.drop_index(f"ix_automated_reminder_delivery_suppression_rules_{column}", table_name="automated_reminder_delivery_suppression_rules")
    op.drop_table("automated_reminder_delivery_suppression_rules")

    op.drop_index("ix_automated_receipts_provider_event", table_name="automated_reminder_delivery_receipts")
    op.drop_index("ix_automated_receipts_delivery_status", table_name="automated_reminder_delivery_receipts")
    for column in ("created_at", "failure_code", "idempotency_key", "signature_verified", "received_at", "status", "event_type", "provider_message_id", "provider_name", "delivery_id"):
        op.drop_index(f"ix_automated_reminder_delivery_receipts_{column}", table_name="automated_reminder_delivery_receipts")
    op.drop_table("automated_reminder_delivery_receipts")

    op.drop_index("ix_automated_delivery_safety", table_name="automated_reminder_delivery_attempts")
    op.drop_index("ix_automated_delivery_notification_status", table_name="automated_reminder_delivery_attempts")
    op.drop_index("ix_automated_delivery_reminder_status", table_name="automated_reminder_delivery_attempts")
    op.drop_index("ix_automated_delivery_owner_status_channel", table_name="automated_reminder_delivery_attempts")
    for column in (
        "created_at", "canceled_at", "failed_at", "delivered_at", "sent_at", "queued_at",
        "provider_message_id", "provider_name", "message_hash", "contact_destination_hash",
        "sends_external_message", "auto_send", "dry_run", "approved_at", "approved_by",
        "manual_review_required", "status", "blocked_reason", "eligibility_result",
        "template_version", "template_key", "channel", "notification_id", "reminder_id", "owner_id",
    ):
        op.drop_index(f"ix_automated_reminder_delivery_attempts_{column}", table_name="automated_reminder_delivery_attempts")
    op.drop_table("automated_reminder_delivery_attempts")

    op.drop_index("ix_automated_delivery_template_review", table_name="automated_reminder_delivery_templates")
    op.drop_index("ux_automated_delivery_template_version", table_name="automated_reminder_delivery_templates")
    for column in ("created_at", "approved_at", "approved_by", "review_status", "category", "language", "channel", "template_version", "template_key", "id"):
        op.drop_index(f"ix_automated_reminder_delivery_templates_{column}", table_name="automated_reminder_delivery_templates")
    op.drop_table("automated_reminder_delivery_templates")
