// Real Chromium + unchanged React + FastAPI + disposable PostgreSQL.
// Route interception only drops/delays a real response in the named fault cases.
const { chromium, expect } = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const UI = 'http://127.0.0.1:5173';
const API = 'http://127.0.0.1:18026';
const out = process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE === 'PR26');
fs.mkdirSync(out, { recursive: true });
const passed = [], failures = [], requests = [], pageErrors = [], external = [];
let browser, context, page, auth;
const fields = ['patient_name','species','sex','age_info','breed','weight','coat_color','owner_name','owner_phone','chief_complaint','history','exam_findings','analysis','treatment','prognosis'];
const saveRegion = () => page.getByRole('region', { name: '首次保存病例核对', exact: true });
const updateRegion = () => page.getByRole('region', { name: '更新已绑定病例核对', exact: true });
const responseFor = (suffix, method='POST') => page.waitForResponse(r => new URL(r.url()).pathname.endsWith(suffix) && r.request().method() === method);
async function record(name) {
  passed.push(name);
  console.log('PASS:', name);
  await page.screenshot({ path: path.join(out, `${passed.length}-${name}.png`), fullPage: true });
}
async function api(method, route, data) {
  assert(route.startsWith('/api/'));
  const r = await context.request.fetch(API+route, { method, headers: auth, data });
  assert.equal(r.status(), 200, await r.text());
  return r.json();
}
async function setup() {
  context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block' });
  await context.route('**/*', route => {
    const origin = new URL(route.request().url()).origin;
    if ([UI, API].includes(origin)) return route.continue();
    external.push(origin); return route.abort('blockedbyclient');
  });
  page = await context.newPage();
  page.on('dialog', d => d.accept());
  page.on('pageerror', e => pageErrors.push(e.message));
  page.on('response', r => requests.push({ method: r.request().method(), path: new URL(r.url()).pathname, status: r.status() }));
  await page.goto(UI);
  await page.getByPlaceholder('邮箱', { exact: true }).fill('browser-owner@example.com');
  await page.getByPlaceholder('密码', { exact: true }).fill('Synthetic-PR26-only-20260916');
  const login = responseFor('/auth/login');
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const lr = await login; assert.equal(lr.status(), 200);
  auth = { Authorization: 'Bearer '+(await lr.json()).access_token };
  await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
}
async function reviewAI() {
  const signature = page.getByPlaceholder('如 HS-0001 / Dr.Zhao', { exact: true });
  await signature.fill('Synthetic-E2E');
  const audit = responseFor('/api/audit-log');
  await page.getByRole('button', { name: '确认覆核并写入审计', exact: true }).click();
  assert.equal((await audit).status(), 201);
  await expect(page.getByRole('button', { name: '审计已写入', exact: true })).toBeVisible();
}
async function startCase(name) {
  await page.getByPlaceholder('如：乐乐 / Lucky', { exact: true }).fill(name);
  for (const [label,value] of [['性别','M'],['年龄信息','4岁'],['品种 / 宠物信息','合成品种'],['体重','5kg'],['毛色','白'],['主人姓名','合成主人'],['主人电话','synthetic-only']]) {
    await page.getByLabel(label, { exact: true }).fill(value);
  }
  await page.getByLabel('主诉（必填）', { exact: true }).fill('合成犬呕吐两次，精神正常');
  await page.getByLabel('既往史', { exact: true }).fill('医生原始病史🐾\n既往用药需要保留。');
  await page.getByLabel('体检/化验摘要', { exact: true }).fill('合成体检记录');
  const create = responseFor('/api/ai/consult/session');
  await page.getByRole('button', { name: '提交分析（不入库）', exact: true }).click();
  const r = await create; assert.equal(r.status(), 200); const s = await r.json();
  await expect(saveRegion().getByRole('button', { name: '核对保存内容', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: '请在下方核对后保存', exact: true })).toBeDisabled();
  return s.session_id;
}
async function followup(text) {
  await page.getByPlaceholder('请填写对当前追问的回答', { exact: true }).fill(text);
  const answer = responseFor('/answer');
  await page.getByRole('button', { name: '提交追问回答', exact: true }).click();
  assert.equal((await answer).status(), 200);
  await expect(page.getByPlaceholder('请填写对当前追问的回答', { exact: true })).toHaveValue('');
}
async function preview() {
  const next = responseFor('/preview-case');
  await saveRegion().getByRole('button', { name: /^(核对保存内容|重新预览保存内容)$/ }).click();
  const r = await next; assert.equal(r.status(), 200);
  await expect(saveRegion().getByLabel('已核对本次保存内容', { exact: true })).toBeVisible();
  return r.json();
}
async function confirm() {
  await saveRegion().getByLabel('已核对本次保存内容', { exact: true }).check();
  await saveRegion().getByRole('button', { name: '确认并保存病例', exact: true }).click();
}
async function checkSaved(sid, snapshot) {
  await expect(page.getByRole('status').filter({ hasText: /已回读病例 #\d+，基本信息与本次核对内容一致/ })).toBeVisible();
  const s = await api('GET', '/api/ai/consult/session/'+sid);
  const c = await api('GET', '/api/cases/'+s.case_id);
  for (const field of fields) assert.equal(c[field], snapshot[field], field);
  return c;
}
async function main() {
  browser = await chromium.launch({ headless: true });
  console.log('Chromium:', browser.version());
  await setup();
  let sid = await startCase('浏览器合成犬 A');
  await followup('合成回答：持续两天，没有血液');
  await reviewAI();
  const before = (await api('GET','/api/cases')).total;
  let p = await preview();
  assert.equal((await api('GET','/api/cases')).total, before);
  assert.equal((await api('GET','/api/ai/consult/session/'+sid)).case_id, null);
  await expect(saveRegion().getByRole('button',{ name:'确认并保存病例',exact:true })).toBeDisabled();
  await saveRegion().getByLabel('已核对本次保存内容',{exact:true}).check();
  const history = '医生修改后病史🐾\n原文尾部空白保留。  \n';
  await page.getByLabel('既往史',{exact:true}).fill(history);
  await expect(saveRegion().getByText('内容已修改，原确认失效，请重新核对。',{exact:true})).toBeVisible();
  await expect(saveRegion().getByRole('button',{ name:'确认并保存病例',exact:true })).toHaveCount(0);
  p = await preview(); assert(p.history.startsWith(history));
  await record('preview_edit_invalidates_confirmation');
  await confirm();
  const saved = await checkSaved(sid,p);
  assert.equal((await api('GET','/api/cases')).total,before+1);
  await record('first_save_fifteen_fields_real_readback');
  await page.getByPlaceholder('请填写对当前追问的回答',{exact:true}).fill('合成后续补问回答');
  await expect(updateRegion().getByRole('button',{name:'核对更新内容',exact:true})).toBeDisabled();
  await followup('合成后续补问回答：饮水情况已核对');
  assert.equal((await api('GET','/api/cases/'+saved.id)).history,saved.history);
  await reviewAI();
  const next = responseFor('/preview-update-case');
  await updateRegion().getByRole('button',{name:'核对更新内容',exact:true}).click();
  const up = await (await next).json();
  assert(up.proposed.history.startsWith(saved.history));
  await expect(updateRegion().getByRole('button',{name:'确认并更新病例',exact:true})).toBeDisabled();
  await updateRegion().getByLabel('已核对本次更新内容',{exact:true}).check();
  const updated = responseFor('/update-case');
  await updateRegion().getByRole('button',{name:'确认并更新病例',exact:true}).click();
  assert.equal((await updated).status(),200);
  await expect(updateRegion().getByText(new RegExp('已读取病例 #'+saved.id))).toBeVisible();
  const actual = await api('GET','/api/cases/'+saved.id);
  for(const k of Object.keys(up.proposed)) assert.equal(actual[k],up.proposed[k],k);
  await record('bound_update_review_original_history_retained');
  await updateRegion().getByRole('link',{name:'查看已保存病例 #'+saved.id,exact:true}).click();
  await expect(page.getByRole('heading',{name:'病例详情 #'+saved.id,exact:true})).toBeVisible();
  // Keep this assertion: persistence alone is insufficient if the doctor cannot
  // see the original history in CaseDetail. Capture failure and run other cases.
  try {
    await expect(page.getByText('医生修改后病史🐾',{exact:false}).first()).toBeVisible();
    await record('case_detail_displays_original_doctor_history');
  } catch(error) {
    failures.push({name:'case_detail_displays_original_doctor_history',error:String(error)});
    await page.screenshot({path:path.join(out,'case-detail-missing-original.png'),fullPage:true});
    fs.writeFileSync(path.join(out,'case-detail-missing-original.txt'),await page.locator('body').innerText());
    console.error('FAIL: case_detail_displays_original_doctor_history');
  }
  await page.reload();
  await expect(page.getByRole('heading',{name:'病例详情 #'+saved.id,exact:true})).toBeVisible();
  assert.deepEqual(await api('GET','/api/cases/'+saved.id),actual);
  await record('case_detail_reopen_and_refresh_persisted');
  await context.close();

  await setup(); sid = await startCase('浏览器合成犬 B 响应丢失'); await reviewAI(); p = await preview();
  const baseline = (await api('GET','/api/cases')).total;
  let posts=0;
  await page.route('**/save-case', async route => {
    posts++; const response = await route.fetch(); assert.equal(response.status(),200);
    await route.abort('failed'); // Server has committed; only its response is lost.
  });
  await confirm(); await checkSaved(sid,p);
  assert.equal(posts,1); assert.equal((await api('GET','/api/cases')).total,baseline+1);
  await record('lost_save_response_reads_binding_without_second_post');
  await context.close();

  await setup(); sid = await startCase('浏览器合成犬 C 回读失败'); await reviewAI(); p = await preview();
  let rejectRead=true, savePosts=0;
  page.on('request', r => { if(r.method()==='POST' && new URL(r.url()).pathname.endsWith('/save-case')) savePosts++; });
  await page.route('**/api/ai/consult/session/'+sid, route => rejectRead && route.request().method()==='GET' ? route.abort('failed') : route.continue());
  await confirm();
  await expect(saveRegion().getByText('暂时无法回读，保存结果待核对。已保留输入和核对内容，请先核对保存结果。',{exact:true})).toBeVisible();
  await expect(page.getByLabel('既往史',{exact:true})).toHaveValue('医生原始病史🐾\n既往用药需要保留。');
  rejectRead=false;
  await saveRegion().getByRole('button',{name:'核对保存结果',exact:true}).click();
  await checkSaved(sid,p); assert.equal(savePosts,1);
  await record('readback_failure_preserves_inputs_and_retries_get_only');
  assert.deepEqual(external,[]); assert.deepEqual(pageErrors,[]);
  await record('no_external_requests_or_uncaught_browser_errors');
}
main().then(()=>{ process.exitCode=failures.length ? 1 : 0; }).catch(async error=>{
  process.exitCode=1; console.error(error);
  failures.push({name:'browser_scenario',error:String(error)});
  if(page) { await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{}); fs.writeFileSync(path.join(out,'failure-dom.txt'),await page.locator('body').innerText().catch(()=>'')); }
}).finally(async()=>{
  fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify({status:process.exitCode===0?'PASS':'FAIL',passed,failures,requests,pageErrors,external},null,2));
  if(browser) await browser.close();
});
