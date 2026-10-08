import React, { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { draftOwner } from "../consultDraft";
import { validDocumentReports } from "../manualLabDocuments";
import { validImagingReports } from "../manualImagingDocuments";
import { validDocumentComparison } from "../labComparisonDocuments";
import { readComparison } from "../labComparison";
import { readDocumentPlans, validDocumentPlan } from "../followupPlanDocuments";
const ClinicalDocFollowupPlanSelection = lazy(() => import("./ClinicalDocFollowupPlanSelection"));
const ClinicalDocLabComparisonSelection = lazy(() => import("./ClinicalDocLabComparisonSelection"));
const ClinicalDocImagingSelection = lazy(() => import("./ClinicalDocImagingSelection"));
const ClinicalDocLabSelection = lazy(() => import("./ClinicalDocLabSelection"));

const fields = [
  ["visit.case_id", "病例编号"], ["visit.pet_name", "动物名称"],
  ["visit.species", "物种"], ["visit.age", "年龄"], ["visit.sex", "性别"],
  ["visit.weight", "体重"], ["visit.complaint", "主诉"], ["visit.history", "病史原文"],
  ["visit.exam", "查体记录"], ["visit.assessment", "评估内容（非最终诊断）"],
  ["visit.plan", "诊疗计划原文"], ["visit.notes", "预后与补充说明"],
  ["visit.follow_up", "复查安排状态"], ["export.account_id", "导出账号（非签名）"],
];

export default function ClinicalDocReview({ caseId, templateId, label, requestToken, onDownload, onClose, onInspectLab, onInspectImaging, onInspectFollowup, sourceRevision = 0 }) {
  const reviewFields = templateId === "outpatient_record_zh" ? [
    ...fields.slice(0, 2), ["visit.owner_name", "宠主姓名"], ["visit.coat_color", "宠物毛色"],
    ...fields.slice(2),
  ] : fields;
  const [preview, setPreview] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [planPreviewReady,setPlanPreviewReady]=useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [labOpen, setLabOpen] = useState(false), [labIds, setLabIds] = useState([]);
  const selected = useRef([]);
  const [imagingOpen, setImagingOpen] = useState(false), [imagingIds, setImagingIds] = useState([]);
  const selectedImaging = useRef([]), previousSourceRevision = useRef(sourceRevision);
  const [comparisonOpen, setComparisonOpen] = useState(false), [comparisonChoice, setComparisonChoice] = useState(null);
  const selectedComparison = useRef(null), comparisonSession = useRef(false), documentRequest = useRef(null), recheckRequest = useRef(null);
  const [planOpen,setPlanOpen]=useState(false),[planChoice,setPlanChoice]=useState(null),[planReadRevision,setPlanReadRevision]=useState(0);
  const selectedPlan=useRef(null),planSession=useRef(false),planRecheck=useRef(null);
  const active = useRef(false), pending = useRef(false), generation = useRef(0), heading = useRef(null);
  const callbacks = useRef({ onDownload, onClose });
  callbacks.current = { onDownload, onClose };
  const current = stamp => active.current && generation.current === stamp &&
    Boolean(requestToken) && localStorage.getItem("token") === requestToken;

  async function load() {
    if (pending.current || !active.current || localStorage.getItem("token") !== requestToken) return;
    pending.current = true;
    const stamp = ++generation.current;
    documentRequest.current?.abort(); documentRequest.current = new AbortController();
    const ids = [...selected.current], imageIds = [...selectedImaging.current], choice = selectedComparison.current;
    const plan = selectedPlan.current;
    setBusy(true); setPreview(null); setConfirmed(false); setPlanPreviewReady(false); setMessage("正在读取已保存的草稿内容…");
    try {
      const { data } = await api.post("/api/clinical-docs/render-preview", {
        case_id: caseId, template_id: templateId, output: "docx",
        ...(ids.length ? {manual_lab_report_ids:ids} : {}),
        ...(imageIds.length ? {manual_imaging_report_ids:imageIds} : {}),
        ...(choice ? {manual_lab_comparison:choice.request} : {}),
        ...(plan ? {manual_followup_plan:plan.request} : {}),
      }, { signal: documentRequest.current.signal, timeout: 15000, expectedAuthOwner: draftOwner(requestToken) });
      if (!current(stamp)) return;
      if (data.case_id !== caseId || data.template_id !== templateId ||
          !/^[a-f0-9]{64}$/.test(data.content_snapshot || "") ||
          data.context?.["visit.case_id"] !== String(caseId) ||
          !reviewFields.every(([key]) => typeof data.context?.[key] === "string") ||
          !Array.isArray(data.missing_required_keys) || data.missing_required_keys.length || data.writes_database !== false ||
          (ids.length && !validDocumentReports(data.manual_lab_reports, ids)) ||
          (!ids.length && data.manual_lab_reports?.length) ||
          (imageIds.length && !validImagingReports(data.manual_imaging_reports, imageIds)) ||
          (!imageIds.length && data.manual_imaging_reports?.length) ||
          !validDocumentComparison(data.manual_lab_comparison, choice, caseId) ||
          !validDocumentPlan(data.manual_followup_plan, plan, caseId)) {
        throw new Error("未收到可核对的完整草稿，当前服务可能尚未支持。请重新读取，暂不能确认下载。");
      }
      setPreview(data); setMessage("");
    } catch (error) {
      if (current(stamp)) {
        const detail = error.response?.data?.detail;
        setMessage(typeof detail === "string" ? detail : error.message || "读取草稿失败，请重试。");
      }
    } finally {
      if (current(stamp)) { pending.current = false; setBusy(false); }
    }
  }

  useEffect(() => {
    active.current = true;
    pending.current = false;
    selected.current=[]; setLabIds([]); setLabOpen(false);
    selectedImaging.current=[]; setImagingIds([]); setImagingOpen(false);
    selectedComparison.current=null; setComparisonChoice(null); setComparisonOpen(false); comparisonSession.current=false;
    selectedPlan.current=null;setPlanChoice(null);setPlanOpen(false);planSession.current=false;
    heading.current?.focus();
    void load();
    return () => { active.current = false; generation.current++; documentRequest.current?.abort(); recheckRequest.current?.abort(); planRecheck.current?.abort(); };
  }, [caseId, templateId, requestToken]);

  function invalidateDocument() {
    generation.current++; pending.current=false; documentRequest.current?.abort();
    setPreview(null); setConfirmed(false); setBusy(false);
  }
  function selectComparison(choice) {
    invalidateDocument(); selectedComparison.current=choice; setComparisonChoice(choice);
    setMessage(choice ? "已选择一对项目，请重新读取完整草稿并逐项核对。" : "对照选择或来源已变化，请重新选择并核对完整草稿。");
  }
  function selectPlan(choice) {
    invalidateDocument();selectedPlan.current=choice;setPlanChoice(choice);
    setMessage(choice ? '已选择复查计划，请重新读取完整草稿并核对。' : '复查计划选择或病例已变化，请重新选择并核对完整草稿。');
  }
  useEffect(()=>{
    const reset=()=>{if(active.current&&planSession.current){selectPlan(null);}};
    const focus=()=>{reset();if(planSession.current)setPlanReadRevision(v=>v+1);};
    const storage=e=>{if(e.key==='token'||e.key===null){reset();planRecheck.current?.abort();setPlanOpen(false);}};
    const affects=c=>{
      const method=c?.method?.toLowerCase(),url=c?.url;
      return (method==='post'&&['followup-plan','attachments','manual-lab','manual-imaging'].some(k=>url===`/api/cases/${caseId}/${k}/confirm`)) ||
        (['put','patch','delete'].includes(method)&&url===`/api/cases/${caseId}`) ||
        (method==='post'&&['edit-confirm','confirm-edit','analyze'].some(k=>url===`/api/cases/${caseId}/${k}`));
    };
    const request=api.interceptors.request.use(c=>{if(affects(c))reset();return c;});
    const reread=c=>{
      if(!affects(c)||!active.current||!planSession.current)return;
      reset();setPlanReadRevision(v=>v+1);planRecheck.current?.abort();const abort=new AbortController();planRecheck.current=abort;
      const stamp=generation.current;
      readDocumentPlans(caseId,requestToken,abort.signal).catch(()=>{
        if(current(stamp)&&!abort.signal.aborted)setMessage('复查计划独立回读未完成，原文书核对已失效，请刷新后重新核对。');
      });
    };
    const response=api.interceptors.response.use(r=>{reread(r.config);return r;},e=>{reread(e.config);return Promise.reject(e);});
    window.addEventListener('focus',focus);window.addEventListener('storage',storage);
    return()=>{api.interceptors.request.eject(request);api.interceptors.response.eject(response);window.removeEventListener('focus',focus);window.removeEventListener('storage',storage);};
  },[caseId,templateId,requestToken]);
  // Remains installed when the selector is closed. Invalidate at request start,
  // including failures/lost replies; never wait for the editor's follow-up GET.
  useEffect(() => {
    const reset = () => { if (active.current && comparisonSession.current) selectComparison(null); };
    const focus = () => reset(), storage = e => { if (e.key === 'token' || e.key === null) reset(); };
    const affects = c => c?.method?.toLowerCase() === 'post' && ['attachments','manual-lab','manual-imaging'].some(k => c.url === `/api/cases/${caseId}/${k}/confirm`);
    const request = api.interceptors.request.use(c => { if (affects(c)) reset(); return c; });
    const reread = c => {
      if (affects(c) && active.current && comparisonSession.current) {
        reset(); recheckRequest.current?.abort(); recheckRequest.current=new AbortController();
        readComparison(caseId, requestToken, recheckRequest.current.signal).catch(() => {});
      }
    };
    const response = api.interceptors.response.use(r => { reread(r.config); return r; }, e => { reread(e.config); return Promise.reject(e); });
    window.addEventListener('focus', focus); window.addEventListener('storage', storage);
    return () => { api.interceptors.request.eject(request); api.interceptors.response.eject(response); window.removeEventListener('focus', focus); window.removeEventListener('storage', storage); };
  }, [caseId, templateId, requestToken]);

  function selectLabs(ids) {
    invalidateDocument();
    selected.current=[...ids]; setLabIds([...ids]); setPreview(null); setConfirmed(false); setBusy(false);
    setMessage("检验选择或来源状态已变化，请重新读取完整草稿并核对。");
  }

  function selectImaging(ids) {
    invalidateDocument();
    selectedImaging.current=[...ids]; setImagingIds([...ids]); setPreview(null); setConfirmed(false); setBusy(false);
    setMessage("影像选择或来源状态已变化，请重新读取完整草稿并核对。");
  }
  useEffect(()=>{
    if(previousSourceRevision.current!==sourceRevision){previousSourceRevision.current=sourceRevision;selectLabs([]);selectImaging([]);setLabOpen(false);setImagingOpen(false);selectComparison(null);setComparisonOpen(false);selectPlan(null);setPlanReadRevision(v=>v+1);}
  },[sourceRevision]);

  function leave() {
    active.current = false; generation.current++; documentRequest.current?.abort();
  }

  async function download() {
    const stamp = generation.current;
    if (pending.current || !current(stamp) || !preview || !confirmed || (preview.manual_followup_plan && !planPreviewReady)) return;
    documentRequest.current?.abort(); documentRequest.current = new AbortController();
    pending.current = true; setBusy(true); setConfirmed(false); setMessage("正在生成已核对的草稿…");
    try {
      const result = await callbacks.current.onDownload(preview.content_snapshot, () => current(stamp), [...selected.current], [...selectedImaging.current], selectedComparison.current?.request, documentRequest.current.signal, selectedPlan.current?.request);
      if (!current(stamp)) return;
      setPreview(null);
      setMessage(result?.ok ? "已生成本次核对的草稿；仍未签署。再次下载请重新读取并核对。" :
        result?.status === 409 ? "病例或模板内容已变化，原确认已失效。请重新读取并核对草稿。" :
          `${result?.message || "下载未完成"}；请重新读取并核对草稿后重试。`);
    } finally {
      if (current(stamp)) { pending.current = false; setBusy(false); }
    }
  }

  return <section aria-label="文书草稿内容核对" className="screen-only"
    style={{ margin: "20px 0", padding: 18, border: "2px solid #93c5fd", borderRadius: 10 }}>
    <h2 ref={heading} tabIndex={-1}>核对{label}</h2>
    <p>瀚森宠物医院 · 草稿，待医生核对、尚未签署。本页核对已保存内容；Word/WPS 的分页请在下载后检查。</p>
    <button type="button" onClick={() => { leave(); callbacks.current.onClose(); }}>关闭草稿核对</button>{" "}
    <Link to={`/cases/${caseId}/edit`} onClick={leave}>返回病例更正</Link>{" "}
    <button type="button" disabled={busy} onClick={load}>重新读取草稿</button>
    {" "}<button type="button" disabled={busy} onClick={()=>{selectLabs([]);setLabOpen(v=>!v);}}>{labOpen ? "不纳入检验报告" : "选择已核对检验报告"}</button>
    {labOpen && <Suspense fallback={<p>正在打开检验选择…</p>}><ClinicalDocLabSelection caseId={caseId} requestToken={requestToken}
      selected={labIds} onChange={selectLabs} onInspect={()=>{leave();onInspectLab?.();}}/></Suspense>}
    {" "}<button type="button" disabled={busy} onClick={()=>{selectImaging([]);setImagingOpen(v=>!v);}}>{imagingOpen ? "不纳入影像报告" : "选择已核对影像报告"}</button>
    {imagingOpen && <Suspense fallback={<p>正在打开影像选择…</p>}><ClinicalDocImagingSelection caseId={caseId} requestToken={requestToken}
      selected={imagingIds} onChange={selectImaging} onInspect={()=>{leave();onInspectImaging?.();}}/></Suspense>}
    {['outpatient_record_zh', 'owner_visit_summary_zh'].includes(templateId) && <>
      {' '}<button type="button" disabled={busy} onClick={()=>{planSession.current=true;setPlanOpen(v=>!v);}}>{planOpen?'收起复查计划选择':'选择复查计划附节'}</button>
      {planChoice&&<p>已选择复查计划 #{planChoice.request.id} 版本 {planChoice.request.version}。<button type="button" onClick={()=>selectPlan(null)}>移除本次复查计划附节</button></p>}
      {planOpen&&<Suspense fallback={<p>正在打开复查计划选择…</p>}><ClinicalDocFollowupPlanSelection caseId={caseId} requestToken={requestToken} templateId={templateId} readRevision={planReadRevision}
        onSelect={selectPlan} onInspect={target=>{leave();onInspectFollowup?.(target);}}/></Suspense>}
    </>}
    {templateId === 'outpatient_record_zh' && <>
      {' '}<button type="button" disabled={busy} onClick={() => { comparisonSession.current=true; selectComparison(null); setComparisonOpen(v => !v); }}>{comparisonOpen ? '关闭对照选择并移除' : '选择检验前后对照附节'}</button>
      {comparisonChoice && <p>已明确选择一对项目；尚需重新读取完整草稿并确认。<button type="button" onClick={() => selectComparison(null)}>移除本次对照附节</button></p>}
      {comparisonOpen && <Suspense fallback={<p>正在打开对照选择…</p>}><ClinicalDocLabComparisonSelection caseId={caseId} requestToken={requestToken} sourceRevision={sourceRevision}
        onSelect={selectComparison} onInvalidated={() => selectComparison(null)} onInspect={target => {leave();onInspectLab?.(target);}} /></Suspense>}
    </>}
    {message && <p role="status" aria-live="polite">{message}</p>}
    {preview && <div>
      {reviewFields.map(([key, title]) => <section key={key} aria-label={title + "核对内容"}>
        <h3>{title}</h3>
        <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", font: "inherit", lineHeight: 1.6 }}>{preview.context[key]}</pre>
      </section>)}
      {!!preview.manual_lab_reports?.length && <Suspense fallback={<p>正在显示检验附节…</p>}><ClinicalDocLabSelection mode="preview" reports={preview.manual_lab_reports}/></Suspense>}
      {!!preview.manual_imaging_reports?.length && <Suspense fallback={<p>正在显示影像附节…</p>}><ClinicalDocImagingSelection mode="preview" reports={preview.manual_imaging_reports}/></Suspense>}
      {preview.manual_lab_comparison && <Suspense fallback={<p>正在显示对照附节…</p>}><ClinicalDocLabComparisonSelection mode="preview" payload={preview.manual_lab_comparison}/></Suspense>}
      {preview.manual_followup_plan && <Suspense fallback={<p>正在显示复查计划附节…</p>}><ClinicalDocFollowupPlanSelection mode="preview" payload={preview.manual_followup_plan} onReady={()=>setPlanPreviewReady(true)}/></Suspense>}
      <p>导出账号：{preview.context['export.account_id']} · 生成时间：{preview.context.timestamp} · 文书内容校验标识：{preview.document_hash}</p>
      <label><input type="checkbox" checked={confirmed} disabled={busy || Boolean(preview.manual_followup_plan && !planPreviewReady)}
        onChange={event => setConfirmed(event.target.checked)} /> 已核对本次草稿内容（仍未签署）</label>{" "}
      <button type="button" disabled={busy || !confirmed || Boolean(preview.manual_followup_plan && !planPreviewReady)} onClick={download}>确认并下载草稿 DOCX</button>
    </div>}
  </section>;
}
