# B3：发热／精神沉郁、老年动物筛查

2026-10-04 用户整批批准。两项按顺序实现，完成共同回归后提交一个候选；不为每项重复触发相同 CI。基线 `e584f8ec8646cfbdcad6d0ef9a3fadaa465ffa02`，树 `d819cdd04f504c9ac79f7e9bc7e0feef3b90e6af`。独立分支 `feat/intake-batch-b3-20261004`，新草稿 PR 目标 B2 分支；旧 PR 保持原状。

## 范围与验收

犬猫医生采集临床草稿。发热／精神沉郁分别记录实测值、单位、时间、方法、来源和精神变化；不从触感推算体温或从体温推断精神状态。老年筛查记录日常功能、饮食饮水、排泄、活动、睡眠行为、既往疾病和用药；不自动诊断、不按年龄填入异常或正常。

六状态、原文、版本和指纹保持独立；未测、未知、未询问、无法观察不补成正常。停用条件分支保留回看，排除活动 AI 上下文。账号、动物、物种、会话、主诉或输入变化使旧确认失效。复用 AI 失败时手工保存，以及未知结果先 GET 核对，禁止盲目重发写请求。

每项犬猫各一例，共 4 个新增合成病例、8 份新增两类 DOCX；验证保存、重登回看、更正、旧文书确认失效、原文完整及门诊宠主姓名和毛色。保留 M7、B1、B2 全部回归；真实 Chromium、隔离 SQLite 和 CI 原生 PostgreSQL 的并发一次保存及新进程回读覆盖两项。保留原 CI 断言、初始 JS 460000 字节阈值和完整证据分卷重组验证。

## 预算与边界

最多 10 个不同路径；2 轮首次实现 + 2 轮修正；最多 3 次完整本地回归、4 次候选 CI（主动重跑也计数）。一个分支、一个草稿 PR。独立记账，B2 余额不挪用。最终提交、结果、实际预算和样本在草稿 PR 记录，避免为补写结果重复跑 CI。

不合并、不部署、不操作生产数据；不改数据库、依赖、诊断引擎，不调用外部模型，不启用真实 R1。发布前核对 main、B2、自动部署及预览关闭。本地原工作区 Git 元数据丢失，已使用独立克隆恢复固定远端基线，旧文件不覆盖。

已知限制：既有关键词引擎存在鉴别与紧急程度误匹配，B3 不修该引擎或自由文本否定解析；技术验收不代表临床结论正确。问卷仍需医生审阅，自动渲染不代替 Word/WPS 人工验收；M6 五份人工检查继续后补。

## 允许路径

- `knowledge-base/companion/intake/fever_lethargy.json`
- `knowledge-base/companion/intake/senior_screening.json`
- `backend/chief_complaint_intake.py`
- `frontend/src/chiefComplaintIntakeState.js`
- `frontend/src/components/ChiefComplaintIntake.jsx`
- `frontend/tests/chief-complaint-intake.test.jsx`
- `tests/test_chief_complaint_intake.py`
- `tests/acceptance/chief_complaint_intake_checks.cjs`
- `.github/workflows/consult-browser-postgres.yml`
- `docs/clinical_docs/INTAKE_BATCH_B3.md`
