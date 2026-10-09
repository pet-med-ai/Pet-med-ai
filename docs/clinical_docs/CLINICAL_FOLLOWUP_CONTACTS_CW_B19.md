# CW-B19 人工随访记录保存与回看

2026-10-09 11:33:45（Asia/Shanghai）用户已批准 [22 文件方案](https://chatgpt.com/space/page_5a8a9e2773d481918d8bce1e173dd406)，连续做到独立草稿 PR 与精确 HEAD CI。承接 CW-B18 PR #63 最终 HEAD `73ba51e664241bac2b664d10d8eaf242b991a0e5`、树 `ceb4e6aca1dc7d929dbbde6a0d423471f3d4738e`，不从 main 重新起步。

## 行为与界限

从 CW-B18 清单准确定位病例及计划后，病例页按需打开“人工随访记录”。医生明确选择当前有效、已核对的计划，填写已经发生的联系或联系尝试，经完整预览、勾选核对后保存。该记录不表示已复诊、已完成检查或病情改善，不关闭计划，不生成医嘱，不通知、不预约、不派单、不进入本批文档或电子签名。账号仅表示登记账号。

联系方式固定为 phone / wechat / in_person / other；结果为 reached / not_reached / declined / other，界面没有默认选择。实际联系时间为上海时间 `YYYY-MM-DDTHH:mm+08:00`，验证真实日历、跨日和未来时间；与服务进程时区无关。原文必填，上限 2000 Unicode 字符；后续安排可空，上限 1000；更正/撤销原因必填，上限 500。保留原文字面值、空白、Unicode 与模板符号，不插值或自动整理。

每个计划允许多个独立联系根记录。更正追加版本，原版本保留且标记旧版本；撤销保留原数据和撤销原因。每病例最多 50 条联系版本行（包含旧版本与撤销），使用 cap+1 完整检测，超限/损坏拒绝继续，不静默截断。达到 50 条仍可回看和撤销。

每条记录冻结来源计划 id/root/version、完整原文、原病例身份、核对账号与时间。新建仅允许当前 `planned` 来源；来源计划后续更正/撤销、病例变化时，旧联系仍以冻结内容回看并展示来源当前状态。历史联系可更正或撤销，不能改绑来源，也不会产生对旧计划的隐式写入。

## 数据与一致性

复用现有 FollowUp 和 AuditLog，不新增表、字段或迁移。新 namespace 的 status 为 `cw-b19-recorded/superseded/withdrawn`，channel/source 为 `clinical-followup-contacts-cw-b19`。FollowUp.due_date 保持来源计划日期转换值，done_at 始终为空；实际联系时间只存于本批 JSON note。审计绑定请求、操作、行/版本、登记身份、时间、原因及内容摘要。读、预览与回执均校验完整版本链、来源与每个审计；损坏记录和审计不会伪装为空清单。

新 API 根路径 `/api/cases/{case_id}/followup-contacts`：GET 列表、POST `/preview`、POST `/confirm`、GET `/requests/{request_id}`。真实账号鉴权与 Case 行锁复用 CW-B14；病例、完整计划来源与记录状态做 CAS。记录与审计同事务提交，同一请求与同一正文只提交一次；正文变更冲突。保存结果未知时先查原请求结果，不自动重写；界面完成独立 GET 回读后才清除草稿。

功能默认关闭，需同时设置 `FOLLOWUP_CONTACTS_ENABLED=1`、`FOLLOWUP_CONTACTS_SYNTHETIC_ONLY=1`，且为 test/development、非 Render 环境，CW-B14 开关也须开启。响应包括鉴权/校验错误保持 private/no-store。不会新增浏览器临床持久化。病例/账号切换、输入变化、焦点/可见性、病例或来源计划写入会使旧预览失效；同病例刷新保留未保存原文，未知保存结果锁定写入。

CW-B14 唯一行为增量是 `legacy_only` 排除本批 status 前缀或 channel，包括损坏的新 namespace 行。CW-B14/17/18 计划读取和旧 KPI 算法、文档模块保持原样，独立隔离测试比较本批保存前后旧计划、总览、清单、KPI、门诊及宠主文档原文。

## 验证与证据

专项覆盖严格结构、日历与时区、原文长度、鉴权/开关/归属/删除、50 条边界、来源更正/撤销、失效预览、独立回读、审计损坏、重复确认、并发冲突、回滚和丢回包。原有功能测试均在本次候选执行，旧范围门禁在各自冻结提交执行，新门禁约束批准的 22 个路径及 main.py 两行注册和 legacy_only 唯一改动。

真实 PostgreSQL 使用 CI 的一次性本地服务、真实 ORM/JWT/API 与独立连接，并验证重启进程重新登录回读；不以 SQLite 代替 PostgreSQL。本地环境不能启动非 root 原生 PostgreSQL，因此本地仅执行明示的 SQLite 隔离测试及真实 Chromium，原生 PostgreSQL 结果以 CI 为准。浏览器覆盖犬猫、清单准确导航、联系生命周期、来源历史、实际回包丢失、延迟预览、焦点失效、旧草稿、窄屏和重新登录。

继承全部历史证据。分包原始上限 22 MiB、最多 8 包；CI 验证 SHA256、重组一致性后上传，保留 14 天。本地下载与重组能否完成如实追加 PR，不把 CI 重组冒称为本地重组。

## 独立预算与收尾

22 个文件；初始实现 1；修正≤3；完整本地回归≤2；候选 CI≤3；独立分支 1、草稿 PR 1；外部业务调用 0；新增采购 0 元。允许路径以 `scripts/validate_clinical_followup_contacts_cw_b19.py` 为准，不挪用旧预算。

草稿候选＝实施中；CI 通过＝待精确候选结果；已合并＝否；已上线＝否；医生验收＝未验收。最终实耗、HEAD、CI 与证据追加 PR，不为改旧状态文字新增收尾提交或重跑成功 CI。提交前只读核对 Render 自动部署与预览关闭，提交保留 `[skip render]`。不合并、不部署、不迁移、不操作生产数据。医生、原五份 Mac Word、CW-B5 原独立 100 次/1 元真实语音仍待补；异宠 B5＝Snake Depth V2。
