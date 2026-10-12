# CW-B17 复查计划纳入就诊资料总览

2026-10-09 00:22:11（Asia/Shanghai）用户整批批准 [20 文件方案](https://chatgpt.com/space/page_24c2da184d2c81919f73723960e8d890)，连续做到草稿 PR 与 CI。不合并、不部署、不迁移、不操作生产数据。[skip render]

## 基线与状态

CW-B16 [PR #61](https://github.com/pet-med-ai/Pet-med-ai/pull/61) 最终 HEAD `dde9b8c763e5c837b26b5f206240f31ead0cecfc`，树 `90fe32dc93a5dcc9018321a7f8b7d977fd034b66`。3 条工作流、6 个 job 成功；21/21 文件、初始 1/1、修正 1/3、本地回归 1/2、候选 CI 1/3，业务调用 0、采购 0 元。新分支 `feat/followup-plan-overview-cw-b17-20261009` 叠加于 CW-B16，草稿 PR base 保留 `feat/followup-plan-owner-docs-cw-b16-20261008`。

本批草稿候选＝实施中；CI 通过＝待精确提交验证；已合并＝否；已上线＝否；医生验收＝未验收。最终记录追加本批 PR，不为更新旧状态新增提交或重跑成功 CI。

## 行为与兼容

- 医生主动打开总览，查看本病例已保存计划、原文、上海日历日期、根记录/版本、核对账号/时间与更正/撤销原因；可精确返回原计划面板，保留未保存草稿。
- `GET /api/cases/{id}/visit-overview` 显式传 `include_followup_plan=true` 才请求新扩展。未传、false 或新开关关闭时保留 CW-B10 协议及快照语义，不查询 FollowUp。旧回包不能解释成没有计划。
- `FOLLOWUP_PLAN_OVERVIEW_ENABLED`、`FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY` 默认关闭；仅 test/development、非 Render 环境可启用。仍受总览和附件门禁约束。CW-B14 关闭时返回明确 disabled 分组，records/counts/case 为 null，不能表示零条。
- 新协议 `clinical-case-overview-cw-b17-v1` 增加 `groups.followup` 与 `followup` 内部导航目标。分组字段严格限定 status、records、counts、case、timezone；逐条复用 CW-B14 public 结构，最大 50 版本，最多一个当前计划。planned/needs_review/superseded/withdrawn 分开统计。
- 在原件锁和同一病例事务/会话内组装全部分组并生成快照；不调用嵌套计划事务。损坏记录、版本链或日期不跳过，返回 409；数据库失败为 503；认证/不可访问为 401/404，非法查询为 422。成功及可控服务错误 private/no-store，标识不写业务库。
- 总览不写病例、FollowUp、审计、附件，也不做临时文件清理。旧式随访不混入；不改变 KPI，不计算逾期风险，不登记实际完成，不预约或对外发送。
- 请求开始即清除旧快照；计划和病例写操作成功、失败或丢失回包后独立 GET。焦点、账号、病例和来源变化使旧请求失效；不拼接写回包、不自动重发写请求。导航仅按 ID/版本定位。
- 两类文书仍默认不选择计划、要求原流程全文核对。本批不改文书、模型、迁移、主路由、依赖、锁文件或部署配置。

## 验证与证据

新增真实 JWT/SQLite 路由及 13 类并发测试；原生 PostgreSQL 复验同一矩阵，追加犬猫只读控制及新进程重新登录回读。前端验证严格双协议、完整版本链与计数、禁用/空/错误区分、保存失败刷新、精确回看和草稿保护；真实 Chromium 犬猫验证包含实际成功、失败、丢失回包、50 版本与长文窄屏、重新登录和迟到响应。

历史 CW-B10 浏览器拦截精确匹配接口 pathname，适配查询参数并保留旧断言。CW-B16 及以前范围门禁在冻结提交执行；历史功能、文书、逐页渲染、知识库、依赖审计、构建和首屏预算继续在新候选验收。预计 3 条适用工作流、6 个 job，实际触发为准；不把未触发工作流记作成功。

完整证据保留全部历史和新增文件，索引与分包逐文件 SHA-256、每原始包≤22 MiB、最多 8 包、CI 上传前完整重组验证、保留 14 天；超限不能裁减。CI 内验证、索引下载和本地重组分别记录。LibreOffice 不代替 Mac Word 或医生验收。

## 独立预算

20 个指定文件；首次实现 1 次、修正≤3 轮、完整本地回归≤2 次、候选 CI≤3 次、分支/草稿 PR 各 1；业务外部调用 0 次、采购 0 元。不挪用旧批余额。每个新候选精确 HEAD 的工作流集合计一次候选 CI；主动重跑另计。定向检查不伪装全量回归。超范围或超预算先报告可审阅状态与实耗。

提交前只读复核四项相关 Render 自动部署、触发器与预览关闭；提交和 PR 保留 [skip render]。医生、原五份 Mac Word、CW-B5 真实外部语音实测继续待补，原 100 次/1 元独立；异宠 B5＝Snake Depth V2。

## 指定路径

1. `backend/clinical_followup_plan_overview.py`
2. `backend/clinical_case_overview.py`
3. `backend/clinical_case_overview_api.py`
4. `frontend/src/visitOverview.js`
5. `frontend/src/components/CaseVisitOverview.jsx`
6. `frontend/src/pages/CaseDetail.jsx`
7. `frontend/tests/followup-plan-overview.test.jsx`
8. `frontend/tests/case-detail-followup-plan-overview.test.jsx`
9. `frontend/tests/run-consult-update-review.mjs`
10. `tests/test_clinical_followup_plan_overview.py`
11. `tests/test_clinical_followup_plan_overview_concurrency.py`
12. `tests/acceptance/clinical_followup_plan_overview_checks.cjs`
13. `tests/acceptance/clinical_case_overview_checks.cjs`
14. `tests/acceptance/postgres_checks.py`
15. `tests/acceptance/fixture.py`
16. `tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json`
17. `.github/workflows/consult-browser-postgres.yml`
18. `scripts/validate_clinical_followup_plan_overview_cw_b17.py`
19. `docs/clinical_docs/CLINICAL_FOLLOWUP_PLAN_OVERVIEW_CW_B17.md`
20. `docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md`
