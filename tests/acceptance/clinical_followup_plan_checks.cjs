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
tmp=tempfile.TemporaryDirectory(prefix='cwb14-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb14-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb14-private-')
os.environ.update(FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb14-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Followup backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Followup backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1440,height:1000}});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await button(page,'登录').click();await expect(button(page,'退出')).toBeVisible();}
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(r.ok(),await r.text());return r.status()===204?null:r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_plans_cw_b14_cases.json','utf8'));
 let confirms=0,downloads=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/followup-plan/confirm'))confirms++;});page.on('download',()=>downloads++);
 const view=page.getByRole('region',{name:'人工复查计划',exact:true});
 async function fill(data){
  for(const [name,key] of [['计划复查日期','planned_date'],['复查目的','purpose'],['提前返回条件','return_conditions'],['复查备注','note']])await view.getByLabel(name,{exact:true}).fill(data[key]);
  await view.getByLabel('复查项目 1',{exact:true}).fill(data.items[0]);
  if(await view.getByLabel('复查项目 2',{exact:true}).count()===0)await button(view,'添加复查项目').click();
  await view.getByLabel('复查项目 2',{exact:true}).fill(data.items[1]);
 }
 async function review(){await button(view,'预览并核对复查计划').click();await expect(view.getByLabel('已核对复查计划',{exact:true})).toBeVisible();await expect(button(view,'确认保存复查计划')).toBeDisabled();await view.getByLabel('已核对复查计划',{exact:true}).check();}
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B14 合成'+species})).id;
  const root=`/api/cases/${cid}/followup-plan`;const oldCase=await call('GET',`/api/cases/${cid}`);let count=confirms;
  await page.goto(UI+'/cases/'+cid);await button(page,'打开检验项目').click();await button(page,'录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('保留旧检验草稿 '+species);
  await button(page,'打开复查计划').click();await expect(view).toContainText('尚未建立复查计划，不代表无需复查');await button(view,'新增复查计划').click();await fill(fixture.browser_plan);await review();
  if(species==='cat')await page.route(API+root+'/confirm',async r=>{const response=await r.fetch();assert(response.ok(),await response.text());await r.abort('failed');},{times:1});
  await button(view,'确认保存复查计划').evaluate(el=>{el.click();el.click();});
  await expect(view.getByRole('region',{name:'复查计划草稿',exact:true})).toHaveCount(0);assert.equal(confirms,count+1);
  const first=await call('GET',root);assert.deepEqual(first.plans[0].data,fixture.browser_plan);assert.equal(first.plans.length,1);
  assert.deepEqual(await call('GET',`/api/cases/${cid}`),oldCase);await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('保留旧检验草稿 '+species);
  await button(view,'更正复查计划').click();await fill(fixture.corrected_plan);await view.getByLabel('复查更正或撤销原因',{exact:true}).fill(fixture.correction_reason.replaceAll('\r',''));await review();
  await view.getByLabel('复查备注',{exact:true}).fill(fixture.corrected_plan.note+' changed');await expect(view.getByLabel('已核对复查计划',{exact:true})).toHaveCount(0);await fill(fixture.corrected_plan);await review();
  // Real stale case mutation; focus invalidates old review and re-reads, keeps draft.
  await call('PUT',`/api/cases/${cid}`,{history:'CW-B14 后续已保存正文'});await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await expect(view.getByLabel('已核对复查计划',{exact:true})).toHaveCount(0);await expect(view).toContainText('病例资料已变化 · 待重新核对');await expect(view.getByLabel('复查目的',{exact:true})).toHaveValue(fixture.corrected_plan.purpose);
  await review();await button(view,'确认保存复查计划').click();await expect(view.getByRole('region',{name:'复查计划草稿',exact:true})).toHaveCount(0);
  const corrected=await call('GET',root);assert.deepEqual(corrected.plans.map(p=>p.data),[fixture.browser_plan,fixture.corrected_plan]);assert.equal(corrected.plans[1].version,2);assert.equal(corrected.plans[0].state,'superseded');
  await button(view,'撤销复查计划').click();await view.getByLabel('复查更正或撤销原因',{exact:true}).fill(fixture.withdrawal_reason);await review();await button(view,'确认保存复查计划').click();await expect(view.getByRole('region',{name:'复查计划草稿',exact:true})).toHaveCount(0);
  const withdrawn=await call('GET',root);assert.equal(withdrawn.plans.length,2);assert.equal(withdrawn.plans[1].state,'withdrawn');assert.equal(withdrawn.plans[1].withdrawal.reason,fixture.withdrawal_reason);assert.equal(confirms,count+3);
  // Delayed actual preview after focus must not re-enable its stale confirmation.
  await button(view,'新增复查计划').click();await fill(fixture.browser_plan);let release,arrive;const held=new Promise(r=>release=r),started=new Promise(r=>arrive=r);
  await page.route(API+root+'/preview',async r=>{const response=await r.fetch();assert(response.ok());arrive();await held;await r.fulfill({response}).catch(()=>{});},{times:1});
  await button(view,'预览并核对复查计划').click();await started;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));release();await expect(button(view,'刷新复查计划')).toBeEnabled();await expect(view.getByLabel('已核对复查计划',{exact:true})).toHaveCount(0);assert.equal(confirms,count+3);
  await button(view,'放弃复查草稿').click();await view.screenshot({path:path.join(out,'cwb14-'+species+'-history.png')});
  await page.goto(UI);await button(page,'退出').click();await login();token=await page.evaluate(()=>localStorage.getItem('token'));await page.goto(UI+'/cases/'+cid);await button(page,'打开复查计划').click();await expect(view).toContainText('已撤销');
  assert.deepEqual(await call('GET',root),withdrawn);saved.push({case_id:cid,listing:withdrawn});passed.push(species+'_raw_create_correct_withdraw_stale_focus_relogin'+(species==='cat'?'_lost_reply':''));
 }
 assert.equal(downloads,0);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 fs.writeFileSync(path.join(out,'cwb14-browser-saved.json'),JSON.stringify({saved,confirm_posts:confirms,downloads,external_calls:0},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb14-failure.png')}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.writeFileSync(path.join(out,'cwb14-browser-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
