# M3：导出前内容核对与更正后重新核对

## 授权、基线与预算

用户已批准 `PMAI-M3-document-review-scope-2026-09-23.md` 的具体范围并要求连续执行。
基线：`5e20bb06cbd6049ce8d5da0cea6f61b2d6f123c0`（PR #39 已合并的 M2）。
分支：`feat/document-review-m3-20260923`。M3 仅交付一个草稿 PR 和新提交 CI，不自动合并。

上限：8 个文件、3 轮修订、2 次完整本地回归、2 次候选提交 CI、1 分支/1 草稿 PR。
提交包含 `[skip render]`；提交前实时确认正式双端 Auto-Deploy / PR previews Off，不改设置。
不迁移、不恢复、不操作生产数据、设备、处方/账单、宠主消息或基础设施/凭据/权限，不激活 R1。

## 用户流程

病例详情选择「导出门诊病历草稿 DOCX」或「导出宠主说明草稿 DOCX」，先打开内容核对面板。
面板从现有只读预览接口读取当前账号可访问病例的已保存原文，显示全部业务字段、缺失项和账号归属。
医生勾选「已核对本次草稿内容（仍未签署）」后才能确认下载；也可关闭或进入已有病例更正页。
本页是内容核对，不模拟 Word/WPS 排版，不保存审阅/签署状态，不替代医生或实机验收。

病例、模板或账号切换，关闭、离页、重新读取和错误都不能沿用旧确认或迟到响应。
下载成功后清除本次确认；再次下载需重新读取并核对。旧入院/出院下载和既有下载互斥保留。
核对期间其他模板入口禁用；关闭后可重新选模板。键盘可操作，打开聚焦标题，正常关闭恢复原入口焦点。

## 后端契约与兼容性

两种门诊预览新增 `content_snapshot`：完整 SHA256，绑定模板 ID、模板文件字节 SHA256、病例/账号与实际文书业务字段。
排除生成时间与原有 `document_hash`；同一内容跨秒有效。原文、缺失字段、字面双花括号和控制字符规则均复用 M2。

下载请求可带 `expected_content_snapshot`。若与服务器本次读取的内容不一致，返回 409，提示重新核对且不返回文件。
校验和 DOCX 生成复用同一个上下文与模板字节，防止校验后再次读模板造成不一致。它是内容前置条件，不是数字签名或永久修订历史，也不阻止校验后另一会话继续修改病例。

门诊 DOCX 响应提供 `X-PMAI-Content-Snapshot`，并仅为该响应暴露此校验头供浏览器读取。
新前端核对响应标识，缺失或不符就不下载，避免预览后服务器回退到旧版并忽略新参数。未改变允许访问的来源、认证或权限。
新前端连接旧后端时，预览缺少能力会显示提示并停止该草稿下载。

旧客户端不带新参数时继续按原接口下载；旧模板行为保留。请求新参数但使用旧模板返回 422，避免虚假声称受新核对保证保护。
没有模型、模板资产、依赖、病例写入路由或环境配置修改。

## 修改文件（仅 8 个）

1. `backend/clinical_docs_api.py`
2. `frontend/src/pages/CaseDetail.jsx`
3. `frontend/src/components/ClinicalDocReview.jsx`
4. `frontend/tests/case-detail-documents.test.jsx`
5. `tests/test_clinical_doc_lifecycle.py`
6. `tests/acceptance/visit_document_checks.cjs`
7. `.github/workflows/consult-browser-postgres.yml`
8. `docs/clinical_docs/VISIT_MILESTONE_M3.md`

## 验收与复现

隔离夹具使用合成病例、真实 ASGI/JWT 和临时 SQLite，禁止外网与其他数据库连接；GitHub CI 保留原生临时 PostgreSQL/Chromium 链路。

```sh
python tests/test_consult_update_preview.py
python tests/test_consult_first_save.py
python tests/test_manual_case_create.py
python tests/test_clinical_doc_lifecycle.py
npm --prefix frontend run test:consult-update
python scripts/validate_outpatient_document_templates.py
VITE_API_BASE=http://127.0.0.1:18026 npm --prefix frontend run build -- --manifest
node frontend/tests/check-route-chunks.mjs
bash scripts/ci_static_checks.sh
```

前端保留原 179 项行为测试，并新增 18 项；文书/详情专项共 45 项。
后端保留原 59 项并新增 7 项，共 66 项（33+10+5+18）；其中逐字段变更通过子用例覆盖两个模板的所有业务字段。
专项包含稳定快照、模板字节更改、跨病例/账号/模板、拒绝过期/畸形标识、旧客户端兼容、无写入及空白/特殊/长原文一致。
浏览器保留旧 109 个检查点，并新增两模板预览与 DOCX 内容一致、键盘焦点、并发更正后拒绝旧确认和重新核对下载的实际链路。

本地第一轮后端 66/66 通过；前端首轮因测试辅助函数将整个页面输入框当成唯一输入框而失败。
第二轮修订将选择范围限定到文书核对区，没有删除保护断言；文书专项 45/45 通过。
第二次完整前端回归 197/197 通过；后端完整回归 66/66 通过。静态检查以及新提交 CI 的实际回执写入 PR，不能将预期数量或旧 SHA 的通过记录当成通过。
本地构建初始 JS 442,029 字节；460,000 / 500,000 字节性能门保持。锁定依赖审计 0 项漏洞；模板契约通过。
本地 PostgreSQL 服务不可用，原生 PostgreSQL/Chromium 验收交由现有 GitHub CI 完成，不用 SQLite 代替该验收。

## 上线边界

M2 的真实医生审阅及 Word/WPS 分页回执仍待补齐，M3 不绕过此发布暂停。
M3 合并需要明确授权；后续符合所有条件时可沿用持续部署授权。
如获准部署，先再次查明后端启动链不执行迁移/生产数据操作，确认双端 Off、兼容旧前端及可用回退，再按后端→前端顺序逐步验收。
不使用生产病例或业务请求验收。发布前重新核对实际 main/候选 SHA、CI、线上版本和正在进行的部署。
