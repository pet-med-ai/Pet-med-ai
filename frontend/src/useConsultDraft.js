import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { clearDraft, draftOwner, hasDraftContent, readDraft, writeDraft } from "./consultDraft";

export default function useConsultDraft(data, paused) {
  const owner = draftOwner(localStorage.getItem("token"));
  const [initialOwner] = useState(owner);
  const [initial] = useState(() => readDraft(owner));
  const [offer, setOffer] = useState(initial.draft);
  const [message, setMessage] = useState(initial.error);
  const signature = JSON.stringify(data);
  const latest = useRef(signature);
  latest.current = signature;
  const saved = useRef(null);

  useLayoutEffect(() => {
    if (offer || paused) return;
    if (!owner || owner !== initialOwner) { clearDraft(); return; }
    if (signature === saved.current) return;
    if (!hasDraftContent(data)) { clearDraft(); setMessage(initial.error || ""); return; }
    const ok = writeDraft(owner, data);
    setMessage(ok ? (hasDraftContent(data) ? "当前输入已暂存在本标签页，尚不代表已保存病例。" : "") : "浏览器暂时无法保留最新草稿，刷新或离开可能丢失输入。请先完成病例保存。");
  }, [signature, owner, initialOwner, offer, paused]);

  useEffect(() => {
    const changed = event => {
      if (event.key === "token" || event.key === null) {
        clearDraft();
        window.location.reload();
      }
    };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  }, []);

  return {
    offer, message, owner,
    accepted() { setOffer(null); },
    discard() { clearDraft(); setOffer(null); setMessage(""); },
    markSaved() { saved.current = latest.current; const cleared = clearDraft(); setMessage(cleared ? "本次输入已保存并回读，标签页草稿已清除。" : "病例已保存并回读，但浏览器未能清除本页草稿。"); },
  };
}
