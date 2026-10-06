# 伴侣动物医生工作流批次对应与交付状态

2026-10-06 建档。原异宠开发目录的 **B5 = Snake Depth V2** 保持原意；本索引以 CW 前缀区分医生工作流。旧 PR 标题、提交、文档及预算记录保持原样，通过下表对应。未来使用 CW 前缀，不将裸 B5 改写为语音任务。

| 本线名称 | 历史名称 / PR | 范围 | 草稿候选 | CI 通过 | 已合并 | 已上线 | 医生验收 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CW-M7 | M7 / [#45](https://github.com/pet-med-ai/Pet-med-ai/pull/45) | 犬猫腹泻采集；后补门诊宠主姓名/毛色 | 草稿 PR | 历史候选已通过 | 否 | 待核验 | 待补 |
| CW-B1 | B1 / [#46](https://github.com/pet-med-ai/Pet-med-ai/pull/46) | 食欲/消瘦、多饮多尿、咳嗽/呼吸 | 草稿 PR | 历史候选已通过 | 否 | 待核验 | 待补 |
| CW-B2 | B2 / [#47](https://github.com/pet-med-ai/Pet-med-ai/pull/47) | 晕厥/抽搐、排尿、皮肤、跛行/疼痛 | 草稿 PR | 历史候选已通过 | 否 | 待核验 | 待补 |
| CW-B3 | B3 / [#48](https://github.com/pet-med-ai/Pet-med-ai/pull/48) | 发热/精神沉郁、老年筛查 | 草稿 PR | 历史候选已通过 | 否 | 待核验 | 待补 |
| CW-B4 | B4 / [#49](https://github.com/pet-med-ai/Pet-med-ai/pull/49) | 输入依据和问诊链路修复 | 草稿 PR | 历史候选已通过 | 否 | 待核验 | 待补 |
| CW-B5 | CW-B5 / [#50](https://github.com/pet-med-ai/Pet-med-ai/pull/50) | 外部语音草稿、医生确认、费用上限 | 草稿 PR | bba8703 四组适用 CI 通过 | 否 | 否 | 待补；真实服务调用未验收 |
| CW-B6 | CW-B6 / [#51](https://github.com/pet-med-ai/Pet-med-ai/pull/51) | 手工原件归档、核对、授权回看、撤销 | 草稿 PR | b981aed 四组适用 CI 通过 | 否 | 否 | 未验收 |
| CW-B7 | 检验项目人工录入 | 原件抄录、逐项核对、版本更正和撤销 | 已批准，独立候选实现 | 待本批精确提交验证 | 否 | 否 | 未验收 |

历史 CI 状态仅对应各历史候选；不能作为新提交的 CI 结果。最后四项是独立状态：“草稿 PR + CI 通过”不代表合并、上线或医生验收。后续精确提交/工作流与实际预算在对应 PR 和 [CW-B6 批准页](https://chatgpt.com/space/page_0f8a935095e8819191bf42662c7ded6a)追加，不为记录状态重跑成功 CI。

开发顺序：CW-B6 已到草稿 PR 和 CI；当前推进批准的 CW-B7 人工检验录入与核对，方案见 [MANUAL_LAB_RESULTS_CW_B7.md](../clinical_docs/MANUAL_LAB_RESULTS_CW_B7.md)。CW-B7 精确提交、CI 和实际预算追加至[批准页](https://chatgpt.com/space/page_ef7694de75848191852e3938271226f3)及本批 PR，不为更新目录文字重跑已成功的 CI。OCR、设备接入、生产持久存储及上线均未预先授权，应另行给出范围、预算及验收标准。CW-B5 外部转写仍沿用单独 100 次/1 元额度，未获得测试凭据及获准网络条件前不调用；本批外部服务费用 0 元。五份 Mac Word 人工检查继续后补。

CW-B6 技术方案及限制见 [CASE_ATTACHMENTS_CW_B6.md](../clinical_docs/CASE_ATTACHMENTS_CW_B6.md)。所有阶段继续保留不合并、不部署、不操作生产数据的边界。
