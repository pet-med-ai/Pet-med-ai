// Real Chromium + real authenticated app and bytes. No service or route mock.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {createHash,randomUUID}=require('node:crypto'),{spawn,spawnSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out&&process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb8-browser-')),passed=[],errors=[],external=[];
let browser,page,server;
const python=process.env.PMAI_PYTHON||'python';
const generated=spawnSync(python,['-B','tests/fixtures/build_attachment_cw_b6_fixtures.py',temp],{encoding:'utf8'});
assert.equal(generated.status,0,generated.stderr);
const prefix=process.argv.includes('--local-sqlite')?`
import os,sys,tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb8-api-')
os.environ.clear();os.environ.update(DATABASE_URL='sqlite:///'+str(Path(tmp.name)/'synthetic.sqlite'),SECRET_KEY='synthetic-cwb8-only',ENVIRONMENT='test',RENDER='false')
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
private=tempfile.TemporaryDirectory(prefix='cwb8-private-')
os.environ.update(CASE_ATTACHMENTS_ENABLED='1',CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',CASE_ATTACHMENTS_DIR=private.name,MANUAL_LAB_RESULTS_ENABLED='1',MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1',MANUAL_LAB_DOCUMENTS_ENABLED='1',MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1')
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb8-backend.log'),'w');server=spawn(python,['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<70;i++){if(server.exitCode!==null)throw Error('Document backend exited');try{if((await fetch(API+'/healthz')).ok)break;}catch{}if(i===69)throw Error('Document backend unavailable');await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({headless:true});const context=await browser.newContext({serviceWorkers:'block',viewport:{width:1400,height:1080},acceptDownloads:true});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 async function login(){await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();}
 await login();const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 async function call(method,url,data){const r=await context.request.fetch(API+url,{method,headers:auth,data});assert(r.ok(),await r.text());return r.json();}
 const original=JSON.parse(fs.readFileSync('tests/fixtures/manual_lab_cw_b7_cases.json','utf8')),results=[];
 const button=(scope,name)=>scope.getByRole('button',{name,exact:true});
 for(const species of ['dog','cat']){
  const cid=(await call('POST','/api/cases',{patient_name:'CW-B8合成'+species,species,owner_name:'合成宠主',coat_color:'黑白（合成）',chief_complaint:'合成检验文书',history:'原始病史 < & {{literal}}'})).id;
  const files=`/api/cases/${cid}/attachments`,root=`/api/cases/${cid}/manual-lab`,name=species==='dog'?'synthetic.pdf':'synthetic.png',mime=species==='dog'?'application/pdf':'image/png',raw=fs.readFileSync(path.join(temp,name));
  const upload=await context.request.post(API+files+'/uploads/'+randomUUID().replaceAll('-',''),{headers:{...auth,'Content-Type':mime,'X-Attachment-Filename':name,'X-Case-Token':(await call('GET',files)).case_token},data:raw});assert(upload.ok());const source=(await upload.json()).attachment;
  const ab={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation:'confirm',expected_case_token:(await call('GET',files)).case_token,metadata:{title:'合成原件',kind:'lab',taken_at:'',reported_at:'',source:'',note:''},reason:''};const ap=await call('POST',files+'/preview',ab);await call('POST',files+'/confirm',{...ab,preview_token:ap.preview_token,reviewed:true});
  let row;
  async function change(op){const b={request_id:randomUUID().replaceAll('-',''),attachment_id:source.id,operation:op,expected_case_token:(await call('GET',root)).case_token,report_id:row?.id||null,expected_report_token:row?.token||'',data:op==='withdraw'?null:structuredClone(original),reason:op==='create'?'':'合成更正或撤销'};if(op==='correct')b.data.items[0].value='0.0700';const p=await call('POST',root+'/preview',b);row=(await call('POST',root+'/confirm',{...b,preview_token:p.preview_token,reviewed:true})).report;}
  await change('create');const before=await call('GET','/api/cases/'+cid);
  await page.goto(UI+'/cases/'+cid);
  const panel=page.getByRole('region',{name:'文书草稿内容核对',exact:true});
  async function choose(label){await button(page,label).click();await button(panel,'选择已核对检验报告').click();await panel.getByLabel('纳入 '+original.report.title,{exact:true}).check();await button(panel,'重新读取草稿').click();await expect(panel.getByRole('region',{name:'检验结果文书附节',exact:true})).toBeVisible();await expect(button(panel,'确认并下载草稿 DOCX')).toBeDisabled();}
  for(const [label,template] of [['导出门诊病历草稿 DOCX','outpatient_record_zh'],['导出宠主说明草稿 DOCX','owner_visit_summary_zh']]){
   await choose(label);await expect(panel).toContainText('0.0100');await expect(panel).toContainText('未测');await expect(panel).toContainText(source.sha256);
   await panel.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();const waiting=page.waitForEvent('download');await button(panel,'确认并下载草稿 DOCX').click();const d=await waiting;const dest=path.join(out,`cwb8-${species}-${template}.docx`);await d.saveAs(dest);
   const xml=spawnSync(python,['-c',"import sys,zipfile;from xml.etree import ElementTree as E;z=zipfile.ZipFile(sys.argv[1]);print(''.join(E.fromstring(z.read('word/document.xml')).itertext()))",dest],{encoding:'utf8'});assert.equal(xml.status,0,xml.stderr);for(const v of ['0.0100','<0.0010','未测','未提供',source.sha256])assert(xml.stdout.includes(v),v);
   await button(panel,'关闭草稿核对').click();passed.push(species+'_'+template+'_real_selection_review_download_literal_values');
  }
  await choose('导出门诊病历草稿 DOCX');await panel.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();await change('correct');await button(panel,'确认并下载草稿 DOCX').click();await expect(panel).toContainText('原确认已失效');await expect(button(panel,'确认并下载草稿 DOCX')).toHaveCount(0);
  await button(panel,'刷新可选检验报告').click();await panel.getByLabel('纳入 '+original.report.title,{exact:true}).check();await button(panel,'重新读取草稿').click();await expect(panel).toContainText('0.0700');await expect(button(panel,'确认并下载草稿 DOCX')).toBeDisabled();
  await panel.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();await change('withdraw');await page.evaluate(()=>window.dispatchEvent(new Event('focus')));await expect(panel).toContainText('当前没有可纳入');await expect(button(panel,'确认并下载草稿 DOCX')).toHaveCount(0);
  await button(panel,'返回检验项目与原件').click();await expect(panel).toHaveCount(0);await expect(page.getByRole('region',{name:'检验项目人工录入',exact:true})).toContainText('已撤销');
  const after=await call('GET','/api/cases/'+cid);assert.equal(after.history,before.history);results.push({case_id:cid,species,reports:(await call('GET',root)).reports});await page.screenshot({path:path.join(out,'cwb8-'+species+'-withdrawn.png'),fullPage:true});
  passed.push(species+'_stale_export_conflict_refresh_recheck_withdraw_source_navigation');
 }
 // Genuine delayed preview and export replies are dropped after leaving the case.
 const cid=results[0].case_id;await page.goto(UI+'/cases/'+cid);await button(page,'导出门诊病历草稿 DOCX').click();await expect(page.getByRole('region',{name:'文书草稿内容核对',exact:true})).toContainText('原始病史');
 await button(page,'关闭草稿核对').click();
 const otherEmail='cwb8-other-'+randomUUID()+'@example.com';
 assert((await context.request.post(API+'/auth/signup',{data:{email:otherEmail,password:'Synthetic-PR26-only-20260916'}})).ok());
 const otherLogin=await context.request.post(API+'/auth/login',{form:{username:otherEmail,password:'Synthetic-PR26-only-20260916'}});assert(otherLogin.ok());const otherToken=(await otherLogin.json()).access_token;
 for(const scenario of ['case','account'])for(const endpoint of ['render-preview','render']){
  await page.evaluate(t=>localStorage.setItem('token',t),auth.Authorization.slice(7));await page.goto(UI+'/cases/'+cid);
  let ready,release,finished;const seen=new Promise(r=>ready=r),gate=new Promise(r=>release=r),done=new Promise(r=>finished=r);let downloadCount=0;const listener=()=>downloadCount++;page.on('download',listener);
  await page.route('**/clinical-docs/'+endpoint,async route=>{try{const response=await route.fetch();assert.equal(response.status(),200);ready();await gate;await route.fulfill({response}).catch(()=>{});}finally{finished();}});
  await button(page,'导出门诊病历草稿 DOCX').click();
  if(endpoint==='render'){await page.getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();await button(page,'确认并下载草稿 DOCX').click();}
  await seen;if(scenario==='case')await page.goto(UI+'/cases/'+results[1].case_id);else await page.evaluate(t=>{localStorage.setItem('token',t);window.dispatchEvent(new StorageEvent('storage',{key:'token'}));},otherToken);release();await done;await page.unroute('**/clinical-docs/'+endpoint);await expect(page.getByRole('region',{name:'文书草稿内容核对',exact:true})).toHaveCount(0);assert.equal(downloadCount,0);page.off('download',listener);
 }
 passed.push('genuine_late_preview_and_download_discarded_after_case_and_account_change');
 await page.evaluate(t=>localStorage.setItem('token',t),auth.Authorization.slice(7));await page.goto(UI);await button(page,'退出').click();await login();await page.goto(UI+'/cases/'+cid);
 await page.reload();await button(page,'导出门诊病历草稿 DOCX').click();await expect(button(page,'选择已核对检验报告')).toBeVisible();await expect(page.getByRole('region',{name:'检验结果文书附节',exact:true})).toHaveCount(0);
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);fs.writeFileSync(path.join(out,'cwb8-browser-saved.json'),JSON.stringify({results,external_calls:0},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb8-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{
 if(browser)await browser.close();if(server&&server.exitCode===null){server.kill('SIGTERM');await new Promise(resolve=>{const timer=setTimeout(()=>{server.kill('SIGKILL');resolve();},5000);server.once('exit',()=>{clearTimeout(timer);resolve();});});}
 fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb8-lab-document-checks.json'),JSON.stringify({passed,errors,external,external_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));
});
