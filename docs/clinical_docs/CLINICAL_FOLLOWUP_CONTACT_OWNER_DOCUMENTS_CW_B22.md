# CW-B22 人工随访记录纳入宠主说明草稿

2026-10-09 18:48:52（Asia/Shanghai）用户批准 [22 文件范围与独立预算](https://chatgpt.com/space/page_c18f00bd8df08191a7ed4bf567b55d12)，连续做到叠加草稿 PR 和精确 HEAD 的全部适用 CI。[skip render]

## 基线和预算

承接 CW-B21 PR #66 的 `7793ec36df0b79b1c82a770a8b5276d7739c3303`，树 `d83122335230f8b767053de4fca0e837dfc39514`。分支 `feat/followup-contact-owner-docs-cw-b22-20261009`；PR base 为 `feat/followup-contact-docs-cw-b21-20261009`，不从 main 丢失前批成果。

22 路径（9 新增、13 修改），初始实现 1、修正≤3、完整本地回归≤2、候选 CI≤3、分支/草稿 PR 各 1、外部业务调用 0、新采购 0 元。不得挪用旧批次预算；范围由本批校验器固定。最终结果、失败证据和实耗更新 PR，不为旧状态文字新增收尾提交或重跑成功 CI。

不合并、不部署、不迁移、不恢复或操作生产数据。每次提交前只读核对四个 Render 服务的自动部署、触发器和 PR 预览关闭；提交与 PR 保留 `[skip render]`。main 与正式前后端保持 `793894523be602bd8da265f8f7e8e63e417027a7`。

## 医生流程

宠主说明默认不选、不读取联系记录。医生主动选择一条当前 `recorded` 版本，重新读取正文和全部附节，核对后下载未签署 DOCX。只接受同病例的一条有效版本；旧版、撤销版不自动替换为新版本。

逐字保留联系时间（上海）、方式、实际结果、记录和后续安排原文、更正原因、登记账号/时间、ID/根/版本。显示当前病例、联系登记时和来源计划保存时身份。来源冻结原文保留日期、目的、项目、提前返回条件、备注和核对信息，另列来源当前状态。来源后续更正或撤销不抹去联系事实；来源链、审计损坏则拒绝。

选择和完整预览提醒医生：原文可能含内部备注或旧身份；核对是否适合出示给宠主，可取消纳入，或回到原记录更正。系统不自动删改、不生成面向宠主的改写、不发送。历史来源不自动成为当前安排；当前计划仍独立选择。联系不代表已复诊、完成检查、改善或关闭计划。

## 协议与隔离

只扩展 `owner_visit_summary_zh`；选择仍为严格五字段 `{id, version, token, source_token, case_token}`。新增 owner schema `clinical-followup-contact-owner-documents-cw-b22-v1` 和响应 `template_id` 绑定。CW-B21 门诊 schema、字段及旧请求保持原状；两个模板的快照不能互用。

`FOLLOWUP_CONTACT_OWNER_DOCUMENTS_ENABLED` 与 `FOLLOWUP_CONTACT_OWNER_DOCUMENTS_SYNTHETIC_ONLY` 默认关闭；同时要求 CW-B21 联系文书、CW-B14/CW-B19 基础开关、test/development 且非 Render。未选请求不依赖新开关、不读联系、不改变快照。

支持检验、影像、当前计划与联系的组合；拒绝检验前后对照（含显式 null）与 `include_diagnostic_data`。当前计划组合传递真实模板，不能绕过 CW-B16 宠主说明计划开关。完整内容快照绑定账号、模板字节、当前病例、记录、来源、审计摘要及全部选定附节。

复用现有 Case 事务和原件锁，完整读取及 DOCX 字节生成完成前不释放；不嵌套数据库会话。不写病例、FollowUp、AuditLog、附件或清理原件，不增加模型或迁移。审计 SQL metadata 使用 ORM extra_data；datetime 按 ISO 序列化。保留 50 版本/100 审计 cap+1、真实 JWT、404 归属检查及 private/no-store。

选择、取消、刷新、病例/账号/模板切换、焦点与可见性变化、相关写请求开始均使确认失效；选择器收起时保护仍有效。成功、失败和丢回复后独立回读；迟到预览或下载不能恢复确认。准确回看保留同病例草稿和未知保存结果，无新增临床浏览器持久化。

## 验证与证据

保留历史测试及命令；仅调整批准的三处 CW-B21 模板边界断言。新增 owner 后端、SQLite 并发、历史隔离、真实 CaseDetail 与 Chromium 犬猫测试。覆盖模板串用、独立开关、当前计划开关、显式 null 对照、逐字原文、三类身份、历史来源、草稿、未知保存状态、实际下载和重新登录。

原生 PostgreSQL 覆盖独立连接并发和新进程双账号重新登录后回读；新回读函数定义在 `--readback` 早退出之前。SQLite 预检不代替原生 PostgreSQL。四类完整 DOCX 为短记录、最大长度、历史来源/日期、检验+影像+当前计划+联系；逐字 ZIP/XML 核验并渲染、查看全部页面。

保留历史冻结门禁、30 分钟综合验收超时、首屏 JS≤460000 字节、单 chunk≤500000 字节和七个次级路由按需加载。完整证据索引保留全部历史内容，原始分包≤22 MiB、≤8 包、下载 ZIP<25 MiB、逐文件 SHA256、CI 重组校验、14 天保留。CI 校验与实际索引/分包取回分别记录。

草稿候选＝实施中；CI 通过＝待精确 HEAD；未合并、未上线、医生未验收。最终 PR 记录优先于冻结状态。医生验收、原五份 Mac Word、CW-B5 原独立 100 次/1 元真实外部语音实测待补；本批不使用其额度。异宠 B5＝Snake Depth V2。LibreOffice 检查不替代医生与 Mac Word 验收。

## 指定路径

1. `backend/clinical_followup_contact_documents.py`（修改）
2. `backend/clinical_docs_api.py`（修改）
3. `frontend/src/followupContactDocuments.js`（修改）
4. `frontend/src/components/ClinicalDocFollowupContactSelection.jsx`（修改）
5. `frontend/src/components/ClinicalDocReview.jsx`（修改）
6. `frontend/tests/followup-contact-owner-documents.test.jsx`（新增）
7. `frontend/tests/case-detail-followup-contact-owner-documents.test.jsx`（新增）
8. `frontend/tests/followup-contact-documents.test.jsx`（修改）
9. `frontend/tests/run-consult-update-review.mjs`（修改）
10. `tests/test_clinical_followup_contact_owner_documents.py`（新增）
11. `tests/test_clinical_followup_contact_owner_document_concurrency.py`（新增）
12. `tests/test_clinical_followup_contact_owner_document_isolation.py`（新增）
13. `tests/test_clinical_followup_contact_documents.py`（修改）
14. `tests/acceptance/clinical_followup_contact_owner_document_checks.cjs`（新增）
15. `tests/acceptance/clinical_followup_contact_document_checks.cjs`（修改）
16. `tests/acceptance/postgres_checks.py`（修改）
17. `tests/acceptance/fixture.py`（修改）
18. `tests/fixtures/clinical_followup_contact_owner_documents_cw_b22_cases.json`（新增）
19. `.github/workflows/consult-browser-postgres.yml`（修改）
20. `scripts/validate_clinical_followup_contact_owner_documents_cw_b22.py`（新增）
21. `docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACT_OWNER_DOCUMENTS_CW_B22.md`（新增）
22. `docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md`（修改）
