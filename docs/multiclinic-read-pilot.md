# 院区权限第一批：病例只读入口

本增量基于 `58cdf136093d129fca71fb246a88d7cc896f1c91`，落实多院区设计的第一步。当前交付是可测试的病例权限基础和只读页面；治疗签署持久化在后续增量实施。本分支不改动 PR72 的 Mac 验收版本，也不自动部署或迁移任何既有数据库。

## 当前行为

| 角色／授权 | 病例基本资料 | 诊疗内容 | 本增量写入能力 |
| --- | --- | --- | --- |
| 院区兽医、临床助理、临床审计员 | 对授权范围可读 | 对授权范围可读 | 无 |
| 院区前台 | 对授权范围可读 | 不返回这些字段 | 无 |
| 组织管理员、院区管理员 | 无默认病例权限 | 无默认病例权限 | 无 Web 业务写入 |
| 收费、药房 | 无通用病例权限 | 无通用病例权限 | 无；对应专用投影待实现 |
| 指定病例的有效 `clinical.read` 授权 | 仅该病例 | 仅该病例 | 无 |

机构是租户边界。URL 中的机构和院区 ID 只选择工作范围，不能授予权限。服务端每次读取重新检查账号、服务端会话、成员状态、角色有效期、机构与院区状态。未知 `policy_version` 拒绝访问。

旧病例回填后保持 `owner_private`：即使在同一院区，普通临床角色也不能读取其他人的旧私人病例；病例所有者仍需有效院区角色，或获得显式病例只读授权。新建院区共享病例的写入入口尚未开放，不把所有旧病例自动改成共享。

数据库使用独立 `pmai_scope_runtime` 角色，不能直接读写 `cases` 或旧子表。两种安全屏障视图分别提供诊疗字段和前台字段；视图下的病例表启用 `ENABLE/FORCE ROW LEVEL SECURITY`。前台即使直接查询诊疗视图，也拿不到诊疗行。身份与机构上下文通过事务级 `set_config(..., true)` 绑定，连接复用后清空。

`PMAI_MULTICLINIC_MODE=read_pilot` 时，除 `/healthz` 和 `/api/v2/` 外所有后端路径返回 `409 CLINIC_WORKFLOW_NOT_PORTED`；v2 下仅注册下列接口。旧病例、文书、附件、随访、设备导入、AI、导出等入口均不能绕过这道边界。未知模式也拒绝业务请求。默认 `off` 维持旧模式，v2 接口不可用。

## 接口与页面

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| POST | `/api/v2/auth/login` | JSON `{email,password}`；返回 15 分钟 v2 access token，并持久化会话；仅允许 active human 账号 |
| POST | `/api/v2/auth/logout` | 撤销当前服务端会话；204 |
| GET | `/api/v2/scopes` | 返回当前可查阅的机构、院区和读权限；不自动选第一个院区 |
| GET | `/api/v2/organizations/{org}/clinics/{clinic}/cases` | `projection=clinical|demographics`、`after=0`、`limit=1..100`；仅返回可访问行 |
| GET | 同上追加 `/{case_id}` | 不存在或无权限统一 404；旧 email-sub JWT 不接受 |

全部 v2 响应 `Cache-Control: no-store`。v2 JWT 使用独立密钥、稳定整数用户 ID、`sid`、`tv`、`ver=2`、固定 audience/issuer；JWT 中没有可用于授权的角色。撤销成员资格不必等 token 到期；下一个 SQL 语句按最新权限判断。已经完成授权并执行的读取不承诺被追溯取消。

前端 `VITE_MULTICLINIC_READ_PILOT=1` 构建显示独立院区查阅页：登录 → 主动选院区 → 列表 → 详情。令牌只在本页内存；刷新需重新登录，本批没有 refresh-cookie 功能。切院区、退出、当前会话 401 会清除旧内容，迟到响应不能填回。治疗文本标注“未经本系统签署”，没有保存、处方、签署或下载按钮。

## 数据与迁移

活动迁移链新增 `0009_diag_data → mc01_scope_expand`；不激活历史 `0010` 草案。mc01 只扩展数据库结构并将 `cases.owner_id` 删除策略改为 RESTRICT；ORM 同时移除用户删除时的病例级联。`source` 代码运行不会自行执行迁移。

| 对象 | 本批结构 |
| --- | --- |
| users | `status`、`principal_kind`、`token_version`；保留整数 ID |
| organizations / clinics | UUID，机构状态、策略版本、权限 epoch；院区含时区与唯一 code |
| org_memberships / role_bindings | 显式人员归属、机构／院区角色范围、有效期、撤销时间、授予者 |
| patients | UUID、机构内编号；历史病例按病例生成独立患者，不按同名／电话合并 |
| cases | `org_id, clinic_id, patient_id` 可空扩展；`visibility` 默认 owner_private；行版本、临床 epoch |
| case_access_grants | 指定病例、同机构成员、只读权限、原因、到期与撤销；复合外键防止串租户 |
| auth_sessions | UUID、用户、令牌版本、到期和撤销时间 |
| access_audit_events | 权限操作原因、操作前后内容、幂等键；安装策略后禁止 UPDATE/DELETE/TRUNCATE |
| migration_batches | 映射摘要、批次、游标、原文摘要与计数；与同批回填原子提交 |

这些新表由显式 SQL/迁移管理；`multiclinic/migration_ownership.py` 防止旧 ORM 的 autogenerate 将它们误判成应删除对象。后续改动须写新的前向迁移，并运行真实 PostgreSQL 检查；不在生产库用 `create_all` 补表。

回填清单为 JSON，完整字段由 `multiclinic.migrate.Manifest` 校验。必要顶层字段：`migration_key, operator_user_id, reason, organizations, clinics, memberships, role_bindings, cases`。每条病例映射必须明确 `{case_id, expected_owner_id, org_id, clinic_id}`。账号必须已存在；不自动创建员工，不重编号病例，不改变原始临床内容或旧日期时区。记录的 `operator_user_id` 是迁移操作员声明的审计关联，不是医生电子签名。

可运行的合成映射示例见测试中的 `ClinicPostgresTests.manifest`；真实映射必须由院方核对，不直接拿合成 ID 使用。

### 隔离演练步骤

以下命令是运行手册，本分支创建不会执行这些操作。先建立独立目标并验证备份恢复，停止该目标的旧 Web、worker、队列与写入方；管理员核对目标 URL 和当前 Alembic 版本。数据库管理连接与 Web 运行连接分离。新策略安装后，旧进程不得继续连接该目标。

1. 在已核对的目标，用管理连接从 `0009_diag_data` 升到 `mc01_scope_expand`。若版本不同，先设计前向桥接，禁止 `stamp` 假装已迁移。
2. 提供单独 `MULTICLINIC_ADMIN_DATABASE_URL`；脚本不会回退使用 `DATABASE_URL`。先运行 `python scripts/multiclinic_admin.py backfill approved-mapping.json` 做事务内验证并回滚；核对输出摘要后，在同一已授权演练目标加 `--apply --batch-size 200` 执行。
3. 回填中断可用相同清单、migration_key 和 batch-size 继续。清单变化、旧 owner 不符、目标院区跨机构或已被别的批次分配都会拒绝。每批回填和 checkpoint 一起提交。进入只读入口前核对遗漏病例；未映射病例不会在入口出现。
4. 在这个隔离目标运行 `python scripts/multiclinic_admin.py install-read-policy`。需要该目标的建角色、DDL 和授权能力；只读策略安装与展开迁移分开，避免结构升级无意改变旧应用读取行为。数据库用户口令由目标环境配置，本仓库不生成生产密码。
5. Web 设置 `PMAI_MULTICLINIC_MODE=read_pilot`、`MULTICLINIC_DATABASE_URL` 指向 `pmai_scope_runtime` 连接、`MULTICLINIC_TOKEN_SECRET` 使用独立随机长密钥（至少 32 字符）。前端设置 `VITE_MULTICLINIC_READ_PILOT=1` 和正确的 `VITE_API_BASE` 后构建。客户端开关本身不是安全边界。
6. 用受控合成账号检查下面测试矩阵后再评审。账号公开注册、旧 token、旧业务路由均不可用于该模式。

权限撤销管理命令：`python scripts/multiclinic_admin.py revoke-membership --org-id UUID --membership-id UUID --actor-id INTEGER --reason TEXT --request-key HEX64`。只允许记录为该机构有效组织管理员的 actor；组织锁 → 成员锁 → 状态／epoch／审计在同一事务完成。同请求键重复调用只回放，不重复撤销；异载荷冲突。管理数据库凭据必须由可信运维持有，不能提供给浏览器。本批没有开放成员管理 Web API。

回滚：mc01 拒绝破坏性 downgrade。新写入前恢复已验证的旧备份；有新会话、权限或迁移审计记录后，使用兼容新结构的修复或只读停机，不能退回会绕过院区边界的旧服务。不要给 Web 超级用户、表所有者、BYPASSRLS、角色继承或 DDL 权限。应用每次请求都会核对运行角色边界。

## 本地和 CI 验证

```bash
# 已存在的专用 PostgreSQL 测试服务：测试会另建随机 pmai_scope_test_* 数据库并销毁。
# PMAI_TEST_POSTGRES_ADMIN_URL 只绑定到测试管理员，不能指向业务库或生产管理员。
python scripts/run_multiclinic_tests.py

# 或由本机 PostgreSQL 二进制创建、停止并清理临时集群：
python scripts/run_multiclinic_tests.py --postgres-bin /absolute/path/to/postgresql/bin

cd frontend
node tests/run-consult-update-review.mjs clinic-read-pilot case-list-auth case-detail-auth-expiry
VITE_MULTICLINIC_READ_PILOT=1 npm run build
```

数据库测试覆盖真实 Alembic 链、非 owner 运行账号、跨机构／院区、旧私人病例、前台字段投影、管理员权限分离、授权过期、成员撤销、服务账号、会话撤销、连接池上下文清除、旧路由封堵、复合外键、物理删除保护、策略重复安装、回填断点与原文校验。前端测试包含切院区迟到响应、旧 401、退出与内容清除；现有登录／病例列表／401 用例作为回归。

旧静态治理包把 `backend/models.py` 锁定为历史哈希；本批移除用户删除级联后，直接在新代码上运行旧包会报 `NO-GO: protected hash backend/models.py`。CI 因此先确认历史文档、验证器、runner、Render 配置和旧检查脚本均未更改，再在固定 `58cdf136` 临时 worktree 重放原检查；当前 backend 的语法及新权限／模型行为由当前分支检查和独立 PostgreSQL/UI job 验证。原哈希不修改，旧包通过不能替代新分支验收。单独运行旧脚本看到该 NO-GO 是范围不匹配，应使用 `python scripts/check_frozen_candidate.py` 并检查新 job。

## 尚未完成的方案内容

本增量不能作为医院正式全功能上线依据。接下来依次实施：

1. 写入工作流和所有病例子对象的机构／院区列、复合外键、权限审计与 RLS；账号人员管理界面、已验证医生档案、refresh-cookie/CSRF、防暴力登录、部署健康检查与正式迁移收紧。
2. `mc02_treatment_store`：治疗草稿与不可变版本、复核记录、真实医生绑定、签署挑战、幂等提交／未知结果查询、撤销和补正、审计事务。旧 `Case.treatment` 只导入为未签署原文。
3. 完整回填和验收后再实施 `mc03_scope_enforce`，收紧必要 NOT NULL 与全部业务表隔离；旧路由逐个迁入授权层后才能开放。
4. 电子签名服务证明、处方、设备、语音、自动消息、收费库存等各自接入与验收。不得因为签署了治疗记录就自动触发处方、扣库存或发送消息。

既有 S6/S7/S8/S8A 凭证只对应原候选版本；不沿用为本分支的 Mac 原生 Safari 验收结论。
