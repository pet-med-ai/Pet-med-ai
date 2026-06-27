# Exotics Drug Dose Source Evidence Abstraction V1

        ## Purpose

        This stage creates a controlled evidence-abstraction protocol for future exotic-species medication source review.

        It is not a dose engine, not a prescription engine, and not a treatment-plan engine.

        ## Current level

        ```text
        current_level=evidence_abstraction_template_only_not_dose_engine
        is_dose_engine=false
        is_prescription_engine=false
        is_treatment_plan_engine=false
        source_review_status=evidence_abstraction_protocol_ready_not_started
        drug_dose_status=not_reviewed_not_enabled
        dose_output_enabled=false
        ```

        ## Species groups

        ```text
        rabbit, bird, ferret, turtle, lizard, snake, amphibian, fish, guinea_pig, hamster, chinchilla, rat_mouse, hedgehog, sugar_glider
        ```

        ## Review domains

        - analgesia_and_pain_control_source_review: Pain-control evidence abstraction without usable dosing values
- antimicrobial_source_review: Antimicrobial evidence abstraction without usable dosing values
- antiparasitic_source_review: Antiparasitic evidence abstraction without usable dosing values
- fluid_and_supportive_care_source_review: Supportive-care evidence abstraction without usable numeric protocols
- sedation_anesthesia_risk_source_review: Sedation/anesthesia risk evidence abstraction without protocol details
- emergency_stabilization_source_review: Emergency stabilization evidence abstraction without treatment protocols

        ## Allowed abstraction fields

        - source identifier
        - source type
        - citation metadata
        - species applicability
        - indication category
        - qualitative evidence-strength hint
        - qualitative contraindication theme
        - qualitative monitoring theme
        - source conflict note

        ## Blocked abstraction fields

        - numeric medication amount
        - route text
        - frequency text
        - prescription direction
        - treatment protocol
        - client-facing instruction

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

        ## Matrix

        See:

        ```text
        docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_EVIDENCE_ABSTRACTION_MATRIX_V1.csv
        ```

        The matrix intentionally records only whether a class of metadata may be abstracted. It must not contain usable dosing directions.

        ## Static validation

        ```bash
        python3 scripts/validate_exotics_drug_dose_source_evidence_abstraction.py
        bash scripts/ci_static_checks.sh
        ```

        ## Decision

        ```text
        decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_V1
        ```
