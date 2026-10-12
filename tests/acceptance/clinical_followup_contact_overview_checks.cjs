// Real browser, application, JWT and disposable database; reply faults are explicit.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process'),{randomUUID}=require('node:crypto');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const passed=[],errors=[],external=[],saved=[];let browser,page,server;
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb20-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb20-only',ENVIRONMENT='test',RENDER='false')
sys.path[:]=[str(Path('backend').resolve())]+[p for p in sys.path if Path(p or '.').resolve()!=Path('.').resolve()]
def guard(event,args):
    if event in {'socket.connect','socket.connect_ex','socket.bind'} and isinstance(args[1],tuple):assert args[1][0] in {'127.0.0.1','::1'} and args[1][1]==18026
    if event=='socket.getaddrinfo':assert args[0] in {'127.0.0.1','localhost','::1',None}
sys.addaudithook(guard)
import main,db,models
db.Base.metadata.create_all(db.engine)
`:`
import sys
sys.path.insert(0,'tests/acceptance')
import fixture as f
main=f.main
`;
const boot=prefix+`
import os,tempfile
private=tempfile.TemporaryDirectory(prefix='cwb20-private-')
os.environ.update(VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OVERVIEW_ENABLED='1',FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_CONTACT_OVERVIEW_ENABLED='1',FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_CONTACTS_ENABLED='1',FOLLOWUP_CONTACTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb20-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Overview backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Overview backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1440,height:1040}});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const account={email:'cwb20-'+randomUUID()+'@example.com',password:randomUUID()};
 assert((await context.request.post(API+'/auth/signup',{data:account})).ok());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill(account.email);await page.getByPlaceholder('密码',{exact:true}).fill(account.password);await button(page,'登录').click();await expect(button(page,'退出')).toBeVisible();}
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const response=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(response.ok(),await response.text());return response.status()===204?null:response.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_contact_overview_cw_b20_cases.json','utf8'));
 const uuid=()=>randomUUID().replaceAll('-','');
 async function planSave(cid,operation='create',row=null){
  const root=`/api/cases/${cid}/followup-plan`,listing=await call('GET',root);
  const body={request_id:uuid(),operation,plan_id:row?.id??null,expected_plan_token:row?.token||'',expected_case_token:listing.case_token,expected_state_token:listing.state_token,
   data:operation==='withdraw'?null:fixture[operation==='correct'?'corrected_plan':'plan'],reason:operation==='create'?'':'CW-B20 合成来源更正'};
  const preview=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:preview.preview_token,reviewed:true})).plan;
 }
 async function contactSave(cid,source,operation='create',row=null,data=fixture.contact){
  const root=`/api/cases/${cid}/followup-contacts`,listing=await call('GET',root),plan=listing.plans.find(p=>p.id===(row?.source.id||source.id));
  const body={request_id:uuid(),operation,contact_id:row?.id??null,expected_contact_token:row?.token||'',source_plan_id:plan.id,source_plan_version:plan.version,
   expected_source_token:plan.token,expected_case_token:listing.case_token,expected_state_token:listing.state_token,data:operation==='withdraw'?null:data,
   reason:operation==='create'?'':fixture[operation==='withdraw'?'withdrawal_reason':'correction_reason']};
  const preview=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:preview.preview_token,reviewed:true})).record;
 }
 let writes=[],downloads=0,confirms=0;
 page.on('request',r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(r.url());if(r.method()==='POST'&&r.url().endsWith('/followup-contacts/confirm'))confirms++;});
 page.on('download',()=>downloads++);
 const overview=page.getByRole('region',{name:'就诊资料总览',exact:true});
 const group=overview.getByRole('region',{name:'人工随访资料状态',exact:true});
 const editor=page.getByRole('region',{name:'人工随访记录',exact:true});
 const planEditor=page.getByRole('region',{name:'人工复查计划',exact:true});
 const inventoryUrl=cid=>`/api/cases/${cid}/visit-overview?include_followup_plan=true&include_followup_contacts=true`;
 async function inventory(cid){const value=await call('GET',inventoryUrl(cid));delete value.read_at;return value;}
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',fixture[species==='dog'?'case':'cat_case'])).id;
  let source=await planSave(cid),first=await contactSave(cid,source);
  const corrected=await contactSave(cid,source,'correct',first,fixture.corrected);await contactSave(cid,source,'withdraw',corrected);
  const second=await contactSave(cid,source,'create',null,species==='cat'?fixture.long_contact:fixture.contact);
  source=await planSave(cid,'correct',source);const current=await contactSave(cid,source);
  await page.goto(UI+'/cases/'+cid);writes=[];
  const before=await inventory(cid),contactsBefore=await call('GET',`/api/cases/${cid}/followup-contacts`);
  await button(page,'打开就诊资料总览').click();await expect(group).toContainText('旧版本 1');await expect(group).toContainText('已撤销 1');
  const original=group.getByRole('article',{name:`随访总览记录 ${first.id} 版本 1`,exact:true});
  await original.getByText('查看随访原文与冻结来源',{exact:true}).click();
  const literals=await original.locator('dd').allTextContents();assert(literals.includes(fixture.contact.note));assert(literals.includes(fixture.plan.purpose));
  await expect(original).toContainText('来源计划已更正');
  await button(original,`回看随访 #${first.id} 版本 1`).click();await expect(editor).toContainText(`正在回看随访 #${first.id} 版本 1`);
  const inspected=editor.getByRole('article',{name:`人工随访记录 ${first.id}`,exact:true});await expect(inspected.locator('details')).toHaveAttribute('open','');
  await expect(inspected).toBeFocused();
  await button(original,`回看计划 #${first.source.id} 版本 ${first.source.version}`).click();await expect(planEditor).toContainText(`正在回看计划 #${first.source.id} 版本 1`);
  assert.deepEqual(await inventory(cid),before);assert.deepEqual(await call('GET',`/api/cases/${cid}/followup-contacts`),contactsBefore);assert.deepEqual(writes,[]);
  passed.push(species+'_literal_history_provenance_exact_contact_plan_navigation_readonly');
  await button(page,'打开检验项目').click();await button(page.getByRole('region',{name:'检验项目人工录入',exact:true}),'录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('CW-B20 未保存检验');
  await button(planEditor,'更正复查计划').click();await planEditor.getByLabel('复查目的',{exact:true}).fill('CW-B20 未保存计划');
  await button(editor.getByRole('article',{name:`人工随访记录 ${current.id}`,exact:true}),'更正人工随访记录').click();
  await editor.getByLabel('随访记录原文',{exact:true}).fill('CW-B20 未保存联系');await editor.getByLabel('随访更正或撤销原因',{exact:true}).fill('合成回看保留草稿');
  await button(original,`回看随访 #${first.id} 版本 1`).click();await expect(editor).toContainText(`正在回看随访 #${first.id} 版本 1`);
  await expect(editor.getByLabel('随访记录原文',{exact:true})).toHaveValue('CW-B20 未保存联系');await expect(planEditor.getByLabel('复查目的',{exact:true})).toHaveValue('CW-B20 未保存计划');await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('CW-B20 未保存检验');
  assert.deepEqual(writes,[]);passed.push(species+'_three_unsaved_drafts_preserved_without_write');
  if(species==='cat'){
   const longRow=group.getByRole('article',{name:`随访总览记录 ${second.id} 版本 1`,exact:true});await longRow.getByText('查看随访原文与冻结来源',{exact:true}).click();assert((await longRow.locator('dd').allTextContents()).includes(fixture.long_contact.note));
  }
  await group.screenshot({path:path.join(out,`cwb20-${species}-overview-wide.png`)});
  await page.setViewportSize({width:390,height:844});await group.screenshot({path:path.join(out,`cwb20-${species}-overview-narrow.png`)});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.setViewportSize({width:1440,height:1040});
  passed.push(species+'_wide_narrow_full_text_layout');
  if(species==='dog'){
   const pattern=`**/api/cases/${cid}/followup-contacts`;
   const missing=async route=>{const response=await route.fetch(),data=await response.json();data.records=data.records.filter(r=>r.root_id!==first.root_id);await route.fulfill({response,json:data});};
   await context.route(pattern,missing);await button(original,`回看随访 #${first.id} 版本 1`).click();await expect(editor).toContainText('指定随访版本当前无法读取');
   await expect(editor.getByLabel('随访记录原文',{exact:true})).toHaveValue('CW-B20 未保存联系');await context.unroute(pattern,missing);
   await button(original,`回看随访 #${first.id} 版本 1`).click();await expect(editor).toContainText(`正在回看随访 #${first.id} 版本 1`);passed.push('missing_exact_target_never_substitutes_or_edits');
   source=await planSave(cid,'withdraw',source);await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
   await expect(group.getByRole('article',{name:`随访总览记录 ${current.id} 版本 1`,exact:true})).toContainText('来源计划已撤销');
   await expect(editor.getByLabel('随访记录原文',{exact:true})).toHaveValue('CW-B20 未保存联系');passed.push('withdrawn_source_retains_history_and_draft');
   const overviewPattern=`**/api/cases/${cid}/visit-overview?*`;let arrive,release,finish,held=false;
   const seen=new Promise(r=>arrive=r),gate=new Promise(r=>release=r),done=new Promise(r=>finish=r);
   const late=async route=>{if(held){await route.continue();return;}held=true;try{const response=await route.fetch();arrive();await gate;await route.fulfill({response}).catch(()=>{});}finally{finish();}};
   await context.route(overviewPattern,late);await button(overview,'刷新就诊资料总览').click();await seen;
   await call('PUT',`/api/cases/${cid}`,{patient_name:'CW-B20 焦点后新身份'});await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
   await expect(overview).toContainText('CW-B20 焦点后新身份');release();await done;await context.unroute(overviewPattern,late);
   await expect(overview).toContainText('CW-B20 焦点后新身份');
   await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));await expect(overview).toContainText('CW-B20 焦点后新身份');passed.push('late_snapshot_focus_visibility_refresh_keeps_new_case');
   await button(editor,'预览并核对人工随访').click();await editor.getByLabel('已核对人工随访',{exact:true}).check();
   const confirmPattern=`**/api/cases/${cid}/followup-contacts/confirm`,statusPattern=`**/api/cases/${cid}/followup-contacts/requests/*`;
   const lost=async route=>{const response=await route.fetch();assert(response.ok(),await response.text());await route.abort('failed');};
   const unavailable=route=>route.abort('failed');await context.route(confirmPattern,lost);await context.route(statusPattern,unavailable);
   const confirmsBefore=confirms;await button(editor,'确认保存人工随访').click();await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toBeVisible();
   await expect(button(original,`回看随访 #${first.id} 版本 1`)).toBeVisible();await button(original,`回看随访 #${first.id} 版本 1`).click();
   await expect(editor).toContainText(`正在回看随访 #${first.id} 版本 1`);await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toBeVisible();
   await expect(button(editor,'预览并核对人工随访')).toBeDisabled();assert.equal(confirms,confirmsBefore+1);
   await context.unroute(statusPattern,unavailable);await context.unroute(confirmPattern,lost);
   await button(editor,'核对随访保存结果').click();await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toHaveCount(0);assert.equal(confirms,confirmsBefore+1);
   passed.push('actual_lost_write_reply_navigation_retains_unknown_then_status_no_repeat');
  }
  saved.push({case_id:cid,overview:await inventory(cid),contacts:await call('GET',`/api/cases/${cid}/followup-contacts`)});
 }
 // Re-login and reopen the saved inventories from the server.
 await page.goto(UI);await button(page,'退出').click();await login();token=await page.evaluate(()=>localStorage.getItem('token'));
 for(const item of saved){assert.deepEqual(await inventory(item.case_id),item.overview);assert.deepEqual(await call('GET',`/api/cases/${item.case_id}/followup-contacts`),item.contacts);}
 await page.goto(UI+'/cases/'+saved[0].case_id);await button(page,'打开就诊资料总览').click();await expect(group).toBeVisible();
 await page.goto(UI+'/cases/'+saved[1].case_id);await button(page,'打开就诊资料总览').click();await expect(overview).toContainText(fixture.cat_case.patient_name);await expect(group).toContainText('旧版本 1');
 const other={email:'cwb20-other-'+randomUUID()+'@example.com',password:randomUUID()};assert((await context.request.post(API+'/auth/signup',{data:other})).ok());
 const auth=await context.request.post(API+'/auth/login',{form:{username:other.email,password:other.password}});assert(auth.ok());const otherToken=(await auth.json()).access_token;
 await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);
 await expect(group).toHaveCount(0);await expect(page.getByText(fixture.cat_case.patient_name,{exact:true})).toHaveCount(0);
 passed.push('relogin_exact_saved_readback_case_and_account_isolation');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,0);
 fs.writeFileSync(path.join(out,'cwb20-browser-results.json'),JSON.stringify({status:'PASS',passed,saved,confirms,downloads,external_requests:external,page_errors:errors},null,2));
 console.log(JSON.stringify({status:'PASS',passed,confirms,downloads,external_requests:external,page_errors:errors},null,2));
}
main().catch(async error=>{console.error(error);if(page)await page.screenshot({path:path.join(out,'cwb20-failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>server.once('exit',resolve));}});
