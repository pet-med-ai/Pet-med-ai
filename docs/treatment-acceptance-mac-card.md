# 新候选 Mac / Safari 合成验收操作卡

此包继承 #75 `8d70d10f` 的多院区与治疗签署业务代码，增加独立验收工具。
**实际固定候选以包内 `acceptance-manifest.json` 和启动回执中的完整 commit 为准。**
启动前逐文件核验；源码被修改则拒绝启动。旧 S6—S8A 不计入本轮。

## 首次启动（先做这一段）

1. 在 Mac 下载并解压 `PMAI-treatment-acceptance-候选号.tar.gz`。
2. 打开终端，输入 `cd `（有空格），把解压后的 `PMAI-treatment-acceptance` 文件夹拖入终端，再按回车。
3. 若未安装 PostgreSQL 17，执行 `brew install postgresql@17`。不运行 `brew services start`。
4. 执行：

   ```sh
   bash scripts/treatment_acceptance_mac.command
   ```

   首次准备 Python 3.11 虚拟环境和前端依赖，随后打开原生 Safari。需要本机 Python 3.11、Node/npm 和 Homebrew；任何缺项会直接报错，保留错误供排查，不自行替换成旧包。
5. 使用终端显示的**本次随机合成密码**，账号 `doctor-a@example.invalid`。选择“合成机构A／一院”，查看 **#101 合成犬-基础签署**。
6. 保持启动终端打开。先填写诊断、评估和治疗措施 → 保存治疗草稿 → 冻结版本 → 勾选核对、填原因 → 审核通过 → **再次勾选核对**、输入密码 → 再次认证并确认签署。
   必须实际看到“已独立回读签署”，原文逐字一致才记为通过。

复制到评估和治疗措施的原文（第一处是真实换行，后面的 `\n` 是两个字符）：

```text
合成验收 café 🐾
原文 {{literal}}; literal \n remains
```

## 状态、停止与清理

另开一个终端，同样 `cd` 到解压文件夹后执行；不要关闭 Safari 标签页来代替停止服务。

```sh
bash scripts/treatment_acceptance_mac.command status
bash scripts/treatment_acceptance_mac.command control stop
bash scripts/treatment_acceptance_mac.command cleanup
```

`stop` 必须返回 `status=STOPPED`、`cleanup=true`。它停止本轮服务器并删除本轮临时 PostgreSQL；`cleanup` 再移除随机账号文件及前端构建，保留回执。
每次重新启动都会新建数据库，前一轮合成病例不会接着使用；异常停止时保留本轮路径和日志，不手工删除不认识的目录。

## 账号与权限（同一个随机合成密码）

| 账号（均加 `@example.invalid`） | 应观察到的结果 |
| --- | --- |
| doctor-a | 一院医生；#101 等共享病例可编辑、审核、签署；不能看 #103 私有病例 |
| doctor-b | 一院第二医生；另可读自己的 #103 私有病例 |
| assistant | 一院助理；可保存/冻结草稿，不能审核/签署 |
| frontdesk | 一院基本资料；没有诊疗原文和治疗签署区 |
| admin | 组织管理账号；无默认病例读取权限 |
| remote | 二院医生；对一院仅 #102 显式只读，不能修改/签署 |
| other | 另一机构医生；只看自己的隔离院区 |

## 后续分段验收（完成基础段后逐项做）

以下命令都在第二个终端运行，仅影响本轮新建的合成数据库。
CLI 回执和代理响应记录只证明测试条件，**不能代替 Safari 界面、复制结果或浏览器收包观察**。

| 项目 | 操作与通过条件 |
| --- | --- |
| 旧草稿失效 | #108 冻结后修改并保存草稿；旧冻结版本不能审核/签署 |
| 诊断来源变化 | #108 冻结后运行 `bash scripts/treatment_acceptance_mac.command control source-change`；再审核旧版，应提示来源变化。命令只向 #108 新增合成诊断报告 |
| 401 原文保留 | doctor-a 在 #108 写入尚未保存的文本，运行 `bash scripts/treatment_acceptance_mac.command control expire`，点击“重新读取治疗记录”；原文只读且可复制，旧勾选/密码失效。退出前先复制未保存原文 |
| 丢响应与原请求 | #109 保存→冻结→审核后，运行 `bash scripts/treatment_acceptance_mac.command control lose-sign-response`，再签署。点击“停止等待（保留原请求）”；同一标签页退出并用同账号重登、打开 #109、查询原请求，必须独立回读且只新增一次签署。最后运行 `… control release`。换账号不能恢复原账号的请求 |
| 双医生 | 运行 `bash scripts/treatment_acceptance_mac.command control policy-two`；doctor-a 在 #107 重新保存、冻结、审核；同人签署被拒绝，doctor-b 登录后核对并签署成功。此规则作用于合成机构A全部院区，会使之前冻结但未签署的来源失效。完成后 `… control policy-self` |
| 修订／作废／再签 | 在 #110 形成首次签署，填原因→创建修订草稿→修改保存→重新冻结审核签署；旧签署显示被替代。再勾选待作废签署、填原因和密码作废；历史仍在，草稿原文仍在。重新冻结、审核、认证可形成新签署 |
| 迟到 200 | 运行 `bash scripts/treatment_acceptance_mac.command control late-200`，再“查看”某病例使响应被暂扣；退出并换 doctor-b，打开 #103；执行 `… control release`，旧病例不得填回 |
| 迟到 401 | 同上换成 `… control late-401`。换账号/病例后释放，不应清掉新账号内容。401 是明确的测试注入；不是医院实际会话事故 |

`…` 表示同一完整前缀 `bash scripts/treatment_acceptance_mac.command`，不要把省略号作为命令输入。
迟到响应最多暂扣 180 秒；一次只挂一个条件，`release` 解除。浏览器主动取消请求时应记录为取消，不宣称已收到迟到包。

可以逐项保留本人观察（必须在 macOS，填写实际 Safari 版本和看到的结果）：

```sh
bash scripts/treatment_acceptance_mac.command observe sign-readback PASS --browser 'Safari 实际版本' --note '本人看到独立回读；病例号、文本与版本一致'
```

项目键：`roles`、`sign-readback`、`utf8`、`stale-draft`、`stale-source`、`expired-copy`、`lost-response`、`two-person`、`amend-revoke-resign`、`late-200`、`late-401`。
单项可以记 `PASS`、`FAIL` 或 `BLOCKED`；回执不自动把整体验收改成通过。只记录实际观察，未做的留空。

## 一次性数据库独立演练

开发侧已独立执行；Mac 无需为重复已有结果再运行。若要另做 Mac 本机演练，先停止浏览器会话，然后：

```sh
bash scripts/treatment_acceptance_mac.command drill
```

工具自己创建全新源集群和两个全新恢复集群，不接受任何现有数据库 URL。
依次执行空库→0009、合成旧病例、迁移前备份/恢复、mc01 显式回填 dry-run/apply/同清单重放、只读策略、mc02、医生核验、旧文本未签署导入、真实 API 签署/修订/作废/再签、签署后备份/恢复。
核对全表数据摘要、序列、权限/角色、RLS、函数、触发器和约束，再用受限运行账号回读原签署与请求回执。
PostgreSQL 恢复可能把 varchar 常量数组到 text 数组的 CHECK 转型分配到每个元素；校验器只归一化这一个明确等价形式，并另验证恢复后的非法状态值被 CHECK 拒绝。
备份不含角色密码；恢复后单独设置新的合成运行密码。备份包和回执留在本轮路径，三个临时集群全部停机清理。

## 证据边界

- 本包实际运行当前候选的 React 页面、v2 路由、权限门和 PostgreSQL 策略；验收宿主单独提供静态页面与测试条件，不是生产部署入口。
- 当前 Linux 自动化、CI Chromium、新 Mac/Safari 人工结果分别列账。`manual_safari_result=PENDING`、`acceptance=NOT_CLOSED` 保持到人工复核完成。
- 本轮不是证书电子签名、真实处方或医院数据库迁移；不涉及真实数据、外发消息、真实设备、收费库存和生产恢复。
- 单机逻辑备份恢复不等于云服务 PITR、跨地域灾备、生产规模性能或医院恢复时间验收。Mac Word/旧版手工项目另按原台账处理。
