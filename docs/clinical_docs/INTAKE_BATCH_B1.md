# B1：三项医生采集问诊

2026-10-04 用户整批批准。范围：食欲下降／消瘦、多饮多尿、咳嗽／呼吸困难；犬猫适用，临床草稿，医生确认后沿用现有保存和文书链路。

基线 `25bc2b10db8caffbe31dafc7a7bc4cebdea62bdc`（树 `d109805e9ff66e74863c74a8d29b02f7119749ed`）。分支 `feat/intake-batch-b1-20261004`，新草稿 PR 目标为 `feat/diarrhea-intake-m7-20261001`。原 PR #45 / #44 / #41 不修改；不合并、不部署、不操作生产数据，不改数据库或依赖，不启用 R1。

## 实现与验收

独立版本与指纹的模板只记录原文和明确状态；未知、空白、明确否定与停用分支不输入旧关键词引擎，原文仍完整进入病史。账号、病例、物种、会话或主诉切换使确认失效；切换模板保留旧原文，不自动重新映射。刷新只恢复输入，不恢复确认。收起问卷保留草稿。

M7 接口、草稿字段与历史快照保持兼容。新增主诉存入独立的 `chiefComplaint` 草稿字段，一次只有一个活动问卷。AI 不可用时仍可核对后进入手工新建；保存未知沿用锁和回读，导出不写病例。门诊病历保留宠主姓名与毛色。

每项犬猫各一个合成病例，真实 Chromium 完成保存、重新登录回看、更正和两类 DOCX；真实隔离 PostgreSQL 验证并发首次保存和新进程回读。测试不连接外部模型或生产数据库。旧 M7 的十八路径、补充八路径固定提交/树检查和原体积阈值保留，B1 单独检查三十路径。知识库校验加入本工作流，因独立 Validate KB 工作流只接收目标 main 的 PR。

## 执行预算

最多 30 路径；3 轮首次实现 + 3 轮共享修正；3 次完整本地回归；最多 6 次候选 CI（主动重跑另计）。一个新分支、一个新草稿 PR。先核对相同提交结果，不重复跑 CI。超预算或需要清单外文件时停止相关写操作并说明阻塞。

当前检查点：B1-01 首次实现完成，后端 114/114、React 258/258、模板、知识库、构建与体积检查通过（初始 JS 456904 字节）。提交后静态检查及针对性联网审计通过（零漏洞）。本地 Chromium + 隔离 SQLite 犬猫 10/10，四份实际 DOCX 原文比较通过。

候选 1 `52318871e18cc58afca9efd900997a540a173c2e`：病史保留、更新预览、CI Gate 成功；浏览器/PG 工作流在新增 B1 PG 用例失败，原因是旧尾部提前关闭了客户端。共享修正第 1 轮将关闭操作移动到所有用例之后，并使合成主诉使用对应问卷名称。原断言未删除、阈值未降低。将以候选 2 验证；不重复完整本地回归。

草稿 PR #46：https://github.com/pet-med-ai/Pet-med-ai/pull/46 。消耗：首次实现 1/3，共享修正 1/3，完整本地 1/3，候选 CI 2/6（含本次计划提交）。B1-02 / B1-03 待 B1-01 的 CI 通过后顺序实现。

M6 剩余五份 Word/WPS 验收继续后补。软件测试和自动渲染不代表人工 Word/WPS 验收、临床审阅或上线批准。

## 允许路径

- `knowledge-base/companion/intake/appetite_weight.json`
- `knowledge-base/companion/intake/polyuria_polydipsia.json`
- `knowledge-base/companion/intake/cough_breathing.json`
- `backend/chief_complaint_intake.py`
- `backend/diarrhea_intake.py`
- `backend/main.py`
- `frontend/src/components/ChiefComplaintIntake.jsx`
- `frontend/src/components/DiarrheaIntake.jsx`
- `frontend/src/chiefComplaintIntakeState.js`
- `frontend/src/diarrheaIntakeState.js`
- `frontend/src/App.jsx`
- `frontend/src/consultDraft.js`
- `tests/test_chief_complaint_intake.py`
- `tests/test_diarrhea_intake.py`
- `tests/test_consult_first_save.py`
- `tests/test_consult_update_preview.py`
- `tests/test_clinical_doc_lifecycle.py`
- `frontend/tests/chief-complaint-intake.test.jsx`
- `frontend/tests/diarrhea-intake.test.jsx`
- `frontend/tests/consult-draft.test.jsx`
- `frontend/tests/consult-first-save.test.jsx`
- `frontend/tests/consult-update-review.test.jsx`
- `frontend/tests/manual-case-create.test.jsx`
- `frontend/tests/run-consult-update-review.mjs`
- `tests/acceptance/postgres_checks.py`
- `tests/acceptance/chief_complaint_intake_checks.cjs`
- `tests/acceptance/diarrhea_intake_checks.cjs`
- `.github/workflows/consult-browser-postgres.yml`
- `docs/clinical_docs/INTAKE_BATCH_B1.md`
- `tests/test_manual_case_create.py`

## B1-02 检查点

B1-01 修正候选 `65d383b6d1d14a4ecabf07ff2537d88b5544e3e4` 的四组 CI 全部成功。浏览器/PG 验收：https://github.com/pet-med-ai/Pet-med-ai/actions/runs/37185695922 。

本检查点新增多饮多尿模板，饮水量、排尿频次及尿量分别保存；测量单位、时段、估测/未测与多宠家庭无法归属的原文保留。复用原权限、确认、保存和文书链路。新增原文与单位不被数值化或阈值解释的测试；共用犬猫浏览器及 PostgreSQL 用例自动覆盖两种主诉。

本候选提交后执行第 2 次完整本地回归并提交第 3 次候选 CI；实时结果以草稿 PR #46 为准。预算规划：路径 16/30，首次实现 2/3，共享修正 1/3，完整本地 2/3，候选 CI 3/6。咳嗽／呼吸困难待此项通过后继续。
