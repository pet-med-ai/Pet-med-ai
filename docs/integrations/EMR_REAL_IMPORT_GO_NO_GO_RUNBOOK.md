# EMR 真实导入前 Go / No-Go Runbook V1

> 阶段定位：本文件是 EMR Webhook 从 dry-run / receipt / review action 进入真实导入前的安全门禁。  
> 本阶段只做 runbook 与模板，不创建病例、不更新病例、不下载附件、不写真实导入代码。

## 1. 背景

Pet-Med-AI 当前已经完成以下 EMR Webhook 安全前置能力：

```txt
EMR Webhook 规范文档
EMR Webhook dry-run 接收端
Webhook inbox / receipt 数据模型
EMR Webhook receipt persistence
EMR → Case 映射 dry-run
EMR Webhook inbox review API
EMR Webhook inbox detail UI
EMR Webhook inbox review action
```

下一步如果要进入真实导入，必须先通过本 Runbook 的 Go / No-Go 门禁。

## 2. 本阶段安全边界

本阶段仍然不做：

```txt
不创建 Case
不更新 Case
不下载附件
不写真实导入队列
不把 webhook_inbox 自动推进生产病例
不绕过临床签字
不绕过回滚确认
```

本阶段只输出：

```txt
真实导入前 Go / No-Go 判断标准
导入批次冻结模板
临床签字模板
回滚决策模板
上线后监测模板
```

## 3. Go 条件

真实导入前，必须同时满足以下条件。

### 3.1 技术前置

```txt
1. Render PostgreSQL 已升级到当前 Alembic head
2. 线上 smoke ALL PASS
3. webhook_inbox API 可查询 receipt
4. review action 已能写入 audit_log
5. EMR → Case mapping dry-run 对目标样本通过
6. 幂等键 Idempotency-Key 无批内重复
7. 失败样本已全部落地为错误清单
8. 所有待导入样本均有 batch_id
```

### 3.2 数据前置

```txt
1. 每个 receipt 都有 receipt_id
2. 每个 receipt 都有 idempotency_key
3. 每个 receipt 都有 payload_hash
4. 每个 receipt 都有 mapped_case_preview
5. required mapping fields 缺失率为 0
6. 需要临床判断的 warning 已处理
7. external_case_id / external_encounter_id 映射明确
8. 未同意或已撤回同意的客户数据已排除
```

### 3.3 临床前置

```txt
1. 临床负责人完成抽查
2. 抽查比例 >= 5% 或 >= 200 条，取较大者
3. 高风险 / 异常 warning 样本 100% 抽查
4. 诊断 / 主诉 / 病史 / 检查摘要可读
5. 影像 / 附件仅作为外链或摘要，不自动下载
6. 临床签字完成
```

### 3.4 运营前置

```txt
1. 导入窗口已公告
2. 旧 EMR 进入只读或增量冻结窗口
3. 回滚负责人在线
4. Render 数据库备份确认
5. 导入期间暂停无关 schema 变更
6. 导入完成后 24 小时监控负责人明确
```

## 4. No-Go 条件

出现任一条件时，不得进入真实导入：

```txt
1. 线上 smoke 未通过
2. Alembic current 不是 head
3. webhook_inbox 有未处理 rejected 记录
4. required fields 缺失
5. duplicate idempotency_key 未解释
6. 临床抽查未签字
7. 数据撤回 / opt-out 未过滤
8. 回滚快照未确认
9. 导入窗口未冻结
10. 负责人缺席
```

## 5. 真实导入前冻结流程

### 5.1 批次冻结

每个导入批次必须生成：

```txt
batch_id
source_system
source_export_time
record_count
payload_hash_manifest
reviewed_receipt_count
ready_for_import_count
rejected_count
clinical_signoff_id
rollback_snapshot_id
```

冻结后不允许继续修改批次内容。若修正数据，必须生成新 batch。

### 5.2 推荐批次命名

```txt
emr-import-YYYYMMDD-wave01
emr-import-YYYYMMDD-wave02
```

## 6. 回滚预案

真实导入前必须准备回滚方案。

### 6.1 最小回滚条件

出现以下任一情况应考虑回滚：

```txt
1. 导入后病例数量与预期偏差 > 1%
2. 关键字段缺失率 > 阈值
3. 重复病例数量超阈值
4. 患者 / 主人明显错配
5. 医生代表抽查失败率超过阈值
6. 线上 smoke 失败
7. 导入影响现有病例查询 / 保存
```

### 6.2 回滚方式

优先级从高到低：

```txt
1. 批次标记禁用 / soft delete
2. 按 batch_id 删除导入记录
3. 恢复数据库快照
```

注意：当前 Pet-Med-AI 还没有正式 real-import batch 表，因此真实导入实现前必须先设计 batch_id 与 rollback metadata。

## 7. 上线后监测

导入后 24 小时内必须监测：

```txt
1. 新增病例数
2. 导入失败数
3. 重复病例数
4. 病例详情打开成功率
5. 病例搜索 / 筛选是否正常
6. webhook_inbox 状态分布
7. audit_log 写入成功率
8. 医生反馈问题数
```

导入后 7 天内每日至少复盘一次。

## 8. Go / No-Go 会议议程

```txt
1. 技术负责人确认 Alembic / smoke / Render 状态
2. 数据负责人确认 batch freeze 与校验报告
3. 临床负责人确认抽查和签字
4. 运营负责人确认导入窗口和回滚值班
5. 最终 Go / No-Go 决策
6. 记录决策人、时间、理由和条件
```

## 9. 禁止事项

```txt
禁止在没有临床签字的情况下真实导入
禁止跳过 dry-run 直接创建病例
禁止手动修改生产数据库绕过 audit_log
禁止用 git add . 提交导入相关代码
禁止在导入期间混入无关功能开发
```

## 10. 下一阶段建议

本 Runbook 完成后，下一阶段才考虑：

```txt
EMR real import batch model V1
```

也就是通过 Alembic 新增真实导入批次表、记录 batch_id、source、operator、status、rollback markers。仍然不要直接做真实写 Case。
