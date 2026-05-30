# KPI SQL 草案 V1

> 本文件是 SQL 口径草案，不保证当前数据库可直接运行。  
> 当前 V1 只用于后续数据模型设计和 API 实现前的口径对齐。

## 1. 病例字段完整度率

```sql
SELECT
  ROUND(
    SUM(
      CASE
        WHEN chief_complaint IS NOT NULL AND chief_complaint <> ''
         AND weight IS NOT NULL AND weight <> ''
         AND exam_findings IS NOT NULL AND exam_findings <> ''
         AND analysis IS NOT NULL AND analysis <> ''
         AND treatment IS NOT NULL AND treatment <> ''
        THEN 1 ELSE 0
      END
    ) * 1.0 / COUNT(*),
    4
  ) AS completeness_rate
FROM cases
WHERE created_at BETWEEN :start AND :end
  AND deleted_at IS NULL;
```

## 2. 影像复拍率

依赖未来 `imaging` 表。

```sql
WITH g AS (
  SELECT case_id, body_part, modality, COUNT(*) AS c
  FROM imaging
  WHERE ts BETWEEN :start AND :end
    AND is_planned_review = 0
  GROUP BY case_id, body_part, modality
)
SELECT ROUND(
  SUM(CASE WHEN c > 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
  4
) AS repeat_rate
FROM g;
```

## 3. 回访合规率

依赖未来 `followups` 表。

```sql
SELECT ROUND(
  SUM(
    CASE
      WHEN done_at >= due_date
       AND done_at < due_date + INTERVAL '2 day'
      THEN 1 ELSE 0
    END
  ) * 1.0 /
  SUM(CASE WHEN due_date IS NOT NULL THEN 1 ELSE 0 END),
  4
) AS followup_rate
FROM followups
WHERE due_date BETWEEN :start AND :end;
```

## 4. 平均结案时长

依赖 cases 后续具备稳定的 `closed_at` 字段。

```sql
SELECT ROUND(
  AVG(EXTRACT(EPOCH FROM (closed_at - created_at)) / 3600.0),
  1
) AS avg_ttc_hour
FROM cases
WHERE status = 'closed'
  AND closed_at BETWEEN :start AND :end;
```

## 5. 重复影像占比

依赖未来 `imaging_billing` 表。

```sql
SELECT ROUND(
  SUM(CASE WHEN tag = 'duplicate' THEN fee ELSE 0 END) * 1.0 / SUM(fee),
  4
) AS duplicate_fee_share
FROM imaging_billing
WHERE bill_date BETWEEN :start AND :end;
```

## 6. QA 审计覆盖率

依赖未来 `qa_audit` 表。

```sql
SELECT ROUND(
  COUNT(DISTINCT q.case_id) * 1.0 / COUNT(DISTINCT c.id),
  4
) AS qa_coverage
FROM cases c
LEFT JOIN qa_audit q ON q.case_id = c.id
WHERE c.created_at BETWEEN :start AND :end
  AND c.deleted_at IS NULL;
```

## 7. 注意事项

- 当前 SQL 是口径草案。
- 字段名会在 KPI 数据模型 V1 中定稿。
- SQLite / PostgreSQL 日期函数不同，正式实现要以 Render PostgreSQL 为准。
- 不要在没有模型和 Alembic migration 的情况下直接把这些 SQL 接到生产 API。
