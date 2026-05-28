# 医院设备接口需求与架构 V1

> 阶段定位：本阶段只做需求与架构文档，不改后端、不改前端、不改数据库、不跑 smoke。
>
> 目标：先把医院设备如何接入 Pet-Med-AI 的边界、数据流、设备清单、未来 API 草案和分期路线定清楚，避免后续直接写接口导致返工。

## 1. 当前结论

医院设备接入 Pet-Med-AI 不建议让设备直接连接云端后端。推荐架构是：

```text
医院设备 / PACS / LIS / HIS
        ↓
医院内网本地设备网关 petmed-device-gateway
        ↓
标准化 / 去重 / 关联病例 / 缓存重试 / 审计日志
        ↓ HTTPS
Pet-Med-AI Integration API
        ↓
DiagnosticReport / Observation / ImagingStudy / Attachment
        ↓
病例详情 / AI 辅助分析 / 检验影像摘要
```

第一阶段只做“结果接入”，不做设备控制。

## 2. 本阶段范围

### 本阶段做

```text
1. 设备接口总体架构
2. 设备清单采集模板
3. 数据匹配机制：case_id / visit_id / accession_id
4. 影像、检验、监护、体征设备的接口边界
5. Pet-Med-AI Integration API 草案
6. 分阶段开发路线
7. 验收标准
```

### 本阶段不做

```text
1. 不新增数据库表
2. 不新增 FastAPI 接口
3. 不新增前端页面
4. 不接真实设备
5. 不写 DICOM / HL7 / ASTM 解析器
6. 不做设备控制
7. 不做自动处方或药物剂量
```

## 3. 总体原则

### 3.1 设备不直接连云端

不推荐让影像设备、检验仪、监护仪直接访问 Render 后端。

原因：

```text
1. 很多设备只支持内网、串口、共享目录、TCP 或明文协议。
2. 很多设备没有现代 HTTPS / Token / 重试 / 错误处理能力。
3. 设备直连云端会放大网络安全风险。
4. 医院内网和公网环境差异大，故障排查困难。
5. 未来可能需要缓存、重试、审计、手工匹配，这些都应在网关层做。
```

### 3.2 先接结果，不控制设备

V1/V2 只做：

```text
设备结果接收
原始数据留档
标准化
关联病例
前端展示
AI 读取摘要
```

不做：

```text
远程启动检查
远程改变设备参数
下发治疗指令
自动收费
自动处方
```

### 3.3 统一病例匹配字段

设备数据必须能稳定关联到病例。推荐核心字段：

```text
case_id：Pet-Med-AI 内部病例 ID
visit_id：一次就诊 / 一次问诊 / 一次检查流程 ID
accession_id：检查申请号，推荐用于设备侧录入或条码扫描
external_patient_id：外部 HIS/PMS 患者 ID，可选
```

优先级：

```text
1. accession_id 精确匹配
2. case_id 精确匹配
3. visit_id 精确匹配
4. 手工匹配
5. 禁止只靠宠物名 + 主人电话 + 日期自动匹配
```

## 4. 推荐系统架构

```text
┌──────────────────────────────────────────────┐
│ 医院设备                                      │
│ DR/CR/CT/US/Lab/Monitor/Scale/Barcode         │
└───────────────────────┬──────────────────────┘
                        │
                        │ DICOM / HL7 / ASTM / CSV / PDF / RS232 / TCP / SDK
                        ↓
┌──────────────────────────────────────────────┐
│ petmed-device-gateway                         │
│ - 接收设备消息                                 │
│ - 保存原始 payload                             │
│ - 解析并标准化                                 │
│ - 生成 idempotency_key                         │
│ - 匹配 accession_id / case_id                  │
│ - 失败缓存 / 重试                              │
│ - 审计日志                                     │
└───────────────────────┬──────────────────────┘
                        │
                        │ HTTPS + API Key / JWT
                        ↓
┌──────────────────────────────────────────────┐
│ Pet-Med-AI Backend                            │
│ /api/integrations/...                         │
│ - 鉴权                                         │
│ - 幂等处理                                     │
│ - 数据落库                                     │
│ - 关联病例                                     │
└───────────────────────┬──────────────────────┘
                        ↓
┌──────────────────────────────────────────────┐
│ Pet-Med-AI Frontend                           │
│ - 病例详情显示检验 / 影像                       │
│ - AI 读取异常摘要                              │
│ - 医生确认与归档                               │
└──────────────────────────────────────────────┘
```

## 5. 设备分类与接口路线

| 设备类别 | 常见接口 | V1 策略 | 备注 |
|---|---|---|---|
| DR / CR / CT / MRI | DICOM C-STORE、DICOMweb、PACS 导出 | 优先做影像索引，不替代 PACS | 保存 study_uid、series、viewer_url、thumbnail |
| 超声 / 内窥镜 | DICOM、图片、视频、PDF | 先接报告 / 文件 / 图片 | 视频体积大，先只做附件引用 |
| 血常规 / 生化 / 电解质 / 血气 | HL7 v2、ASTM、CSV、TXT、串口、TCP、厂商 SDK | 先接结构化结果 | WBC/ALT/CREA/GLU/K 等按 Observation 结构表达 |
| 尿检 / 粪检 | HL7/CSV/PDF/手工录入 | 先接 CSV/PDF 或手工上传 | 显微镜结果可先走报告附件 |
| 麻醉机 / 监护仪 | HL7、TCP、串口、厂商协议 | 后期做时间序列 | 第一阶段不建议做实时流 |
| 体重秤 / 体温计 | 串口、蓝牙、USB HID、HTTP | 可作为低风险试点 | 写入体征 Observation |
| 扫码枪 / RFID | USB HID、键盘口、HTTP | 先用于 accession_id | 辅助设备匹配病例 |

## 6. 标准映射建议

### 6.1 影像

影像优先考虑：

```text
DICOM C-STORE：设备主动把影像发送到网关
DICOMweb QIDO-RS：查询影像对象
DICOMweb WADO-RS：获取影像对象或渲染图
DICOMweb STOW-RS：上传影像对象
```

Pet-Med-AI 不必第一阶段做完整 PACS。更稳的做法是：

```text
已有 PACS：Pet-Med-AI 保存索引、缩略图、viewer_url
无 PACS：本地网关或轻量 DICOM server 先接收，再上传索引
```

### 6.2 检验

检验单项结果建议映射为类似 FHIR Observation 的结构：

```json
{
  "code": "WBC",
  "name": "白细胞",
  "value": 18.2,
  "unit": "10^9/L",
  "reference_range": "6.0-17.0",
  "flag": "H"
}
```

整张报告建议映射为类似 DiagnosticReport 的结构：

```json
{
  "report_type": "laboratory",
  "category": "hematology",
  "observations": [],
  "conclusion": "白细胞升高，提示炎症或应激可能。",
  "represented_form_url": "https://..."
}
```

### 6.3 影像报告

影像检查可以拆成两层：

```text
ImagingStudy：影像 study / series / instance 索引
DiagnosticReport：影像报告正文和结论
```

## 7. 数据匹配流程

推荐未来流程：

```text
1. 医生在 Pet-Med-AI 创建病例或检查申请。
2. 系统生成 accession_id。
3. accession_id 显示为条码 / 二维码。
4. 设备检查时录入或扫描 accession_id。
5. 设备结果进入本地网关。
6. 网关按 accession_id 自动匹配病例。
7. 如果匹配失败，进入“待匹配队列”。
8. 医生或前台手工确认后归档。
```

### 7.1 accession_id 格式建议

```text
PM-YYYYMMDD-CASEID-SEQ
示例：PM-20260528-000088-01
```

字段含义：

```text
PM：Pet-Med-AI
YYYYMMDD：创建日期
CASEID：病例 ID
SEQ：同一病例下第几次检查申请
```

### 7.2 匹配失败处理

匹配失败不能丢数据。应进入：

```text
integration_pending_queue
```

显示：

```text
设备名称
检查时间
设备侧患者名
设备侧 patient_id
accession_id
结果摘要
原始 payload
候选病例
手工绑定按钮
```

## 8. 未来数据库模型草案

> 这里只是草案，不在本阶段建表。

### 8.1 Device

```text
id
device_uid
name
manufacturer
model
department
location
device_type
interface_type
enabled
created_at
updated_at
```

### 8.2 DeviceMessage

```text
id
device_id
message_uid
message_type
raw_payload_path
raw_payload_hash
received_at
processed_at
status
error_message
idempotency_key
```

### 8.3 DiagnosticReport

```text
id
case_id
visit_id
accession_id
report_type
category
source
status
issued_at
conclusion
raw_payload_ref
represented_form_url
created_at
updated_at
```

### 8.4 Observation

```text
id
diagnostic_report_id
case_id
code
name
value_number
value_text
unit
reference_range
flag
observed_at
created_at
```

### 8.5 ImagingStudy

```text
id
case_id
visit_id
accession_id
study_uid
modality
study_datetime
series_count
instance_count
viewer_url
thumbnail_url
dicomweb_endpoint
created_at
updated_at
```

### 8.6 IntegrationJob

```text
id
job_uid
source
status
attempt_count
last_error
next_retry_at
created_at
updated_at
```

## 9. 安全设计

### 9.1 鉴权

V1 推荐：

```text
网关 API Key
请求签名 HMAC
idempotency_key
每个医院 / 每个网关独立凭据
```

后期可升级：

```text
mTLS
IP allowlist
短期 JWT
网关证书轮换
```

### 9.2 数据安全

```text
1. 原始 payload 应保存在受控目录或对象存储。
2. 上传前可做最小必要字段抽取。
3. 影像文件大对象不一定直接进 PostgreSQL。
4. 日志中避免记录完整主人电话、身份证、详细地址等敏感信息。
5. 失败消息要脱敏。
```

### 9.3 审计

每次设备数据进入系统应记录：

```text
received_at
source_device
payload_hash
matched_case_id
processed_by
status
error_message
```

## 10. 分阶段路线

### Phase 1：医院设备接口需求与架构 V1

当前阶段。只写文档。

目标：

```text
HOSPITAL_DEVICE_INTEGRATION.md
DEVICE_INVENTORY_TEMPLATE.csv
PETMED_INTEGRATION_API_DRAFT.md
```

验收：

```text
文档进入 docs/integrations/
不改运行代码
不需要 smoke
```

### Phase 2：设备清单采集

拿到医院真实设备清单、厂家接口文档、样例文件。

产出：

```text
DEVICE_INVENTORY_FILLED.csv
sample_hl7/
sample_csv/
sample_dicom_metadata/
```

### Phase 3：Alembic 数据库迁移 V1

先把数据库迁移体系立起来，避免后续设备表靠临时补列。

### Phase 4：诊断数据模型 V1

新增：

```text
DiagnosticReport
Observation
ImagingStudy
Device
DeviceMessage
IntegrationJob
```

### Phase 5：Pet-Med-AI Integration API V1

实现后端接口，支持 mock payload 入库。

### Phase 6：本地设备网关 V1

先支持：

```text
CSV 文件夹监听
HL7 文件夹监听
DICOM 元数据接收或导入
失败重试
```

### Phase 7：检验结果接入 V1

先接血常规 / 生化 / 电解质。

### Phase 8：影像索引接入 V1

先接 ImagingStudy 索引、缩略图、viewer_url，不替代 PACS。

### Phase 9：病例详情显示检验 / 影像 V1

病例详情新增诊断数据区域。

### Phase 10：AI 读取检验异常摘要 V1

AI 不直接读原始全文，先读结构化摘要：

```text
贫血
白细胞升高
肝酶升高
肾指标升高
低血糖
高钾
尿比重异常
```

## 11. 验收标准

本阶段验收：

```text
1. docs/integrations/HOSPITAL_DEVICE_INTEGRATION.md 存在
2. docs/integrations/DEVICE_INVENTORY_TEMPLATE.csv 存在
3. docs/integrations/PETMED_INTEGRATION_API_DRAFT.md 存在
4. git diff 只包含上述文档
5. 不需要本地 smoke
6. 不需要线上 smoke
```

提交命令必须限定目标文件：

```bash
git add docs/integrations/HOSPITAL_DEVICE_INTEGRATION.md \
        docs/integrations/DEVICE_INVENTORY_TEMPLATE.csv \
        docs/integrations/PETMED_INTEGRATION_API_DRAFT.md
```

禁止：

```bash
git add .
```

## 12. 资料来源与标准参考

- DICOM 官方说明：DICOM 是医学影像信息传输、存储、检索、打印、处理和显示的国际标准。
- DICOMweb 官方说明：DICOMweb 是基于 Web 的 DICOM 标准，包含 QIDO-RS、WADO-RS、STOW-RS、UPS-RS 等 RESTful 服务。
- HL7 FHIR Observation：用于记录测量值和简单断言，适合体征、实验室数据、设备测量等。
- HL7 FHIR DiagnosticReport：适合实验室、病理、影像等诊断报告，可包含 atomic results、图像、文本解释和格式化报告。
- HL7 FHIR ImagingStudy：用于表达 DICOM imaging study 的 study/series/instance 信息，但不直接存储 DICOM 实例本体。
