// Real frontend + v2 API + fresh PostgreSQL. Linux Chromium is not native Safari.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const { chromium, expect } = require(process.env.PMAI_PLAYWRIGHT_MODULE || '@playwright/test');
const state = process.env.PMAI_ACCEPTANCE_STATE;
assert(state, 'PMAI_ACCEPTANCE_STATE is required');
const receipt = JSON.parse(fs.readFileSync(path.join(state, 'receipt.json')));
const fixture = JSON.parse(fs.readFileSync(path.join(state, 'accounts.json')));
const control = action => execFileSync(process.env.PMAI_ACCEPTANCE_PYTHON || 'python', ['scripts/treatment_acceptance.py', '--state', state, 'control', action], { stdio: 'pipe' });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const errors = [], checks = [], caseWritePaths = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('request', request => {
  const pathname = new URL(request.url()).pathname;
  if (['POST', 'PATCH', 'PUT', 'DELETE'].includes(request.method()) && pathname.startsWith('/api/v2/organizations/')) {
    caseWritePaths.push(pathname);
  }
});
const text = '合成验收 café 🐾\n原文 {{literal}}; literal \\n remains';
const result = { candidate: receipt.candidate, browser: 'Linux Chromium', manual_safari_result: 'PENDING', acceptance: 'NOT_CLOSED', checks };

async function login(name='doctor-a') {
  await page.getByLabel('邮箱', { exact: true }).fill(name + '@example.invalid');
  await page.getByLabel('密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page.getByRole('button', { name: '退出登录', exact: true })).toBeVisible();
}
async function openCase(id) {
  await page.getByLabel('机构／院区', { exact: true }).selectOption(fixture.org + '/' + fixture.clinic);
  await page.getByRole('row').filter({ has: page.getByRole('cell', { name: '#' + id, exact: true }) }).getByRole('button', { name: '查看', exact: true }).click();
  await expect(page.locator('[aria-label="病例详情"] h2').first()).toContainText('#' + id);
  if (await page.locator('[aria-label="治疗签署"]').count()) await expect(page.getByRole('button', { name: '重新读取治疗记录', exact: true })).toBeEnabled();
}
async function logout() { await page.getByRole('button', { name: '退出登录', exact: true }).click(); await expect(page.getByRole('button', { name: '登录', exact: true })).toBeEnabled(); }
const saveDraft = () => page.getByRole('button', { name: '保存治疗草稿', exact: true }).click();
async function freeze(content=text, save=saveDraft) {
  await page.getByLabel('治疗诊断', { exact: true }).fill('合成诊断，仅软件验收');
  await page.getByLabel('治疗评估', { exact: true }).fill(content);
  await page.getByLabel('治疗措施', { exact: true }).fill(content);
  await save();
  await page.getByRole('button', { name: '冻结版本供核对', exact: true }).click();
  await expect(page.getByLabel('已核对冻结版本', { exact: true })).toBeEnabled();
}
async function saveWithForeignReceipt() {
  const casePath = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/101`;
  const draftPath = casePath + '/treatment/draft';
  const draftURL = new URL(draftPath, receipt.url).href;
  const writesBefore = caseWritePaths.length;
  const lookups = [];
  function observeLookup(request) {
    const url = new URL(request.url());
    if (request.method() === 'GET' && url.pathname.startsWith(casePath + '/commands/')) lookups.push(url.href);
  }
  page.on('request', observeLookup);
  let committed;
  // Forward the existing first save once. Change only the committed response delivered to the page.
  await page.route(draftURL, async route => {
    const original = await route.fetch({ maxRedirects: 0, maxRetries: 0 });
    committed = await original.json();
    const foreignKey = committed.idempotency_key === '0'.repeat(64) ? '1'.repeat(64) : '0'.repeat(64);
    await route.fulfill({ response: original, json: { ...committed, idempotency_key: foreignKey } });
  }, { times: 1 });
  const [delivered] = await Promise.all([
    page.waitForResponse(response => response.url() === draftURL && response.request().method() === 'PATCH'),
    saveDraft(),
  ]);
  const key = delivered.request().headers()['idempotency-key'];
  const submitted = delivered.request().postDataJSON().content;
  assert.match(key, /^[0-9a-f]{64}$/);
  assert.equal(delivered.status(), 201);
  assert.equal(committed.state, 'committed');
  assert.equal(committed.operation, 'draft.save');
  assert.equal(committed.idempotency_key, key);
  const altered = await delivered.json();
  assert.notEqual(altered.idempotency_key, key);
  assert.deepEqual({ ...altered, idempotency_key: key }, committed);

  const lookup = page.getByRole('button', { name: '查询原请求', exact: true });
  const freezeButton = page.getByRole('button', { name: '冻结版本供核对', exact: true });
  await expect(lookup).toBeEnabled();
  await expect(page.getByText('待核对请求：' + key, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '保存治疗草稿', exact: true })).toBeDisabled();
  await expect(freezeButton).toBeDisabled();
  assert.deepEqual(lookups, []);
  const lookupURL = new URL(casePath + '/commands/' + key + '?operation=draft.save', receipt.url).href;
  const aggregateURL = new URL(casePath + '/treatment', receipt.url).href;
  const [original, aggregate] = await Promise.all([
    page.waitForResponse(response => response.url() === lookupURL && response.request().method() === 'GET'),
    page.waitForResponse(response => response.url() === aggregateURL && response.request().method() === 'GET'),
    lookup.click(),
  ]);
  assert.equal(original.status(), 201);
  assert.deepEqual(await original.json(), committed);
  assert.equal(aggregate.status(), 200);
  const recovered = await aggregate.json();
  assert.equal(recovered.draft_etag, committed.draft_etag);
  assert.equal(recovered.draft.draft_version, committed.draft_version);
  assert.deepEqual(recovered.draft.content, submitted);
  await expect(lookup).toHaveCount(0);
  await expect(page.getByLabel('治疗评估', { exact: true })).toHaveValue(submitted.assessment);
  await expect(freezeButton).toBeEnabled();
  assert.deepEqual(lookups, [lookupURL]);
  assert.deepEqual(caseWritePaths.slice(writesBefore), [draftPath]);
  page.off('request', observeLookup);
  checks.push('foreign-draft-receipt-original-key-recovery-no-repeat-write');
}
async function review() {
  await page.getByLabel('已核对冻结版本', { exact: true }).check();
  await page.getByLabel('操作原因', { exact: true }).fill('核对合成原文');
  await page.getByRole('button', { name: '审核通过', exact: true }).click();
  // The action button itself also says 审核通过. Wait for the persisted review,
  // after reload has reset the previous acknowledgement, before checking again.
  await expect(page.getByRole('button', { name: '审核通过', exact: true })).toHaveCount(0);
  await expect(page.locator('[aria-label="冻结版本"]')).toContainText('审核：');
  await expect(page.getByLabel('已核对冻结版本', { exact: true })).toBeEnabled();
}
async function sign() {
  await page.getByLabel('已核对冻结版本', { exact: true }).check();
  await page.getByLabel('签署认证密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '再次认证并确认签署', exact: true }).click();
}
async function readback() {
  await expect(page.locator('[aria-label="独立回读签署"]')).toBeVisible();
}
async function rejectWrongPassword(action) {
  const frozen = page.getByLabel('已核对冻结版本', { exact: true });
  const revoke = page.getByLabel('已核对待作废签署', { exact: true });
  const password = page.getByLabel('签署认证密码', { exact: true });
  const button = page.getByRole('button', { name: action === 'sign' ? '再次认证并确认签署' : '再次认证并作废签署', exact: true });
  await frozen.check();
  if (action === 'revoke') await revoke.check();
  await password.fill('deliberately-invalid-synthetic-password');
  const writesBefore = caseWritePaths.length;
  const [proof] = await Promise.all([
    page.waitForResponse(response => response.request().method() === 'POST' &&
      new URL(response.url()).pathname === '/api/v2/auth/reauthenticate'),
    button.click(),
  ]);
  assert.equal(proof.status(), 401);
  assert.equal((await proof.json()).code, 'REAUTHENTICATION_FAILED');
  await expect(page.getByText('再次认证未通过，本次操作尚未提交。请重新核对并输入当前账号密码。', { exact: true })).toBeVisible();
  await expect(page.locator('[aria-label="病例详情"] h2').first()).toContainText('#101');
  await expect(page.locator('[aria-label="冻结版本"]')).toContainText('审核通过');
  await expect(frozen).not.toBeChecked();
  if (action === 'revoke') {
    await expect(revoke).not.toBeChecked();
    await expect(page.locator('[aria-label="当前有效签署"]')).toBeVisible();
  }
  await expect(password).toHaveValue('');
  await expect(button).toBeDisabled();
  await expect(page.getByRole('button', { name: '查询原请求', exact: true })).toHaveCount(0);
  assert.equal(caseWritePaths.length, writesBefore, 'Rejected proof must not send a case mutation');
  return writesBefore;
}
async function checkDiscardOnCaseSwitch() {
  const heading = page.locator('[aria-label="病例详情"] h2').first();
  const assessment = page.getByLabel('治疗评估', { exact: true });
  const rowButton = id => page.getByRole('row')
    .filter({ has: page.getByRole('cell', { name: '#' + id, exact: true }) })
    .getByRole('button', { name: '查看', exact: true });
  const writesBefore = caseWritePaths.length;
  await openCase(110);
  // Only #104 has an imported treatment draft. #110 starts with an empty assessment.
  await expect(assessment).toHaveValue('');
  const localText = '仅在本页的合成评估 🐾\n未保存 {{navigation}}';
  await assessment.fill(localText);

  async function selectImportedCase(discard) {
    const targetPath = `/api/v2/organizations/${fixture.org}/clinics/${fixture.clinic}/cases/104`;
    const [prompt, detail] = await Promise.all([
      page.waitForEvent('dialog', { timeout: 10000 }).then(async dialog => {
        const observed = { type: dialog.type(), message: dialog.message() };
        if (discard) await dialog.accept();
        else await dialog.dismiss();
        return observed;
      }),
      page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).pathname === targetPath),
      rowButton(104).click(),
    ]);
    assert.equal(detail.status(), 200);
    assert.equal(prompt.type, 'confirm');
    assert.match(prompt.message, /未保存.*草稿/);
  }

  await selectImportedCase(false);
  await expect(heading).toContainText('#110');
  await expect(assessment).toHaveValue(localText);
  await expect(page.getByText('有尚未保存的修改。保存后才能冻结和签署。', { exact: true })).toBeVisible();

  await selectImportedCase(true);
  await expect(heading).toContainText('#104');
  await expect(assessment).toHaveValue(text);
  await expect(page.getByLabel('治疗措施', { exact: true })).toHaveValue(text);

  await rowButton(110).click();
  await expect(heading).toContainText('#110');
  await expect(assessment).toHaveValue('');
  assert.equal(caseWritePaths.length, writesBefore, 'Navigating and discarding must send no case mutation');
  checks.push('dirty-case-switch-cancel-preserves-confirm-discards-without-write');
}
async function prepared(kind, after=0) {
  await expect.poll(() => {
    const events = JSON.parse(fs.readFileSync(path.join(state, 'events.json')));
    return events.filter(e => e.event === 'response_prepared' && e.kind === kind).length;
  }).toBeGreaterThan(after);
}

try {
  await page.goto(receipt.url);
  await login();
  await checkDiscardOnCaseSwitch();
  await openCase(101); await freeze(text, saveWithForeignReceipt); await review();
  const beforeSign = await rejectWrongPassword('sign');
  await sign(); await readback();
  assert.equal(caseWritePaths.length, beforeSign + 1);
  assert.match(caseWritePaths.at(-1), /\/cases\/101\/treatment\/revisions\/[^/]+\/signatures$/);
  assert((await page.locator('[aria-label="独立回读签署"]').textContent()).includes(text));
  checks.push('save-freeze-review-sign-independent-readback', 'exact-utf8-text', 'sign-wrong-password-retry-readback');
  await logout(); await login('frontdesk'); await openCase(101);
  await expect(page.locator('[aria-label="治疗签署"]')).toHaveCount(0);
  assert(!(await page.locator('[aria-label="病例详情"]').textContent()).includes(text));
  await logout(); await login('admin');
  await expect(page.getByText('当前账号尚无病例读取权限，请联系院内权限管理员。', { exact: true })).toBeVisible();
  await logout(); await login('remote'); await openCase(102);
  await expect(page.getByRole('button', { name: '保存治疗草稿', exact: true })).toBeDisabled();
  await expect(page.getByRole('row').filter({ has: page.getByRole('cell', { name: '#101', exact: true }) })).toHaveCount(0);
  checks.push('frontdesk-projection-admin-separation-cross-clinic-readonly');
  await logout(); await login('assistant'); await openCase(102); await freeze();
  await page.getByLabel('已核对冻结版本', { exact: true }).check(); await page.getByLabel('操作原因', { exact: true }).fill('助理不能审核');
  await expect(page.getByRole('button', { name: '审核通过', exact: true })).toBeDisabled();
  checks.push('assistant-draft-without-signing');
  await logout(); await login(); await openCase(108); await freeze();
  await page.getByLabel('治疗评估', { exact: true }).fill(text + '\n新草稿');
  await page.getByRole('button', { name: '保存治疗草稿', exact: true }).click();
  await expect(page.getByText('草稿已修改，此冻结版本不能继续审核或签署。', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '冻结版本供核对', exact: true }).click();
  await expect(page.getByLabel('已核对冻结版本', { exact: true })).toBeEnabled();
  control('source-change');
  await page.getByLabel('已核对冻结版本', { exact: true }).check(); await page.getByLabel('操作原因', { exact: true }).fill('旧来源失效');
  await page.getByRole('button', { name: '审核通过', exact: true }).click();
  await expect(page.getByText('病例、诊断资料或签署规则已变化。请重新读取并冻结新版本。', { exact: true })).toBeVisible();
  await page.getByLabel('治疗评估', { exact: true }).fill(text + '\n未保存');
  control('expire'); await page.getByRole('button', { name: '重新读取治疗记录', exact: true }).click();
  await expect(page.getByRole('heading', { name: '未保存原文 · 只读保留', exact: true })).toBeVisible();
  assert((await page.locator('[aria-label="治疗签署"]').textContent()).includes(text + '\n未保存'));
  checks.push('stale-draft-and-diagnostic-source', '401-copyable-original');
  await logout(); await login(); await openCase(109); await freeze(); await review();
  control('lose-sign-response'); await sign(); await prepared('lose-sign-response');
  await page.getByRole('button', { name: '停止等待（保留原请求）', exact: true }).click();
  await logout(); await login(); await openCase(109);
  await page.getByRole('button', { name: '查询原请求', exact: true }).click(); await readback();
  assert.equal(caseWritePaths.filter(p => p.includes('/cases/109/') && p.endsWith('/signatures')).length, 1);
  control('release'); checks.push('lost-response-same-account-query-no-duplicate');
  control('policy-two'); await openCase(107); await freeze(); await review(); await sign();
  await expect(page.getByText('本院要求由另一位已核验医生签署。', { exact: true })).toBeVisible();
  await logout(); await login('doctor-b'); await openCase(107); await sign(); await readback();
  checks.push('two-person-rule');
  control('policy-self'); await openCase(101);
  await page.getByLabel('操作原因', { exact: true }).fill('合成修订');
  await page.getByRole('button', { name: '创建修订草稿', exact: true }).click();
  await freeze(text + '\n修订'); await review(); await sign(); await readback();
  await expect(page.getByText(/已由新签署替代/)).toBeVisible();
  await page.getByLabel('操作原因', { exact: true }).fill('合成作废');
  const beforeRevoke = await rejectWrongPassword('revoke');
  await page.getByLabel('已核对待作废签署', { exact: true }).check();
  await page.getByLabel('签署认证密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '再次认证并作废签署', exact: true }).click();
  await expect(page.getByText(/ · 已作废 · /)).toBeVisible();
  await expect(page.locator('[aria-label="独立回读签署"]')).toContainText('revoked');
  assert.equal(caseWritePaths.length, beforeRevoke + 1);
  assert.match(caseWritePaths.at(-1), /\/cases\/101\/treatment\/signatures\/[^/]+\/revocations$/);
  await freeze(text + '\n作废后新签署'); await review(); await sign(); await readback();
  checks.push('amend-revoke-resign-history', 'revoke-wrong-password-retry-readback');
  await logout(); await login(); await openCase(101);
  for (const kind of ['late-200', 'late-401']) {
    control(kind);
    await page.getByRole('row').filter({ has: page.getByRole('cell', { name: '#101', exact: true }) }).getByRole('button', { name: '查看', exact: true }).click();
    await prepared(kind);
    await logout(); await login('doctor-b'); await openCase(103);
    control('release');
    await expect(page.locator('[aria-label="病例详情"] h2').first()).toContainText('#103');
    await expect(page.getByRole('button', { name: '退出登录', exact: true })).toBeVisible();
    checks.push(kind + '-account-case-isolation');
    await logout(); await login(); await openCase(101);
  }
  assert.deepEqual(errors, []);
  result.status = 'PASS';
} catch (error) {
  result.status = 'FAILED'; result.error = String(error); result.page_errors = errors;
  throw error;
} finally {
  fs.writeFileSync(path.join(state, 'chromium-receipt.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
  await browser.close();
}
