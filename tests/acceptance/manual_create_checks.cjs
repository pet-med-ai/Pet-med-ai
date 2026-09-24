// Real React/Chromium, authenticated FastAPI and disposable native PostgreSQL.
// Faults drop actual responses or block reads; they never fabricate a success.
const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const UI = 'http://127.0.0.1:5173', API = 'http://127.0.0.1:18026';
const out = process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE === 'PR26');
let browser, context, page, auth;
const passed = [], failures = [], external = [], pageErrors = [], writes = [];
const review = () => page.getByRole('region', { name: '手工新建病例核对', exact: true });
const field = label => page.locator('label').filter({ has: page.getByText(label, { exact: true }) }).locator('input, textarea, select');
const button = name => review().getByRole('button', { name, exact: true });
const createWrites = () => writes.filter(w => w.route === '/api/cases');
const expectedFields = ['patient_name','species','sex','age_info','breed','weight','coat_color','owner_name','owner_phone','chief_complaint','history','exam_findings','analysis','treatment','prognosis'];
const nullPayload = Object.fromEntries(expectedFields.map(key => [key, key === 'species' ? 'dog' : null]));
async function record(name) {
  passed.push(name); console.log('PASS:', name);
  await page.screenshot({ path: path.join(out, `manual-create-${passed.length}-${name}.png`), fullPage: true });
}
async function read(id) {
  const result = await context.request.get(API + '/api/cases/' + id, { headers: auth });
  assert.equal(result.status(), 200, await result.text()); return result.json();
}
async function verifyPayload(expected) {
  await expect(review()).toContainText('本次核对的十五项内容一致');
  const receipt = await page.evaluate(() => JSON.parse(sessionStorage.getItem('pmai.manual-create-attempt.v1')));
  assert.deepEqual(receipt.payload, expected);
  const actual = await read(receipt.caseId);
  for (const key of expectedFields) assert.equal(actual[key], expected[key], key);
  await expect(review().getByRole('region', { name: '手工新建实际回读', exact: true })).toBeVisible();
  return actual;
}
async function prepare() {
  await button('核对新建内容').click();
  await review().getByLabel('已核对本次新建内容', { exact: true }).check();
}
async function fillRequired(name) {
  await field('病例名 / 宠物名（必填）').fill(name);
  await field('主诉（必填）').fill('仅用于隔离软件验收，非临床病例');
}
async function main() {
  browser = await chromium.launch({ headless: true });
  console.log('Chromium manual-create acceptance:', browser.version());
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block' });
  await context.route('**/*', route => {
    const origin = new URL(route.request().url()).origin;
    if ([UI, API].includes(origin)) return route.continue();
    external.push(origin); return route.abort();
  });
  page = await context.newPage();
  page.on('dialog', dialog => dialog.accept()); // Deliberately confirm synthetic reload warnings.
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', request => {
    const route = new URL(request.url()).pathname;
    if (request.method() === 'POST' && route.startsWith('/api/')) writes.push({ route, data: request.postDataJSON() });
  });
  await page.goto(UI);
  await page.getByPlaceholder('邮箱', { exact: true }).fill('browser-owner@example.com');
  await page.getByPlaceholder('密码', { exact: true }).fill('Synthetic-PR26-only-20260916');
  const login = page.waitForResponse(r => r.request().method() === 'POST' && new URL(r.url()).pathname === '/auth/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  assert.equal((await login).status(), 200);
  await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
  auth = { Authorization: 'Bearer ' + await page.evaluate(() => localStorage.getItem('token')) };

  await page.goto(UI + '/cases/new/edit');
  await fillRequired('将丢弃的合成输入');
  await page.reload();
  await page.getByRole('button', { name: '丢弃新建输入', exact: true }).click();
  await expect(field('病例名 / 宠物名（必填）')).toHaveValue('');
  assert.equal(createWrites().length, 0);
  assert.equal(await page.evaluate(() => sessionStorage.getItem('pmai.manual-case-draft.v1')), null);
  await record('unsent_draft_discard_does_not_create_a_case');
  const first = { ...nullPayload, patient_name: '隔离手工新建犬🐾', species: 'cat', sex: 'F', age_info: '2y', breed: '合成品种', weight: '5.2kg', coat_color: '白', owner_name: '虚构主人', owner_phone: 'synthetic-only', chief_complaint: '  手工主诉\n ', history: '  原始病史🐾\n尾部空格。  \n', exam_findings: '未实施真实检查', analysis: '手工分析 <script>literal</script>', treatment: '  手工处理\n ', prognosis: '手工随访' };
  const labels = {
    patient_name: '病例名 / 宠物名（必填）', species: '物种', sex: '性别', age_info: '年龄信息', breed: '品种 / 宠物信息', weight: '体重', coat_color: '毛色', owner_name: '主人姓名', owner_phone: '主人电话', chief_complaint: '主诉（必填）', history: '既往史 / 动态问诊追问记录', exam_findings: '体检 / 化验 / 来源信息', analysis: 'AI 分析', treatment: '治疗建议', prognosis: '风险提示 / 后续随访'
  };
  for (const [key, label] of Object.entries(labels)) {
    if (key === 'species') await field(label).selectOption(first[key]);
    else await field(label).fill(first[key]);
  }
  await page.reload();
  await expect(field(labels.patient_name)).toHaveValue('');
  await expect(button('核对新建内容')).toBeDisabled();
  await page.getByRole('button', { name: '恢复新建输入', exact: true }).click();
  for (const [key, label] of Object.entries(labels)) await expect(field(label)).toHaveValue(first[key]);
  assert.equal(createWrites().length, 0);
  await record('fifteen_unsent_fields_survive_refresh_and_explicit_restore');
  await prepare();
  assert.equal(createWrites().length, 0);
  await field(labels.treatment).fill('  核对后修改的手工处理\n ');
  first.treatment = '  核对后修改的手工处理\n ';
  await expect(review().getByLabel('已核对本次新建内容', { exact: true })).not.toBeChecked();
  await expect(button('确认并创建病例')).toBeDisabled();
  await expect(review()).toContainText('输入已修改，原确认失效');
  assert.equal(createWrites().length, 0);
  await record('standalone_preview_has_no_write_and_input_change_invalidates_confirmation');

  await page.reload();
  await expect(button('确认并创建病例')).toHaveCount(0);
  await page.getByRole('button', { name: '恢复新建输入', exact: true }).click();
  await expect(field(labels.treatment)).toHaveValue(first.treatment);
  await button('核对新建内容').click();
  await expect(review().getByLabel('已核对本次新建内容', { exact: true })).not.toBeChecked();
  assert.equal(createWrites().length, 0);
  await record('previewed_input_refresh_requires_a_new_confirmation');
  await review().getByLabel('已核对本次新建内容', { exact: true }).check();
  // Dispatch two actual DOM clicks in one task to exercise the synchronous guard.
  await button('确认并创建病例').evaluate(element => { element.click(); element.click(); });
  const saved = await verifyPayload(first);
  assert.equal(createWrites().length, 1);
  assert.deepEqual(createWrites()[0].data, first);
  await record('double_click_creates_once_and_fifteen_fields_read_back_exactly');

  await page.reload();
  await expect(button('确认并创建病例')).toHaveCount(0);
  await button('核对保存结果').click();
  await verifyPayload(first); assert.equal(createWrites().length, 1);
  await record('reload_recovers_receipt_and_checks_get_only');

  await review().getByRole('link', { name: '查看已保存病例 #' + saved.id, exact: true }).click();
  await page.reload();
  const history = page.getByRole('region', { name: '完整病史原文', exact: true }).locator('.text-body');
  await expect(history).toBeVisible(); assert.equal(await history.textContent(), first.history);
  assert.equal((await read(saved.id)).treatment, first.treatment);
  await record('saved_case_detail_refresh_retains_manual_clinical_text');

  await page.goto(UI + '/cases/new/edit');
  await button('核对保存结果').click(); await verifyPayload(first);
  await button('新建另一个病例').click();
  await expect(field(labels.patient_name)).toHaveValue('');
  await page.getByRole('button', { name: '返回首页', exact: true }).click();
  const homeName = '首页转入手工核对合成犬';
  await field('病例名 / 宠物名').fill(homeName);
  await field('主诉（必填）').fill('首页合成主诉');
  await field('既往史').fill('  首页病史原文🐾\n ');
  await page.getByRole('button', { name: '手工新建（核对后保存）', exact: true }).click();
  await expect(field(labels.patient_name)).toHaveValue(homeName);
  await expect(field(labels.history)).toHaveValue('  首页病史原文🐾\n ');
  assert.equal(createWrites().length, 1);
  await prepare();
  await button('确认并创建病例').click();
  await verifyPayload({ ...nullPayload, patient_name: homeName, chief_complaint: '首页合成主诉', history: '  首页病史原文🐾\n ' });
  assert.equal(createWrites().length, 2);
  assert(writes.every(w => w.route === '/api/cases'), 'Manual path created a session or audit');
  await record('homepage_handoff_preserves_input_and_requires_same_review');

  await button('新建另一个病例').click();
  await fillRequired('回读暂时失败合成犬'); await prepare();
  const getRoute = url => url.origin === API && /^\/api\/cases\/\d+$/.test(url.pathname);
  await page.route(getRoute, handler => handler.request().method() === 'GET' ? handler.abort('failed') : handler.continue());
  await button('确认并创建病例').click();
  await expect(review()).toContainText('暂时无法回读');
  assert.equal(createWrites().length, 3);
  await page.reload();
  await expect(button('确认并创建病例')).toHaveCount(0);
  await page.unroute(getRoute);
  await button('核对保存结果').click();
  await verifyPayload({ ...nullPayload, patient_name: '回读暂时失败合成犬', chief_complaint: '仅用于隔离软件验收，非临床病例' });
  assert.equal(createWrites().length, 3);
  assert.equal(await page.evaluate(() => sessionStorage.getItem('pmai.manual-case-draft.v1')), null);
  await record('failed_readback_and_reload_retry_only_get');

  await button('新建另一个病例').click();
  await fillRequired('创建响应丢失合成犬'); await prepare();
  let committedId;
  await page.route(API + '/api/cases', async handler => {
    if (handler.request().method() !== 'POST') return handler.continue();
    const real = await handler.fetch(); assert.equal(real.status(), 201);
    committedId = (await real.json()).id; await handler.abort('failed');
  });
  await button('确认并创建病例').click();
  await expect(review()).toContainText('创建结果待核实');
  assert.equal((await read(committedId)).patient_name, '创建响应丢失合成犬');
  assert.equal(createWrites().length, 4);
  await page.reload();
  await expect(review()).toContainText('发现上次新建记录');
  await expect(button('核对新建内容')).toHaveCount(0);
  await expect(button('确认并创建病例')).toHaveCount(0);
  assert.equal(createWrites().length, 4);
  const inputDraft = await page.evaluate(() => sessionStorage.getItem('pmai.manual-case-draft.v1'));
  for (const kind of ['deleted', 'expired']) {
    await page.evaluate(({ kind, inputDraft }) => {
      if (kind === 'deleted') sessionStorage.removeItem('pmai.manual-case-draft.v1');
      else { const draft = JSON.parse(inputDraft); draft.updatedAt = Date.now() - 8 * 60 * 60 * 1000; sessionStorage.setItem('pmai.manual-case-draft.v1', JSON.stringify(draft)); }
    }, { kind, inputDraft });
    await page.reload();
    await expect(button('核对新建内容')).toHaveCount(0);
    await expect(button('确认并创建病例')).toHaveCount(0);
    assert(await page.evaluate(() => sessionStorage.getItem('pmai.manual-create-attempt.v1')));
    assert.equal(createWrites().length, 4);
  }
  await record('draft_deletion_and_expiry_do_not_unlock_uncertain_create');
  assert.deepEqual(external, []); assert.deepEqual(pageErrors, []);
  assert(writes.every(w => w.route === '/api/cases'));
  await record('lost_real_post_response_blocks_recreation_after_reload');
}
main().catch(async error => {
  process.exitCode = 1; failures.push(String(error)); console.error(error);
  if (page) {
    await page.screenshot({ path: path.join(out, 'manual-create-failure.png'), fullPage: true }).catch(() => {});
    fs.writeFileSync(path.join(out, 'manual-create-failure-dom.txt'), await page.locator('body').innerText().catch(() => ''));
  }
}).finally(async () => {
  fs.writeFileSync(path.join(out, 'manual-create-checks.json'), JSON.stringify({ passed, failures, external, pageErrors }, null, 2));
  if (browser) await browser.close();
});
