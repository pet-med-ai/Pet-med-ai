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
tmp=tempfile.TemporaryDirectory(prefix='cwb18-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb18-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb18-private-')
os.environ.update(FOLLOWUP_PLAN_QUEUE_ENABLED='1',FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY='1',VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OVERVIEW_ENABLED='1',FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1',FOLLOWUP_PLAN_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1',FOLLOWUP_PLANS_ENABLED='1',FOLLOWUP_PLANS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb18-backend.log'),'w');server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Queue backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Queue backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1400,height:1080}});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));let acceptLeave=true;page.on('dialog',d=>acceptLeave?d.accept():d.dismiss());
 const button=name=>page.getByRole('button',{name,exact:true});
 const account={email:'cwb18-'+require('node:crypto').randomUUID()+'@example.com',password:require('node:crypto').randomUUID()};
 assert((await context.request.post(API+'/auth/signup',{data:account})).ok());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill(account.email);await page.getByPlaceholder('密码',{exact:true}).fill(account.password);await button('登录').click();await expect(button('退出')).toBeVisible();}
 await page.goto(UI+'/followup-plans');await expect(page.getByText('请先登录后查看复查计划清单。',{exact:true})).toBeVisible();
 await login();let token=await page.evaluate(()=>localStorage.getItem('token'));
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:{Authorization:'Bearer '+token},data});assert(r.ok(),await r.text());return r.status()===204?null:r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_followup_plan_queue_cw_b18_cases.json','utf8'));
 const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 async function save(cid,operation='create',row=null,data=fixture.plan){
  const root=`/api/cases/${cid}/followup-plan`,l=await call('GET',root),body={request_id:require('node:crypto').randomUUID().replaceAll('-',''),operation,plan_id:row?.id??null,expected_plan_token:row?.token||'',expected_case_token:l.case_token,expected_state_token:l.state_token,data:operation==='withdraw'?null:{...data,planned_date:today},reason:operation==='create'?'':'CW-B18 合成更正'};
  const p=await call('POST',root+'/preview',body);return (await call('POST',root+'/confirm',{...body,preview_token:p.preview_token,reviewed:true})).plan;
 }
 const cases=[];
 for(let i=0;i<23;i++){const species=i%2?'cat':'dog',cid=(await call('POST','/api/cases',{...fixture[species==='dog'?'case':'cat_case'],patient_name:'合成清单'+i+species})).id;let row=await save(cid,'create',null,i===1?fixture.long_plan:fixture.plan);if(i===0)row=await save(cid,'correct',row);cases.push({cid,row,species});}
 let writes=0;page.on('request',r=>{if(['POST','PUT','DELETE','PATCH'].includes(r.method())&&r.url().startsWith(API))writes++;});
 await page.getByText('其他工作入口',{exact:true}).click();await page.getByRole('link',{name:'复查计划工作清单',exact:true}).click();await expect(page.getByText('上海日期 '+today+' · 共 23 个病例计划 · 第 1 页',{exact:true})).toBeVisible();
 await button('下一页').click();await expect(page.getByText('上海日期 '+today+' · 共 23 个病例计划 · 第 2 页',{exact:true})).toBeVisible();assert.equal(await page.locator('main > ol > li').count(),3);await button('上一页').click();
 await call('PUT','/api/cases/'+cases[0].cid,{history:'CW-B18 分页期间更正'});await button('下一页').click();await expect(page.getByText('病例、计划或日期已变化，正在重新读取第 1 页。',{exact:true})).toBeVisible();
 await page.getByLabel('计划有效状态',{exact:true}).selectOption('needs_review');await expect(page.locator('main > ol > li')).toHaveCount(1);await page.getByLabel('计划有效状态',{exact:true}).selectOption('all');
 for(const mode of ['next7','all','past']){await page.getByLabel('计划日期范围',{exact:true}).selectOption(mode);await expect(page.getByText('正在读取复查计划清单…',{exact:true})).toHaveCount(0);}
 await expect(page.getByText('当前筛选下没有计划记录；空清单不等于无需复查。',{exact:true})).toBeVisible();
 await page.getByLabel('计划日期范围',{exact:true}).selectOption('custom');await page.getByLabel('计划开始日期',{exact:true}).fill(today);await page.getByLabel('计划结束日期',{exact:true}).fill(today);await expect(page.locator('main > ol > li')).toHaveCount(20);
 passed.push('entry_filters_paging_stale_snapshot_reset_empty_custom');
 for(const item of cases.slice(0,2)){
  const li=page.locator('main > ol > li').filter({hasText:'病例 #'+item.cid}).first();await li.getByText('展开完整计划原文',{exact:true}).click();
  await li.screenshot({path:path.join(out,`cwb18-${item.species}-queue.png`)});
  await li.getByRole('link',{name:`打开病例 #${item.cid} 的计划 #${item.row.id} 版本 ${item.row.version}`,exact:true}).click();
  const panel=page.getByRole('region',{name:'人工复查计划',exact:true});await expect(panel).toContainText(`正在回看计划 #${item.row.id} 版本 ${item.row.version}`);
  await button('更正复查计划').click();await page.getByLabel('复查目的',{exact:true}).fill('CW-B18 未保存 '+item.species);
  await button('打开检验项目').click();await button('录入检验报告').click();await page.getByLabel('报告标题',{exact:true}).fill('CW-B18 未保存检验');
  await page.evaluate(target=>{history.pushState(null,'',target);dispatchEvent(new PopStateEvent('popstate'));},`/cases/${item.cid}?followup_plan=${item.row.id}&followup_version=${item.row.version}`);
  await expect(page.getByLabel('复查目的',{exact:true})).toHaveValue('CW-B18 未保存 '+item.species);await expect(page.getByLabel('报告标题',{exact:true})).toHaveValue('CW-B18 未保存检验');
  acceptLeave=false;await page.getByRole('link',{name:'返回复查计划清单',exact:true}).click();await expect(panel).toBeVisible();
  acceptLeave=true;await page.getByRole('link',{name:'返回复查计划清单',exact:true}).click();await expect(page.locator('main > ol > li')).toHaveCount(20);
  passed.push(item.species+'_exact_plan_independent_read_draft_preserved_leave_prompt');
 }
 await page.setViewportSize({width:390,height:844});const cat=page.locator('main > ol > li').filter({hasText:'病例 #'+cases[1].cid}).first();await cat.getByText('展开完整计划原文',{exact:true}).click();await cat.scrollIntoViewIfNeeded();assert.equal(await cat.locator('details li').count(),10);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'cwb18-long-narrow.png')});await page.setViewportSize({width:1400,height:1080});
 await page.route(API+'/api/followup-plan-queue**',r=>r.abort('failed'),{times:1});await button('刷新清单').click();await expect(page.getByRole('alert')).toContainText('清单读取失败');await button('重试读取清单').click();await expect(page.locator('main > ol > li')).toHaveCount(20);
 await page.evaluate(()=>dispatchEvent(new Event('blur')));await expect(page.locator('main > ol > li')).toHaveCount(0);await page.evaluate(()=>dispatchEvent(new Event('focus')));await expect(page.locator('main > ol > li')).toHaveCount(20);
 const dog=cases[0];await save(dog.cid,'withdraw',dog.row);await page.evaluate(()=>dispatchEvent(new Event('focus')));await expect(page.getByText('上海日期 '+today+' · 共 22 个病例计划 · 第 1 页',{exact:true})).toBeVisible();
 await page.goto(UI+`/cases/${dog.cid}?followup_plan=${dog.row.id}&followup_version=${dog.row.version}`);await expect(page.getByRole('region',{name:'人工复查计划',exact:true})).toContainText('已撤销');
 await page.goto(UI+`/cases/${dog.cid}?followup_plan=999999999&followup_version=1`);await expect(page.getByText('指定计划版本当前无法读取，请刷新核对。',{exact:true})).toBeVisible();
 await page.goto(UI+`/cases/${dog.cid}?followup_plan=1&followup_version=51`);await expect(page.getByText('计划定位信息无效，请返回清单重新打开。',{exact:true})).toBeVisible();
 await page.goto(UI+'/followup-plans');await expect(page.locator('main > ol > li')).toHaveCount(20);
 let release,arrive,done;const gate=new Promise(r=>release=r),seen=new Promise(r=>arrive=r),finished=new Promise(r=>done=r);
 await page.route(API+'/api/followup-plan-queue**',async r=>{const result=await r.fetch();arrive();await gate;await r.fulfill({response:result}).catch(()=>{});done();},{times:1});
 await button('刷新清单').click();await seen;await page.evaluate(()=>{localStorage.removeItem('token');dispatchEvent(new StorageEvent('storage',{key:'token'}));});release();await finished;await expect(page.getByText('请先登录后查看复查计划清单。',{exact:true})).toBeVisible();await expect(page.locator('main > ol > li')).toHaveCount(0);
 assert.equal(writes,0);passed.push('long_narrow_network_focus_withdrawn_missing_invalid_auth_late_get_only');
 await login();token=await page.evaluate(()=>localStorage.getItem('token'));await page.goto(UI+'/followup-plans');await expect(page.getByText('上海日期 '+today+' · 共 22 个病例计划 · 第 1 页',{exact:true})).toBeVisible();
 saved.push(await call('GET','/api/followup-plan-queue?range=all&page_size=50'));assert.equal(errors.length,0,errors.join('\n'));assert.deepEqual(external,[]);
 fs.writeFileSync(path.join(out,'cwb18-browser.json'),JSON.stringify({passed,errors,external,saved,doctor_accepted:false},null,2));console.log('CW-B18 real Chromium PASS:',passed.join('; '));
}
main().catch(error=>{console.error(error);process.exitCode=1;fs.writeFileSync(path.join(out,'cwb18-browser-failure.json'),JSON.stringify({passed,errors,external,error:String(error)},null,2));}).finally(async()=>{if(browser)await browser.close();if(server){server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));}});
