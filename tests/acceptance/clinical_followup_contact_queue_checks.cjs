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
tmp=tempfile.TemporaryDirectory(prefix='cwb23-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb23-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb23-private-')
os.environ.update(FOLLOWUP_CONTACT_QUEUE_ENABLED='1',FOLLOWUP_CONTACT_QUEUE_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_QUEUE_ENABLED='1',FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY='1',VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OVERVIEW_ENABLED='1',FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_CONTACT_OVERVIEW_ENABLED='1',FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_CONTACTS_ENABLED='1',FOLLOWUP_CONTACTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb23-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Queue backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Queue backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1440,height:1040}});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));let acceptLeave=true;page.on('dialog',d=>acceptLeave?d.accept():d.dismiss());
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const account={email:'cwb23-'+randomUUID()+'@example.com',password:randomUUID()};
 assert((await context.request.post(API+'/auth/signup',{data:account})).ok());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill(account.email);await page.getByPlaceholder('密码',{exact:true}).fill(account.password);await button(page,'登录').click();await expect(button(page,'退出')).toBeVisible();}
 await page.goto(UI+'/followup-plans');await expect(page.getByText('请先登录后查看复查计划清单。',{exact:true})).toBeVisible();
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(r.ok(),await r.text());return r.status()===204?null:r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_contact_queue_cw_b23_cases.json','utf8'));
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()),uuid=()=>randomUUID().replaceAll('-','');
 async function planSave(cid,operation='create',row=null){
  const root=`/api/cases/${cid}/followup-plan`,l=await call('GET',root),body={request_id:uuid(),operation,plan_id:row?.id??null,expected_plan_token:row?.token||'',expected_case_token:l.case_token,expected_state_token:l.state_token,data:operation==='withdraw'?null:{...fixture[operation==='correct'?'corrected_plan':'plan'],planned_date:today},reason:operation==='create'?'':'CW23 合成来源更正'};
  const p=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:p.preview_token,reviewed:true})).plan;
 }
 async function contactSave(cid,source,data=fixture.contact){
  const root=`/api/cases/${cid}/followup-contacts`,l=await call('GET',root),p=l.plans.find(r=>r.id===source.id),body={request_id:uuid(),operation:'create',contact_id:null,expected_contact_token:'',source_plan_id:p.id,source_plan_version:p.version,expected_source_token:p.token,expected_case_token:l.case_token,expected_state_token:l.state_token,data,reason:''};
  const preview=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:preview.preview_token,reviewed:true})).record;
 }
 const cases=[];
 for(let i=0;i<23;i++){
  const species=i%2?'cat':'dog',cid=(await call('POST','/api/cases',{...fixture[species==='dog'?'case':'cat_case'],patient_name:`CW23 清单 ${i} ${species}`})).id;
  let plan=await planSave(cid),history=null,current=null;
  if(i<2){history=await contactSave(cid,plan);plan=await planSave(cid,'correct',plan);current=await contactSave(cid,plan,i===1?fixture.long_contact:fixture.contact);}
  cases.push({cid,species,plan,history,current});
 }
 let writes=0,confirms=0;const queueRequests=[];
 page.on('request',r=>{if(['POST','PUT','DELETE','PATCH'].includes(r.method())&&r.url().startsWith(API))writes++;if(r.url().endsWith('/followup-contacts/confirm')&&r.method()==='POST')confirms++;if(r.url().includes('/followup-plan-queue'))queueRequests.push(r.url());});
 async function openQueue(){await page.goto(UI+'/followup-plans');await expect(page.locator('main > ol > li')).toHaveCount(20);await page.getByLabel('显示人工随访记录',{exact:true}).check();await expect(page.getByRole('region',{name:'人工随访登记摘要'})).toHaveCount(20);}
 await page.goto(UI+'/followup-plans');await expect(page.locator('main > ol > li')).toHaveCount(20);assert(queueRequests.every(u=>!u.includes('include_followup_contacts')));
 await page.getByLabel('显示人工随访记录',{exact:true}).check();await expect(page.getByRole('region',{name:'人工随访登记摘要'})).toHaveCount(20);
 await button(page,'下一页').click();await expect(page.locator('main > ol > li')).toHaveCount(3);await button(page,'上一页').click();
 for(const [value,count] of [['current',2],['historical_only',0],['none',20],['all',20]]){const response=page.waitForResponse(r=>r.url().includes('/api/followup-plan-queue?')&&new URL(r.url()).searchParams.get('contact_state')===value);await page.getByLabel('随访登记情况',{exact:true}).selectOption(value);assert((await response).ok());await expect(page.locator('main > ol > li')).toHaveCount(count);}
 await page.getByLabel('计划日期范围',{exact:true}).selectOption('custom');await page.getByLabel('计划开始日期',{exact:true}).fill(today);await page.getByLabel('计划结束日期',{exact:true}).fill(today);await expect(page.locator('main > ol > li')).toHaveCount(20);
 assert.equal(writes,0);passed.push('explicit_default_isolation_filters_dates_paging_readonly');
 for(const item of cases.slice(0,2)){
  await openQueue();const li=page.locator('main > ol > li').filter({hasText:`CW23 清单 ${cases.indexOf(item)} ${item.species}`}).first();
  await li.getByText('展开本版计划最近联系原文',{exact:true}).click();await li.getByText('展开历史计划最近联系原文',{exact:true}).click();
  await expect(li).toContainText('来源计划已更正');assert((await li.textContent()).includes(item.current.data.note));assert((await li.textContent()).includes(item.history.source.data.purpose));
  await li.screenshot({path:path.join(out,`cwb23-${item.species}-queue-wide.png`)});await page.setViewportSize({width:390,height:844});await li.screenshot({path:path.join(out,`cwb23-${item.species}-queue-narrow.png`)});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.setViewportSize({width:1440,height:1040});
  await li.getByRole('link',{name:`回看来源计划 #${item.history.source.id} 版本 ${item.history.source.version}`,exact:true}).click();
  await expect(page.getByRole('region',{name:'人工复查计划',exact:true})).toContainText(`正在回看计划 #${item.history.source.id} 版本 ${item.history.source.version}`);
  await openQueue();await page.getByRole('link',{name:`回看随访 #${item.current.id} 版本 1`,exact:true}).click();
  const editor=page.getByRole('region',{name:'人工随访记录',exact:true}),planEditor=page.getByRole('region',{name:'人工复查计划',exact:true});
  await expect(editor).toContainText(`正在回看随访 #${item.current.id} 版本 1`);
  const beforeWrites=writes;await button(editor.getByRole('article',{name:`人工随访记录 ${item.current.id}`,exact:true}),'更正人工随访记录').click();
  await editor.getByLabel('随访记录原文',{exact:true}).fill('CW23 未保存 '+item.species);await editor.getByLabel('随访更正或撤销原因',{exact:true}).fill('合成准确定位验证');
  await button(page,'打开复查计划').click();await button(planEditor,'更正复查计划').click();await planEditor.getByLabel('复查目的',{exact:true}).fill('CW23 未保存计划');
  await button(page,'打开检验项目').click();await button(page,'录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('CW23 未保存检验');
  async function locate(){await page.evaluate(target=>{history.pushState(null,'',target);dispatchEvent(new PopStateEvent('popstate'));},`/cases/${item.cid}?followup_contact=${item.history.id}&followup_contact_version=1`);await expect(editor).toContainText(`正在回看随访 #${item.history.id} 版本 1`);}
  await locate();await expect(editor.getByLabel('随访记录原文',{exact:true})).toHaveValue('CW23 未保存 '+item.species);await expect(planEditor.getByLabel('复查目的',{exact:true})).toHaveValue('CW23 未保存计划');await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('CW23 未保存检验');assert.equal(writes,beforeWrites);
  acceptLeave=false;await page.getByRole('link',{name:'返回复查计划清单',exact:true}).click();await expect(editor).toBeVisible();acceptLeave=true;
  await button(editor,'预览并核对人工随访').click();await editor.getByLabel('已核对人工随访',{exact:true}).check();
  const confirmPattern=`**/api/cases/${item.cid}/followup-contacts/confirm`,statusPattern=`**/api/cases/${item.cid}/followup-contacts/requests/*`;
  const lost=async r=>{const response=await r.fetch();assert(response.ok(),await response.text());await r.abort('failed');},unavailable=r=>r.abort('failed');
  await context.route(confirmPattern,lost);await context.route(statusPattern,unavailable);const n=confirms;
  await button(editor,'确认保存人工随访').click();await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toBeVisible();await expect(button(editor,'核对随访保存结果')).toBeEnabled();
  await locate();await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toBeVisible();await expect(button(editor,'预览并核对人工随访')).toBeDisabled();assert.equal(confirms,n+1);await expect(button(editor,'核对随访保存结果')).toBeEnabled();
  await context.unroute(statusPattern,unavailable);await context.unroute(confirmPattern,lost);await button(editor,'核对随访保存结果').click();await expect(editor.getByRole('region',{name:'随访保存结果待核对',exact:true})).toHaveCount(0);assert.equal(confirms,n+1);
  const contacts=await call('GET',`/api/cases/${item.cid}/followup-contacts`);assert.equal(contacts.records.filter(r=>r.state==='recorded'&&r.root_id===item.current.root_id).length,1);
  await page.goto(UI+`/cases/${item.cid}?followup_contact=${item.current.id}&followup_contact_version=1`);await expect(editor).toContainText('旧版本');await expect(editor).toContainText(`正在回看随访 #${item.current.id} 版本 1`);
  await page.goto(UI+`/cases/${item.cid}?followup_contact=999999999&followup_contact_version=1`);await expect(editor).toContainText('指定随访版本当前无法读取');
  await page.goto(UI+`/cases/${item.cid}?followup_contact=2&followup_contact_version=51`);await expect(page.getByRole('alert')).toContainText('随访定位信息无效');
  saved.push({case_id:item.cid,contacts});passed.push(item.species+'_full_literal_wide_narrow_exact_sources_three_drafts_actual_lost_reply_old_missing_invalid');
 }
 await openQueue();await call('PUT','/api/cases/'+cases[0].cid,{history:'CW23 分页已变化'});await button(page,'下一页').click();await expect(page.getByText('病例、计划或日期已变化，正在重新读取第 1 页。',{exact:true})).toBeVisible();
 await page.route(API+'/api/followup-plan-queue**',r=>r.abort('failed'),{times:1});await button(page,'刷新清单').click();await expect(page.getByRole('alert')).toContainText('清单读取失败');await button(page,'重试读取清单').click();await expect(page.locator('main > ol > li')).toHaveCount(20);
 await page.evaluate(()=>dispatchEvent(new Event('blur')));await expect(page.locator('main > ol > li')).toHaveCount(0);await page.evaluate(()=>dispatchEvent(new Event('focus')));await expect(page.locator('main > ol > li')).toHaveCount(20);
 let release,arrive,done;const gate=new Promise(r=>release=r),seen=new Promise(r=>arrive=r),finished=new Promise(r=>done=r);
 await page.route(API+'/api/followup-plan-queue**',async r=>{const response=await r.fetch();arrive();await gate;await r.fulfill({response}).catch(()=>{});done();},{times:1});
 await button(page,'刷新清单').click();await seen;await page.getByLabel('显示人工随访记录',{exact:true}).uncheck();release();await finished;await expect(page.getByRole('region',{name:'人工随访登记摘要'})).toHaveCount(0);await expect(page.locator('main > ol > li')).toHaveCount(20);
 const beforeLogout=await call('GET','/api/followup-plan-queue?range=all&page_size=50&include_followup_contacts=true');delete beforeLogout.read_at;
 await page.goto(UI);await button(page,'退出').click();await login();token=await page.evaluate(()=>localStorage.getItem('token'));
 const afterLogin=await call('GET','/api/followup-plan-queue?range=all&page_size=50&include_followup_contacts=true');delete afterLogin.read_at;assert.deepEqual(afterLogin,beforeLogout);
 await openQueue();await page.evaluate(()=>{localStorage.removeItem('token');dispatchEvent(new StorageEvent('storage',{key:'token'}));});await expect(page.getByText('请先登录后查看复查计划清单。',{exact:true})).toBeVisible();await expect(page.locator('main > ol > li')).toHaveCount(0);
 passed.push('snapshot_conflict_network_focus_late_mode_and_relogin_account_isolation');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(confirms,2);
 fs.writeFileSync(path.join(out,'cwb23-browser-results.json'),JSON.stringify({status:'PASS',passed,saved,confirms,external_requests:external,page_errors:errors},null,2));console.log(JSON.stringify({status:'PASS',passed,confirms,external_requests:external,page_errors:errors},null,2));
}
main().catch(async error=>{console.error(error);if(page)await page.screenshot({path:path.join(out,'cwb23-failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));}});
