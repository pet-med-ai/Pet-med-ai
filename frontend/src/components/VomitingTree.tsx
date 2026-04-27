// frontend/src/components/VomitingTree.tsx
import { useEffect, useMemo, useRef, useState } from "react";

type Prompt = { id: string; text: string; text_zh: string; text_en: string; };
type Node = {
  id: string;
  label: string;
  label_zh: string;
  label_en: string;
  prompts?: Prompt[];
  children?: Node[];
};

type Props = {
  targetPath?: string[];
};

function normalizeLabel(text: string) {
  return (text || "").replace(/[（(].*?[）)]/g, "").replace(/\s+/g, "").trim();
}

function buildLabelIndex(root: Node, map: Map<string, string>) {
  map.set(normalizeLabel(root.label_zh || root.label), root.id);
  map.set(normalizeLabel(root.label_en || root.label), root.id);
  (root.children || []).forEach((c) => buildLabelIndex(c, map));
}

function buildParentMap(root: Node, parent: string | null, map: Map<string, string | null>) {
  map.set(root.id, parent);
  (root.children || []).forEach((c) => buildParentMap(c, root.id, map));
}

const PATH_ALIAS_TO_ID: Record<string, string> = {
  "消化系统": "vomiting",
  "胃肠道": "triage",
  "急性呕吐": "triage.acute",
};

export default function VomitingTree({ targetPath = [] }: Props) {
  const [data, setData] = useState<Node | null>(null);
  const [locale, setLocale] = useState<"zh" | "en">("zh");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string>("");
  const nodeRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    fetch(`/api/v1/vomiting/tree?locale=${locale}&embed=prompts`)
      .then(r => r.json())
      .then(d => setData(d.root));
  }, [locale]);

  const idPath = useMemo(() => {
    if (!data || !targetPath.length) return [];
    const labelIndex = new Map<string, string>();
    buildLabelIndex(data, labelIndex);
    return targetPath
      .map((label) => labelIndex.get(normalizeLabel(label)) || PATH_ALIAS_TO_ID[normalizeLabel(label)] || "")
      .filter(Boolean);
  }, [data, targetPath]);

  useEffect(() => {
    if (!data || !idPath.length) return;
    const parentMap = new Map<string, string | null>();
    buildParentMap(data, null, parentMap);

    const toExpand = new Set<string>();
    idPath.forEach((id) => {
      let cur: string | null | undefined = id;
      while (cur) {
        toExpand.add(cur);
        cur = parentMap.get(cur) || null;
      }
    });
    setExpandedIds(toExpand);
    const lastId = idPath[idPath.length - 1];
    setActiveId(lastId);
    setTimeout(() => {
      nodeRefs.current[lastId]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  }, [data, idPath]);

  const renderNode = (n: Node) => (
    <li key={n.id} style={{marginBottom: 8}}>
      <div
        ref={(el) => { nodeRefs.current[n.id] = el; }}
        style={{
          fontWeight: 600,
          borderRadius: 6,
          padding: "4px 6px",
          background: activeId === n.id ? "#fef3c7" : "transparent",
          border: activeId === n.id ? "1px solid #f59e0b" : "1px solid transparent",
        }}
      >
        {locale === "zh" ? n.label_zh || n.label : n.label_en || n.label}
      </div>
      {n.prompts && n.prompts.length > 0 && (
        <ul>
          {n.prompts.map(p => (
            <li key={p.id} style={{opacity: .85}}>
              {locale === "zh" ? p.text_zh || p.text : p.text_en || p.text}
            </li>
          ))}
        </ul>
      )}
      {n.children && n.children.length > 0 && expandedIds.has(n.id) && (
        <ul style={{marginLeft: 12}}>
          {n.children.map(renderNode)}
        </ul>
      )}
    </li>
  );

  return (
    <div style={{padding: 16}}>
      <div style={{display:"flex", gap:8, marginBottom:12}}>
        <button onClick={()=>setLocale("zh")} disabled={locale==="zh"}>中文</button>
        <button onClick={()=>setLocale("en")} disabled={locale==="en"}>English</button>
      </div>
      {!data ? <div>Loading…</div> : <ul>{renderNode(data)}</ul>}
    </div>
  );
}
