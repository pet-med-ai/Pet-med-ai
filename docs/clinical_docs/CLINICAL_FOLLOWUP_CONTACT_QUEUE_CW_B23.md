# CW-B23 复查工作清单纳入人工随访记录

用户于 2026-10-09 21:19:00（Asia/Shanghai）批准 21 个指定文件与独立预算，连续到草稿 PR 与精确 HEAD 的 CI。批准方案：https://chatgpt.com/space/page_39808adf14f08191bd5b8104775bbbb9 。当前实施候选；最终结果和实耗见对应 PR，不新增状态文字收尾提交或重跑成功 CI。

## 目标和医生流程

现有 [CW-B18 清单](https://github.com/pet-med-ai/Pet-med-ai/blob/21a2afaa100807842dd42a4967e24b771e362d12/frontend/src/pages/FollowupPlanQueue.jsx)只展示复查计划；[CW-B19](https://github.com/pet-med-ai/Pet-med-ai/blob/21a2afaa100807842dd42a4967e24b771e362d12/backend/clinical_followup_contacts.py)已保存人工随访，CW-B20 提供病例内准确回看，CW-B21 和 CW-B22 已纳入两类文书。本批把已登记事实带回原工作清单，作为医生查找和核对的入口。

医生登录 → 打开复查计划清单 → 主动开启“显示人工随访记录” → 按计划日期和登记情况筛选 → 展开已保存原文 → 打开准确联系版本或来源计划。默认保持原清单，关闭新视图时不读取联系或联系审计。

1. 清单仍限当前账号拥有的未删除病例，每病例仅列当前未撤销计划。原有今天、未来 7 天、早于今天、自定义和全部日期，以及计划核对状态筛选保持原义。

2. 每行分别显示“本版计划的有效联系记录数”和“历史计划的有效联系记录数”。各组最多展示一条最近的有效记录，按实际联系时间排序，同一时间用记录 ID 确定顺序；更正保存时间不能把较早的联系变成最近联系。

3. 只把每个联系根的最新 `recorded` 版本计入上述数量。旧版本和已撤销记录仍在病例原面板回看；“暂无有效登记”不表示从未联系。历史来源包括已更正、已撤销的旧计划版本，不自动改绑到当前计划。

4. 新增登记情况筛选：全部、有本版计划登记、仅历史计划有登记、暂无有效登记。只描述记录，不使用“已完成复查”“已改善”或“未联系宠主”等推断。

5. 展开时保留联系时间、方式、结果、原文、后续安排、更正原因、登记信息、ID／根／版本，以及冻结来源计划的完整原文和来源当前状态。当前病例、登记时和来源保存时的最小身份分列；不额外返回电话字段、病例病史正文或审计请求正文。医生已写入原文的内容保持字面值，不自动删改。

6. 每组提供准确联系版本和准确来源计划链接；仍可打开当前计划。全部历史联系在原病例面板查看。清单不新增保存、更正、撤销、预约、通知、分派、自动医嘱、AI 判断或复诊完成登记。

## 叠加基线和核验结果

2026 年 10 月 9 日约 19:59（北京时间）只读核对：[CW-B22 PR #67](https://github.com/pet-med-ai/Pet-med-ai/pull/67)为 open、draft、未合并，1 个提交、22 个文件；本地工作区干净。其最终回执和精确 HEAD 的 CI 已完成，旧方案页的“待批准”冻结文字不作为当前实施状态。

- 精确基线 HEAD：`21a2afaa100807842dd42a4967e24b771e362d12`。

- 内容树：`f0bba24b08585d856b1122e1a514b23832a3eacc`。

- 本批 PR base：`feat/followup-contact-owner-docs-cw-b22-20261009`。

- 拟建分支：`feat/followup-contact-queue-cw-b23-20261009`，已创建；从上述 HEAD 接续。

| CW-B22 工作流 | 精确 HEAD 的结果 |
| --- | --- |
| [CI Gate 37921813500](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/37921813500) | 2 个 job success |
| [Consult update preview 37921813556](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/37921813556) | 2 个 job success |
| [Consult browser and PostgreSQL acceptance 37921813538](https://github.com/pet-med-ai/Pet-med-ai/actions/runs/37921813538) | 2 个 job success |

共 3 条工作流、6 个 job 全部通过，均为第 1 次尝试。CW-B22 已耗 22/22 文件、初始 1/1、修正 1/3、完整回归 1/2、候选 CI 1/3；剩余额度不转入本批。其 CI 已完成 687 文件、7 分包的重组及逐文件校验；索引实际下载遇到 HTTP 403，本地取回和重组仍未完成，这与 CI 成功分列。

`main` 与正式前后端 live 提交均为 `793894523be602bd8da265f8f7e8e63e417027a7`。正式后端、静态前端、旧前端和 staging 的 `autoDeploy=no`、`autoDeployTrigger=off`、PR previews 关闭均已只读复核。

## 接口和数据一致性

复用 `GET /api/followup-plan-queue`。只有显式 `include_followup_contacts=true` 才进入新协议 `clinical-followup-contact-queue-cw-b23-v1`，可带 `contact_state=all|current|historical_only|none`，默认 all。未带该开关时沿用 CW-B18 的严格参数、响应和查询路径；关闭模式下不接受联系筛选。重复参数、未知参数、其他开关值以及伪造 owner 参数均拒绝。

新功能独立受 `FOLLOWUP_CONTACT_QUEUE_ENABLED=1` 和 `FOLLOWUP_CONTACT_QUEUE_SYNTHETIC_ONLY=1` 控制，默认关闭，且仅允许 test/development、非 Render 环境；同时要求 CW-B18、CW-B19 及 CW-B14 原开关满足。真实 JWT 鉴权后仅查询当前账号。关闭或未授权时不查询联系；成功和错误响应保持 `private, no-store`。

新服务复用 CW-B18 独立只读事务、日期规则和病例候选读取。PostgreSQL 使用 REPEATABLE READ、READ ONLY，SQLite 显式 BEGIN；在同一事务内最多 4 次业务 SELECT，分别批量读取病例、计划、联系和联系审计，JWT 用户查询另计。禁止逐病例追加查询。

上限保持 200 个相关病例、10000 条计划版本；新增联系上限为 10000 条版本行、20000 条审计，每病例仍为 50 条联系版本和 100 条审计。各查询使用上限加一检测；先完整校验相关病例、全部计划链、联系链及审计，再筛选、计数和分页。超限、来源缺失、版本损坏或审计异常明确失败，不截断、修复或伪装为空清单。

从 CW-B19 `records` 中抽取完整纯校验函数，原路径仍执行原查询并委托校验，不改变写入、CAS、幂等回执、审计或错误语义。批量路径保持 namespace 的 status 前缀或 channel 来源的 OR 定义，额外验证批量分组与病例绑定，防止错组。

新快照绑定协议、账号、上海日期、日期及登记筛选、页大小、病例完整来源指纹、所有计划和联系版本及审计内容。未展示或已撤销版本变化也使旧快照失效。连续分页须携带快照，冲突明确返回并重新读取第 1 页；原计划日期、病例 ID、计划 ID 的排序保持一致。GET 不写业务表或审计、不清理附件、不生成文书。

## 页面和准确定位

新视图在既有按需加载的清单页面中，默认未开启；新响应由独立模块严格校验字段、状态、计数、时间、身份、来源归组、筛选和分页。未知 schema、错病例、错误计数或错误来源不得渲染成有效记录。原 CW-B18 响应校验器保持原样。

账号变化、切换视图或筛选、分页、刷新、窗口失焦／返回、可见性和上海跨日均使旧显示失效。AbortController 与请求序号拦截迟到回包；错误时保留筛选并允许只读重试，不退回旧结果冒充新视图。不新增临床数据的浏览器持久化。

联系链接只携带病例 ID、`followup_contact` 和 `followup_contact_version`；来源计划沿用已有准确定位参数。不放正文、电话、凭据或快照。CaseDetail 严格验证成对、单值、正安全整数及版本≤50，拒绝联系与计划参数混用；重新读取病例及原 CW-B19 列表后定位准确版本。

同病例定位不卸载原面板，不清除未保存原文或未知保存结果。跨病例和返回清单沿用离开保护。记录后来更正或撤销时，显示指定旧版本及状态；缺失或非法定位明确提示，不跳到另一条联系。当前计划与历史来源不相互替换。

## 指定文件范围

以下 21 条路径已核对：12 个新路径尚不存在，9 个修改路径均在基线存在。未列出的路径不在本批范围；`main.py`、CW-B18 服务及前端协议辅助模块均无需修改。

**新增 12 个文件**

1. `backend/clinical_followup_contact_queue.py` — 联系清单协议、批量读取、归组与快照。

2. `frontend/src/followupContactQueue.js` — 新响应校验、查询、提示和准确链接。

3. `frontend/src/components/FollowupContactQueueSummary.jsx` — 本版与历史联系的数量、原文和回看入口。

4. `frontend/tests/followup-contact-queue.test.jsx` — 默认隔离、筛选、分页、失效及恶意回包。

5. `frontend/tests/case-detail-followup-contact-queue.test.jsx` — 严格定位、准确回看及草稿保护。

6. `tests/test_clinical_followup_contact_queue.py` — 协议、鉴权、链和审计、上限及固定查询数。

7. `tests/test_clinical_followup_contact_queue_concurrency.py` — SQLite 一致性与失效快照。

8. `tests/test_clinical_followup_contact_queue_isolation.py` — 纯校验等价、只读及历史功能隔离。

9. `tests/acceptance/clinical_followup_contact_queue_checks.cjs` — 真实 Chromium 清单和准确定位。

10. `tests/fixtures/clinical_followup_contact_queue_cw_b23_cases.json` — 犬猫、多账号、当前和历史来源夹具。

11. `scripts/validate_clinical_followup_contact_queue_cw_b23.py` — 21 路径、叠加基线、受控差异和历史门禁。

12. `docs/clinical_docs/CLINICAL_FOLLOWUP_CONTACT_QUEUE_CW_B23.md` — 冻结本批协议、范围及验收约定。

**修改 9 个文件**

1. `backend/clinical_followup_plan_queue_api.py` — 显式开关分派和联系参数校验；原请求保留旧路径。

2. `backend/clinical_followup_contacts.py` — 仅抽取可接收预取记录及审计的纯校验函数。

3. `frontend/src/pages/FollowupPlanQueue.jsx` — 主动开启、登记筛选、双模式失效和联系展示。

4. `frontend/src/pages/CaseDetail.jsx` — 联系清单 URL 的严格解析与准确回看。

5. `frontend/tests/run-consult-update-review.mjs` — 加入本批两组前端测试。

6. `tests/acceptance/postgres_checks.py` — 原生 PostgreSQL 批量快照、并发、只读与新进程回读。

7. `tests/acceptance/fixture.py` — 独立默认关闭的合成环境开关和夹具支持。

8. `.github/workflows/consult-browser-postgres.yml` — 加入本批门禁和验收，保留历史命令及证据。

9. `docs/product/PET_MED_AI_CLINICAL_WORKFLOW_BATCH_INDEX.md` — 仅追加 CW-B23 对应及冻结实施约定。

模型、迁移、依赖和锁文件、Render 配置、文书模板与导出代码、联系和计划的写入协议、旧 KPI 均不改。旧范围校验器在各自冻结提交执行；历史功能测试在新候选执行。本批不删除、跳过或放宽旧断言来换取通过。

## 验收和证据

1. **事实与边界**：犬猫、多账号、删除病例、空列表、四种联系结果；多联系根、更正、撤销、同一实际时间、Unicode／空白／换行／模板符号和最长原文。验证本版与历史分组、仅历史登记、无有效登记以及计划需重新核对，不推断完成情况。

2. **协议和规模**：真实 JWT、全部独立开关组合、重复／非法参数、分页及日期边界；200／201 病例、50／51 联系版本、100／101 审计、总行数上限及损坏链。验证 4 次以内业务 SELECT、无逐病例查询、默认旧路径零联系／审计读取。所有错误均不泄露其他账号病例。

3. **一致性**：SQLite WAL 与原生 PostgreSQL 用独立连接在多次 SELECT 之间实际提交计划／联系更正撤销、病例身份／正文／归属／删除和审计变化。读取必须来自一个完整快照；旧快照不能继续翻页。原生 PostgreSQL 验证 READ ONLY，新进程双账号重新登录独立回读；SQLite 不替代 PostgreSQL。

4. **真实浏览器**：犬猫宽窄屏，主动开启／关闭、四种登记筛选、日期与分页、完整原文、两类准确链接、旧版本／缺失／非法定位；迟到回包、账号切换、失焦返回、跨日和重试。同病例未保存计划／联系草稿及实际保存丢回包后的未知结果均保留。

5. **隔离和回归**：比对默认 CW-B18 清单、CW-B19 读写回执、CW-B20 总览、CW-B21／22 文书、旧 KPI 和审计；证明纯校验抽取未放宽规则，新 GET 没有 DML／DDL、审计或附件清理。保留全部既有后端、前端、浏览器、数据库和完整 DOCX 渲染证据。

6. **性能和交付**：首屏 JS≤460000 字节、单 chunk≤500000 字节、原七个次级路由按需加载、锁定依赖审计通过。最终精确 HEAD 的全部适用 CI 成功；不以旧提交成功替代新候选结果。

保留现有综合 CI 30 分钟时限及全部历史执行命令。先定向预检批量分组、ORM 审计 JSON 与时间序列化、新进程回读所需定义，再执行完整回归。

所有历史及本批证据进入完整索引，原始分包≤22 MiB、最多 8 包、每个下载 ZIP<25 MiB，CI 内重组并逐文件核验字节数和 SHA256，保留 14 天。本批以清单和病例宽窄屏截图及数据库证据为主，不增加文书模板。预计超限时提供具体大小再申请调整，不删减历史证据。最终分别记录 CI 内验证、索引／分包实际取回和本地重组结果；取回失败如实记录。

## 独立预算

| 项目 | CW-B23 上限 | 当前实施实耗 |
| --- | --- | --- |
| 指定文件 | 21 个，12 新增、9 修改 | 0 |
| 初始实现 | 1 轮 | 0 |
| 修正 | 3 轮 | 0 |
| 完整本地回归 | 2 次 | 0 |
| 候选 HEAD 的 CI | 3 次 | 0 |
| 独立分支 | 1 个 | 0 |
| 草稿 PR | 1 个 | 0 |
| 外部业务调用 | 0 次 | 0 |
| 新增采购 | 0 元 | 0 元 |

预算为上限，不要求用满。本次只读规划不消耗实施额度；不挪用 CW-B22 或其他批次预算。定向检查计入相应实现／修正轮次，不拆分隐瞒完整回归次数。必要的第 22 条路径、扩大行为或任一预算超限，须保留已有结果，列出具体失败证据、实耗和所需扩围。


继续不合并、不部署、不迁移、不操作生产数据；所有提交保留 [skip render]。医生验收、原五份 Mac Word 与 CW-B5 原独立 100 次/1 元真实外部语音实测待补，异宠 B5＝Snake Depth V2。
