import React, { useState } from "react";
import AIPetConsultBox from "./AIPetConsultBox";
import VomitingTree from "./VomitingTree";

export default function AISection() {
  const [result, setResult] = useState(null);
  const [treePath, setTreePath] = useState([]);

  return (
    <section style={{ marginTop: 16 }}>
      <AIPetConsultBox
        onResult={(data) => setResult(data)}
        onTreePathLocate={(normalizedPath) => setTreePath(normalizedPath)}
      />
      <div style={{ marginTop: 12, border: "1px solid #e5e7eb", borderRadius: 12 }}>
        <VomitingTree targetPath={treePath} />
      </div>
      {result?.doctor_confirmation_required && (
        <p style={{ marginTop: 8, color: "#92400e" }}>
          当前为半自动建议，需医生最终确认。
        </p>
      )}
    </section>
  );
}
