# CW-B21 人工随访记录纳入门诊病历草稿

2026-10-09 15:30:34（Asia/Shanghai）用户整批批准 [20 文件方案](https://chatgpt.com/space/page_39f4e98736c08191ab1d4da44a5c9c84)，连续做到叠加草稿 PR 和精确 HEAD 的全部适用 CI。[skip render]

## 基线、预算与边界

承接 CW-B20 PR #65 的 `a6ad9166b19984f535eed39ecd5c22a7a47b4369`，树 `1ea8dc856e567c128753b340060e282b67988a94`。分支 `feat/followup-contact-docs-cw-b21-20261009`，PR base 为 `feat/followup-contact-overview-cw-b20-20261009`。不得从 main 遗漏叠加成果。

独立预算：20 路径（12 新增、8 修改）；初始实现 1、修正≤3、完整本地回归≤2、候选 CI≤3、分支/草稿 PR 各 1；业务外部调用 0、采购 0 元。下列范围以新增校验器固定；不借用旧额度。实耗、失败证据和最终结果追加 PR，不为状态文字再提交或重跑已成功的 CI。

不合并、不部署、不迁移、不恢复或操作生产数据。每次提交前只读核对正式后端、静态前端、旧前端及 staging 自动部署、触发器和 PR 预览关闭；提交及 PR 保留 `[skip render]`。main 与正式前后端保持 `793894523be602bd8da265f8f7e8e63e417027a7`。

## 医生流程与数据含义

打开已保存病例的门诊病历草稿，主动选择一条当前有效人工随访，重新读取完整文书、核对正文和全部附节后下载未签署 DOCX。默认不选；只允许一个独立联系根的当前 `recorded` 版本。旧版本和已撤销联系不可选择，也不会自动替换为其他版本。

附节逐字保留实际联系/尝试时间（上海）、方式、结果、记录和后续安排原文、更正原因、登记账号/时间、ID/根/版本。保留 Unicode、换行、空白和模板符号。分别显示当前病例、联系登记时和来源计划保存时的动物姓名、物种、宠主姓名及病例 ID。

完整展示联系冻结的来源计划：日期、目的、项目原文、提前返回条件、备注、核对账号/时间和 ID/根/版本；另列来源当前状态。来源后来更正或撤销不抹去有效联系事实，只要完整来源及审计仍可验证，重新核对后仍可纳入。缺失或损坏明确失败。历史来源不自动成为本次复查安排；当前计划附节仍单独选择。联系结果不等同已复诊、完成检查、改善或关闭计划。

## 协议和事务

仅 `outpatient_record_zh` 接受新增 `manual_followup_contact`，精确字段为 `{id, version, token, source_token, case_token}`。显式 null、缺项、额外字段、布尔/小数 ID、非法版本/摘要均拒绝。其他模板及 `include_diagnostic_data` 组合拒绝。响应 schema 为 `clinical-followup-contact-documents-cw-b21-v1`。

`FOLLOWUP_CONTACT_DOCUMENTS_ENABLED` 与 `FOLLOWUP_CONTACT_DOCUMENTS_SYNTHETIC_ONLY` 默认关闭，须显式为 1，且 CW-B14/CW-B19 底层开关有效、环境为 test/development、非 Render。未选联系的旧请求不读联系，不要求本批开关；响应、正文、快照沿用旧行为，包括旧模板对未解析占位符的既有拒绝。

复用完整版本链和审计校验，保留 50 联系版本、100 审计 cap+1，异常不截断或修复。审计摘要使用 ORM `extra_data` 读取 SQL `metadata`，时间采用 ISO 序列化。选择绑定联系内容、当前来源状态和当前病例；完整快照另绑定账号、模板字节、冻结来源、审计摘要及其他选定附节。

复用既有 Case 事务及原件锁顺序，不嵌套会话；全部读取、复核和 DOCX 字节生成完成后才释放锁。预览/导出不写病例、FollowUp、AuditLog 或附件，也不清理原件。真实 JWT、病例归属与删除检查持续有效，成功/错误响应 private/no-store。仅联系附节不改变 `visit.follow_up`。

前端按需加载选择和预览，完整附节实际显示后才允许全文确认。选择、取消、刷新、病例/账号/模板变化、失焦/重新可见及相关写请求开始都会使旧确认失效；面板收起后保护继续生效。保存成功、失败和丢回包后独立回读，迟到预览/下载不能恢复旧确认。准确版本导航保留同病例草稿及未知保存结果，无新增临床浏览器持久化。

## 验证与证据

新增后端、SQLite 并发和隔离测试；真实 Chromium 犬猫选择/移除/完整核对/实际 DOCX 下载、迟到回包、准确回看、未保存草稿、未知保存结果及重新登录；原生 PostgreSQL 独立连接竞争与新进程双账号回读。提交前定向检查审计 JSON 和 `--readback` 依赖。SQLite 结果不代替原生 PostgreSQL。

生成短记录、最大长度、历史来源/日期边界、检验+影像+对照+当前计划+联系四类完整文书。核对 ZIP/XML 字面原文并渲染全部页面。保留全部历史测试、冻结基线门禁、首屏 JS≤460000 字节、每 chunk≤500000 字节及七个次级路由按需加载检查。

证据进入完整索引：原始分包≤22 MiB、最多 8 包、下载 ZIP<25 MiB，逐文件 SHA256 和 CI 内重组核验，保留 14 天。PR 区分 CI 核验与索引/分包实际本地取回，不能互相替代。

草稿候选＝实施中；CI 通过＝待精确 HEAD；已合并＝否；已上线＝否；医生验收＝未验收。最终对应 PR 记录优先于冻结文字。医生验收、原五份 Mac Word 实机检查、CW-B5 原独立 100 次/1 元真实外部语音实测待补；不消耗其额度。异宠 B5＝Snake Depth V2。LibreOffice 不替代医生或 Mac Word 验收。

## 指定路径

1. `backend/clinical_followup_contact_documents.py`
2. `backend/clinical_docs_api.py`
3. `frontend/src/followupContactDocuments.js`
4. `frontend/src/components/ClinicalDocFollowupContactSelection.jsx`
5. `frontend/src/components/ClinicalDocReview.jsx`
6. `frontend/src/pages/CaseDetail.jsx`
7. `frontend/tests/followup-contact-documents.test.jsx`
8. `frontend/tests/case-detail-followup-contact-documents.test.jsx`
9. `frontend/tests/run-consult-update-review.mjs`
10. `tests/test_clinical_followup_contact_documents.py`
11. `tests/test_clinical_followup_contact_document_concurrency.py`
12. `tests/test_clinical_followup_contact_document_isolation.py`
13. `tests/acceptance/clinical_followup_contact_document_checks.cjs`
14. `tests/acceptance/postgres_checks.py`
15. `tests/acceptance/fixture.py`
16. `tests/fixtures/clinical_followup_contact_documents_cw_b21_cases.json`
17. `.github/workflows/consult-browser-postgres.yml`
18. `scripts/validate_clinical_followup_contact_documents_cw_b21.py`
19. `docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACT_DOCUMENTS_CW_B21.md`
20. `docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md`
