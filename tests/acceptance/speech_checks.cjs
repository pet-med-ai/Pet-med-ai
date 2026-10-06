// Actual Chromium media capture + real authenticated app; vendor alone is mocked.
const {chromium, expect} = require('@playwright/test');
const assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const {spawn} = require('node:child_process');
const UI='http://127.0.0.1:5173', API='http://127.0.0.1:18026', out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const passed=[], errors=[], external=[]; let browser, page, server;
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cwb5-pcm-'));
const fixture=path.join(temp,'synthetic.wav');
const pcm=Buffer.alloc(44+16000*2*2);
pcm.write('RIFF');pcm.writeUInt32LE(pcm.length-8,4);pcm.write('WAVE',8);pcm.write('fmt ',12);pcm.writeUInt32LE(16,16);pcm.writeUInt16LE(1,20);pcm.writeUInt16LE(1,22);pcm.writeUInt32LE(16000,24);pcm.writeUInt32LE(32000,28);pcm.writeUInt16LE(2,32);pcm.writeUInt16LE(16,34);pcm.write('data',36);pcm.writeUInt32LE(pcm.length-44,40);
for(let i=0;i<32000;i++)pcm.writeInt16LE(Math.round(Math.sin(2*Math.PI*440*i/16000)*3000),44+i*2);
fs.writeFileSync(fixture,pcm); // Fixed synthetic input only; removed before artifacts.
const prefix = process.argv.includes('--local-sqlite') ? `
import os, sys, tempfile
from pathlib import Path
tmp=tempfile.TemporaryDirectory(prefix='cwb5-browser-')
url='sqlite:///'+str(Path(tmp.name)/'cwb5.sqlite')
os.environ.clear(); os.environ.update(DATABASE_URL=url,SECRET_KEY='synthetic-cwb5-browser-only',ENVIRONMENT='test',RENDER='false')
sys.path[:] = [str(Path('backend').resolve())] + [p for p in sys.path if Path(p or '.').resolve() != Path('.').resolve()]
def guard(event,args):
    if event in {'socket.connect','socket.connect_ex','socket.bind'} and isinstance(args[1],tuple):
        assert args[1][0] in {'127.0.0.1','::1'} and args[1][1]==18026
    if event=='socket.getaddrinfo': assert args[0] in {'127.0.0.1','localhost','::1',None}
sys.addaudithook(guard)
import main,db,models
db.Base.metadata.create_all(db.engine)
from fastapi.testclient import TestClient
with TestClient(main.app) as client:
    assert client.post('/auth/signup',json={'email':'browser-owner@example.com','password':'Synthetic-PR26-only-20260916'}).status_code==200
import speech_budget
speech_budget.initialize_ledger()
` : `
import sys
sys.path.insert(0,'tests/acceptance')
import fixture as f
main=f.main
`;
const boot=prefix+`
import speech_transcription as provider
provider.ensure_enabled=lambda:None
async def recognize(audio,rid):
    provider.validate_wav(audio)
    return {'text':'未见呕吐，零点五毫升','provider_request_id':'mock-only-cwb5'}
provider.recognize=recognize
import uvicorn
uvicorn.run(main.app,host='127.0.0.1',port=18026,loop='asyncio')
`;
async function main(){
 const log=fs.openSync(path.join(out,'cwb5-mock-backend.log'),'w');
 server=spawn(process.env.PMAI_PYTHON||'python',['-B','-c',boot],{stdio:['ignore',log,log],env:process.env});
 for(let i=0;i<50;i++){
  if(server.exitCode!==null)throw Error('Mock backend failed; inspect cwb5-mock-backend.log');
  try{if((await fetch(API+'/healthz')).ok)break;}catch{}
  if(i===49)throw Error('Mock backend unavailable');
  await new Promise(r=>setTimeout(r,200));
 }
 browser=await chromium.launch({headless:true,args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--use-file-for-fake-audio-capture='+fixture,'--autoplay-policy=no-user-gesture-required']});
 // Playwright 1.55 pauses Chromium worklets on attach (upstream issue #37592).
 // Resume that debugger pause through public CDP; capture remains real.
 const cdp=await browser.newBrowserCDPSession();
 cdp.on('Target.targetCreated', async ({targetInfo}) => {
  if(!targetInfo.type.includes('worklet'))return;
  try {
   const {sessionId}=await cdp.send('Target.attachToTarget',{targetId:targetInfo.targetId,flatten:false});
   await cdp.send('Target.sendMessageToTarget',{sessionId,message:JSON.stringify({id:1,method:'Runtime.runIfWaitingForDebugger'})});
  } catch(e) { errors.push('worklet debugger resume: '+e.message); }
 });
 await cdp.send('Target.setDiscoverTargets',{discover:true});
 const context=await browser.newContext({permissions:['microphone'],serviceWorkers:'block',viewport:{width:1440,height:1050}});
 await context.route('**/*',r=>[UI,API].includes(new URL(r.request().url()).origin)?r.continue():(external.push(r.request().url()),r.abort()));
 await context.addInitScript(() => {
   window.__speechErrors=[];
   const get=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
   navigator.mediaDevices.getUserMedia=async(...args)=>{try{window.__speechErrors.push({stage:'get-start'});const result=await get(...args);window.__speechErrors.push({stage:'get-ready'});return result;}catch(e){window.__speechErrors.push({stage:'permission',name:e.name,message:e.message});throw e;}};
   const add=AudioWorklet.prototype.addModule;
   AudioWorklet.prototype.addModule=async function(...args){try{window.__speechErrors.push({stage:'worklet-start'});const result=await add.apply(this,args);window.__speechErrors.push({stage:'worklet-ready'});return result;}catch(e){window.__speechErrors.push({stage:'worklet',name:e.name,message:e.message});throw e;}};
 });
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const field=label=>page.locator('label').filter({has:page.getByText(label,{exact:true})}).locator('input,textarea,select');
 await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();
 const auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 await field('病例名 / 宠物名').fill('CW-B5浏览器合成犬');await field('主诉（必填）').fill('常规体检');await field('既往史').fill('原始手写病史保留。');
 let event=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/ai/consult/session');
 await page.getByRole('button',{name:'提交分析（不入库）',exact:true}).click();const session=await (await event).json();
 await page.getByRole('button',{name:'打开语音草稿',exact:true}).click();const voice=page.getByRole('region',{name:'语音病史草稿',exact:true});
 await voice.getByLabel('本次仅为虚构病例合成音频',{exact:true}).check();
 async function record(){await voice.getByRole('button',{name:'开始录音',exact:true}).click();await expect(voice.getByRole('button',{name:'停止录音',exact:true})).toBeVisible({timeout:15000});await page.waitForTimeout(1200);await voice.getByRole('button',{name:'停止录音',exact:true}).click();}
 await record();let sent;await page.route('**/api/speech/transcribe',r=>{sent=r.request().postDataJSON();return r.continue();});
 event=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/speech/transcribe');await voice.getByRole('button',{name:'提交转写',exact:true}).click();const transcript=await (await event).json();assert(transcript.receipt);
 const wav=Buffer.from(sent.audio_base64,'base64');assert.equal(wav.toString('ascii',0,4),'RIFF');assert.equal(wav.readUInt32LE(24),16000);assert.equal(wav.readUInt16LE(22),1);assert.equal(wav.readUInt16LE(34),16);assert(wav.length>3200&&wav.length<=960044);
 assert.equal(await field('既往史').inputValue(),'原始手写病史保留。');await expect(voice.getByRole('button',{name:'确认加入病史草稿',exact:true})).toBeDisabled();
 await voice.getByLabel('医生修订稿',{exact:true}).fill('未见呕吐，0.5 毫升。');await voice.getByLabel('已对照原文并核对关键内容',{exact:true}).check();await voice.getByRole('button',{name:'确认加入病史草稿',exact:true}).click();
 assert.equal(await field('既往史').inputValue(),'原始手写病史保留。\n\n未见呕吐，0.5 毫升。');
 const cached=await page.evaluate(()=>sessionStorage.getItem('pmai.consult-draft.v1'));assert(cached.includes('零点五毫升'));assert(!cached.includes('audio_base64'));
 passed.push('real_worklet_fixed_wav_doctor_confirmation_append_and_no_cached_audio');
 await page.screenshot({path:path.join(out,'cwb5-doctor-review.png'),fullPage:true});
 await field('既往史').fill('原始手写病史保留。\n\n未见呕吐，0.5 毫升。\n手工补充。');await expect(voice).toContainText('语音确认已失效');
 await voice.getByRole('button',{name:'已重新核对语音来源和病史',exact:true}).click();await expect(voice.getByRole('button',{name:'已重新核对语音来源和病史',exact:true})).toHaveCount(0);
 passed.push('manual_edit_invalidates_then_explicit_source_review_without_asr');
 await page.getByPlaceholder('如 HS-0001 / Dr.Zhao',{exact:true}).fill('CW-B5-Synthetic');await page.getByRole('button',{name:'确认覆核并写入审计',exact:true}).click();await expect(page.getByRole('button',{name:'审计已写入',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'进入保存前核对 →',exact:true}).click();const review=page.getByRole('region',{name:'首次保存病例核对',exact:true});await review.getByRole('button',{name:'核对保存内容',exact:true}).click();await review.getByLabel('已核对本次保存内容',{exact:true}).check();
 let writes=0;await page.route('**/api/ai/consult/session/*/save-case',async r=>{writes++;await r.fetch();await r.abort('failed');});await review.getByRole('button',{name:'确认并保存病例',exact:true}).evaluate(e=>{e.click();e.click();});await expect(page.getByRole('region',{name:'本次保存回读',exact:true})).toBeVisible();assert.equal(writes,1);
 let r=await context.request.get(API+'/api/ai/consult/session/'+session.session_id,{headers:auth});const cid=(await r.json()).case_id;r=await context.request.get(API+'/api/cases/'+cid,{headers:auth});const saved=await r.json();assert(saved.history.includes('未见呕吐，0.5 毫升。'));assert(saved.history.startsWith('原始手写病史保留。'));
 passed.push('lost_save_response_real_readback_one_write_preserves_original');
 for(const template of ['outpatient_record_zh','owner_visit_summary_zh']){
  const p=await context.request.post(API+'/api/clinical-docs/render-preview',{headers:auth,data:{case_id:cid,template_id:template}});assert.equal(p.status(),200);const preview=await p.json();assert.equal(preview.context['visit.history'],saved.history);
  const doc=await context.request.post(API+'/api/clinical-docs/render',{headers:auth,data:{case_id:cid,template_id:template,expected_content_snapshot:preview.content_snapshot}});assert.equal(doc.status(),200);fs.writeFileSync(path.join(out,'cwb5-'+template+'.docx'),await doc.body());
 }
 passed.push('both_actual_docx_use_final_confirmed_history');
 // Independent denied-permission context exercises the actual browser UI branch.
 const denied=await browser.newContext({serviceWorkers:'block'});await denied.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Denied','NotAllowedError');};});
 const deniedPage=await denied.newPage();await deniedPage.goto(UI);await deniedPage.evaluate(token=>localStorage.setItem('token',token),auth.Authorization.slice(7));await deniedPage.goto(UI+'/?restore_session_id='+session.session_id);await deniedPage.getByRole('button',{name:'打开语音草稿',exact:true}).click();const d=deniedPage.getByRole('region',{name:'语音病史草稿',exact:true});await d.getByLabel('本次仅为虚构病例合成音频',{exact:true}).check();await d.getByRole('button',{name:'开始录音',exact:true}).click();await expect(d).toContainText('麦克风未获许可');await denied.close();passed.push('permission_denial_retains_manual_input');
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 fs.writeFileSync(path.join(out,'cwb5-browser-saved.json'),JSON.stringify({case_id:cid,history:saved.history,provider:'mock',actual_asr_calls:0},null,2));
}
main().catch(async e=>{process.exitCode=1;errors.push(String(e));console.error(e);if(page&&!page.isClosed())console.error(await page.evaluate(()=>({audioErrors:window.__speechErrors,voice:document.querySelector('[aria-label="语音病史草稿"]')?.innerText})).catch(()=>({})));if(page&&!page.isClosed())await page.screenshot({path:path.join(out,'cwb5-failure.png'),fullPage:true}).catch(()=>{});}).finally(async()=>{if(browser)await browser.close();if(server)server.kill('SIGTERM');fs.rmSync(temp,{recursive:true,force:true});fs.writeFileSync(path.join(out,'cwb5-speech-checks.json'),JSON.stringify({passed,errors,external,actual_asr_calls:0,backend:process.argv.includes('--local-sqlite')?'SQLite':'PostgreSQL'},null,2));});
