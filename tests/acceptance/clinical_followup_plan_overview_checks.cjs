// Real Chromium, JWT, app and database. Faults cover no-commit and lost actual replies.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const passed=[],errors=[],external=[],saved=[];let browser,page,server;
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb17-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb17-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb17-private-')
os.environ.update(VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OVERVIEW_ENABLED='1',FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1',FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb17-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Overview backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Overview backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1400,height:1080},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const account={email:'cwb17-'+require('node:crypto').randomUUID()+'@example.com',password:require('node:crypto').randomUUID()};
 assert((await context.request.post(API+'/auth/signup',{data:account})).ok());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill(account.email);await page.getByPlaceholder('密码',{exact:true}).fill(account.password);await button(page,'登录').click();await expect(button(page,'退出')).toBeVisible();}
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(r.ok(),await r.text());return r.status()===204?null:r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_plan_overview_cw_b17_cases.json','utf8'));
 let downloads=0,confirmPosts=0;page.on('download',()=>downloads++);page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/followup-plan/confirm'))confirmPosts++;});
 const view=page.getByRole('region',{name:'就诊资料总览',exact:true}),group=view.getByRole('region',{name:'复查计划资料状态',exact:true});
 const editor=page.getByRole('region',{name:'人工复查计划',exact:true});
 for(const species of ['dog','cat']){
  const confirmBaseline=confirmPosts;
  const cid=(await call('POST','/api/cases',{...fixture[species==='dog'?'case':'cat_case']})).id,root=`/api/cases/${cid}/followup-plan`;
  async function save(operation='create',row=null,data=fixture.plan){
   const l=await call('GET',root),body={request_id:require('node:crypto').randomUUID().replaceAll('-',''),operation,plan_id:row?.id??null,expected_plan_token:row?.token||'',expected_case_token:l.case_token,expected_state_token:l.state_token,data:operation==='withdraw'?null:data,reason:operation==='create'?'':'合成更正或撤销原文'};
   const p=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:p.preview_token,reviewed:true})).plan;
  }
  let row=await save();await page.goto(UI+'/cases/'+cid);
  await expect(view).toHaveCount(0);await button(page,'打开检验项目').click();await button(page,'录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('保留检验草稿 '+species);
  await button(page,'打开复查计划').click();await button(editor,'更正复查计划').click();await editor.getByLabel('复查目的',{exact:true}).fill('未保存计划原文 '+species);
  await button(page,'打开就诊资料总览').click();await expect(group).toContainText('2028-02-29');await expect(group).toContainText('计划不代表已复查');
  await group.getByText('查看复查计划原文',{exact:true}).click();await expect(group).toContainText('复查总览原文 {{visit.pet_name}}');
  await group.screenshot({path:path.join(out,`cwb17-${species}-saved.png`)});
  await button(group,`回看计划 #${row.id} 版本 ${row.version}`).click();await expect(editor).toContainText(`正在回看计划 #${row.id} 版本 ${row.version}`);
  await expect(editor.getByLabel('复查目的',{exact:true})).toHaveValue('未保存计划原文 '+species);await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('保留检验草稿 '+species);
  await button(page,'收起就诊资料总览').click();await button(page,'打开就诊资料总览').click();await expect(group).toBeVisible();
  await button(view,'核对宠主说明草稿').click();const doc=page.getByRole('region',{name:'文书草稿内容核对',exact:true});
  await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();await expect(doc.getByRole('region',{name:'文书复查计划附节',exact:true})).toHaveCount(0);await button(doc,'关闭草稿核对').click();
  await editor.getByLabel('复查更正或撤销原因',{exact:true}).fill('CW-B17 浏览器合成更正');
  async function review(){await button(editor,'预览并核对复查计划').click();await editor.getByLabel('已核对复查计划',{exact:true}).check();}
  await review();
  if(species==='dog'){
   await page.route(API+root+'/confirm',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'synthetic_no_commit'})}),{times:1});
   await button(editor,'确认保存复查计划').click();await expect(editor).toContainText('暂未查到该请求已提交');
   await expect(button(group,`回看计划 #${row.id} 版本 1`)).toBeVisible();assert.equal((await call('GET',root)).plans.length,1);
   await expect(editor.getByLabel('复查目的',{exact:true})).toHaveValue('未保存计划原文 '+species);await review();
  }
  let release,arrive,finish;const gate=new Promise(r=>release=r),seen=new Promise(r=>arrive=r),done=new Promise(r=>finish=r);
  await page.route(API+root+'/confirm',async r=>{const response=await r.fetch();assert(response.ok());arrive();await gate;if(species==='cat')await r.abort('failed');else await r.fulfill({response});finish();},{times:1});
  await button(editor,'确认保存复查计划').click();await seen;await expect(group).toHaveCount(0);release();await done;
  await expect(editor.getByRole('region',{name:'复查计划草稿',exact:true})).toHaveCount(0);
  const listing=await call('GET',root);assert.equal(listing.plans.length,2);row=listing.plans.at(-1);
  await expect(button(group,`回看计划 #${row.id} 版本 2`)).toBeVisible();assert.equal(confirmPosts-confirmBaseline,species==='dog'?2:1);
  await button(group,`回看计划 #${row.id} 版本 2`).click();await expect(editor).toContainText(`正在回看计划 #${row.id} 版本 2`);
  await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('保留检验草稿 '+species);
  await call('PUT','/api/cases/'+cid,{history:'CW-B17 更正病史'});await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(group).toContainText('病例资料已变化');
  row=await save('withdraw',row);await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(group).toContainText('已撤销');
  row=await save('create',null,fixture.short_plan);await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(button(group,`回看计划 #${row.id} 版本 1`)).toBeVisible();
  if(species==='dog'){
   for(let i=0;i<47;i++)row=await save('correct',row,i===46?fixture.long_plan:fixture.short_plan);
   await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(group.getByRole('article')).toHaveCount(50);
   await page.setViewportSize({width:390,height:844});const last=group.getByRole('article').last();await last.getByText('查看复查计划原文',{exact:true}).click();await last.scrollIntoViewIfNeeded();
   assert.equal(await last.locator('li').count(),10);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
   await page.screenshot({path:path.join(out,'cwb17-50-versions-long-narrow.png')});await page.setViewportSize({width:1400,height:1080});
  }
  const expected=await call('GET',`/api/cases/${cid}/visit-overview?include_followup_plan=true`);saved.push({case_id:cid,overview:expected});
  passed.push(species+'_exact_version_preserved_drafts_independent_refresh_'+(species==='dog'?'failed_save_50_versions_narrow':'lost_committed_reply'));
  await page.goto(UI);await button(page,'退出').click();await login();token=await page.evaluate(()=>localStorage.getItem('token'));
  await page.goto(UI+'/cases/'+cid);await button(page,'打开就诊资料总览').click();await expect(button(group,`回看计划 #${row.id} 版本 ${row.version}`)).toBeVisible();
  // Hold an authenticated old overview while navigating away; it cannot leak back.
  let releaseRead,readSeen,readDone;const held=new Promise(r=>releaseRead=r),ready=new Promise(r=>readSeen=r),finished=new Promise(r=>readDone=r);
  await page.route(url=>url.pathname===`/api/cases/${cid}/visit-overview`,async r=>{const response=await r.fetch();assert(response.ok());readSeen();await held;await r.fulfill({response}).catch(()=>{});readDone();},{times:1});
  await button(view,'刷新就诊资料总览').click();await ready;await page.goto(UI);releaseRead();await finished;await expect(view).toHaveCount(0);
  passed.push(species+'_fresh_login_readback_and_late_response_navigation');
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,0);assert.equal(confirmPosts,3);
 fs.writeFileSync(path.join(out,'cwb17-browser-saved.json'),JSON.stringify({saved,downloads,confirm_posts:confirmPosts,external_calls:0},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb17-failure.png')}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.writeFileSync(path.join(out,'cwb17-browser-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
