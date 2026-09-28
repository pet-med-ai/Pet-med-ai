// Real Chromium + the isolated PostgreSQL API; synthetic records only.
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {randomUUID,createHash}=require('node:crypto');
const {execFileSync}=require('node:child_process');
const UI='http://127.0.0.1:5173',API='http://127.0.0.1:18026',out=process.env.PMAI_ACCEPTANCE_OUT;
assert(out && process.env.PMAI_SYNTHETIC_ACCEPTANCE==='PR26');
const samples=path.join(out,'m6-samples');fs.mkdirSync(samples,{recursive:true});
let browser,context,page,auth,id,base;const passed=[],failures=[],errors=[],external=[],writes=[],files=[];
const region=name=>page.getByRole('region',{name,exact:true});
const plan=()=>region('医生复查计划'),review=()=>region('文书草稿内容核对');
const short='  M6医生手填复查说明 <5 & >2 {{literal}} 🐾\n\t短说明末行  ';
const long=Array.from({length:65},(_,i)=>`第 ${i+1} 条：医生手填合成复查说明；未见呕吐，不添加额外结论。`).join('\n')+'\nM6长说明末行完整保留。';
const templates=[['outpatient_record_zh','导出门诊病历草稿 DOCX'],['owner_visit_summary_zh','导出宠主说明草稿 DOCX']];
const call=async(method,url,data,status=200)=>{const r=await context.request.fetch(API+url,{method,headers:auth,...(data===undefined?{}:{data})});assert.equal(r.status(),status,await r.text());return r.json();};
const state=()=>call('GET',base);
const record=async name=>{passed.push(name);console.log('PASS:',name);await page.screenshot({path:path.join(out,'m6-'+passed.length+'.png'),fullPage:true});};
async function openPlan(){await page.getByRole('button',{name:'复查计划',exact:true}).click();await expect(plan().getByRole('button',{name:'重新读取复查计划',exact:true})).toBeEnabled();await expect(region('服务器复查记录')).toBeVisible();}
async function fillPlan(note){await plan().getByLabel('复查日期',{exact:true}).fill('2026-10-03');await plan().getByLabel('医生复查说明',{exact:true}).fill(note);}
async function previewPlan(cancel=false){await plan().getByRole('button',{name:cancel?'核对撤销当前计划':'核对复查计划',exact:true}).click();await expect(region('复查保存核对')).toBeVisible();await expect(plan().getByRole('button',{name:'确认并保存复查操作',exact:true})).toBeDisabled();await plan().getByLabel('已核对本次复查操作',{exact:true}).check();}
async function savePlan(){await plan().getByRole('button',{name:'确认并保存复查操作',exact:true}).click();await expect(plan()).toContainText('本次操作已保存并核实');}
async function openDoc(label){const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/clinical-docs/render-preview');await page.getByRole('button',{name:label,exact:true}).click();const r=await pending;assert.equal(r.status(),200);await expect(review().getByRole('button',{name:'确认并下载草稿 DOCX',exact:true})).toBeDisabled();return r.json();}
async function confirmDoc(){await review().getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();await review().getByRole('button',{name:'确认并下载草稿 DOCX',exact:true}).click();}
const closeDoc=()=>review().getByRole('button',{name:'关闭草稿核对',exact:true}).click();
function docText(file){return execFileSync('python',['-c','import sys,zipfile;from xml.etree import ElementTree as E;z=zipfile.ZipFile(sys.argv[1]);root=E.fromstring(z.read("word/document.xml"));ns="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}";assert any(b"PAGE" in z.read(n) for n in z.namelist() if n.startswith("word/footer"));print("\\n".join("".join((n.text or "") if n.tag==ns+"t" else "\\n" if n.tag==ns+"br" else "\\t" if n.tag==ns+"tab" else "" for n in p.iter()) for p in root.iter(ns+"p")))',file],{encoding:'utf8'});}
async function downloadSamples(kind,note){
 const before=await state(),beforeWrites=writes.length;
 for(const [template,label] of templates){
  const p=await openDoc(label);assert(p.context['visit.follow_up'].includes(note));
  const event=page.waitForEvent('download');await confirmDoc();const download=await event;
  const name=template+'-m6-'+kind+'.docx',file=path.join(samples,name);await download.saveAs(file);
  const text=docText(file);assert(text.includes(p.context['visit.follow_up']));assert(text.includes('待医生核对'));
  if(kind==='cancelled'){assert(!text.includes(short));assert(!text.includes('M6长说明末行完整保留。'));}
  files.push({name,template,kind,case_id:id,content_snapshot:p.content_snapshot,sha256:createHash('sha256').update(fs.readFileSync(file)).digest('hex'),follow_up:p.context['visit.follow_up']});
  await closeDoc();
 }
 assert.deepEqual(await state(),before);assert.equal(writes.length,beforeWrites);
 await record(kind+'_both_reviewed_docx_exact_text_page_field_and_no_write');
}
async function externalReplace(note){
 const s=await state(),body={action:'replace',expected_state_token:s.state_token,due_date:'2026-10-03',note};
 const p=await call('POST',base+'/preview',body);
 return call('POST',base+'/confirm',{...body,expected_preview_token:p.preview_token,request_id:randomUUID().replaceAll('-','')});
}
async function main(){
 browser=await chromium.launch({headless:true});context=await browser.newContext({acceptDownloads:true,serviceWorkers:'block',viewport:{width:1440,height:1000}});
 await context.route('**/*',route=>{const origin=new URL(route.request().url()).origin;if([UI,API].includes(origin))return route.continue();external.push(origin);return route.abort();});
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 page.on('request',r=>{if(new URL(r.url()).pathname.endsWith('/follow-up/confirm'))writes.push(r.postDataJSON());});
 await page.goto(UI);await page.getByPlaceholder('邮箱',{exact:true}).fill('browser-owner@example.com');await page.getByPlaceholder('密码',{exact:true}).fill('Synthetic-PR26-only-20260916');await page.getByRole('button',{name:'登录',exact:true}).click();await expect(page.getByRole('button',{name:'退出',exact:true})).toBeVisible();
 auth={Authorization:'Bearer '+await page.evaluate(()=>localStorage.getItem('token'))};
 const original=await call('POST','/api/cases',{patient_name:'M6复查计划合成犬（仅供验收）',chief_complaint:'本次合成主诉，待医生核对',history:'未见呕吐，不排除其他原因。'},201);
 id=original.id;base='/api/cases/'+id+'/follow-up';await page.goto(UI+'/cases/'+id);await openPlan();await fillPlan(short);
 assert.equal(writes.length,0);await page.reload();await openPlan();await expect(region('复查输入恢复')).toBeVisible();await expect(plan().getByLabel('医生复查说明',{exact:true})).toHaveValue('');
 await plan().getByRole('button',{name:'恢复复查输入',exact:true}).click();await expect(plan().getByLabel('医生复查说明',{exact:true})).toHaveValue(short);
 await previewPlan();assert.equal(writes.length,0);await savePlan();assert.equal(writes.length,1);assert.equal((await state()).current.note,short);
 await record('current_tab_draft_requires_explicit_restore_preview_and_confirm');
 await downloadSamples('short',short);

 // Both a pending plan review and a pending document review must fail after
 // an independent authenticated client changes the same synthetic plan.
 await fillPlan('过期候选，不得覆盖新计划');await previewPlan();await openDoc(templates[0][1]);
 await externalReplace('另一个客户端已保存原文');const count=writes.length;
 const rejected=page.waitForResponse(r=>new URL(r.url()).pathname===base+'/confirm');
 await plan().getByRole('button',{name:'确认并保存复查操作',exact:true}).click();assert.equal((await rejected).status(),409);
 await expect(plan()).toContainText('本次请求已被服务拒绝');assert.equal(writes.length,count+1);assert.equal((await state()).current.note,'另一个客户端已保存原文');
 const stale=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/clinical-docs/render');await confirmDoc();assert.equal((await stale).status(),409);await expect(review()).toContainText('原确认已失效');await closeDoc();
 await record('concurrent_saved_plan_rejects_both_stale_confirmations');

 // Drop the POST response *after* the API committed, and deny receipt reads.
 // Refresh cannot create a new operation; only the durable original receipt
 // may resolve the pending state after the network is restored.
 await fillPlan(long);await previewPlan();const beforeLost=writes.length;
 await page.route('**'+base+'/confirm',async route=>{const r=await route.fetch();assert.equal(r.status(),200);await route.abort('failed');});
 await page.route('**'+base+'/receipts/*',route=>route.abort('failed'));
 await plan().getByRole('button',{name:'确认并保存复查操作',exact:true}).click();
 await expect(region('复查保存结果待核对')).toBeVisible();await expect(plan().getByRole('button',{name:'核对复查保存结果',exact:true})).toBeEnabled();
 assert.equal(writes.length,beforeLost+1);assert.equal((await state()).current.note,long);
 await page.reload();await openPlan();await expect(region('复查保存结果待核对')).toBeVisible();assert.equal(writes.length,beforeLost+1);
 await page.unroute('**'+base+'/confirm');await page.unroute('**'+base+'/receipts/*');
 await plan().getByRole('button',{name:'核对复查保存结果',exact:true}).click();await expect(plan()).toContainText('本次操作已保存并核实');assert.equal(writes.length,beforeLost+1);
 assert.equal((await state()).items.length,3);await record('committed_response_loss_refresh_and_readonly_receipt_recovery_no_duplicate');
 await downloadSamples('long',long);

 // A verified change in this tab also proactively invalidates an open review.
 await openDoc(templates[1][1]);await review().getByLabel('已核对本次草稿内容（仍未签署）',{exact:true}).check();
 await previewPlan(true);await savePlan();await expect(review().getByRole('button',{name:'确认并下载草稿 DOCX',exact:true})).toBeDisabled();
 await expect(review()).toContainText('当前无有效复查安排；此前计划已撤销');await closeDoc();
 const cancelled=await state();assert.equal(cancelled.current,null);assert(cancelled.items.every(r=>r.managed && r.status==='cancelled'));
 assert.equal(cancelled.items[0].note,short);assert.equal(cancelled.items[2].note,long);assert.deepEqual(await call('GET','/api/cases/'+id),original);
 await record('cancel_keeps_history_and_invalidates_open_doc_confirmation');
 await downloadSamples('cancelled','当前无有效复查安排；此前计划已撤销');
 assert.equal(files.length,6);assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 fs.writeFileSync(path.join(samples,'manifest.json'),JSON.stringify({format:'pmai-m6-desktop-review-v1',synthetic:true,case_id:id,desktop_acceptance:'pending Word and WPS Mac',files},null,2));
 fs.writeFileSync(path.join(samples,'README.txt'),'M6 合成样本，未签署、未用于真实诊疗。\n请用 Microsoft Word Mac 和 WPS Mac 分别打开六份 DOCX，记录软件与 macOS 版本、总页数、连续页码、跨页文字、末行及无文字遮挡。\nshort/long 为已保存手工复查原文；cancelled 必须仅显示当前无有效安排，不能把旧计划呈现为有效计划。\n宠主说明仍仅作医生核对草稿，不原样交给宠主。\n与同一 CI 产物 application-commit.txt 及 manifest.json 核对后验收；禁止覆盖原样本。\n');
}
main().catch(async e=>{process.exitCode=1;failures.push(String(e));console.error(e);if(page){await page.screenshot({path:path.join(out,'m6-failure.png'),fullPage:true}).catch(()=>{});fs.writeFileSync(path.join(out,'m6-failure-dom.txt'),await page.locator('body').innerText().catch(()=>''));}}).finally(async()=>{fs.writeFileSync(path.join(out,'followup-plan-checks.json'),JSON.stringify({passed,failures,errors,external,confirm_requests:writes.length,samples:files},null,2));if(browser)await browser.close();});
