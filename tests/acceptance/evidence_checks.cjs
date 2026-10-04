// Real Chromium + authenticated isolated application; no synthetic AI responses.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
let browser,page;const passed=[],failures=[],errors=[],external=[],samples=[];
async function main(){
 browser=await chromium.launch({headless:true});
 for(const animal of ['dog','cat']){
  const context=await browser.newContext({acceptDownloads:true,serviceWorkers:'block',viewport:{width:1440,height:1000}});
  await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
  page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
  const region=name=>page.getByRole('region',{name,exact:true});
  const field=label=>page.locator('label').filter({has:page.getByText(label,{exact:true})}).locator('input,textarea,select');
  async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();}
  await login();const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
  const raw='  不清楚🐾\n尚待医生询问  ';
  await field('病例名 / 宠物名').fill('B4合成'+animal);await field('物种').selectOption(animal);await field('主诉（必填）').fill('常规体检；未见黑便');await field('既往史').fill('B4原始医生记录🐾');
  await field('主人姓名').fill('B4合成宠主');await field('毛色').fill('合成黑白');
  let event=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/ai/consult/session');
  await page.getByRole('button',{name:'提交分析（不入库）',exact:true}).click();let response=await event;assert.equal(response.status(),200);let session=await response.json();
  assert.equal(session.result.risk_level,'待核对');assert.deepEqual(session.result.diseases.diseases,[]);
  await expect(region('问诊输入依据')).toContainText('未知或矛盾记录不能视为正常');
  await region('问诊输入依据').getByText('查看记录来源与判断状态',{exact:true}).click();await expect(region('问诊输入依据')).toContainText('明确否定');
  await page.screenshot({path:path.join(out,'b4-'+animal+'-negative.png'),fullPage:true});passed.push(animal+'_negative_no_false_candidates_visible_evidence');
  event=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/answer')&&r.request().method()==='POST');
  await page.getByPlaceholder('请填写对当前追问的回答',{exact:true}).fill(raw);await page.getByRole('button',{name:'提交追问回答',exact:true}).click();response=await event;assert.equal(response.status(),200);session=await response.json();
  assert.equal(session.result.risk_level,'待核对');assert.deepEqual(session.result.diseases.diseases,[]);
  assert.equal(session.answers.at(-1).answer,raw);await expect(region('问诊输入依据')).toContainText('未知／待核对');passed.push(animal+'_unknown_followup_does_not_confirm_question');
  await page.getByPlaceholder('如 HS-0001 / Dr.Zhao',{exact:true}).fill('B4-Synthetic');await page.getByRole('button',{name:'确认覆核并写入审计',exact:true}).click();await expect(page.getByRole('button',{name:'审计已写入',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'进入保存前核对 →',exact:true}).click();const review=region('首次保存病例核对');await review.getByRole('button',{name:'核对保存内容',exact:true}).click();await review.getByLabel('已核对本次保存内容',{exact:true}).check();
  let writes=0;await page.route('**/api/ai/consult/session/*/save-case',r=>{writes++;return r.continue();});await review.getByRole('button',{name:'确认并保存病例',exact:true}).evaluate(e=>{e.click();e.click();});await expect(region('本次保存回读')).toBeVisible();assert.equal(writes,1);
  const route=API+'/api/ai/consult/session/'+session.session_id;let r=await context.request.get(route,{headers:auth});let stored=await r.json();assert.deepEqual(stored.result.input_evidence,session.result.input_evidence);
  const id=stored.case_id;r=await context.request.get(API+'/api/cases/'+id,{headers:auth});const saved=await r.json();assert(saved.history.includes(raw));assert(saved.treatment.includes('待核对'));assert(!saved.analysis.includes('扭转'));
  await page.goto(UI);await page.getByRole('button',{name:'退出',exact:true}).click();await login();await page.goto(UI+'/cases/'+id);await page.reload();assert.equal(await region('完整病史原文').locator('.text-body').textContent(),saved.history);passed.push(animal+'_reviewed_save_once_relogin_exact_original');
  for(const [label,key] of [['导出门诊病历草稿 DOCX','outpatient'],['导出宠主说明草稿 DOCX','owner-summary']]){
   event=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/clinical-docs/render-preview');await page.getByRole('button',{name:label,exact:true}).click();const preview=await (await event).json();assert.equal(preview.context['visit.history'],saved.history);assert(preview.context['visit.plan'].includes('待核对'));assert(!preview.context['visit.assessment'].includes('扭转'));
   const doc=region('文书草稿内容核对');await expect(doc.getByRole('button',{name:'确认并下载草稿 DOCX',exact:true})).toBeDisabled();await doc.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();event=page.waitForEvent('download');await doc.getByRole('button',{name:'确认并下载草稿 DOCX',exact:true}).click();const download=await event;const file='b4-'+animal+'-'+key+'.docx';await download.saveAs(path.join(out,file));samples.push({species:animal,case_id:id,file,history:saved.history,treatment:saved.treatment});await doc.getByRole('button',{name:'关闭草稿核对',exact:true}).click();passed.push(animal+'_'+key+'_reviewed_actual_docx');
  }
  await page.screenshot({path:path.join(out,'b4-'+animal+'-saved.png'),fullPage:true});await context.close();
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
}
main().catch(async e=>{process.exitCode=1;failures.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'b4-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{fs.writeFileSync(path.join(out,'b4-evidence-checks.json'),JSON.stringify({passed,failures,errors,external,samples},null,2));if(browser)await browser.close();});
