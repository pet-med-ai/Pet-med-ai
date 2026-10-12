# B4：问诊输入依据与无依据候选修复

2026-10-05 用户批准：最多 18 个文件、1 轮首次实现 + 3 轮修正、2 次完整本地回归、3 次候选 CI；一个分支、一个草稿 PR。一个提交触发的适用工作流合计一次候选 CI，主动重跑另计。不挪用 B3 余额。

基线提交 `59dcb643510e75d76efd0147545565a0fe327e3c`，树 `a6a28084a251b38abd4b2e6a2c6348e33a846582`。独立分支 `feat/consult-evidence-b4-20261005`，草稿 PR 目标 B3；B3 保留。最终验证结果和实际预算记于 PR，避免补写结果触发重复 CI。

## 范围与行为

修复当前犬猫问诊路径：问题标签不会自动成为症状；自由文本中的明确否定、未知、既往时间和冲突分别记录。简单单症状追问的肯定回答可提供依据；多症状问题仅答“有”保持待核对。问卷状态与原文分开处理，停用分支继续留在病史但不参与推断。普通追问不再裁掉原文首尾空白。

基于现有特征和条件规则生成疾病候选，犬猫知识库整组参考目录不再直接作为患者候选，也不在没有依据时默认胃肠疾病。每项候选返回命中的特征；输入记录保留来源、原文、判断状态。没有可用症状依据或存在未知/时间/冲突时显示“待核对”；明确当前高风险特征仍显示高风险并要求核对冲突。信息未知不等于正常。

限定的规则解析不是通用中文理解。只支持已测试的显式表达；复杂否定范围、复合问题和未明确当前状态的既往表述保留待医生核对。现有词表和临床规则仍可能漏识别或误识别，技术回归不代表医学有效性或临床安全性认证。异宠路径不在本批语义修复范围。没有新增医学阈值、处方或外部模型。

## 验收

- 原始复现：未见黑便；复合问题回答“没有”“不清楚”；常规体检；仅皮肤瘙痒。
- 对照与边界：黑便、干呕伴腹胀、无尿、呼吸困难、抽搐；否定与阳性并存、前后冲突、双重否定、既往记录、不明确否定范围、未知问卷和停用条件分支。
- 犬猫真实认证接口、隔离 SQLite、原生 PostgreSQL 并发一次保存及新进程回读；保留全部既有回归。
- 真实 Chromium 查看依据和待核对提示、回答追问、人工核对保存、重新登录回看、两类实际 DOCX。原文与待核对提示完整，确认与错误重试约束继续有效。
- 冻结 M7/B1/B2/B3 范围检查，B4 自己的增量限制；保留初始 JS 460000 字节门限、CI 完整证据分卷检查。成功 CI 不重跑。

不合并、不部署、不操作生产数据；不改数据库 schema 或依赖，不迁移、不恢复、不启用真实 R1。M6 五份 Word/WPS 人工检查继续后补。文书模板未改，生成样本只是技术验证，仍需医生审核。

## 允许路径

- `backend/clinical_evidence.py`
- `backend/feature_engine.py`
- `backend/companion_animal_knowledge.py`
- `backend/diagnosis_engine.py`
- `backend/risk_engine.py`
- `backend/orchestrator.py`
- `backend/dynamic_consult.py`
- `backend/main.py`
- `frontend/src/App.jsx`
- `frontend/src/components/ConsultEvidence.jsx`
- `frontend/tests/consult-evidence.test.jsx`
- `frontend/tests/run-consult-update-review.mjs`
- `tests/test_clinical_evidence.py`
- `tests/test_consult_evidence.py`
- `tests/acceptance/evidence_checks.cjs`
- `tests/acceptance/postgres_checks.py`
- `.github/workflows/consult-browser-postgres.yml`
- `docs/clinical_docs/CONSULT_EVIDENCE_B4.md`
