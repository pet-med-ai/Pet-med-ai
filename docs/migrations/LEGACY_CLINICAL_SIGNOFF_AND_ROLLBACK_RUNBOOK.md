# 旧病例导入临床签字与回滚 Runbook V1

> 阶段定位：真实导入前的临床验收、Go/No-Go、切换、回滚与上线后监测手册。  
> 本阶段只新增文档和模板，不写数据库、不调用真实导入、不创建病例、不修改后端运行逻辑。

## 1. 使用场景

本 Runbook 用于旧系统病例数据正式进入 Pet-Med-AI 前的最后安全门槛，覆盖：

- 旧病例 CSV 样本 dry-run 后的临床抽查。
- API dry-run batch report 的业务确认。
- 正式导入前的 Go / No-Go 决策。
- 导入失败或上线后发现严重问题时的回滚流程。
- 上线后 1–7 天的数据质量监测。

当前阶段不执行真实导入。真实导入必须在单独阶段实现，并且必须先通过本 Runbook 的签字流程。

## 2. 前置条件

开始临床签字与回滚准备前，必须确认：

1. `旧系统数据迁移清单与 CSV 样板 V1` 已完成。
2. `旧病例导入预校验器 V1` 已完成。
3. `旧病例导入 dry-run V1` 已完成。
4. `旧病例导入 API mock V1` 已完成。
5. `旧病例导入 API dry-run V2` 已完成。
6. `旧病例导入 pilot batch V1` 已完成。
7. 本地 smoke：`ALL PASS`。
8. 线上 smoke：`ALL PASS`。
9. Alembic baseline 已完成，Render PostgreSQL 已确认 `current = 0001_baseline (head)`。
10. 正式导入前目标库有可用备份或快照。

## 3. 样本抽查规则

推荐最低抽查口径：

- 若 pilot batch ≤ 200 条：抽查全部或不少于 50 条。
- 若 pilot batch > 200 条：抽查不少于 5%，且不少于 200 条。
- 必须覆盖：
  - 犬病例。
  - 猫病例。
  - 异宠病例，如有。
  - 高风险病例。
  - 有影像元数据病例。
  - 有随访到期病例。
  - 字段缺失较多的边缘样本。

抽查人应至少包括：

- 临床负责人。
- 门诊医生代表。
- 数据迁移执行人。
- 系统负责人。

## 4. Go / No-Go 标准

### 必须通过

| 项目 | 阈值 |
|---|---|
| CSV validator errors | 0 |
| API dry-run rejected | 0 |
| `ready_for_import` | true |
| patient_name 覆盖率 | 100% |
| species 覆盖率 | 100% |
| chief_complaint 覆盖率 | 100% |
| 临床抽查严重错误 | 0 |
| 用户隔离 / 登录 / 病例列表 smoke | ALL PASS |
| 回滚方案 | 已确认 |
| 负责人签字 | 已完成 |

### 可接受但需记录

| 项目 | 处理方式 |
|---|---|
| owner_name 缺失 | 可接受，记录缺失率 |
| owner_phone 缺失 | 可接受，记录缺失率 |
| breed 缺失 | 可接受 |
| weight 缺失 | 可接受，但高风险病例建议补齐 |
| imaging_count=0 | 可接受，确认旧系统确实无影像 |
| follow_up_due 空 | 可接受，确认旧系统无随访计划 |

### 必须 No-Go

出现以下任一情况，不允许正式导入：

- 任何 CSV 必填字段批量缺失。
- case_id 或 idempotency_key 有重复。
- API dry-run 有 rejected 记录。
- 临床抽查发现诊断、病史、影像链接严重错配。
- 线上 smoke 未通过。
- 目标库没有备份 / 快照。
- 负责人未签字。
- 回滚路径未验证。

## 5. 正式切换前流程

1. 通知门诊和相关人员切换窗口。
2. 旧系统进入只读或冻结导出窗口。
3. 导出最终增量 CSV。
4. 执行 CSV validator。
5. 执行 JSONL dry-run mapper。
6. 执行 API dry-run report。
7. 生成 pilot / production review package：
   - 原始 CSV。
   - errors CSV。
   - JSONL payload。
   - API dry-run report JSON。
   - 临床抽查清单。
   - Go / No-Go checklist。
8. 临床负责人签字。
9. 系统负责人确认备份。
10. 才能进入真实导入阶段。

## 6. 回滚触发条件

正式导入阶段或上线后监测中，出现以下情况应触发回滚评估：

- 导入后 smoke 失败。
- 登录、病例列表、病例详情核心功能异常。
- 导入批次关键字段错配。
- 临床抽查严重错误数 > 0。
- 影像外链批量不可达。
- 重复病例批量产生。
- 用户隔离异常。
- 性能明显异常且影响门诊使用。
- 负责人判定存在临床风险。

## 7. 回滚动作等级

### Level 1：暂停导入

适用于真实导入尚未完成，或错误只影响后续批次。

动作：

1. 停止导入任务。
2. 保留已生成日志。
3. 锁定错误批次。
4. 修复 CSV / mapping / payload。
5. 重新 dry-run。
6. 临床负责人重新确认。

### Level 2：隐藏或隔离导入批次

适用于未来真实导入实现了 `migration_batch_id` 或批次标签后。

动作：

1. 将该批次从业务页面隐藏，或标记为待审核。
2. 保留数据库记录。
3. 禁止手工逐条删除。
4. 导出受影响 case_id 列表。
5. 修复后重新导入或恢复可见。

### Level 3：数据库快照恢复

适用于严重错配、核心功能受损或大规模错误导入。

动作：

1. 宣布系统维护。
2. 禁止继续写入。
3. 使用导入前快照恢复目标库。
4. 恢复后跑线上 smoke。
5. 临床负责人复核关键病例。
6. 记录事故复盘。

## 8. 上线后监测

正式导入后的建议监测窗口：

- T+0：导入完成后立即 smoke。
- T+1 小时：抽查病例列表、搜索、详情、动态问诊。
- T+1 天：复查临床反馈和错误日志。
- T+7 天：关闭迁移观察期或进入补导阶段。

监测指标：

| 指标 | 建议阈值 |
|---|---|
| 新系统 smoke | ALL PASS |
| 导入病例可检索率 | ≥ 99% |
| 样本病例详情打开率 | 100% |
| 严重错配 | 0 |
| 重复病例 | 0 |
| 影像外链可达率 | ≥ 98%，如有影像 |
| 随访日期有效率 | ≥ 98%，如有随访 |
| 用户隔离异常 | 0 |

## 9. 当前可执行命令

CSV 校验：

```bash
python3 scripts/validate_legacy_cases_csv.py legacy_cases.csv   --errors-out migration_errors_$(date +%Y%m%d).csv   --report-out migration_report_$(date +%Y%m%d).json
```

JSONL dry-run：

```bash
python3 scripts/legacy_cases_to_case_payloads.py legacy_cases.csv   --jsonl-out legacy_case_payloads.jsonl   --errors-out migration_errors.csv   --report-out legacy_case_payload_report.json
```

Pilot batch dry-run：

```bash
python3 scripts/run_legacy_pilot_batch.py legacy_cases.csv   --work-dir ./tmp/legacy_pilot
```

Smoke：

```bash
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

## 10. 本阶段完成标准

本阶段完成不代表可以正式导入。完成标准只是：

- 本 Runbook 已入库。
- 临床签字模板已入库。
- Go / No-Go checklist 已入库。
- 回滚决策模板已入库。
- post-go-live 监测模板已入库。
- commit / push 成功。

真实导入必须另开阶段，并且必须先完成临床签字。
