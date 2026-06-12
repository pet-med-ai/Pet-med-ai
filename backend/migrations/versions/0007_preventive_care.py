"""add preventive care reminder models

Revision ID: 0007_preventive_care
Revises: 0006_emr_import_results
Create Date: 2026-06-11 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_preventive_care"
down_revision = "0006_emr_import_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preventive_care_rule_sets",
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("species", sa.String(length=50), nullable=False),
        sa.Column("life_stage", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("trigger_basis", sa.String(length=100), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column("due_window_days", sa.Integer(), nullable=True),
        sa.Column("lead_days", sa.Integer(), nullable=True),
        sa.Column("requires_clinician_confirmation", sa.Boolean(), nullable=False),
        sa.Column("requires_client_consent", sa.Boolean(), nullable=False),
        sa.Column("allow_auto_send", sa.Boolean(), nullable=False),
        sa.Column("recommended_stage", sa.String(length=100), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("rule_id"),
    )
    op.create_index("ix_preventive_care_rule_sets_species", "preventive_care_rule_sets", ["species"], unique=False)
    op.create_index("ix_preventive_care_rule_sets_life_stage", "preventive_care_rule_sets", ["life_stage"], unique=False)
    op.create_index("ix_preventive_care_rule_sets_category", "preventive_care_rule_sets", ["category"], unique=False)
    op.create_index("ix_preventive_care_rule_sets_created_at", "preventive_care_rule_sets", ["created_at"], unique=False)
    op.create_index("ix_preventive_rule_species_category", "preventive_care_rule_sets", ["species", "category"], unique=False)
    op.create_index("ix_preventive_rule_stage_category", "preventive_care_rule_sets", ["recommended_stage", "category"], unique=False)

    op.create_table(
        "preventive_care_reminders",
        sa.Column("reminder_id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("pet_id", sa.String(length=64), nullable=True),
        sa.Column("pet_name", sa.String(length=255), nullable=False),
        sa.Column("species", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=True),
        sa.Column("source_rule_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("due_window_start", sa.DateTime(), nullable=True),
        sa.Column("due_window_end", sa.DateTime(), nullable=True),
        sa.Column("reminder_lead_days", sa.Integer(), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(), nullable=True),
        sa.Column("next_due_date", sa.DateTime(), nullable=True),
        sa.Column("clinician_override", sa.Boolean(), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("client_opt_out", sa.Boolean(), nullable=False),
        sa.Column("channel_preference", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["preventive_care_rule_sets.rule_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("reminder_id"),
    )
    for column in (
        "owner_id", "case_id", "pet_id", "pet_name", "species", "category", "rule_id",
        "source_rule_id", "status", "due_date", "due_window_start", "due_window_end",
        "last_completed_at", "next_due_date", "clinician_override", "client_opt_out", "created_at",
    ):
        op.create_index(f"ix_preventive_care_reminders_{column}", "preventive_care_reminders", [column], unique=False)
    op.create_index("ix_preventive_reminders_owner_status_due", "preventive_care_reminders", ["owner_id", "status", "due_date"], unique=False)
    op.create_index("ix_preventive_reminders_case_category", "preventive_care_reminders", ["case_id", "category"], unique=False)
    op.create_index("ix_preventive_reminders_pet_category_due", "preventive_care_reminders", ["pet_name", "category", "due_date"], unique=False)
    op.create_index("ix_preventive_reminders_optout_status", "preventive_care_reminders", ["client_opt_out", "status"], unique=False)

    op.create_table(
        "preventive_care_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("reminder_id", sa.String(length=64), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("pet_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("event_date", sa.DateTime(), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("lot_number", sa.String(length=100), nullable=True),
        sa.Column("next_due_date", sa.DateTime(), nullable=True),
        sa.Column("clinician_id", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reminder_id"], ["preventive_care_reminders.reminder_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    for column in ("reminder_id", "owner_id", "case_id", "pet_id", "event_type", "category", "event_date", "next_due_date", "clinician_id", "created_at"):
        op.create_index(f"ix_preventive_care_events_{column}", "preventive_care_events", [column], unique=False)
    op.create_index("ix_preventive_events_owner_type_date", "preventive_care_events", ["owner_id", "event_type", "event_date"], unique=False)
    op.create_index("ix_preventive_events_case_type_date", "preventive_care_events", ["case_id", "event_type", "event_date"], unique=False)
    op.create_index("ix_preventive_events_reminder_type", "preventive_care_events", ["reminder_id", "event_type"], unique=False)

    op.create_table(
        "preventive_care_client_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("allow_in_app", sa.Boolean(), nullable=False),
        sa.Column("allow_sms", sa.Boolean(), nullable=False),
        sa.Column("allow_wechat", sa.Boolean(), nullable=False),
        sa.Column("allow_email", sa.Boolean(), nullable=False),
        sa.Column("opt_out_all", sa.Boolean(), nullable=False),
        sa.Column("preferred_channel", sa.String(length=50), nullable=False),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preventive_care_client_preferences_id", "preventive_care_client_preferences", ["id"], unique=False)
    op.create_index("ix_preventive_care_client_preferences_owner_id", "preventive_care_client_preferences", ["owner_id"], unique=True)
    op.create_index("ix_preventive_care_client_preferences_opt_out_all", "preventive_care_client_preferences", ["opt_out_all"], unique=False)
    op.create_index("ix_preventive_client_preferences_optout", "preventive_care_client_preferences", ["opt_out_all", "preferred_channel"], unique=False)

    op.create_table(
        "preventive_care_notification_queue",
        sa.Column("notification_id", sa.String(length=64), nullable=False),
        sa.Column("reminder_id", sa.String(length=64), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("manual_review_required", sa.Boolean(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("client_opt_out_snapshot", sa.Boolean(), nullable=False),
        sa.Column("message_preview", sa.Text(), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reminder_id"], ["preventive_care_reminders.reminder_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("notification_id"),
    )
    for column in ("reminder_id", "owner_id", "case_id", "channel", "status", "scheduled_for", "sent_at", "manual_review_required", "reviewed_by", "failure_code", "created_at"):
        op.create_index(f"ix_preventive_care_notification_queue_{column}", "preventive_care_notification_queue", [column], unique=False)
    op.create_index("ix_preventive_notifications_status_scheduled", "preventive_care_notification_queue", ["status", "scheduled_for"], unique=False)
    op.create_index("ix_preventive_notifications_owner_status", "preventive_care_notification_queue", ["owner_id", "status"], unique=False)
    op.create_index("ix_preventive_notifications_manual_review", "preventive_care_notification_queue", ["manual_review_required", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_preventive_notifications_manual_review", table_name="preventive_care_notification_queue")
    op.drop_index("ix_preventive_notifications_owner_status", table_name="preventive_care_notification_queue")
    op.drop_index("ix_preventive_notifications_status_scheduled", table_name="preventive_care_notification_queue")
    for column in ("created_at", "failure_code", "reviewed_by", "manual_review_required", "sent_at", "scheduled_for", "status", "channel", "case_id", "owner_id", "reminder_id"):
        op.drop_index(f"ix_preventive_care_notification_queue_{column}", table_name="preventive_care_notification_queue")
    op.drop_table("preventive_care_notification_queue")

    op.drop_index("ix_preventive_client_preferences_optout", table_name="preventive_care_client_preferences")
    op.drop_index("ix_preventive_care_client_preferences_opt_out_all", table_name="preventive_care_client_preferences")
    op.drop_index("ix_preventive_care_client_preferences_owner_id", table_name="preventive_care_client_preferences")
    op.drop_index("ix_preventive_care_client_preferences_id", table_name="preventive_care_client_preferences")
    op.drop_table("preventive_care_client_preferences")

    op.drop_index("ix_preventive_events_reminder_type", table_name="preventive_care_events")
    op.drop_index("ix_preventive_events_case_type_date", table_name="preventive_care_events")
    op.drop_index("ix_preventive_events_owner_type_date", table_name="preventive_care_events")
    for column in ("created_at", "clinician_id", "next_due_date", "event_date", "category", "event_type", "pet_id", "case_id", "owner_id", "reminder_id"):
        op.drop_index(f"ix_preventive_care_events_{column}", table_name="preventive_care_events")
    op.drop_table("preventive_care_events")

    op.drop_index("ix_preventive_reminders_optout_status", table_name="preventive_care_reminders")
    op.drop_index("ix_preventive_reminders_pet_category_due", table_name="preventive_care_reminders")
    op.drop_index("ix_preventive_reminders_case_category", table_name="preventive_care_reminders")
    op.drop_index("ix_preventive_reminders_owner_status_due", table_name="preventive_care_reminders")
    for column in (
        "created_at", "client_opt_out", "clinician_override", "next_due_date", "last_completed_at",
        "due_window_end", "due_window_start", "due_date", "status", "source_rule_id",
        "rule_id", "category", "species", "pet_name", "pet_id", "case_id", "owner_id",
    ):
        op.drop_index(f"ix_preventive_care_reminders_{column}", table_name="preventive_care_reminders")
    op.drop_table("preventive_care_reminders")

    op.drop_index("ix_preventive_rule_stage_category", table_name="preventive_care_rule_sets")
    op.drop_index("ix_preventive_rule_species_category", table_name="preventive_care_rule_sets")
    op.drop_index("ix_preventive_care_rule_sets_created_at", table_name="preventive_care_rule_sets")
    op.drop_index("ix_preventive_care_rule_sets_category", table_name="preventive_care_rule_sets")
    op.drop_index("ix_preventive_care_rule_sets_life_stage", table_name="preventive_care_rule_sets")
    op.drop_index("ix_preventive_care_rule_sets_species", table_name="preventive_care_rule_sets")
    op.drop_table("preventive_care_rule_sets")
