# CW-B24 完整就诊闭环验收与医生验收包

2026 年 10 月 10 日，用户批准 12 个指定文件和独立预算，连续做到一个叠加草稿 PR 与精确 HEAD 的适用 CI。方案：https://chatgpt.com/space/page_bcc92946137c8191b0ec398768b8fc56 。本文件冻结实施约定，最终结果和实耗以对应 PR 回执为准，不为更新状态文字另造提交。

基线 CW-B23 PR #68：`07a4c31bdbad3c0225641ab8faf23dc3357cf9eb`，树 `1cda1f540355752022580c81b86a27908244a9e3`；PR base 为 `feat/followup-contact-queue-cw-b23-20261009`。本批分支 `feat/visit-journey-acceptance-cw-b24-20261010`。全部前批成果保留。

## 连续流程

使用真实前端、JWT、后端与临时数据库。犬猫各从实际页面建立同一病例，依次完成原始病史保存、回读、两份原件上传与核对、人工检验及影像、检验更正历史、复查计划、人工随访、清单准确联系及来源定位、两类文书全篇核对与下载、刷新及重新登录后回读。关键临床写入都由页面发出；API 只用于合成账号创建、独立读取和明确标记的并发故障准备。

使用固定合成原文，覆盖 Unicode、模板符号、空白、换行、原始与更正值。每次保存次数、请求 ID、来源、版本、审计和病例归属绑定到实际结果。人工录入不调用 AI 或语音，也不生成通知、自动医嘱或复查完成结论。

四类异常为：实际联系更正已提交但确认及回执回包丢失，随后 GET 核实且不重复保存；已核对的文书来源被另一合成客户端更正，409 拒绝且需重新核对；真实迟到预览在切换病例或账号后失效、其他账号各接口 404；真实文书生成成功但下载响应丢失或用户取消，均不得记为下载成功。

## 数据与证据

`clinical_visit_journey_readback.py` 启动新进程，通过受限只读连接读取临时数据库。PostgreSQL 地址固定为本机 `127.0.0.1:55432/pmai_acceptance` 和专用合成用户；SQLite 只能位于当前新建、带 CW-B24 标记的临时目录，回读使用 `mode=ro` 和 `query_only`。读回事件钩子拒绝非 SELECT 或只读事务设置，不导入生产连接配置。应用测试启动只允许新建空 SQLite；原生 PostgreSQL 继续沿用原验收的临时实例。

原件的实际下载字节与上传夹具一致；记录的原始数据、根、版本及审计由新进程直接比对数据库。只读清单、文书及重新登录区间前后读取数据库摘要，要求相同。四份实际 DOCX 逐字核对选中内容及版本，文件大小和 SHA256 入账。失败报告保留，不能以标签代替证据。

产物名称：`cwb24-journey.json`、`cwb24-independent-readback.json`、犬猫各宽窄截图、两类 DOCX、`cwb24-pages/` 中的全部页面、`cwb24-render-manifest.json`。自动报告固定医生验收 pending、merged=false、deployed=false。反例测试拒绝错误提交、缺项、错误病例或来源、重复保存、文件替换、页面错误和伪造验收。

CW-B10 原有断言及场景保留，限定调整弹出页加载与请求收尾。公共追踪保持回环地址白名单；异步错误被收集并导致失败，不能作为忽略异常的手段。正常关闭前等待请求和路由处理完成。

## 医生逐项核对

自动验证结果供医生审阅，不填写医生签名或代替实际操作。以下每项由医生记录：所查候选 HEAD、物种与病例 ID、检查日期、预期及实际表现、通过或问题、问题截图或文件名。没有本人结论的项目保持待验收。

| 检查步骤 | 医生要核对的内容 | 医生结论 |
| --- | --- | --- |
| 建档和保存 | 当前病例身份正确，原始病史、否定词、数值、换行完整 | 待填写 |
| 原件与人工结果 | 原件确属当前病例，数值、单位、报告日期及手工原文准确 | 待填写 |
| 更正历史 | 新值保存，旧值可回看，版本与原因清晰 | 待填写 |
| 复查及人工随访 | 日期、原文、来源计划版本正确，不自动推断完成情况 | 待填写 |
| 清单定位 | 联系与来源计划分别打开准确病例、准确版本 | 待填写 |
| 门诊病历草稿 | 已选资料及原文齐全，全文核对后才下载，未签署标记清楚 | 待填写 |
| 宠主说明草稿 | 内容确实适合交给宠主，历史身份及内部原文需本人核对 | 待填写 |
| 失败恢复 | 断网和迟到回包不丢输入、不重复保存，未知结果明确提示 | 待填写 |
| 宽窄屏与文书页面 | 可读、无裁切遮挡，实际 Word 分页及打印效果另行记录 | 待填写 |

缺陷记录格式：编号；候选 HEAD；病例及版本；具体步骤；预期；实际；影响；证据；建议修复路径；复核结论。业务代码缺陷超出本批路径时先保留失败证据并提出具体扩围，不删减验收。

## 固定范围

新增 8 个：

1. `tests/acceptance/clinical_visit_journey_checks.cjs`
2. `tests/acceptance/clinical_visit_journey_readback.py`
3. `tests/acceptance/clinical_visit_journey_harness.cjs`
4. `tests/fixtures/clinical_visit_journey_cw_b24_cases.json`
5. `tests/test_clinical_visit_journey_evidence.py`
6. `scripts/validate_clinical_visit_journey_cw_b24.py`
7. `docs/clinical_docs/CLINICAL_VISIT_JOURNEY_CW_B24.md`
8. `docs/product/PET_MED_AI_FIRST_CLINIC_ACCEPTANCE_MATRIX_CW_B24.md`

修改 4 个：

1. `tests/acceptance/clinical_case_overview_checks.cjs`
2. `tests/acceptance/fixture.py`
3. `.github/workflows/consult-browser-postgres.yml`
4. `docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md`

## 预算与完成约定

| 项目 | 独立上限 |
| --- | --- |
| 指定路径 | 12 个 |
| 初始实现 | 1 轮 |
| 修正 | 3 轮 |
| 完整本地回归 | 2 次 |
| 候选 CI 尝试 | 3 次，失败 job 重试同样计数 |
| 分支和草稿 PR | 各 1 个 |
| 外部业务调用和新增采购 | 0 次、0 元 |

本地定向验证归入所属实现或修正轮次。旧范围校验在各自冻结提交运行；所有历史功能测试在新候选运行。首屏 460000 字节、单 chunk 500000 字节、七个次级路由按需加载、依赖审计、30 分钟综合 CI 保持。全部证据入索引，最多 8 包、原始 part≤22 MiB、下载 ZIP<25 MiB、保留 14 天；CI 内重组逐文件核验，实际取回和本地查看另列。

不合并、不部署、不迁移、不恢复、不操作生产数据。提交前核对四个 Render 服务自动部署及预览关闭；提交及 PR 保留 `[skip render]`。不挪用旧预算，不重跑已成功 CI。

医生验收、原五份 Mac Word 检查和 CW-B5 真实语音实测独立记录，本批样例与自动渲染不能代替其完成凭证。CW-B5 原 100 次／1 元额度保持独立；异宠 B5＝Snake Depth V2。
