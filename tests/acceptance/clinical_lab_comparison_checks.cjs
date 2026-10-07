// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb12-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb12-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb12-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb12-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_LAB_DOCUMENTS_ENABLED='1',MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1',VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1',LAB_RANGE_REVIEW_ENABLED='1',LAB_RANGE_REVIEW_SYNTHETIC_ONLY='1',LAB_COMPARISON_ENABLED='1',LAB_COMPARISON_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb12-backend.log'),'w');server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Comparison backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Comparison backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1500,height:1100},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();
 const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:auth,data});assert(r.ok(),await r.text());return r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_lab_comparison_cw_b12_cases.json','utf8'));
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const view=page.getByRole('region',{name:'同次就诊检验前后对照',exact:true}),lab=page.getByRole('region',{name:'检验项目人工录入',exact:true});
 const results=[];let writes=[],downloads=0,confirms=0;
 const watch=r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(r.url());};
 page.on('download',()=>downloads++);page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/manual-lab/confirm'))confirms++;});
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B12合成'+species})).id;
  const files=`/api/cases/${cid}/attachments`,root=`/api/cases/${cid}/manual-lab`,url=`/api/cases/${cid}/lab-comparison`;
  const sources=[],rows=[];
  async function sourceOp(item,operation,title){
   const b={request_id:randomUUID().replaceAll('-',''),attachment_id:item.id,operation,expected_case_token:(await call('GET',files)).case_token,metadata:{title,kind:'lab',taken_at:'',reported_at:'',source:'',note:''},reason:operation==='confirm'?'':'合成来源核对'};
   const p=await call('POST',files+'/preview',b);return call('POST',files+'/confirm',{...b,preview_token:p.preview_token,reviewed:true});
  }
  for(let i=0;i<2;i++){
   const bytes=Buffer.from(fs.readFileSync(path.join(temp,'synthetic.pdf'),'latin1').replace('CW-B6',`CW-B${i}`),'latin1');
   const r=await context.request.post(API+files+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':'application/pdf','X-Attachment-Filename':`synthetic-${i}.pdf`,'X-Case-Token':(await call('GET',files)).case_token},data:bytes});assert(r.ok(),await r.text());
   const item=(await r.json()).attachment;sources.push(item);await sourceOp(item,'confirm','合成对照原件 '+i);
   const b={request_id:randomUUID().replaceAll('-',''),attachment_id:item.id,operation:'create',expected_case_token:(await call('GET',root)).case_token,report_id:null,expected_report_token:'',data:fixture.reports[i],reason:''};
   const p=await call('POST',root+'/preview',b);rows.push((await call('POST',root+'/confirm',{...b,preview_token:p.preview_token,reviewed:true})).report);
  }
  async function choose(index='4'){
   for(const [label,value] of [['对照报告 A',String(rows[0].id)],['对照报告 B',String(rows[1].id)],['对照项目 A',index],['对照项目 B',index]])await view.getByLabel(label,{exact:true}).selectOption(value);
  }
  const checking=view.getByLabel('确认方法与采样条件可比',{exact:true});
  const result=view.getByRole('article',{name:'检验对照预览',exact:true});
  async function calculate(){await checking.check();await button(view,'核对条件并预览数值差').click();await expect(result).toContainText('差值 B−A：');}
  await page.goto(UI+'/cases/'+cid);writes=[];page.on('request',watch);const beforeDownloads=downloads;
  await button(page,'打开检验前后对照').click();await expect(view).toContainText('CW-B12合成'+species);
  await expect(view.getByLabel('对照报告 A',{exact:true})).toHaveValue('');await expect(checking).not.toBeChecked();
  await choose();await button(view,'核对条件并预览数值差').click();await expect(result).toContainText('尚未确认项目');
  await calculate();await expect(result).toContainText(fixture.expected_deltas[3]);await expect(result).toContainText('参考范围不同');
  for(const v of [fixture.reports[0].items[3].value,fixture.reports[1].items[3].value,fixture.reports[0].report.collected_at,sources[0].sha256,sources[1].sha256])await expect(view).toContainText(v);
  await view.screenshot({path:path.join(out,'cwb12-'+species+'-comparison.png')});
  await button(view,'交换 A 与 B').click();await expect(result).toHaveCount(0);await expect(checking).not.toBeChecked();
  await checking.check();await button(view,'核对条件并预览数值差').click();await expect(result).toContainText('A 的采样时间晚于 B');await expect(result).not.toContainText('差值 B−A');
  await choose('8');await checking.check();await button(view,'核对条件并预览数值差').click();await expect(result).toContainText('两侧并非都是数值结果');
  await choose('9');await expect(view).toContainText(fixture.reports[0].items[8].value);await expect(view).toContainText(fixture.reports[0].items[8].name);
  await choose();await calculate();
  // Hold a real server response, then change selection before it arrives.
  let seenResolve,release,finished;const seen=new Promise(r=>seenResolve=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r),pattern='**/cases/'+cid+'/lab-comparison/preview';
  await page.route(pattern,async route=>{try{const response=await route.fetch();assert.equal(response.status(),200);seenResolve();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(view,'核对条件并预览数值差').click();await seen;await view.getByLabel('对照项目 A',{exact:true}).selectOption('1');release();await done;await page.unroute(pattern);await expect(result).toHaveCount(0);await expect(checking).not.toBeChecked();
  await choose();await calculate();await button(view,`回看检验记录 #${rows[0].id} 版本 1`).click();
  const record=lab.getByRole('article',{name:'检验记录 '+rows[0].id,exact:true});await expect(record.locator('details')).toHaveAttribute('open','');await expect(record).toBeFocused();
  assert(writes.every(u=>u.endsWith('/lab-comparison/preview')));assert.equal(downloads,beforeDownloads);page.off('request',watch);
  passed.push(species+'_explicit_pairs_confirmation_exact_delta_blocked_cases_and_late_selection');
  const downloading=page.waitForEvent('download');await button(record,'打开该记录原件').click();const download=await downloading;
  const target=path.join(out,'cwb12-'+species+'-explicit-original.pdf');await download.saveAs(target);assert.equal(createHash('sha256').update(fs.readFileSync(target)).digest('hex'),sources[0].sha256);assert.equal(download.suggestedFilename(),'synthetic-0.pdf');
  await choose();await button(lab,'录入检验报告').click();await lab.getByLabel('报告标题',{exact:true}).fill('保留未保存对照草稿');
  await button(view,`回看检验记录 #${rows[0].id} 版本 1`).click();await expect(lab.getByLabel('报告标题',{exact:true})).toHaveValue('保留未保存对照草稿');await button(lab,'放弃本页检验草稿').click();
  passed.push(species+'_exact_saved_navigation_explicit_original_sha256_and_draft_preservation');
  await button(page,'打开就诊资料总览').click();await button(page,'核对门诊病历草稿').click();
  const doc=page.getByRole('region',{name:'文书草稿内容核对',exact:true});await expect(button(doc,'确认并下载草稿 DOCX')).toBeDisabled();await doc.getByRole('checkbox',{name:'已核对本次草稿内容（仍未签署）'}).check();await expect(button(doc,'确认并下载草稿 DOCX')).toBeEnabled();
  await button(record,'更正检验记录').click();await lab.getByLabel('报告标题',{exact:true}).fill('合成对照更正版本');await lab.getByLabel('项目 1 结果原文',{exact:true}).fill('1.500');await lab.getByLabel('更正或撤销原因',{exact:true}).fill('合成对照更正验收');
  for(let n=1;n<=fixture.reports[0].items.length;n++)await lab.getByLabel('已核对项目 '+n,{exact:true}).check();
  await button(lab,'核对整份检验记录').click();await lab.getByLabel('已核对整份检验记录',{exact:true}).check();
  const beforeConfirms=confirms,confirmPattern='**/cases/'+cid+'/manual-lab/confirm';
  if(species==='cat')await page.route(confirmPattern,async route=>{const response=await route.fetch();assert.equal(response.status(),200);await route.abort('failed');});
  await button(lab,'确认保存检验记录').click();await expect(lab).toContainText(species==='cat'?'已回读保存结果，未重复提交。':'检验记录已保存。');
  if(species==='cat')await page.unroute(confirmPattern);assert.equal(confirms,beforeConfirms+1);
  await expect(view).toContainText('已被更正');await expect(view.getByLabel('对照报告 A',{exact:true}).locator(`option[value="${rows[0].id}"]`)).toHaveCount(0);await expect(view.getByLabel('对照报告 A',{exact:true})).toHaveValue('');await expect(result).toHaveCount(0);await expect(checking).not.toBeChecked();await expect(button(doc,'确认并下载草稿 DOCX')).toHaveCount(0);await button(doc,'关闭草稿核对').click();
  rows[0]=(await call('GET',root)).reports.find(r=>r.version===2);await choose();await calculate();
  passed.push(species+'_whole_review_'+(species==='cat'?'lost_reply_readback':'save_feedback')+'_clears_pair_and_document_confirmation');
  await sourceOp(sources[0],'update','合成对照来源已更正');
  await button(view,`回看检验记录 #${rows[0].id} 版本 2`).click();await expect(lab).toContainText('版本或状态已变化，未替换为其他记录');
  // A preview made from the now-stale saved selector receives 409 and clears it.
  await button(view,'核对条件并预览数值差').click();await expect(view).toContainText('请刷新并重新选择');await expect(result).toHaveCount(0);
  await button(view,'刷新检验前后对照').click();await expect(view).toContainText('当前报告 1');await expect(view).toContainText('需重新核对');
  await button(view,`回看检验记录 #${rows[0].id} 版本 2`).click();const corrected=lab.getByRole('article',{name:'检验记录 '+rows[0].id,exact:true});
  await button(corrected,'撤销检验记录').click();await lab.getByLabel('更正或撤销原因',{exact:true}).fill('合成对照撤销');await button(lab,'核对整份检验记录').click();await lab.getByLabel('已核对整份检验记录',{exact:true}).check();await button(lab,'确认保存检验记录').click();
  await expect(view).toContainText('已撤销');await expect(view).toContainText('当前报告 1');assert.equal(downloads,beforeDownloads+1);
  await page.setViewportSize({width:390,height:900});await view.screenshot({path:path.join(out,'cwb12-'+species+'-excluded-mobile.png')});await page.setViewportSize({width:1500,height:1100});
  results.push({case_id:cid,species,review:await call('GET',url),remaining:rows[1]});passed.push(species+'_source_stale_preview_409_and_withdrawal_without_automatic_export');
 }
 // Late genuine GET and POST responses must not survive case/account/focus changes.
 const otherEmail='cwb12-other-'+randomUUID()+'@example.com';assert((await context.request.post(API+'/auth/signup',{data:{email:otherEmail,password:'Synthetic-PR26-only-20260916'}})).ok());
 const otherLogin=await context.request.post(API+'/auth/login',{form:{username:otherEmail,password:'Synthetic-PR26-only-20260916'}});assert(otherLogin.ok());const otherToken=(await otherLogin.json()).access_token;
 const cid=results[0].case_id;
 for(const method of ['GET','POST'])for(const scenario of ['case','account','focus']){
  await page.evaluate(t=>localStorage.setItem('token',t),auth.Authorization.slice(7));await page.goto(UI+'/cases/'+cid);
  if(method==='POST'){
   await button(page,'打开检验前后对照').click();await expect(view).toContainText('当前报告 1');
   for(const side of ['A','B']){await view.getByLabel('对照报告 '+side,{exact:true}).selectOption(String(results[0].remaining.id));await view.getByLabel('对照项目 '+side,{exact:true}).selectOption('4');}
   await view.getByLabel('确认方法与采样条件可比',{exact:true}).check();
  }
  let ready,release,finished,held=false;const seen=new Promise(r=>ready=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r),pattern='**/cases/'+cid+'/lab-comparison'+(method==='POST'?'/preview':'');
  await page.route(pattern,async route=>{if(held){await route.continue();return;}held=true;try{const response=await route.fetch();assert.equal(response.status(),200);ready();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(method==='POST'?view:page,method==='POST'?'核对条件并预览数值差':'打开检验前后对照').click();await seen;
  if(scenario==='case')await page.goto(UI+'/cases/'+results[1].case_id);
  else if(scenario==='account')await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);
  else{await call('PUT','/api/cases/'+cid,{weight:'合成焦点 '+method});await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(view).toContainText('合成焦点 '+method);}
  release();await done;await page.unroute(pattern);
  if(scenario==='focus'){await expect(view).toContainText('合成焦点 '+method);await expect(view.getByRole('article',{name:'检验对照预览',exact:true})).toHaveCount(0);await expect(view.getByLabel('对照报告 A',{exact:true})).toHaveValue('');}else await expect(view).toHaveCount(0);
  passed.push('late_'+method+'_response_discarded_after_'+scenario);
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,2);
 fs.writeFileSync(path.join(out,'cwb12-browser-saved.json'),JSON.stringify({results,external_calls:0,explicit_downloads:downloads},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb12-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb12-comparison-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
