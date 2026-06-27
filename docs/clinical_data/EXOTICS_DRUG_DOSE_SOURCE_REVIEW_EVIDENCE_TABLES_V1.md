# Exotics Drug Dose Source Review Evidence Tables V1

        ## Purpose

        This stage creates source-review evidence table shells for future exotic-species medication safety review.

        It is not a dose engine, not a prescription engine, and not a treatment-plan engine. It does not contain evidence rows with usable medication instructions.

        ## Current level

        ```text
        current_level=evidence_tables_schema_only_not_dose_engine
        is_dose_engine=false
        is_prescription_engine=false
        is_treatment_plan_engine=false
        source_review_status=evidence_tables_schema_ready_not_started
        drug_dose_status=not_reviewed_not_enabled
        dose_output_enabled=false
        ```

        ## Species groups

        ```text
        rabbit, bird, ferret, turtle, lizard, snake, amphibian, fish, guinea_pig, hamster, chinchilla, rat_mouse, hedgehog, sugar_glider
        ```

        ## Review domains

        - analgesia_and_pain_control_source_review: Pain-control source evidence table shell
- antimicrobial_source_review: Antimicrobial source evidence table shell
- antiparasitic_source_review: Antiparasitic source evidence table shell
- fluid_and_supportive_care_source_review: Supportive-care source evidence table shell
- sedation_anesthesia_risk_source_review: Sedation/anesthesia risk source evidence table shell
- emergency_stabilization_source_review: Emergency stabilization source evidence table shell

        ## Allowed columns

        - table_id: stable table identifier
- species_group: target exotic species group
- review_domain: source review domain
- source_id: internal source identifier only
- source_type: textbook, formulary, label, paper, review, or guideline category
- citation_key: short bibliographic key without medication directions
- citation_metadata_status: missing / pending_review / reviewed metadata state
- species_applicability_note: qualitative species applicability note
- indication_category: high-level indication category
- evidence_strength_hint: qualitative evidence strength only
- contraindication_theme: qualitative safety theme
- monitoring_theme: qualitative monitoring theme
- source_conflict_note: qualitative conflict note without usable medication instructions
- reviewer_initials: source reviewer initials
- review_status: not_started / in_review / reviewed / rejected

        ## Blocked columns

        - numeric_dose_value: blocked
- dose_unit: blocked
- route_text: blocked
- frequency_text: blocked
- duration_text: blocked
- prescription_direction: blocked
- treatment_protocol: blocked
- client_instruction: blocked

        ## Evidence tables

        See:

        ```text
        docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_MATRIX_V1.csv
        docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_SCHEMA_V1.csv
        ```

        The matrix defines table shells for each species group and review domain. V1 does not populate real source evidence rows.

        ## Safety boundary

        ```text
        no DB write
        no Case write
        no DiagnosticReport write
        no Observation write
        no ImagingStudy write
        no ai_summary write
        no audit log write
        no final diagnosis
        no diagnostic conclusion
        no treatment plan
        no prescription
        no drug dose
        no drug route
        no drug frequency
        no client-facing output
        no external AI/provider call
        no real EMR/lab/DICOM/device ingest
        requires_human_review=true
        clinician_signoff_required=true
        ```

        ## Static validation

        ```bash
        python3 scripts/validate_exotics_drug_dose_source_review_evidence_tables.py
        bash scripts/ci_static_checks.sh
        ```

        ## Decision

        ```text
        decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_V1
        ```
