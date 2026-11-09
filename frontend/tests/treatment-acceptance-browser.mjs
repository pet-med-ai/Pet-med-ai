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
const errors = [], checks = [], requests = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('request', r => { if (r.method() === 'POST' && r.url().endsWith('/signatures')) requests.push(r.url()); });
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
async function freeze(content=text) {
  await page.getByLabel('治疗诊断', { exact: true }).fill('合成诊断，仅软件验收');
  await page.getByLabel('治疗评估', { exact: true }).fill(content);
  await page.getByLabel('治疗措施', { exact: true }).fill(content);
  await page.getByRole('button', { name: '保存治疗草稿', exact: true }).click();
  await page.getByRole('button', { name: '冻结版本供核对', exact: true }).click();
  await expect(page.getByLabel('已核对冻结版本', { exact: true })).toBeEnabled();
}
async function review() {
  await page.getByLabel('已核对冻结版本', { exact: true }).check();
  await page.getByLabel('操作原因', { exact: true }).fill('核对合成原文');
  await page.getByRole('button', { name: '审核通过', exact: true }).click();
  await expect(page.locator('[aria-label="冻结版本"]')).toContainText('审核通过');
}
async function sign() {
  await page.getByLabel('已核对冻结版本', { exact: true }).check();
  await page.getByLabel('签署认证密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '再次认证并确认签署', exact: true }).click();
}
async function readback() {
  await expect(page.locator('[aria-label="独立回读签署"]')).toBeVisible();
}
async function prepared(kind, after=0) {
  await expect.poll(() => {
    const events = JSON.parse(fs.readFileSync(path.join(state, 'events.json')));
    return events.filter(e => e.event === 'response_prepared' && e.kind === kind).length;
  }).toBeGreaterThan(after);
}

try {
  await page.goto(receipt.url);
  await login(); await openCase(101); await freeze(); await review(); await sign(); await readback();
  assert((await page.locator('[aria-label="独立回读签署"]').textContent()).includes(text));
  checks.push('save-freeze-review-sign-independent-readback', 'exact-utf8-text');
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
  assert.equal(requests.filter(p => p.includes('/cases/109/')).length, 1);
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
  await page.getByLabel('已核对待作废签署', { exact: true }).check();
  await page.getByLabel('签署认证密码', { exact: true }).fill(fixture.password);
  await page.getByRole('button', { name: '再次认证并作废签署', exact: true }).click();
  await expect(page.getByText(/ · 已作废 · /)).toBeVisible();
  await freeze(text + '\n作废后新签署'); await review(); await sign(); await readback();
  checks.push('amend-revoke-resign-history');
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
  await browser.close();
}
