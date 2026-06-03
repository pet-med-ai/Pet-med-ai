# EMR → Case 映射 dry-run V1

## 阶段定位

本阶段把已签名的 EMR Webhook payload 映射为 Pet-Med-AI 当前 `CaseCreate` 结构的预览，并生成 import plan。

本阶段仍然只做 dry-run：

```txt
写 webhook_inbox receipt
返回 CaseCreate preview
返回 mapping quality
返回 import_plan
不创建 Case
不更新 Case
不创建 ConsultSession
不下载附件
不写 audit_log
```

## 新增接口

```txt
POST /api/webhooks/emr/case-mapping/dry-run
```

请求头与 `POST /api/webhooks/emr/dry-run` 一致：

```txt
Content-Type: application/json
X-PMAI-Timestamp: <ISO-8601 UTC>
X-PMAI-Signature: sha256=<hmac_sha256(timestamp + "." + raw_body)>
Idempotency-Key: <stable event key>
```

## 返回重点

```json
{
  "message": "emr_case_mapping_dry_run",
  "mode": "case_mapping_dry_run",
  "status": "accepted",
  "dry_run": true,
  "writes_webhook_inbox": true,
  "writes_case_database": false,
  "creates_case": false,
  "updates_case": false,
  "downloads_attachments": false,
  "mapping": {
    "case_create": {
      "patient_name": "咪咪",
      "species": "cat",
      "weight": "3.1kg",
      "chief_complaint": "呕吐、腹泻、食欲差",
      "history": "...",
      "exam_findings": "..."
    },
    "quality": {
      "ready_for_case_create_preview": true,
      "missing_required": [],
      "missing_recommended": []
    }
  },
  "import_plan": {
    "target_operation": "case_create_preview",
    "can_promote_to_real_import": false,
    "next_gate": "EMR real ingestion requires a separate audited implementation and rollback plan."
  }
}
```

## 映射原则

| EMR payload | Pet-Med-AI CaseCreate |
|---|---|
| `pet.name` | `patient_name` |
| `pet.species` | `species` |
| `pet.sex` | `sex` |
| `pet.dob` / `pet.age` | `age_info` |
| `pet.breed` | `breed` |
| `encounter.vitals.weight_kg` or `pet.weight_kg` | `weight` |
| `owner.name` | `owner_name` |
| `owner.phone` | `owner_phone` |
| `encounter.chief_complaint` | `chief_complaint` |
| `case_id / encounter_id / clinician / diagnosis_codes / procedures / meds` | `history` |
| `vitals / attachments summary` | `exam_findings` |

## 验收标准

```txt
1. 签名正确时，/api/webhooks/emr/case-mapping/dry-run 返回 202
2. response.message = emr_case_mapping_dry_run
3. response.mapping.case_create.patient_name = 咪咪
4. response.mapping.case_create.species = cat
5. response.writes_webhook_inbox = true
6. response.writes_case_database = false
7. response.creates_case = false
8. response.import_plan.can_promote_to_real_import = false
9. 重复 Idempotency-Key 返回 duplicate 且复用 receipt_id
10. 本地 / 线上 smoke ALL PASS
```

## 后续阶段

下一阶段不是直接真实入库。建议先做：

```txt
EMR Webhook inbox review API V1
```

用于查看 `webhook_inbox` 中 dry-run receipt、validation report 和 CaseCreate preview。
