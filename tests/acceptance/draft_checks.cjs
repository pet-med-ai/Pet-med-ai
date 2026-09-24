// Real Chromium/React/FastAPI/PostgreSQL. Only named fault checks block a GET
// or sessionStorage write; successful API responses are never fabricated.
const {chromium, expect} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const UI='http://127.0.0.1:5173', API='http://127.0.0.1:18026', KEY='pmai.consult-draft.v1';
const out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const passed=[], failures=[], pageErrors=[], external=[], writes=[];
let browser, context, page, auth;
const draft=()=>page.getByRole('region',{name:'本标签页草稿',exact:true});
const history=()=>page.locator('label').filter({has:page.getByText('既往史',{exact:true})}).locator('textarea');
const followup=()=>page.getByPlaceholder('请填写对当前追问的回答',{exact:true});
const structured=()=>page.getByPlaceholder('填写本项结构化病史；提交追问时会随本轮上下文发给 AI',{exact:true}).first();
const save=()=>page.getByRole('region',{name:'首次保存病例核对',exact:true});
const step=n=>page.getByRole('navigation',{name:'问诊工作台步骤',exact:true}).getByRole('button',{name:['问诊整理','保存前核对','病例回看'][n-1],exact:true});
const responseFor=suffix=>page.waitForResponse(r=>r.request().method()==='POST' && new URL(r.url()).pathname.endsWith(suffix));
async function record(name){passed.push(name);console.log('PASS:',name);await page.screenshot({path:path.join(out,`draft-${passed.length}-${name}.png`),fullPage:true});}
async function request(method, route, data){assert(route.startsWith('/api/'));const r=await context.request.fetch(API+route,{method,headers:auth,data});assert.equal(r.status(),200,await r.text());return r.json();}
async function login(owner='browser-owner'){
  await page.getByPlaceholder('邮箱',{exact:true}).fill(owner+'@example.com');
  await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');
  const next=responseFor('/auth/login');await page.getByRole('button',{name:'登录',exact:true}).click();assert.equal((await next).status(),200);
  await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();
  auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
}
async function setup(){
  if(context)await context.close();
  context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block'});
  await context.route('**/*',route=>{const origin=new URL(route.request().url()).origin;if([UI,API].includes(origin))return route.continue();external.push(origin);return route.abort();});
  page=await context.newPage();page.on('dialog',d=>d.accept());page.on('pageerror',e=>pageErrors.push(e.message));
  page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method()))writes.push(new URL(r.url()).pathname);});
  await page.goto(UI);await login();
}
async function fillForm(name='草稿合成犬'){
  await page.getByPlaceholder('如：乐乐 / Lucky',{exact:true}).fill(name);
  await page.getByLabel('主诉（必填）',{exact:true}).fill('合成犬呕吐两天，精神正常');
  await history().fill('  未提交医生病史🐾\n保留尾部空格。  \n');
  await page.getByLabel('主人电话',{exact:true}).fill('synthetic-draft-only');
}
async function start(){
  const next=responseFor('/api/ai/consult/session');await page.getByRole('button',{name:'提交分析（不入库）',exact:true}).click();return (await next).json();
}
async function audit(){
  await page.getByPlaceholder('如 HS-0001 / Dr.Zhao',{exact:true}).fill('Synthetic-Draft');
  const next=responseFor('/api/audit-log');await page.getByRole('button',{name:'确认覆核并写入审计',exact:true}).click();assert.equal((await next).status(),201);
}
async function preview(){
  await step(2).click();const next=responseFor('/preview-case');await save().getByRole('button',{name:'核对保存内容',exact:true}).click();const p=await (await next).json();
  await save().getByLabel('已核对本次保存内容',{exact:true}).check();return p;
}
async function restore(){await draft().getByRole('button',{name:'恢复本页草稿',exact:true}).click();await expect(draft().getByText('发现本页未完成草稿',{exact:true})).toHaveCount(0);}
async function reloadOffer(){await page.reload();await expect(draft().getByText('发现本页未完成草稿',{exact:true})).toBeVisible();}

async function structuredHistoryAcceptance(){
  await setup();await fillForm('M5多轮结构化合成犬');const created=await start();
  const raws=['  M5-A：否认用药🐾\n<literal> & 保留尾部。  \n','M5-B：未见呕吐，原文不改🐱','M5-C：更正前文，曾用药但名称待核对'];
  let current=created;
  for(const raw of raws.slice(0,2)){
    await followup().fill('合成普通回答');await structured().fill(raw);
    const next=responseFor('/answer');await page.getByRole('button',{name:'提交追问回答',exact:true}).click();const res=await next;assert.equal(res.status(),200);current=await res.json();
    await expect(followup()).toHaveValue('');await expect(structured()).toHaveValue('');
    assert.equal(JSON.parse(current.answers.at(-1).structured_intake_snapshot).sections.flatMap(s=>s.answers)[0].answer,raw);
  }
  const retained=()=>page.getByRole('region',{name:'已提交结构化问诊记录',exact:true});
  const beforeReload=writes.length;await reloadOffer();await restore();assert.equal(writes.length,beforeReload);
  const shown=await retained().locator('pre').allTextContents();assert.equal(shown.length,2);
  raws.slice(0,2).forEach((raw,i)=>{assert(shown[i].includes(raw));assert(shown[i].includes('第 '+(i+1)+' 轮'));});
  assert.equal(await page.locator('literal').count(),0);
  const reread=await request('GET','/api/ai/consult/session/'+created.session_id);assert.deepEqual(reread.answers,current.answers);
  await record('m5_two_round_snapshots_survive_real_postgres_and_browser_refresh');
  await audit();const checked=await preview();
  for(const raw of raws.slice(0,2))assert.equal(checked.history.split(raw).length-1,1);
  await save().getByRole('button',{name:'确认并保存病例',exact:true}).click();await expect(step(3)).toHaveAttribute('aria-current','step');
  const bound=await request('GET','/api/ai/consult/session/'+created.session_id), cid=bound.case_id;assert(cid);
  assert.equal((await request('GET','/api/cases/'+cid)).history,checked.history);
  await record('m5_reviewed_first_save_contains_both_original_rounds_once');
  await step(1).click();await followup().fill('合成更正回答');await structured().fill(raws[2]);
  const endpoint='**/api/ai/consult/session/'+created.session_id+'/answer';const beforeAnswer=writes.filter(p=>p.endsWith('/answer')).length;
  await page.route(endpoint,async handler=>{const real=await handler.fetch();assert.equal(real.status(),200);await handler.abort('failed');});
  await page.getByRole('button',{name:'提交追问回答',exact:true}).click();await expect(page.getByRole('region',{name:'追问结果待核对',exact:true})).toBeVisible();
  await expect(followup()).toHaveValue('合成更正回答');await expect(structured()).toHaveValue(raws[2]);await expect(page.getByRole('button',{name:'提交追问回答',exact:true})).toBeDisabled();
  await page.unroute(endpoint);await page.getByRole('button',{name:'核对追问提交结果',exact:true}).click();await expect(structured()).toHaveValue('');
  assert.equal(writes.filter(p=>p.endsWith('/answer')).length,beforeAnswer+1);await expect(retained().locator('pre')).toHaveCount(3);
  const replay=await context.request.post(API+'/api/ai/consult/session/'+created.session_id+'/answer',{headers:auth,data:{question:'并发旧轮次',answer:'不得再写入',expected_answers_token:current.answers_token}});
  assert.equal(replay.status(),409);assert.equal((await request('GET','/api/ai/consult/session/'+created.session_id)).answers.length,3);
  await record('m5_lost_answer_response_recovers_by_get_and_stale_token_cannot_append');
  await audit();await step(2).click();const update=page.getByRole('region',{name:'更新已绑定病例核对',exact:true});
  await update.getByLabel('本次更新范围',{exact:true}).selectOption('consult_sync');
  const next=responseFor('/preview-update-case');await update.getByRole('button',{name:'核对更新内容',exact:true}).click();const proposed=await (await next).json();
  for(const raw of raws)assert.equal(proposed.proposed.history.split(raw).length-1,1);
  await update.getByLabel('已核对本次更新内容',{exact:true}).check();await update.getByRole('button',{name:'确认并更新病例',exact:true}).click();await expect(step(3)).toHaveAttribute('aria-current','step');
  const actual=await request('GET','/api/cases/'+cid);assert.equal(actual.history,proposed.proposed.history);
  for(let i=0;i<3;i++){assert.equal(actual.history.split(raws[i]).length-1,1);assert(actual.history.includes('第 '+(i+1)+' 轮'));}
  fs.writeFileSync(path.join(out,'m5-structured-case.json'),JSON.stringify({case_id:cid,session_id:created.session_id,raws,history:actual.history},null,2));
  await record('m5_third_round_correction_keeps_first_two_in_review_and_case_readback');
}

async function main(){
  browser=await chromium.launch({headless:true});console.log('Chromium draft acceptance:',browser.version());
  await setup();await fillForm();const original=await history().inputValue(), before=writes.length;
  await reloadOffer();await expect(history()).toHaveValue('');await restore();
  await expect(history()).toHaveValue(original);await expect(page.getByLabel('主人电话',{exact:true})).toHaveValue('synthetic-draft-only');
  assert.equal(writes.length,before);await record('refresh_restores_exact_form_without_server_writes');

  let session=await start();await audit();await preview();await reloadOffer();await restore();
  await expect(step(3)).toBeDisabled();await step(2).click();
  await expect(save().getByLabel('已核对本次保存内容',{exact:true})).toHaveCount(0);
  await expect(save().getByRole('button',{name:'核对保存内容',exact:true})).toBeDisabled();
  await record('refresh_does_not_restore_review_or_save_confirmation');

  await step(1).click();await followup().fill('尚未提交的追问回答🐾');await structured().fill('尚未提交的结构化病史');
  await reloadOffer();const beforeRestore=writes.length;await restore();assert.equal(writes.length,beforeRestore);
  await expect(followup()).toHaveValue('尚未提交的追问回答🐾');await expect(structured()).toHaveValue('尚未提交的结构化病史');
  await record('pending_followup_and_structured_input_survive_refresh');

  session=await request('GET','/api/ai/consult/session/'+session.session_id);
  const q=Array.isArray(session.result.next_questions)?session.result.next_questions[0]:session.result.next_questions.questions[0];
  await request('POST','/api/ai/consult/session/'+session.session_id+'/answer',{question:q,answer:'另一端已提交的合成回答',structured_intake_answers:null});
  await reloadOffer();await restore();await expect(followup()).toHaveValue('');
  const notes=page.getByRole('region',{name:'待重新整理的草稿补充',exact:true});await expect(notes).toContainText('尚未提交的追问回答🐾');await expect(notes).toContainText('尚未提交的结构化病史');
  await record('changed_server_question_keeps_old_pending_notes_separate');

  await setup();await fillForm('草稿保存结果待核对');session=await start();await audit();const p=await preview();
  const count=(await request('GET','/api/cases')).total;
  const sessionRoute='**/api/ai/consult/session/'+session.session_id;
  await page.route(sessionRoute,route=>route.request().method()==='GET'?route.abort('failed'):route.continue());
  await save().getByRole('button',{name:'确认并保存病例',exact:true}).click();
  await expect(save().getByText('暂时无法回读，保存结果待核对。已保留输入和核对内容，请先核对保存结果。',{exact:true})).toBeVisible();
  assert.equal((await request('GET','/api/cases')).total,count+1);
  await reloadOffer();await draft().getByRole('button',{name:'恢复本页草稿',exact:true}).click();
  await expect(draft().getByText('暂时无法读取原问诊，草稿仍保留。请检查登录状态或网络后重试恢复。',{exact:true})).toBeVisible();
  assert(await page.evaluate(key=>!!sessionStorage.getItem(key),KEY));await record('failed_session_read_keeps_recovery_offer');
  await page.unroute(sessionRoute);const writesBefore=writes.length;await restore();assert.equal(writes.length,writesBefore);
  const binding=await request('GET','/api/ai/consult/session/'+session.session_id);assert(binding.case_id);
  await step(2).click();await expect(page.getByRole('region',{name:'更新已绑定病例核对',exact:true})).toContainText('更新病例 #'+binding.case_id);
  await expect(save()).toHaveCount(0);await expect(step(3)).toBeDisabled();
  assert.equal((await request('GET','/api/cases')).total,count+1);assert.equal((await request('GET','/api/cases/'+binding.case_id)).history,p.history);
  await record('refresh_after_committed_save_resolves_binding_without_second_save');

  await setup();await fillForm('草稿成功保存');session=await start();await audit();const checked=await preview();
  await save().getByRole('button',{name:'确认并保存病例',exact:true}).click();
  await expect(step(3)).toHaveAttribute('aria-current','step');
  await expect(draft().getByText('本次输入已保存并回读，标签页草稿已清除。',{exact:true})).toBeVisible();
  assert.equal(await page.evaluate(key=>sessionStorage.getItem(key),KEY),null);await record('verified_first_save_clears_current_draft');
  await step(1).click();await history().fill('保存后新增、尚未保存的病史');await reloadOffer();await restore();
  await expect(history()).toHaveValue('保存后新增、尚未保存的病史');const b=await request('GET','/api/ai/consult/session/'+session.session_id);
  assert.equal((await request('GET','/api/cases/'+b.case_id)).history,checked.history);
  await record('later_unsaved_edits_restore_without_overwriting_saved_case');

  await page.getByRole('button',{name:'退出',exact:true}).click();await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();
  assert.equal(await page.evaluate(key=>sessionStorage.getItem(key),KEY),null);await login('pg-other');
  await expect(history()).toHaveValue('');await expect(draft().getByText('发现本页未完成草稿',{exact:true})).toHaveCount(0);
  await record('logout_clears_draft_before_another_account_logs_in');

  await structuredHistoryAcceptance();

  await page.evaluate(key=>sessionStorage.setItem(key,'{broken'),KEY);await page.reload();
  await expect(history()).toHaveValue('');await expect(draft().getByText('草稿不可读取或已过期；请检查输入后继续。',{exact:true})).toBeVisible();
  await record('corrupt_draft_is_rejected_without_blocking_intake');
  await page.evaluate(key=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(this===sessionStorage && k===key)throw new DOMException('Synthetic quota fault','QuotaExceededError');return original.call(this,k,v);};},KEY);
  await history().fill('存储不可用时当前输入仍保留');await expect(history()).toHaveValue('存储不可用时当前输入仍保留');
  await expect(draft().getByText('浏览器暂时无法保留最新草稿，刷新或离开可能丢失输入。请先完成病例保存。',{exact:true})).toBeVisible();
  assert.deepEqual(pageErrors,[]);assert.deepEqual(external,[]);await record('quota_failure_warns_without_losing_current_input');
}
main().then(()=>{process.exitCode=0;}).catch(async error=>{process.exitCode=1;console.error(error);failures.push(String(error));if(page){await page.screenshot({path:path.join(out,'draft-failure.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(out,'draft-failure-dom.txt'),await page.locator('body').innerText().catch(()=>''));}}).finally(async()=>{fs.writeFileSync(path.join(out,'draft-checks.json'),JSON.stringify({passed,failures,pageErrors,external},null,2));if(browser)await browser.close();});
