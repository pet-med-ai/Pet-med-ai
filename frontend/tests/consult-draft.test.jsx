import React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { test } from "node:test";
import assert from "node:assert/strict";
import { DRAFT_KEY, DRAFT_MAX_AGE, cleanDraft, draftOwner, readDraft, writeDraft, clearDraft } from "../src/consultDraft";
import useConsultDraft from "../src/useConsultDraft";

const memory = () => { const map = new Map(); return { getItem: k => map.get(k) ?? null, setItem: (k,v) => map.set(k,v), removeItem: k => map.delete(k) }; };
const data = (history = "医生病史🐾\r\n保留空白。  \n") => cleanDraft({ fields: { species: "dog", history }, sessionId: null, sessionContext: "[[],[],null]", followupAnswer: "", structuredAnswers: {}, lastSubmission: null, recoveredNotes: "" });
const token = owner => `header.${Buffer.from(JSON.stringify({sub:owner,exp:Math.floor(Date.now()/1000)+3600})).toString("base64url")}.signature`;

test("draft roundtrip preserves exact input and drops credentials, confirmation and receipts", () => {
  const storage = memory(), input = { ...data(), token: "SECRET", preview_token: "CONFIRMED", auditLogReceipt: {log_id:1}, verified: true };
  assert.equal(writeDraft("a", input, storage), true);
  assert.deepEqual(readDraft("a", storage).draft.data, data());
  for (const forbidden of ["SECRET", "CONFIRMED", "auditLogReceipt", "verified"]) assert(!storage.getItem(DRAFT_KEY).includes(forbidden));
});

test("another account cannot recover the previous account's draft", () => {
  const storage = memory(); writeDraft("a",data(),storage);
  assert.equal(readDraft("b",storage).draft,null);
  assert.equal(storage.getItem(DRAFT_KEY),null);
  assert.equal(draftOwner(token("医生@example.com")),"医生@example.com");
  assert.equal(draftOwner("invalid"),null);
});

test("doctor addendum survives draft recovery and older drafts remain readable", () => {
  const storage = memory(), input = data();
  input.fields.historyAddendum = "  复诊补记🐾\r\n新增记录。  \n";
  writeDraft("a", input, storage);
  assert.equal(readDraft("a", storage).draft.data.fields.historyAddendum, input.fields.historyAddendum);
  delete input.fields.historyAddendum;
  writeDraft("a", input, storage);
  assert.equal(readDraft("a", storage).draft.data.fields.historyAddendum, "");
});

test("expired, corrupt and invalid-shaped drafts cannot populate the form", () => {
  const storage = memory(); writeDraft("a",data(),storage,1000);
  assert.equal(readDraft("a",storage,1001+DRAFT_MAX_AGE).draft,null);
  for(const raw of ["{broken", JSON.stringify({version:1,owner:"a",updatedAt:Date.now(),data:{fields:[]}})]) {
    storage.setItem(DRAFT_KEY,raw); assert.equal(readDraft("a",storage).draft,null); assert.equal(storage.getItem(DRAFT_KEY),null);
  }
});

test("quota and disabled storage do not crash or retain a falsely current old copy", () => {
  const storage=memory(); writeDraft("a",data(),storage);
  storage.setItem=()=>{throw new Error("QuotaExceededError");};
  assert.equal(writeDraft("a",data("new"),storage),false); assert.equal(storage.getItem(DRAFT_KEY),null);
  const blocked={getItem(){throw new Error("SecurityError");},removeItem(){throw new Error("SecurityError");}};
  assert.equal(readDraft("a",blocked).draft,null); assert.equal(clearDraft(blocked),false);
});

function mountHook(storage, initialData = data(), paused = false) {
  let current, renderer;
  global.localStorage=memory(); localStorage.setItem("token",token("a"));
  global.window={sessionStorage:storage,addEventListener(){},removeEventListener(){},location:{reload(){}}};
  const Harness=({value,paused})=>{current=useConsultDraft(value,paused);return null;};
  act(()=>{renderer=TestRenderer.create(<Harness value={initialData} paused={paused}/>);});
  return { get hook(){return current;}, update(value,pause=false){act(()=>renderer.update(<Harness value={value} paused={pause}/>));}, close(){act(()=>renderer.unmount());} };
}

test("a pending recovery offer is not overwritten by initial empty input", () => {
  const storage=memory(); writeDraft("a",data("recover me"),storage); const original=storage.getItem(DRAFT_KEY);
  const h=mountHook(storage,data(""));
  assert.equal(h.hook.offer.data.fields.history,"recover me"); assert.equal(storage.getItem(DRAFT_KEY),original);
  h.update(data("unconfirmed change")); assert.equal(storage.getItem(DRAFT_KEY),original); h.close();
});

test("verified save clears draft until input actually changes", () => {
  const storage=memory(),h=mountHook(storage);
  assert(readDraft("a",storage).draft);
  act(()=>h.hook.markSaved()); h.update(data()); assert.equal(storage.getItem(DRAFT_KEY),null);
  h.update(data("later edit")); assert.equal(readDraft("a",storage).draft.data.fields.history,"later edit"); h.close();
});

test("loading a session cannot persist an intermediate empty state", () => {
  const storage=memory(),h=mountHook(storage);
  h.update(data(""),true); assert.equal(readDraft("a",storage).draft.data.fields.history,data().fields.history);
  h.update(data("loaded")); assert.equal(readDraft("a",storage).draft.data.fields.history,"loaded"); h.close();
});

test("changing auth identity cannot write the old form into the new account draft", () => {
  const storage=memory(),h=mountHook(storage);
  localStorage.setItem("token",token("b")); h.update(data("old account input"));
  assert.equal(storage.getItem(DRAFT_KEY),null); h.close();
});
