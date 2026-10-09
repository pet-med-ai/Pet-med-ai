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
tmp=tempfile.TemporaryDirectory(prefix='cwb22-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb22-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb22-private-')
os.environ.update(FOLLOWUP_CONTACT_OWNER_DOCUMENTS_ENABLED='1',FOLLOWUP_CONTACT_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1',FOLLOWUP_CONTACT_DOCUMENTS_ENABLED='1',FOLLOWUP_CONTACT_DOCUMENTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_DOCUMENTS_SYNTHETIC_ONLY='1',VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OVERVIEW_ENABLED='1',FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_CONTACT_OVERVIEW_ENABLED='1',FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_CONTACTS_ENABLED='1',FOLLOWUP_CONTACTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb22-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Overview backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Overview backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1500,height:1100},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const account={email:'cwb22-'+randomUUID()+'@example.com',password:randomUUID()};
 assert((await context.request.post(API+'/auth/signup',{data:account})).ok());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill(account.email);await page.getByPlaceholder('密码',{exact:true}).fill(account.password);await button(page,'登录').click();await expect(button(page,'退出')).toBeVisible();}
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const response=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(response.ok(),await response.text());return response.status()===204?null:response.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_contact_owner_documents_cw_b22_cases.json','utf8'));
 const uuid=()=>randomUUID().replaceAll('-','');
 async function planSave(cid,operation='create',row=null){
  const root=`/api/cases/${cid}/followup-plan`,listing=await call('GET',root);
  const body={request_id:uuid(),operation,plan_id:row?.id??null,expected_plan_token:row?.token||'',expected_case_token:listing.case_token,expected_state_token:listing.state_token,
   data:operation==='withdraw'?null:fixture[operation==='correct'?'corrected_plan':'plan'],reason:operation==='create'?'':'CW-B22 合成来源更正'};
  const preview=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:preview.preview_token,reviewed:true})).plan;
 }
 async function contactSave(cid,source,operation='create',row=null,data=fixture.contact){
  const root=`/api/cases/${cid}/followup-contacts`,listing=await call('GET',root),plan=listing.plans.find(p=>p.id===(row?.source.id||source.id));
  const body={request_id:uuid(),operation,contact_id:row?.id??null,expected_contact_token:row?.token||'',source_plan_id:plan.id,source_plan_version:plan.version,
   expected_source_token:plan.token,expected_case_token:listing.case_token,expected_state_token:listing.state_token,data:operation==='withdraw'?null:data,
   reason:operation==='create'?'':fixture[operation==='withdraw'?'withdrawal_reason':'correction_reason']};
  const preview=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:preview.preview_token,reviewed:true})).record;
 }
 let downloads=0,confirms=0;
 page.on('download',()=>downloads++);page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/followup-contacts/confirm'))confirms++;});
 const doc=page.getByRole('region',{name:'文书草稿内容核对',exact:true});
 const selector=doc.getByRole('region',{name:'选择文书人工随访',exact:true});
 const appendix=doc.getByRole('region',{name:'文书人工随访附节',exact:true});
 const whole=doc.getByRole('checkbox',{name:'已核对本次草稿内容（仍未签署）',exact:true});
 const editor=page.getByRole('region',{name:'人工随访记录',exact:true});
 const planEditor=page.getByRole('region',{name:'人工复查计划',exact:true});
 async function open(){await button(page,'导出宠主说明草稿 DOCX').click();await expect(doc).toBeVisible();await button(doc,'选择人工随访记录附节').click();await expect(button(selector,'将此随访纳入本次文书').last()).toBeEnabled();}
 async function choose(){await button(selector,'将此随访纳入本次文书').last().click();await expect(whole).toHaveCount(0);}
 async function full(){await button(doc,'重新读取草稿').click();await expect(appendix).toBeVisible();await expect(whole).toBeEnabled();await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();}
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',fixture[species==='dog'?'case':'cat_case'])).id;
  let source=await planSave(cid),row=await contactSave(cid,source);
  const root=`/api/cases/${cid}/followup-contacts`;
  await page.goto(UI+'/cases/'+cid);
  await button(page,'打开检验项目').click();await button(page.getByRole('region',{name:'检验项目人工录入',exact:true}),'录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('CW22 未保存检验 '+species);
  await button(page,'打开复查计划').click();await button(planEditor,'更正复查计划').click();await planEditor.getByLabel('复查目的',{exact:true}).fill('CW22 未保存计划 '+species);
  await button(page,'打开人工随访记录').click();await button(editor.getByRole('article',{name:`人工随访记录 ${row.id}`,exact:true}),'更正人工随访记录').click();
  await editor.getByLabel('随访记录原文',{exact:true}).fill('CW22 未保存联系 '+species);await editor.getByLabel('随访更正或撤销原因',{exact:true}).fill('CW22 合成更正');
  await open();await expect(appendix).toHaveCount(0);await expect(selector).toContainText('内部备注或旧身份');await choose();await full();await expect(appendix).toContainText('是否适合出示给宠主');
  const values=await appendix.locator('dd').allTextContents();for(const v of [fixture.contact.note,fixture.contact.next_action,fixture.plan.purpose])assert(values.includes(v),v);
  for(const v of [row.token,source.data.planned_date,'历史原文','尚未签署','当前病例身份','联系登记时身份','来源计划保存时身份'])await expect(appendix).toContainText(v);
  await appendix.screenshot({path:path.join(out,`cwb22-${species}-appendix-wide.png`)});
  await page.setViewportSize({width:390,height:844});await appendix.screenshot({path:path.join(out,`cwb22-${species}-appendix-narrow.png`)});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.setViewportSize({width:1500,height:1100});
  passed.push(species+'_default_explicit_literal_source_identity_wide_narrow');
  await button(doc,'移除本次人工随访附节').click();await expect(whole).toHaveCount(0);await choose();await full();
  // Hold an actual complete preview, then invalidate it before it returns.
  let release,arrive,finish,gate,seen,done;
  function latch(){gate=new Promise(r=>release=r);seen=new Promise(r=>arrive=r);done=new Promise(r=>finish=r);}
  latch();await page.route(API+'/api/clinical-docs/render-preview',async r=>{try{const response=await r.fetch();assert(response.ok());arrive();await gate;await r.fulfill({response}).catch(()=>{});}finally{finish();}},{times:1});
  await button(doc,'重新读取草稿').click();await seen;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));release();await done;await expect(whole).toHaveCount(0);
  await expect(button(selector,'将此随访纳入本次文书').last()).toBeEnabled();await choose();await full();await whole.check();
  const before=await call('GET',root),caseBefore=await call('GET',`/api/cases/${cid}`),planBefore=await call('GET',`/api/cases/${cid}/followup-plan`),count=downloads,confirmed=confirms;
  const waiting=page.waitForEvent('download');await button(doc,'确认并下载草稿 DOCX').evaluate(el=>{el.click();el.click();});const download=await waiting;
  const file=path.join(out,`cwb22-${species}.docx`);await download.saveAs(file);assert.equal(downloads,count+1);assert.equal(confirms,confirmed);
  assert.deepEqual(await call('GET',root),before);assert.deepEqual(await call('GET',`/api/cases/${cid}`),caseBefore);assert.deepEqual(await call('GET',`/api/cases/${cid}/followup-plan`),planBefore);
  const verified=require('node:child_process').spawnSync(process.env.PMAI_PYTHON||'python',['-c',`
import sys,json,zipfile,hashlib
from xml.etree import ElementTree as E
from pathlib import Path
file=Path(sys.argv[1]);fixture=json.loads(Path('tests/fixtures/clinical_followup_contact_owner_documents_cw_b22_cases.json').read_text())
w='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(file) as z:root=E.fromstring(z.read('word/document.xml'))
text='\\n'.join(''.join(n.text or '' if n.tag==w+'t' else '\\n' if n.tag==w+'br' else '\\t' if n.tag==w+'tab' else '' for n in p.iter()) for p in root.iter(w+'p'))
for value in [fixture['contact']['note'],fixture['contact']['next_action'],fixture['contact']['occurred_at'],fixture['plan']['purpose'],fixture['plan']['note'],*fixture['plan']['items'],sys.argv[2]]:assert value in text,repr(value)
assert '尚未签署' in text and '历史原文' in text
assert 'clinical-followup-contact-owner-documents-cw-b22-v1' in text and '是否适合出示给宠主' in text
print(json.dumps({'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'literal_originals':True}))
`,file,row.token],{encoding:'utf8'});assert.equal(verified.status,0,verified.stderr);
  await full();await whole.check();latch();await page.route(API+'/api/clinical-docs/render',async r=>{try{const response=await r.fetch();assert(response.ok());arrive();await gate;await r.fulfill({response}).catch(()=>{});}finally{finish();}},{times:1});
  await button(doc,'确认并下载草稿 DOCX').click();await seen;await page.evaluate(()=>window.dispatchEvent(new Event('focus')));release();await done;await expect(whole).toHaveCount(0);assert.equal(downloads,count+1);
  passed.push(species+'_remove_full_review_readonly_actual_docx_double_click_late_preview_download');
  await expect(button(selector,'回看此随访版本').last()).toBeEnabled();await button(selector,'回看此随访版本').last().click();await expect(doc).toHaveCount(0);await expect(editor).toContainText(`正在回看随访 #${row.id} 版本 1`);
  await open();await button(selector,'回看此随访来源计划').last().click();await expect(doc).toHaveCount(0);await expect(planEditor).toContainText(`正在回看计划 #${source.id} 版本 1`);
  await expect(editor.getByLabel('随访记录原文',{exact:true})).toHaveValue('CW22 未保存联系 '+species);await expect(planEditor.getByLabel('复查目的',{exact:true})).toHaveValue('CW22 未保存计划 '+species);await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('CW22 未保存检验 '+species);
  passed.push(species+'_exact_contact_source_navigation_preserves_three_drafts');
  await open();await choose();await full();await whole.check();await button(doc,'收起人工随访选择').click();
  await editor.getByLabel('随访记录原文',{exact:true}).fill(species==='cat'?fixture.long_contact.note:fixture.corrected.note);
  await button(editor,'预览并核对人工随访').click();await editor.getByLabel('已核对人工随访',{exact:true}).check();
  const confirmPattern=`**/api/cases/${cid}/followup-contacts/confirm`,statusPattern=`**/api/cases/${cid}/followup-contacts/requests/*`;
  const lost=async r=>{const response=await r.fetch();assert(response.ok(),await response.text());await r.abort('failed');};const unavailable=r=>r.abort('failed');
  if(species==='cat'){await context.route(confirmPattern,lost);await context.route(statusPattern,unavailable);}
  const oldConfirms=confirms;await button(editor,'确认保存人工随访').click();await expect(whole).toHaveCount(0);
  if(species==='cat'){
   await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toBeVisible();
   await button(doc,'选择人工随访记录附节').click();await expect(button(selector,'回看此随访版本').first()).toBeEnabled();await button(selector,'回看此随访版本').first().click();
   await expect(editor).toContainText(`正在回看随访 #${row.id} 版本 1`);await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toBeVisible();await expect(button(editor,'预览并核对人工随访')).toBeDisabled();
   await context.unroute(statusPattern,unavailable);await context.unroute(confirmPattern,lost);await button(editor,'核对随访保存结果').click();await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toHaveCount(0);
  }else{await expect(editor.getByRole('region',{name:'人工随访草稿',exact:true})).toHaveCount(0);await button(doc,'关闭草稿核对').click();}
  assert.equal(confirms,oldConfirms+1);row=(await call('GET',root)).records.at(-1);assert.equal(row.version,2);
  // The contact remains valid when its old source is corrected or withdrawn.
  source=await planSave(cid,species==='dog'?'withdraw':'correct',source);await open();await choose();await full();await expect(appendix).toContainText(species==='dog'?'来源计划已撤销':'来源计划已更正');
  assert((await appendix.locator('dd').allTextContents()).includes(fixture.plan.purpose));
  await whole.check();await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));await expect(whole).toHaveCount(0);
  await expect(button(selector,'将此随访纳入本次文书').last()).toBeEnabled();await choose();await full();await whole.check();await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await expect(whole).toHaveCount(0);
  await button(doc,'关闭草稿核对').click();await button(page,'导出门诊病历草稿 DOCX').click();await expect(doc).toBeVisible();await expect(button(doc,'选择人工随访记录附节')).toBeVisible();await expect(appendix).toHaveCount(0);await expect(whole).not.toBeChecked();await button(doc,'关闭草稿核对').click();
  passed.push(species+'_closed_selector_write_invalidation_historical_source_visibility_blur_template'+(species==='cat'?'_lost_reply_unknown_navigation_no_repeat':''));
  saved.push({case_id:cid,contacts:await call('GET',root),download:JSON.parse(verified.stdout)});
 }
 await page.goto(UI);await button(page,'退出').click();await login();token=await page.evaluate(()=>localStorage.getItem('token'));
 for(const item of saved){assert.deepEqual(await call('GET',`/api/cases/${item.case_id}/followup-contacts`),item.contacts);await page.goto(UI+'/cases/'+item.case_id);await open();await expect(appendix).toHaveCount(0);await expect(button(selector,'将此随访纳入本次文书').first()).toBeDisabled();await choose();await full();await expect(appendix).toContainText('版本 2');}
 const other={email:'cwb22-other-'+randomUUID()+'@example.com',password:randomUUID()};assert((await context.request.post(API+'/auth/signup',{data:other})).ok());
 const auth=await context.request.post(API+'/auth/login',{form:{username:other.email,password:other.password}});assert(auth.ok());const otherToken=(await auth.json()).access_token;
 await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);await expect(doc).toHaveCount(0);await expect(page.getByText(fixture.cat_case.patient_name,{exact:true})).toHaveCount(0);
 passed.push('relogin_exact_saved_readback_case_and_account_isolation');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,2);assert.equal(confirms,2);
 const result={status:'PASS',passed,saved,confirms,downloads,external_calls:0,external_requests:external,page_errors:errors,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'};
 fs.writeFileSync(path.join(out,'cwb22-browser-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({...result,saved:undefined},null,2));
}
main().catch(async error=>{console.error(error);if(page)await page.screenshot({path:path.join(out,'cwb22-failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>server.once('exit',resolve));}});
