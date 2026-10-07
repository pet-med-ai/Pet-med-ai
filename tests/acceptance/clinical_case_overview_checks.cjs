// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb10-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb10-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb10-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb10-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_LAB_DOCUMENTS_ENABLED='1',MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1',MANUAL_IMAGING_ENABLED='1',MANUAL_IMAGING_SYNTHETIC_ONLY='1',VISIT_OVERVIEW_ENABLED='1',VISIT_OVERVIEW_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb10-backend.log'),'w');server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Document backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Document backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1400,height:1080},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();}
 await login();const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:auth,data});assert(r.ok(),await r.text());return r.json();}
 const fixture=JSON.parse(fs.readFileSync('tests/fixtures/clinical_case_overview_cw_b10_cases.json','utf8'));
 const labData=JSON.parse(fs.readFileSync('tests/fixtures/manual_lab_cw_b7_cases.json','utf8'));
 const imageData=JSON.parse(fs.readFileSync('tests/fixtures/manual_imaging_cw_b9_cases.json','utf8'));
 const results=[],button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 const view=page.getByRole('region',{name:'就诊资料总览',exact:true});
 let writes=[],downloads=0;
 const watch=r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(r.url());};
 page.on('download',()=>downloads++);
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{...fixture.case,species,patient_name:'CW-B10合成'+species})).id;
  const files=`/api/cases/${cid}/attachments`,records={},sources={};
  async function sourceOp(source,operation,kind){
   const b={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation,expected_case_token:(await call('GET',files)).case_token,metadata:{title:'合成'+kind+'原件',kind,taken_at:'',reported_at:'',source:'',note:''},reason:operation==='withdraw'?'合成撤销':''};
   const p=await call('POST',files+'/preview',b);return call('POST',files+'/confirm',{...b,preview_token:p.preview_token,reviewed:true});
  }
  for(const kind of ['imaging','lab']){
   const name=kind==='imaging'?'synthetic.pdf':'synthetic.png',mime=kind==='imaging'?'application/pdf':'image/png';
   const r=await context.request.post(API+files+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':mime,'X-Attachment-Filename':name,'X-Case-Token':(await call('GET',files)).case_token},data:fs.readFileSync(path.join(temp,name))});
   assert(r.ok(),await r.text());const source=(await r.json()).attachment;
   await sourceOp(source,'confirm',kind==='imaging'?'dr':'lab');sources[kind]=source;
   const root=`/api/cases/${cid}/manual-${kind}`,body={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation:'create',expected_case_token:(await call('GET',root)).case_token,report_id:null,expected_report_token:'',data:kind==='imaging'?imageData:labData,reason:''};
   const preview=await call('POST',root+'/preview',body);
   records[kind]=(await call('POST',root+'/confirm',{...body,preview_token:preview.preview_token,reviewed:true})).report;
  }
  await page.goto(UI+'/cases/'+cid);writes=[];page.on('request',watch);
  await button(page,'打开就诊资料总览').click();await expect(view).toContainText('CW-B10合成'+species);
  await expect(view).toContainText('预后与补充说明尚未填写');
  await expect(view.getByRole('region',{name:'检验资料状态',exact:true})).toContainText('当前已核对 1');
  await expect(view.getByRole('region',{name:'影像资料状态',exact:true})).toContainText('当前已核对 1');
  await view.getByText('查看病史原文',{exact:true}).click();await expect(view).toContainText('未见呕吐；不能排除间歇症状。');
  assert.deepEqual(writes,[]);assert.equal(downloads,0);page.off('request',watch);
  await view.screenshot({path:path.join(out,'cwb10-'+species+'-overview.png')});
  passed.push(species+'_saved_only_literal_snapshot_no_write_or_download');
  // The existing laboratory editor performs a real correction; overview must refresh.
  await button(view,'前往检验项目').first().click();const lab=page.getByRole('region',{name:'检验项目人工录入',exact:true});
  await button(lab,'更正检验记录').click();await lab.getByLabel('报告标题',{exact:true}).fill('合成检验更正版本');
  await lab.getByLabel('更正或撤销原因',{exact:true}).fill('合成总览联动验收');
  for(let n=1;n<=labData.items.length;n++)await lab.getByLabel('已核对项目 '+n,{exact:true}).check();
  await button(lab,'核对整份检验记录').click();await lab.getByLabel('已核对整份检验记录',{exact:true}).check();await button(lab,'确认保存检验记录').click();
  await expect(view.getByRole('region',{name:'检验资料状态',exact:true})).toContainText('旧版本 1');
  await expect(view.getByRole('region',{name:'检验资料状态',exact:true})).toContainText('当前已核对 1');
  // Opening other panels must retain an unrelated, unfinished draft.
  await button(lab,'录入检验报告').click();await lab.getByLabel('报告标题',{exact:true}).fill('保留未保存检验草稿');
  await button(view,'前往影像记录').first().click();await expect(lab.getByLabel('报告标题',{exact:true})).toHaveValue('保留未保存检验草稿');
  const link=view.getByRole('link',{name:'编辑已保存病例（新标签页）',exact:true}).first();
  assert.equal(await link.getAttribute('target'),'_blank');
  const popupPromise=context.waitForEvent('page');await link.click();const popup=await popupPromise;
  await popup.waitForURL(UI+'/cases/'+cid+'/edit');await popup.close();
  await expect(lab.getByLabel('报告标题',{exact:true})).toHaveValue('保留未保存检验草稿');
  passed.push(species+'_existing_lab_correction_refresh_dedup_and_draft_preservation');
  const images=page.getByRole('region',{name:'影像报告人工录入',exact:true});
  await button(images,'撤销影像记录').click();await images.getByLabel('更正或撤销原因',{exact:true}).fill('合成影像撤销');
  await button(images,'核对整份影像记录').click();await images.getByLabel('已核对整份影像记录',{exact:true}).check();await button(images,'确认保存影像记录').click();
  await expect(view.getByRole('region',{name:'影像资料状态',exact:true})).toContainText('已撤销 1');
  await sourceOp(sources.lab,'withdraw','lab');await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
  await expect(view.getByRole('region',{name:'检验资料状态',exact:true})).toContainText('来源不可用 1');
  await expect(lab.getByLabel('报告标题',{exact:true})).toHaveValue('保留未保存检验草稿');
  for(const label of ['核对门诊病历草稿','核对宠主说明草稿']){
   await button(view,label).click();const review=page.getByRole('region',{name:'文书草稿内容核对',exact:true});
   await expect(button(review,'确认并下载草稿 DOCX')).toBeDisabled();await button(review,'关闭草稿核对').click();
  }
  assert.equal(downloads,0);await view.screenshot({path:path.join(out,'cwb10-'+species+'-withdrawn.png')});
  const saved=await call('GET',`/api/cases/${cid}/visit-overview`);results.push({case_id:cid,species,overview:saved});
  passed.push(species+'_existing_imaging_withdrawal_source_invalidated_and_document_review_required');
 }
 const otherEmail='cwb10-other-'+randomUUID()+'@example.com';
 assert((await context.request.post(API+'/auth/signup',{data:{email:otherEmail,password:'Synthetic-PR26-only-20260916'}})).ok());
 const otherLogin=await context.request.post(API+'/auth/login',{form:{username:otherEmail,password:'Synthetic-PR26-only-20260916'}});assert(otherLogin.ok());const otherToken=(await otherLogin.json()).access_token;
 const cid=results[0].case_id;
 for(const scenario of ['case','account','focus']){
  await page.evaluate(t=>localStorage.setItem('token',t),auth.Authorization.slice(7));await page.goto(UI+'/cases/'+cid);
  let ready,release,finished,held=false;const seen=new Promise(r=>ready=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r);
  const pattern='**/cases/'+cid+'/visit-overview';
  await page.route(pattern,async route=>{
   if(held){await route.continue();return;}held=true;
   try{const response=await route.fetch();assert.equal(response.status(),200);ready();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}
  });
  await button(page,'打开就诊资料总览').click();await seen;
  if(scenario==='case')await page.goto(UI+'/cases/'+results[1].case_id);
  else if(scenario==='account')await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);
  else{await call('PUT','/api/cases/'+cid,{patient_name:'焦点返回后新快照'});await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(view).toContainText('焦点返回后新快照');}
  release();await done;await page.unroute(pattern);
  if(scenario==='focus'){await expect(view).toContainText('焦点返回后新快照');await expect(view).not.toContainText('CW-B10合成dog');}
  else await expect(view).toHaveCount(0);
  passed.push('genuine_late_overview_discarded_after_'+scenario);
 }
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.equal(downloads,0);
 fs.writeFileSync(path.join(out,'cwb10-browser-saved.json'),JSON.stringify({results,external_calls:0,downloads},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb10-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb10-overview-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
