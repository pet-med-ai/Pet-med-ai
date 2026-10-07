// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb11-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb11-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb11-only',ENVIRONMENT='test',RENDER='false')
sys.path[:]=[str(Path('backend').resolve())]+[p for p in sys.path if Path(p or '.').resolve()!=Path('.').resolve()]
def guard(event,args):
    if event in {'socket.connect','socket.connect_ex','socket.bind'} and isinstance(args[1],tuple):
        assert args[1][0] in {'127.0.0.1','::1'} and args[1][1]==18026
    if event=='socket.getaddrinfo':assert args[0] in {'127.0.0.1','localhost','::1',None}
sys.addaudithook(guard)
import main,db,models
db.Base.metadata.create_all(db.engine)
from fastapi.testclient import TestClient
with TestClient(main.app) as client:
    assert client.post('/auth/signup',json={'email':'browser-owner@example.com','password':'Synthetic-PR26-only-20260916'}).status_code==200
`:`
import sys
sys.path.insert(0,'tests/acceptance')
import fixture as f
main=f.main
`;
const boot=prefix+`
import os,tempfile
from pathlib import Path
private=tempfile.TemporaryDirectory(prefix='cwb11-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_LAB_DOCUMENTS_ENABLED='1',MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1',VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',LAB_RANGE_REVIEW_ENABLED='1',LAB_RANGE_REVIEW_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb11-backend.log'),'w');server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Range backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Range backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1500,height:1100},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();
 const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:auth,data});assert(r.ok(),await r.text());return r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_lab_range_review_cw_b11_cases.json','utf8'));
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const view=page.getByRole('region',{name:'检验结果区间核对',exact:true}),lab=page.getByRole('region',{name:'检验项目人工录入',exact:true});
 const results=[];let writes=[],downloads=0,confirms=0;
 const watch=r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(r.url());};
 page.on('download',()=>downloads++);page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/manual-lab/confirm'))confirms++;});
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B11合成'+species})).id;
  const files=`/api/cases/${cid}/attachments`,root=`/api/cases/${cid}/manual-lab`,url=`/api/cases/${cid}/lab-range-review`;
  const bytes=fs.readFileSync(path.join(temp,'synthetic.pdf'));
  const r=await context.request.post(API+files+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':'application/pdf','X-Attachment-Filename':'synthetic.pdf','X-Case-Token':(await call('GET',files)).case_token},data:bytes});assert(r.ok(),await r.text());
  const item=(await r.json()).attachment;
  async function sourceOp(operation,title){
   const b={request_id:randomUUID().replaceAll('-',''),attachment_id:item.id,operation,expected_case_token:(await call('GET',files)).case_token,metadata:{title,kind:'lab',taken_at:'',reported_at:'',source:'',note:''},reason:operation==='confirm'?'':'合成来源核对'};
   const p=await call('POST',files+'/preview',b);return call('POST',files+'/confirm',{...b,preview_token:p.preview_token,reviewed:true});
  }
  await sourceOp('confirm','合成区间原件');
  const b={request_id:randomUUID().replaceAll('-',''),attachment_id:item.id,operation:'create',expected_case_token:(await call('GET',root)).case_token,report_id:null,expected_report_token:'',data:fixture.data,reason:''};
  const p=await call('POST',root+'/preview',b);let saved=(await call('POST',root+'/confirm',{...b,preview_token:p.preview_token,reviewed:true})).report;
  await page.goto(UI+'/cases/'+cid);writes=[];page.on('request',watch);const beforeDownloads=downloads;
  await button(page,'打开检验结果区间核对').click();await expect(view).toContainText('CW-B11合成'+species);
  await expect(view).toContainText('区间外 '+fixture.review.counts.out_of_range);await expect(view).toContainText('0.10000000000000000000000000001');
  await expect(view).toContainText('2.001e-8');await expect(view).toContainText('2026-10-07T09:30:00+08:00');await expect(view).toContainText(item.sha256);
  await expect(view.locator('tbody tr')).toHaveCount(fixture.data.items.length);
  for(const [filter,count] of [['out',fixture.review.counts.out_of_range],['unable',fixture.review.counts.unable],['all',fixture.data.items.length]]){
   await view.getByLabel('检验区间项目筛选',{exact:true}).selectOption(filter);await expect(view.locator('tbody tr')).toHaveCount(count);
  }
  await view.screenshot({path:path.join(out,'cwb11-'+species+'-range.png')});
  await button(view,`回看检验记录 #${saved.id} 版本 1`).click();const record=lab.getByRole('article',{name:'检验记录 '+saved.id,exact:true});
  await expect(record.locator('details')).toHaveAttribute('open','');await expect(record).toBeFocused();
  assert.deepEqual(writes,[]);assert.equal(downloads,beforeDownloads);page.off('request',watch);
  passed.push(species+'_saved_decimal_matrix_filters_exact_navigation_no_write_no_auto_download');
  const downloading=page.waitForEvent('download');await button(record,'打开该记录原件').click();const download=await downloading;
  const target=path.join(out,'cwb11-'+species+'-explicit-original.pdf');await download.saveAs(target);
  assert.equal(createHash('sha256').update(fs.readFileSync(target)).digest('hex'),item.sha256);assert.equal(download.suggestedFilename(),'synthetic.pdf');assert.equal(downloads,beforeDownloads+1);
  passed.push(species+'_explicit_source_download_exact_sha256');
  await button(lab,'录入检验报告').click();await lab.getByLabel('报告标题',{exact:true}).fill('保留未保存区间核对草稿');
  await button(view,`回看检验记录 #${saved.id} 版本 1`).click();await expect(lab.getByLabel('报告标题',{exact:true})).toHaveValue('保留未保存区间核对草稿');
  await button(lab,'放弃本页检验草稿').click();
  await button(page,'打开就诊资料总览').click();await button(page,'核对门诊病历草稿').click();
  const doc=page.getByRole('region',{name:'文书草稿内容核对',exact:true});await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();
  await doc.getByRole('checkbox',{name:'已核对本次草稿内容（仍未签署）'}).check();
  await expect(button(doc,'确认并下载草稿 DOCX')).toBeEnabled();
  await button(record,'更正检验记录').click();await lab.getByLabel('报告标题',{exact:true}).fill('合成区间更正版本');await lab.getByLabel('项目 1 结果原文',{exact:true}).fill('1.500');
  await lab.getByLabel('更正或撤销原因',{exact:true}).fill('合成区间更正验收');
  for(let n=1;n<=fixture.data.items.length;n++)await lab.getByLabel('已核对项目 '+n,{exact:true}).check();
  await button(lab,'核对整份检验记录').click();await lab.getByLabel('已核对整份检验记录',{exact:true}).check();
  const beforeConfirms=confirms,pattern='**/cases/'+cid+'/manual-lab/confirm';
  if(species==='cat')await page.route(pattern,async route=>{const response=await route.fetch();assert.equal(response.status(),200);await route.abort('failed');});
  await button(lab,'确认保存检验记录').click();await expect(lab).toContainText(species==='cat'?'已回读保存结果，未重复提交。':'检验记录已保存。');
  if(species==='cat')await page.unroute(pattern);assert.equal(confirms,beforeConfirms+1);
  await expect(view).toContainText('合成区间更正版本');await expect(view).toContainText('区间外 '+(fixture.review.counts.out_of_range-1));await expect(view).toContainText('旧版本');
  await expect(button(doc,'确认并下载草稿 DOCX')).toHaveCount(0);await button(doc,'关闭草稿核对').click();
  const result=await call('GET',url);assert.equal(result.counts.reports,1);assert.equal(result.reports[0].items[0].value,'1.500');assert.equal(result.reports[0].version,2);
  saved=(await call('GET',root)).reports.find(x=>x.version===2);
  passed.push(species+'_whole_review_correction_'+(species==='cat'?'lost_reply_readback':'save_feedback')+'_refresh_and_document_invalidation');
  // A source metadata change invalidates the result instead of silently reusing it.
  await sourceOp('update','合成来源已更正');
  await button(view,`回看检验记录 #${saved.id} 版本 2`).click();await expect(lab).toContainText('版本或状态已变化，未替换为其他记录');
  await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await expect(view).toContainText('当前报告 0');await expect(view).toContainText('需重新核对');
  await button(view,`回看检验记录 #${saved.id} 版本 2`).click();
  const corrected=lab.getByRole('article',{name:'检验记录 '+saved.id,exact:true});
  await button(corrected,'撤销检验记录').click();await lab.getByLabel('更正或撤销原因',{exact:true}).fill('合成撤销');
  await button(lab,'核对整份检验记录').click();await lab.getByLabel('已核对整份检验记录',{exact:true}).check();await button(lab,'确认保存检验记录').click();
  await expect(view).toContainText('已撤销');await expect(view).toContainText('当前报告 0');
  assert.equal(downloads,beforeDownloads+1);await view.screenshot({path:path.join(out,'cwb11-'+species+'-excluded.png')});
  results.push({case_id:cid,species,review:await call('GET',url)});passed.push(species+'_source_change_and_withdrawal_excluded_without_automatic_export');
 }
 const otherEmail='cwb11-other-'+randomUUID()+'@example.com';assert((await context.request.post(API+'/auth/signup',{data:{email:otherEmail,password:'Synthetic-PR26-only-20260916'}})).ok());
 const otherLogin=await context.request.post(API+'/auth/login',{form:{username:otherEmail,password:'Synthetic-PR26-only-20260916'}});assert(otherLogin.ok());const otherToken=(await otherLogin.json()).access_token;
 const cid=results[0].case_id;
 for(const scenario of ['case','account','focus']){
  await page.evaluate(t=>localStorage.setItem('token',t),auth.Authorization.slice(7));await page.goto(UI+'/cases/'+cid);
  let ready,release,finished,held=false;const seen=new Promise(r=>ready=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r),pattern='**/cases/'+cid+'/lab-range-review';
  await page.route(pattern,async route=>{if(held){await route.continue();return;}held=true;try{const response=await route.fetch();assert.equal(response.status(),200);ready();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(page,'打开检验结果区间核对').click();await seen;
  if(scenario==='case')await page.goto(UI+'/cases/'+results[1].case_id);
  else if(scenario==='account')await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);
  else{await call('PUT','/api/cases/'+cid,{patient_name:'区间焦点新快照'});await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(view).toContainText('区间焦点新快照');}
  release();await done;await page.unroute(pattern);
  if(scenario==='focus'){await expect(view).toContainText('区间焦点新快照');await expect(view).not.toContainText('CW-B11合成dog');}else await expect(view).toHaveCount(0);
  passed.push('late_range_response_discarded_after_'+scenario);
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,2);
 fs.writeFileSync(path.join(out,'cwb11-browser-saved.json'),JSON.stringify({results,external_calls:0,explicit_downloads:downloads},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb11-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb11-range-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
