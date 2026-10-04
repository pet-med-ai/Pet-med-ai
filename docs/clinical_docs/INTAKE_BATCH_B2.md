# B2：四项医生采集问诊

2026-10-04 用户整批批准。按晕厥／抽搐、排尿异常、皮肤瘙痒／脱毛、跛行／疼痛的顺序实现；每项完成本地回归及 CI 检查点后继续下一项。

基线 `482b484071b00a28e96cd81b1ead71712bd84354`，树 `c2d804f635262b843997e3fd0ab6ffd071bcd21a`。独立分支 `feat/intake-batch-b2-20261004`；一个新草稿 PR 目标为 B1 分支 `feat/intake-batch-b1-20261004`。不合并、不部署、不操作生产数据，不改数据库或依赖，不启用真实 R1。

## 共同验收

犬猫临床草稿，由医生记录原文；不自动诊断、分类紧急程度、解释阈值或生成处方。六种回答状态、Unicode、单位、时段和资料来源分别保存，空白不补成正常。停用条件分支保留只读原文，当前 AI 上下文只包含活动分支的已记录状态；本批不新增自由文本否定语义解析，仍需医生核对。

独立模板版本及指纹；账号、动物、物种、会话、主诉、模板或输入变化及刷新均使旧确认失效。旧输入不自动映射到新模板；问卷未完成也能收起处理当前诊疗。复用 AI 失败的手工保存及未知结果 GET 核对；不盲目重发 POST。

保存、重新登录回看、更正、旧文书确认失效和两类 DOCX 导出均验证；门诊继续包含宠主姓名及毛色。每项犬猫各一例，最终八个新合成病例、十六份新文书。保留腹泻及 B1 回归，真实 Chromium 与隔离 PostgreSQL 验证并发保存和新进程回读。不连接外部模型及生产数据。

CI 保留固定 main、M7、身份补充的提交/树检查，将 B1 范围冻结在其最终提交，单独验证 B2 精确二十路径。原测试断言与初始 JS 460000 字节阈值不变。证据每片 22 MiB，最多八片；完整文件、哈希和重组校验不变。

## 执行预算

最多 20 个不同路径；4 轮首次实现 + 2 轮共享修正；4 次完整本地回归；最多 6 次候选 CI（含主动重跑）。一个分支、一个草稿 PR。预算单独记账，不沿用 B1 剩余额度。最终提交、验证及实际用量在草稿 PR 和 B2 页面记录，不为补写状态重复触发成功 CI。

## B2-01 实现检查点

晕厥／抽搐分别记录意识、姿势和肢体动作，以及事件前、中、后、情境、持续时间与单位、次数、既往事件、用药和资料来源；未观察或不确定不转成结论。共用参数化测试扩展至本批模板，按已存在的模板逐项运行。本提交随后执行完整本地回归 1 和候选 CI 1。

问卷仍待医生审阅；自动测试和渲染不代表 Word/WPS 人工验收。M6 其余五份人工验收继续后补。

## 允许路径

- `knowledge-base/companion/intake/syncope_seizure.json`
- `knowledge-base/companion/intake/urinary_abnormality.json`
- `knowledge-base/companion/intake/itching_hair_loss.json`
- `knowledge-base/companion/intake/lameness_pain.json`
- `backend/chief_complaint_intake.py`
- `backend/main.py`
- `frontend/src/chiefComplaintIntakeState.js`
- `frontend/src/components/ChiefComplaintIntake.jsx`
- `frontend/src/App.jsx`
- `frontend/src/consultDraft.js`
- `tests/test_chief_complaint_intake.py`
- `frontend/tests/chief-complaint-intake.test.jsx`
- `tests/acceptance/chief_complaint_intake_checks.cjs`
- `tests/acceptance/postgres_checks.py`
- `.github/workflows/consult-browser-postgres.yml`
- `docs/clinical_docs/INTAKE_BATCH_B2.md`
- `tests/test_clinical_doc_lifecycle.py`
- `frontend/tests/consult-draft.test.jsx`
- `tests/test_consult_first_save.py`
- `frontend/tests/consult-first-save.test.jsx`

## B2-02 实现检查点

B2-01 候选 `e5817dd6107eb1a072be98694c26c78662fbe30e` 的三组适用 CI 全部通过：[浏览器与 PostgreSQL](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/37194687178)。本地后端 117/117、React 298/298、Chromium 40/40，含新增犬猫四份 DOCX；零依赖漏洞，初始 JS 457013 字节。

新增排尿异常：实际排尿与尝试频次、单次尿量、用力、疼痛、尿液外观、最后明确排尿时间、观察者和既往处理分别记录。单位、估测、不确定及多宠无法归属的原文不解释为结论；与多饮多尿模板和核对状态互不通用。参数化前端断言扩展至所有主诉间的绑定不匹配。独立病史保留工作流因 B2 未触及其路径而不启动，将同一原测试加入本批浏览器/PG CI；不修改或削弱旧断言。

本实现提交后执行完整本地回归 2、候选 CI 2；预算规划 10/20 路径、2/4 首次实现、0/2 修正。以 PR #47 的候选提交和结果为准。

## B2-03 实现检查点

B2-02 候选 `c64e104291be2c94512e82450bb3afa08da62765` 三组 CI 全部通过：[浏览器与 PostgreSQL](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/37195215974)。本地后端 118/118、React 311/311、Chromium 50/50，含 B2 累计八份实际 DOCX。病史原测试已在本批 CI 运行。

新增皮肤瘙痒／脱毛，两个观察各有独立状态及条件分支。分别记录部位、分布、皮肤和耳部观察、接触、季节、驱虫、用药及处理后的原始观察；不确定范围与无法观察仍保留，不推断病因。新增犬猫独立状态测试，否定瘙痒不影响已观察的毛发变化，旧分支不进入活动上下文。

本实现提交后执行完整本地回归 3、候选 CI 3；预算规划 11/20 路径、3/4 首次实现、0/2 修正。通过后继续跛行／疼痛；实时证据以草稿 PR #47 为准。

## B2-04 最终实现检查点

B2-03 候选 `11afe9fe64c333f100825b24bca45c4b6ae208ec` 三组 CI 全部通过：[浏览器与 PostgreSQL](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/37195710679)。本地后端 119/119、React 324/324、Chromium 60/60，B2 累计十二份 DOCX 原文比较通过；初始 JS 457090 字节，审计零漏洞。

新增跛行／疼痛：部位、侧别、单肢或多肢、起病与变化、负重、休息、活动、疼痛反应、已知外伤与既往处理独立记录。无法定位、观察不全、侧别或肢数不明保持原状态；不从其余观察推断定位。疼痛与外伤各有条件分支，停用分支只读保留。新增犬猫观察隔离测试。

四项模板均已启用，通用回归覆盖 B1 三项与 B2 四项；腹泻回归继续保留。最终将交付四项 × 犬猫 × 两类文书共十六份新增合成样本；每份核对完整病史、状态、长原文与门诊姓名毛色。实际 PostgreSQL 并发保存及独立进程回读随最终候选验证。

本实现提交后执行完整本地回归 4、候选 CI 4。计划实际用量 12/20 路径、4/4 首次实现、0/2 共享修正、4/4 完整本地回归、4/6 候选 CI。最终提交与树、CI、实际预算及样本包以 [草稿 PR #47](https://github.com/pet-med-ai/Pet-med-ai/pull/47) 与 B2 任务页为准，不为补写结果重复触发成功 CI。文案仍需医生审阅，自动渲染不代替人工 Word/WPS 验收；不合并、不部署、不操作生产数据。
