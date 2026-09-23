# M2：门诊基础病历与宠主说明 DOCX 草稿

## 范围与授权

基线：`20550e0f2144aaab6e2990b2db90b78140771856`（已完成 M1）。
分支：`feat/outpatient-documents-m2-20260923`。
本轮仅提交一个草稿 PR；M2 不自动合并，不上线。提交信息含 `[skip render]`，提交前须重新读取正式双端 Auto-Deploy、PR previews 为 Off。

批准预算：最多 11 文件、3 轮修订、2 次完整本地回归、2 次候选提交 CI、1 个分支和 1 个草稿 PR。专项风险验证另行记录。本轮不修改数据库结构、启动链、依赖、权限或基础设施，不连接真实设备，不写入处方、账单，不向宠主发消息，不激活 R1。

## 完成的行为

病例详情提供「导出门诊病历草稿 DOCX」和「导出宠主说明草稿 DOCX」。下载使用当前账号可访问、未删除病例的已保存字段；生成不写数据库。沿用 M1 的防重复、切换病例或账号及离开页面时拦截过期下载机制，失败后可以重试。

新增 `outpatient_record_zh`、`owner_visit_summary_zh` 两个中文 A4 模板。沿用批准的「瀚森宠物医院」抬头；明确标注草稿、待医生核对、尚未签署。账号编号用于导出归属，不代表签名。没有新增地址、电话、医生身份、电子章或诊疗承诺。原入院、出院模板资产及原有渲染行为不变。

栏目调整不改变医学原意；不使用模型改写，不补写剂量、给药频率、复查日期。新模板不支持附加诊断数据合并，显式请求会返回 422。

## 字段来源

| 文书字段 | 病例字段 | 规则 |
| --- | --- | --- |
| 病例编号、动物、物种 | `id`、`patient_name`、`species` | 保存原值 |
| 年龄、性别、体重 | `age_info`、`sex`、`weight` | 体重为文本，不增加或转换单位 |
| 主诉、病史 | `chief_complaint`、`history` | 保留原文及否定词 |
| 查体记录 | `exam_findings` | 缺失不替换成正常结论 |
| 评估内容 | `analysis` | 不标为最终诊断 |
| 诊疗计划 | `treatment` | 原文，无新增医嘱 |
| 预后与补充说明 | `prognosis` | 不推导成复查指令 |
| 复查安排状态 | 无独立字段 | 「未单独记录复查安排，请医生补充确认」 |
| 导出账号 | 当前认证用户 ID | 忽略调用者伪造的署名参数 |

空白字段统一显示「未填写」。保留前后空格、换行、制表符、XML 特殊符号及原文中的双花括号；CRLF/CR 统一为换行。不截断长文本，XML 不支持的控制字符明确拒绝。模板占位符只替换一遍，避免将病例文本再次解释成模板。导出含 UTC 时间与内容校验标识，不是数字签名。

## 验收与复现

隔离数据均为合成病例，SQLite 用例由真实认证与请求路由驱动，外部网络被夹具拒绝。PostgreSQL/Chromium 由 GitHub Actions 的一次性本地数据库与浏览器完成，不读取生产病例。

```sh
python scripts/validate_outpatient_document_templates.py
python tests/test_consult_update_preview.py
python tests/test_consult_first_save.py
python tests/test_manual_case_create.py
python tests/test_clinical_doc_lifecycle.py
npm --prefix frontend run test:consult-update
VITE_API_BASE=http://127.0.0.1:18026 npm --prefix frontend run build -- --manifest
node frontend/tests/check-route-chunks.mjs
```

原有前端 167 项用例保留，新增 12 项：两种模板分别覆盖准确请求、防重复、病例切换、账号切换、卸载及错误重试。后端原 51 项保留，文书套件新增 8 项，覆盖原文、缺失字段、可信归属、长文本、拒绝附加诊断合并、更正后内容/校验标识及非法控制字符。原有三个文书生命周期用例扩展到四种模板。

首轮前端 179/179 通过；首轮后端发现错误的体重字段映射，修复为真实文本字段 `weight` 后文书专项 11/11 通过。禁止以修改期望值掩盖字段丢失；专项同时验证零值与带单位的原始体重文本。最终本地完整回归前端 179/179、后端 59/59（33+10+5+11）通过。新提交 CI 的实测结果记入 PR 验收回执，不能将本地或旧 SHA 的结果代替新提交 CI。

DOCX 检查包括两份空模板和六份合成导出样例（短文本、空字段、长文本各两份）。模板/短文本/空字段各为 1 页，长病史样例各为 3 页；逐页检查页码、换行、末行保留、边界与标题。Word/WPS 的具体分页可能随本机字体略有不同；不将其宣称为已完成真实设备验收。

CI 保留原有全部 PostgreSQL/Chromium 检查，并新增两种草稿字段检查与跨模板防重复检查。验收入口检出 PR 实际 HEAD，绑定上述基线、11 文件白名单及资产/关键实现的 Git blob SHA；不放宽功能检查。初始 JS 上限仍为 460,000 字节，单块上限仍为 500,000 字节。当前本地构建初始 JS 为 437,232 字节；最终以新提交 CI 产物为准。

## 修改文件（仅 11 个）

1. `backend/clinical_docs_api.py`
2. `frontend/src/pages/CaseDetail.jsx`
3. `templates/clinical_docs/outpatient_record_zh.docx`
4. `templates/clinical_docs/owner_visit_summary_zh.docx`
5. `templates/clinical_docs/CLINICAL_DOCS_TEMPLATE_ASSETS_MANIFEST.json`
6. `tests/test_clinical_doc_lifecycle.py`
7. `frontend/tests/case-detail-documents.test.jsx`
8. `tests/acceptance/visit_document_checks.cjs`
9. `scripts/validate_outpatient_document_templates.py`
10. `.github/workflows/consult-browser-postgres.yml`
11. `docs/clinical_docs/VISIT_MILESTONE_M2.md`

## 剩余边界

文书是供医生审阅的原文草稿；不自动签署、发送、归档为正式文书或新增医嘱。复查仍缺独立字段，本轮明确显示缺失而不扩展数据模型。合并及后续产品里程碑需对应的具体授权。将来若批准上线，仍须重新验证完整提交 CI、兼容性、双端关闭自动部署/预览、无重叠部署与可靠回退；本轮不执行部署。
