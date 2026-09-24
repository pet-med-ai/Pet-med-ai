# M4：手工新建病例输入暂存与恢复

## 范围与授权

用户批准 M4 八文件范围与预算，连续执行到草稿 PR 和新提交 CI；不自动合并。
基线为 main `e5d53884789115ffdb3a47d9303d88c4570bf915`，分支 `feat/manual-case-draft-m4-20260924`。
预算上限：8 文件、3 轮修订、2 次完整本地回归、2 次候选 CI、1 分支/1 草稿 PR。
提交包含 `[skip render]`，每次提交前重新核验正式双端 Auto-Deploy / PR previews Off，不修改设置。

## 完成的行为

手工新建页对十五项输入原文使用独立的当前标签页草稿，8 小时有效；刷新或重新进入后由医生选择恢复或丢弃，不自动创建病例。
首页带入输入与旧草稿同时存在时明确选择，不自动合并；消耗后的路由 seed 从当前历史项移除，不能在保存后重新带回。
恢复不恢复确认框、预览、病例编号或成功状态，必须重新核对、确认才提交。

输入草稿与 `pmai.manual-create-attempt.v1` 创建回执分离。草稿过期、损坏、删除或清理失败都不能解除已提交但结果未确认的创建锁；原有 GET 核对和防重复 POST 逻辑保留。
回读确认成功后清理输入草稿，保留创建回执；只有清理成功才能开始另一例。丢弃未提交输入不操作服务器，也不清除创建回执。

按有效登录账号隔离本地草稿；新建页面在账号切换或登录失效时隐藏旧输入，令牌续期后仍检查实际到期时间。
登录/退出清理新草稿；恢复仍不改变服务端认证规则。当前标签页存储不是跨设备同步或正式病历，不保证关闭标签页后恢复。
存储拒绝、草稿不可读、过期、超量和清理失败均有明确提示；不会把旧副本称为最新输入。浏览器允许时提供刷新/关页提醒，移动浏览器不保证弹窗。

## 修改文件（仅八个）

1. `frontend/src/manualCaseDraft.js`
2. `frontend/src/pages/CaseEditorLite.jsx`
3. `frontend/src/components/ManualCaseCreateReview.jsx`
4. `frontend/src/App.jsx`
5. `frontend/tests/manual-case-create.test.jsx`
6. `tests/acceptance/manual_create_checks.cjs`
7. `.github/workflows/consult-browser-postgres.yml`
8. `docs/clinical_docs/VISIT_MILESTONE_M4.md`

不改后端、数据库模型、模板资产、依赖、运行配置、旧文书核对组件或测试总入口；使用现有入口追加行为测试。

## 本地验收与预算实耗

第一轮：手工新建专项 35/35、前端完整 214/214、后端完整 66/66（33+10+5+18）。
第二轮：补充令牌续期后的到期隐藏保护及对应测试，前端完整 215/215、后端完整 66/66，均无失败；保留原前端 197 项并新增 18 项。
专项覆盖十五字段原文、长文本、零值文本、空白、否定词、Unicode/字面 HTML、路由 seed 冲突、过期/损坏/超量、存储失败、账号切换、登录到期、丢弃草稿与创建回执隔离、清理失败阻断下一例。

构建成功，初始 JS 447,438 字节；原 460,000/500,000 字节限制保留。锁定依赖审计 0 项漏洞，M2 模板契约通过。
本地 npm build 的缓存 `.bin/vite` 是失效的复制入口，首次启动未进入构建；改用同一已安装 Vite 包的 `bin/vite.js` 原入口完成构建，没有修改 package.json 或依赖。
原静态门首次因尚未提交的工作区被拒绝，专项诊断为 `postcommit worktree dirty`；将在授权的本地提交形成干净快照后验证，不修改或放宽检查。原静态门及新提交 CI 的最终结果记入 PR 回执，不能用本地或旧 SHA 结果代替。

本地无 PostgreSQL 原生工具；原生 PostgreSQL/Chromium 验收使用现有 CI 的一次性数据库及真实认证，不以 SQLite 代替。
原有 113 个检查点保留，新增四个浏览器场景：丢弃不写入、十五项输入刷新恢复、预览后刷新须重新确认、草稿删除/过期不解除未确认创建锁。最终数量以实际 CI 日志为准。
浏览器仅访问隔离回环地址与合成病例，原有创建一次、真实回读、丢失真实响应后禁止重复提交检查均保留。

当前实耗：8 文件、2 轮修订、2 次完整本地回归、1 次手工新建专项；提交阶段申请第 1 次候选 CI。若后续失败需修订，剩余 1 轮修订/1 次候选 CI；不得重跑第三次完整本地回归。

## 复现入口

```sh
npm --prefix frontend run test:consult-update
python tests/test_consult_update_preview.py
python tests/test_consult_first_save.py
python tests/test_manual_case_create.py
python tests/test_clinical_doc_lifecycle.py
python scripts/validate_outpatient_document_templates.py
VITE_API_BASE=http://127.0.0.1:18026 npm --prefix frontend run build -- --manifest
node frontend/tests/check-route-chunks.mjs
bash scripts/ci_static_checks.sh
```

## 发布及风险边界

M4 保持草稿，不自动合并。M2 的医生审阅与 Word/WPS 桌面分页回执仍待补齐，M3/M4 均不绕过此上线暂停。
不迁移、不恢复、不操作生产数据、不接真实设备、不写处方或账单、不发送宠主消息；不改基础设施、凭据或权限，不激活 R1。
本轮实现本地输入保护，不承诺跨标签页/跨设备幂等创建，也不模拟正式签署或永久审阅记录。
