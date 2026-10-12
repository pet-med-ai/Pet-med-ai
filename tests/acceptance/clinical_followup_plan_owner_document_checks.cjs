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
tmp=tempfile.TemporaryDirectory(prefix='cwb16-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb16-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb16-private-')
os.environ.update(FOLLOWUP_PLAN_OWNER_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1',FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb16-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Plan document backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Plan document backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1500,height:1100},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const account={email:'cwb16-'+require('node:crypto').randomUUID()+'@example.com',password:require('node:crypto').randomUUID()};
 const signup=await context.request.post(API+'/auth/signup',{data:account});assert(signup.ok());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill(account.email);await page.getByPlaceholder('密码',{exact:true}).fill(account.password);await button(page,'登录').click();await expect(button(page,'退出')).toBeVisible();}
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(r.ok(),await r.text());return r.status()===204?null:r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_plan_owner_documents_cw_b16_cases.json','utf8'));
 let downloads=0,confirmPosts=0;page.on('download',()=>downloads++);page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/followup-plan/confirm'))confirmPosts++;});
 for(const species of ['dog','cat']){
  const confirmBaseline=confirmPosts;
  const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B16 合成'+species})).id,root=`/api/cases/${cid}/followup-plan`;
  const l=await call('GET',root),b={request_id:require('node:crypto').randomUUID().replaceAll('-',''),operation:'create',plan_id:null,expected_plan_token:'',expected_case_token:l.case_token,expected_state_token:l.state_token,data:fixture.plan,reason:''};
  const p=await call('POST',root+'/preview',b);let row=(await call('POST',root+'/confirm',{...b,preview_token:p.preview_token,reviewed:true})).plan;
  await page.goto(UI+'/cases/'+cid);await button(page,'打开检验项目').click();await button(page,'录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('保留旧检验草稿 '+species);
  await button(page,'打开复查计划').click();const editor=page.getByRole('region',{name:'人工复查计划',exact:true});await button(editor,'更正复查计划').click();await editor.getByLabel('复查目的',{exact:true}).fill('未保存复查编辑草稿 '+species);
  async function open(){await button(page,'导出宠主说明草稿 DOCX').click();await expect(doc).toBeVisible();await button(doc,'选择复查计划附节').click();await expect(button(selector,'将此计划纳入本次文书').last()).toBeEnabled();}
  const doc=page.getByRole('region',{name:'文书草稿内容核对',exact:true}),selector=doc.getByRole('region',{name:'选择文书复查计划',exact:true}),appendix=doc.getByRole('region',{name:'文书复查计划附节',exact:true});
  const whole=doc.getByRole('checkbox',{name:'已核对本次草稿内容（仍未签署）',exact:true});
  async function choose(){await button(selector,'将此计划纳入本次文书').click();await expect(whole).toHaveCount(0);}
  async function full(){await button(doc,'重新读取草稿').click();await expect(appendix).toBeVisible();await expect(whole).toBeEnabled();await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();}
  await open();await expect(appendix).toHaveCount(0);await expect(selector).toContainText('当前文书：宠主说明草稿');
  await expect(button(doc,'选择检验前后对照附节')).toHaveCount(0);
  const choice={id:row.id,version:row.version,token:row.token};
  const rejected=await context.request.post(API+'/api/clinical-docs/render-preview',{headers:{Authorization:'Bearer '+token},data:{case_id:cid,template_id:'owner_visit_summary_zh',manual_followup_plan:choice,manual_lab_comparison:null}});assert.equal(rejected.status(),422);
  await choose();await full();await whole.check();
  await button(doc,'关闭草稿核对').click();await button(page,'导出门诊病历草稿 DOCX').click();
  await expect(doc).toContainText('核对门诊病历草稿');await expect(appendix).toHaveCount(0);await expect(button(doc,'选择检验前后对照附节')).toBeVisible();await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();
  await button(doc,'关闭草稿核对').click();await open();await expect(appendix).toHaveCount(0);await choose();await full();
  for(const literal of [fixture.plan.planned_date,'核对复查目的 {{visit.pet_name}}','血常规 {{原文}}',row.token,'尚未签署'])await expect(appendix).toContainText(literal);
  await appendix.screenshot({path:path.join(out,`cwb16-${species}-appendix.png`)});
  await button(doc,'移除本次复查计划附节').click();await expect(whole).toHaveCount(0);await choose();await full();
  // Actual complete preview delayed until after focus invalidation.
  let release,arrive,finish;let gate=new Promise(r=>release=r),seen=new Promise(r=>arrive=r),done=new Promise(r=>finish=r);
  await page.route(API+'/api/clinical-docs/render-preview',async r=>{const response=await r.fetch();assert(response.ok());arrive();await gate;await r.fulfill({response}).catch(()=>{});finish();},{times:1});
  await button(doc,'重新读取草稿').click();await seen;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));release();await done;await expect(whole).toHaveCount(0);
  await expect(button(selector,'将此计划纳入本次文书').last()).toBeEnabled();await choose();await full();await whole.check();
  // One actual browser download; save and inspect its real DOCX bytes later.
  const baseline=await call('GET',root),oldCase=await call('GET',`/api/cases/${cid}`),count=downloads;
  const event=page.waitForEvent('download');await button(doc,'确认并下载草稿 DOCX').evaluate(el=>{el.click();el.click();});
  const download=await event;const file=path.join(out,`cwb16-${species}.docx`);await download.saveAs(file);assert.equal(downloads,count+1);assert.equal(confirmPosts,confirmBaseline);
  assert.deepEqual(await call('GET',root),baseline);assert.deepEqual(await call('GET',`/api/cases/${cid}`),oldCase);
  const {spawnSync}=require('node:child_process');const verified=spawnSync(process.env.PMAI_PYTHON||'python',['-c',`
import sys,json,zipfile,hashlib
from xml.etree import ElementTree as E
from pathlib import Path
file=Path(sys.argv[1]);fixture=json.loads(Path('tests/fixtures/clinical_followup_plan_owner_documents_cw_b16_cases.json').read_text())
w='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(file) as z:root=E.fromstring(z.read('word/document.xml'))
text='\\n'.join(''.join(n.text or '' if n.tag==w+'t' else '\\n' if n.tag==w+'br' else '\\t' if n.tag==w+'tab' else '' for n in p.iter()) for p in root.iter(w+'p'))
assert '检验前后对照附节' not in text
assert fixture['owner_document_title'] in text
for value in [fixture['plan']['planned_date'],fixture['plan']['purpose'],fixture['plan']['note'],*fixture['plan']['items'],sys.argv[2]]:assert value in text,repr(value)
print(json.dumps({'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'originals_verified':True}))
`,file,row.token],{encoding:'utf8'});assert.equal(verified.status,0,verified.stderr);
  // Actual render response held across focus must not create a second download.
  await full();await whole.check();gate=new Promise(r=>release=r);seen=new Promise(r=>arrive=r);done=new Promise(r=>finish=r);
  await page.route(API+'/api/clinical-docs/render',async r=>{const response=await r.fetch();assert(response.ok());arrive();await gate;await r.fulfill({response}).catch(()=>{});finish();},{times:1});
  await button(doc,'确认并下载草稿 DOCX').click();await seen;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));release();await done;await expect(whole).toHaveCount(0);assert.equal(downloads,count+1);
  await expect(button(selector,'将此计划纳入本次文书').last()).toBeEnabled();await button(selector,'回看此复查计划版本').click();await expect(doc).toHaveCount(0);
  await expect(editor).toContainText(`正在回看计划 #${row.id} 版本 1`);await expect(editor.getByLabel('复查目的',{exact:true})).toHaveValue('未保存复查编辑草稿 '+species);await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('保留旧检验草稿 '+species);
  // Keep a fully reviewed document while a real plan correction starts. Drop its
  // successful reply for the cat; the editor checks the actual request ledger.
  await open();await choose();await full();await whole.check();await button(doc,'收起复查计划选择').click();
  await editor.getByLabel('复查更正或撤销原因',{exact:true}).fill('CW-B16 合成更正');await button(editor,'预览并核对复查计划').click();await editor.getByLabel('已核对复查计划',{exact:true}).check();
  if(species==='dog'){
   const failedBefore=await call('GET',root);
   await page.route(API+root+'/confirm',r=>r.abort('failed'),{times:1});await button(editor,'确认保存复查计划').click();
   await expect(whole).toHaveCount(0);await expect(editor).toContainText('暂未查到该请求已提交');
   await expect(editor.getByLabel('复查目的',{exact:true})).toHaveValue('未保存复查编辑草稿 '+species);
   assert.deepEqual(await call('GET',root),failedBefore);assert.equal(confirmPosts,confirmBaseline+1);
   await button(doc,'选择复查计划附节').click();await choose();await full();await whole.check();await button(doc,'收起复查计划选择').click();
   await button(editor,'预览并核对复查计划').click();await editor.getByLabel('已核对复查计划',{exact:true}).check();
  }
  gate=new Promise(r=>release=r);seen=new Promise(r=>arrive=r);done=new Promise(r=>finish=r);
  await page.route(API+root+'/confirm',async r=>{const response=await r.fetch();assert(response.ok());arrive();await gate;if(species==='cat')await r.abort('failed');else await r.fulfill({response});finish();},{times:1});
  await button(editor,'确认保存复查计划').click();await seen;await expect(whole).toHaveCount(0);release();await done;
  await expect(editor.getByRole('region',{name:'复查计划草稿',exact:true})).toHaveCount(0);await expect(doc).toContainText('复查计划选择或病例已变化');assert.equal(confirmPosts,confirmBaseline+(species==='dog'?2:1));
  const corrected=await call('GET',root);assert.equal(corrected.plans.at(-1).version,2);row=corrected.plans.at(-1);
  await button(doc,'关闭草稿核对').click();await page.goto(UI);await button(page,'退出').click();await login();token=await page.evaluate(()=>localStorage.getItem('token'));await page.goto(UI+'/cases/'+cid);
  await open();await expect(appendix).toHaveCount(0);assert.equal(await selector.getByRole('button',{name:'将此计划纳入本次文书',exact:true}).count(),2);
  const buttons=selector.getByRole('button',{name:'将此计划纳入本次文书',exact:true});await expect(buttons.first()).toBeDisabled();await buttons.last().click();await full();await expect(appendix).toContainText('版本 2');
  saved.push({case_id:cid,listing:corrected,download:JSON.parse(verified.stdout)});passed.push(species+'_select_clear_raw_docx_double_click_stale_preview_download_exact_source_preserved_drafts_relogin'+(species==='cat'?'_lost_save_reply':'_failed_save_not_committed'));
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,2);assert.equal(confirmPosts,3);
 fs.writeFileSync(path.join(out,'cwb16-browser-saved.json'),JSON.stringify({saved,downloads,confirm_posts:confirmPosts,external_calls:0},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb16-failure.png')}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.writeFileSync(path.join(out,'cwb16-browser-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
