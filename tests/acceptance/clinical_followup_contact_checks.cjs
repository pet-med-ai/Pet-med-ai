// Real Chromium, JWT, app and database. Fault injection drops only actual replies.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const passed=[],errors=[],external=[],saved=[];let browser,page,server;
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb19-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb19-only',ENVIRONMENT='test',RENDER='false')
sys.path[:]=[str(Path('backend').resolve())]+[p for p in sys.path if Path(p or '.').resolve()!=Path('.').resolve()]
def guard(event,args):
    if event in {'socket.connect','socket.connect_ex','socket.bind'} and isinstance(args[1],tuple):assert args[1][0] in {'127.0.0.1','::1'} and args[1][1]==18026
    if event=='socket.getaddrinfo':assert args[0] in {'127.0.0.1','localhost','::1',None}
sys.addaudithook(guard)
import main,db,models
db.Base.metadata.create_all(db.engine)
from fastapi.testclient import TestClient
with TestClient(main.app) as client:assert client.post('/auth/signup',json={'email':'browser-owner@example.com','password':'Synthetic-PR26-only-20260916'}).status_code==200
`:`
import sys
sys.path.insert(0,'tests/acceptance')
import fixture as f
main=f.main
`;
const boot=prefix+`
import os,tempfile
private=tempfile.TemporaryDirectory(prefix='cwb19-private-')
os.environ.update(FOLLOWUP_CONTACTS_ENABLED='1',FOLLOWUP_CONTACTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_QUEUE_ENABLED='1',FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY='1',FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb19-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Followup backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Followup backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1440,height:1000}});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await button(page,'登录').click();await expect(button(page,'退出')).toBeVisible();}
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(r.ok(),await r.text());return r.status()===204?null:r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_contacts_cw_b19_cases.json','utf8'));
 const uuid=()=>require('node:crypto').randomUUID().replaceAll('-','');
 async function planSave(cid,operation='create',row=null){
  const root=`/api/cases/${cid}/followup-plan`,l=await call('GET',root),body={request_id:uuid(),operation,plan_id:row?.id??null,expected_plan_token:row?.token||'',expected_case_token:l.case_token,expected_state_token:l.state_token,data:operation==='withdraw'?null:fixture.plan,reason:operation==='create'?'':'合成来源更正'};
  const p=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:p.preview_token,reviewed:true})).plan;
 }
 let confirms=0,downloads=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/followup-contacts/confirm'))confirms++;});page.on('download',()=>downloads++);
 const view=page.getByRole('region',{name:'人工随访记录',exact:true});
 async function fill(data){
  await view.getByLabel('随访联系时间',{exact:true}).fill(data.occurred_at.slice(0,16));
  await view.getByLabel('随访联系方式',{exact:true}).selectOption(data.method);await view.getByLabel('随访联系结果',{exact:true}).selectOption(data.outcome);
  await view.getByLabel('随访记录原文',{exact:true}).fill(data.note);await view.getByLabel('随访后续安排',{exact:true}).fill(data.next_action);
 }
 async function review(){await button(view,'预览并核对人工随访').click();await expect(view.getByLabel('已核对人工随访',{exact:true})).toBeVisible();await expect(button(view,'确认保存人工随访')).toBeDisabled();await view.getByLabel('已核对人工随访',{exact:true}).check();}
 async function confirm(){await button(view,'确认保存人工随访').evaluate(el=>{el.click();el.click();});await expect(view.getByRole('region',{name:'人工随访草稿',exact:true})).toHaveCount(0);}
 async function oldState(cid){const queue=await call('GET','/api/followup-plan-queue?range=all');delete queue.read_at;return {case:await call('GET',`/api/cases/${cid}`),plans:await call('GET',`/api/cases/${cid}/followup-plan`),queue,kpi:await call('GET','/api/kpi/followups?start=2024-02-01&end=2024-03-31')};}
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B19 合成'+species})).id,source=await planSave(cid),root=`/api/cases/${cid}/followup-contacts`,before=await oldState(cid),count=confirms;
  await page.goto(UI+'/followup-plans');await page.getByLabel('计划日期范围',{exact:true}).selectOption('all');
  await page.getByRole('link',{name:`打开病例 #${cid} 的计划 #${source.id} 版本 1`,exact:true}).click();
  await expect(page.getByRole('region',{name:'人工复查计划',exact:true})).toContainText(`正在回看计划 #${source.id} 版本 1`);
  await button(page,'打开检验项目').click();await button(page,'录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('保留旧草稿 '+species);
  await button(page,'打开人工随访记录').click();await button(view,'新增人工随访记录').click();await expect(view.getByLabel('随访来源计划',{exact:true})).toHaveValue('');
  await view.getByLabel('随访来源计划',{exact:true}).selectOption(String(source.id));await fill(fixture.contact);await review();
  if(species==='cat')await page.route(API+root+'/confirm',async r=>{const response=await r.fetch();assert(response.ok(),await response.text());await r.abort('failed');},{times:1});
  await confirm();assert.equal(confirms,count+1);let first=await call('GET',root);assert.deepEqual(first.records[0].data,fixture.contact);assert.equal(first.records[0].source.id,source.id);
  assert.deepEqual(await oldState(cid),before);await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('保留旧草稿 '+species);
  // Preserve frozen source after a real plan correction, while requiring a new review.
  await button(view,'更正人工随访记录').click();await fill(fixture.corrected);await view.getByLabel('随访更正或撤销原因',{exact:true}).fill(fixture.correction_reason);await review();
  await planSave(cid,'correct',source);await page.evaluate(()=>dispatchEvent(new Event('focus')));await expect(view.getByLabel('已核对人工随访',{exact:true})).toHaveCount(0);await expect(view).toContainText('来源计划已更正');
  await expect(view.getByLabel('随访记录原文',{exact:true})).toHaveValue(fixture.corrected.note);await review();await confirm();
  const corrected=await call('GET',root);assert.deepEqual(corrected.records.map(r=>r.data),[fixture.contact,fixture.corrected]);assert.deepEqual(corrected.records[1].source,first.records[0].source);
  const afterPlan=await oldState(cid);await button(view,'撤销人工随访记录').click();await view.getByLabel('随访更正或撤销原因',{exact:true}).fill(fixture.withdrawal_reason);await review();await confirm();
  const withdrawn=await call('GET',root);assert.deepEqual(withdrawn.records.map(r=>r.state),['superseded','withdrawn']);assert.equal(withdrawn.records[1].withdrawal.reason,fixture.withdrawal_reason);assert.deepEqual(await oldState(cid),afterPlan);assert.equal(confirms,count+3);
  // A real delayed preview is discarded after focus; it must not reopen confirmation.
  await button(view,'新增人工随访记录').click();await view.getByLabel('随访来源计划',{exact:true}).selectOption(String(withdrawn.plans.at(-1).id));await fill(fixture.contact);
  let release,arrive;const held=new Promise(r=>release=r),started=new Promise(r=>arrive=r);
  await page.route(API+root+'/preview',async r=>{const response=await r.fetch();assert(response.ok());arrive();await held;await r.fulfill({response}).catch(()=>{});},{times:1});
  await button(view,'预览并核对人工随访').click();await started;await page.evaluate(()=>dispatchEvent(new Event('focus')));release();await expect(button(view,'刷新人工随访记录')).toBeEnabled();await expect(view.getByLabel('已核对人工随访',{exact:true})).toHaveCount(0);
  await button(view,'放弃人工随访草稿').click();await view.getByText(`查看随访记录 #${withdrawn.records[1].id} 版本 2`,{exact:true}).click();await view.screenshot({path:path.join(out,`cwb19-${species}-history.png`)});
  await page.setViewportSize({width:390,height:844});await view.scrollIntoViewIfNeeded();await view.screenshot({path:path.join(out,`cwb19-${species}-narrow.png`)});assert(await view.evaluate(el=>el.scrollWidth<=el.clientWidth));await page.setViewportSize({width:1440,height:1000});
  await page.goto(UI);await button(page,'退出').click();await login();token=await page.evaluate(()=>localStorage.getItem('token'));await page.goto(UI+'/cases/'+cid);await button(page,'打开人工随访记录').click();await expect(view).toContainText('已撤销');assert.deepEqual(await call('GET',root),withdrawn);
  saved.push({case_id:cid,listing:withdrawn});passed.push(species+'_queue_navigation_exact_source_create_correct_withdraw_focus_late_reply_relogin_old_state'+(species==='cat'?'_lost_confirm_reply':''));
 }
 assert.equal(downloads,0);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 fs.writeFileSync(path.join(out,'cwb19-browser-saved.json'),JSON.stringify({saved,confirm_posts:confirms,downloads,external_calls:0},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb19-failure.png')}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.writeFileSync(path.join(out,'cwb19-browser-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
