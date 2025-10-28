// frontend/src/components/VomitingTree.tsx
import { useEffect, useState } from "react";

type Prompt = { id: string; text: string; text_zh: string; text_en: string; };
type Node = {
  id: string;
  label: string;
  label_zh: string;
  label_en: string;
  prompts?: Prompt[];
  children?: Node[];
};

export default function VomitingTree() {
  const [data, setData] = useState<Node | null>(null);
  const [locale, setLocale] = useState<"zh" | "en">("zh");

  useEffect(() => {
    fetch(`/api/v1/vomiting/tree?locale=${locale}&embed=prompts`)
      .then(r => r.json())
      .then(d => setData(d.root));
  }, [locale]);

  const renderNode = (n: Node) => (
    <li key={n.id} style={{marginBottom: 8}}>
      <div style={{fontWeight: 600}}>{locale === "zh" ? n.label_zh || n.label : n.label_en || n.label}</div>
      {n.prompts && n.prompts.length > 0 && (
        <ul>
          {n.prompts.map(p => (
            <li key={p.id} style={{opacity: .85}}>
              {locale === "zh" ? p.text_zh || p.text : p.text_en || p.text}
            </li>
          ))}
        </ul>
      )}
      {n.children && n.children.length > 0 && (
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
