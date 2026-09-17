// Real Chromium / React / FastAPI / native PostgreSQL, synthetic rows only.
// All HTTP responses are real. Deletion uses the fixture owner's normal API.
const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const UI = 'http://127.0.0.1:5173', API = 'http://127.0.0.1:18026';
const out = process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE === 'PR26');
const passed = [], failures = [], external = [], pageErrors = [];
let browser, context, page, auth;
const review = () => page.getByRole('region', { name: '更新已绑定病例核对', exact: true });
const note = () => page.getByPlaceholder('例如：复诊补充的症状、用药经过、主人新提供的病史', { exact: true });
const step = n => page.getByRole('navigation', { name: '问诊工作台步骤', exact: true })
  .getByRole('button', { name: ['问诊整理', '保存前核对', '病例回看'][n - 1], exact: true });
const next = suffix => page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname.endsWith(suffix));

async function api(method, route, data, status = 200) {
  assert(route.startsWith('/api/'));
  const response = await context.request.fetch(API + route, { method, headers: auth, data });
  assert.equal(response.status(), status, await response.text());
  return status === 204 ? null : response.json();
}

async function scenario(mode, deleteAfterPreview) {
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block' });
  await context.route('**/*', route => {
    const origin = new URL(route.request().url()).origin;
    if ([UI, API].includes(origin)) return route.continue();
    external.push(origin); return route.abort();
  });
  page = await context.newPage();
  page.on('dialog', dialog => dialog.accept());
  page.on('pageerror', error => pageErrors.push(error.message));
  const writes = [];
  page.on('request', request => {
    if (request.method() === 'POST' && new URL(request.url()).pathname.endsWith('/update-case')) writes.push(request.postDataJSON());
  });
  await page.goto(UI);
  await page.getByPlaceholder('邮箱', { exact: true }).fill('browser-owner@example.com');
  await page.getByPlaceholder('密码', { exact: true }).fill('Synthetic-PR26-only-20260916');
  let response = next('/auth/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  assert.equal((await response).status(), 200);
  await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
  auth = { Authorization: 'Bearer ' + await page.evaluate(() => localStorage.getItem('token')) };
  const session = await api('POST', '/api/ai/consult/session', { text: '合成犬呕吐两次，精神正常', species: 'dog' });
  const url = '/api/ai/consult/session/' + session.session_id;
  const body = { patient_name: '删除边界合成犬', history: '  原病史🐾\r\n不得改写。  \n' };
  const first = await api('POST', url + '/preview-case', body);
  const cid = (await api('POST', url + '/save-case', { ...body, expected_preview_token: first.preview_token })).case_id;
  // Each scenario has its own browser context and newly created synthetic case.
  await page.goto(UI + '/?restore_session_id=' + session.session_id);
  const chief = page.locator('label').filter({ has: page.getByText('主诉（必填）', { exact: true }) }).locator('textarea');
  await expect(chief).toHaveValue(session.text);
  const text = '未保存的删除边界补记🐾 ' + mode;
  await note().fill(text);
  await page.getByPlaceholder('如 HS-0001 / Dr.Zhao', { exact: true }).fill('Synthetic-Deleted-Case');
  response = next('/api/audit-log');
  await page.getByRole('button', { name: '确认覆核并写入审计', exact: true }).click();
  assert.equal((await response).status(), 201);
  await expect(page.getByRole('button', { name: '审计已写入', exact: true })).toBeVisible();
  await step(2).click();
  await review().getByLabel('本次更新范围', { exact: true }).selectOption(mode);
  if (!deleteAfterPreview) await api('DELETE', '/api/cases/' + cid, undefined, 204);
  response = next('/preview-update-case');
  await review().getByRole('button', { name: '核对更新内容', exact: true }).click();
  const previewResponse = await response;
  if (deleteAfterPreview) {
    assert.equal(previewResponse.status(), 200, await previewResponse.text());
    assert.equal((await previewResponse.json()).update_mode, mode);
    await review().getByLabel('已核对本次更新内容', { exact: true }).check();
    await api('DELETE', '/api/cases/' + cid, undefined, 204);
    response = next('/update-case');
    await review().getByRole('button', { name: '确认并更新病例', exact: true }).click();
    const rejected = await response;
    assert.equal(rejected.status(), 404, await rejected.text());
    await expect(review()).toContainText('更新未被接受');
  } else {
    assert.equal(previewResponse.status(), 404, await previewResponse.text());
    await expect(review()).toContainText('无法获取更新预览');
  }
  await expect(review().getByRole('button', { name: '确认并更新病例', exact: true })).toHaveCount(0);
  await expect(step(3)).toBeDisabled();
  await step(1).click();
  await expect(note()).toHaveValue(text);
  await api('GET', '/api/cases/' + cid, undefined, 404);
  assert.equal((await api('GET', url)).case_id, cid);
  assert.equal(writes.length, deleteAfterPreview ? 1 : 0);
  assert.deepEqual(external, []); assert.deepEqual(pageErrors, []);
  const name = (deleteAfterPreview ? 'delete_after_preview_' : 'deleted_before_preview_') + mode;
  await page.screenshot({ path: path.join(out, 'deleted-' + name + '.png'), fullPage: true });
  passed.push(name); console.log('PASS:', name);
  await context.close(); context = null; page = null;
}

async function main() {
  browser = await chromium.launch({ headless: true });
  console.log('Chromium deleted-case acceptance:', browser.version());
  for (const mode of ['history_only', 'consult_sync']) {
    await scenario(mode, false);
    await scenario(mode, true);
  }
}
main().catch(async error => {
  process.exitCode = 1; failures.push(String(error)); console.error(error);
  if (page) {
    await page.screenshot({ path: path.join(out, 'deleted-failure.png'), fullPage: true }).catch(() => {});
    fs.writeFileSync(path.join(out, 'deleted-failure-dom.txt'), await page.locator('body').innerText().catch(() => ''));
  }
}).finally(async () => {
  fs.writeFileSync(path.join(out, 'deleted-case-checks.json'), JSON.stringify({ passed, failures, external, pageErrors }, null, 2));
  if (browser) await browser.close();
});
