import React, { useState } from "react";
import axios from "axios";

const App = () => {
  // 表单字段状态
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [history, setHistory] = useState("");
  const [examFindings, setExamFindings] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [treatment, setTreatment] = useState("");
  const [prognosis, setPrognosis] = useState("");

  // 提交表单
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // 发起 POST 请求调用后端分析接口
      const response = await axios.post(
        "https://pet-med-ai-backend.onrender.com/analyze",  // 后端接口地址
        {
          chief_complaint: chiefComplaint,
          history,
          exam_findings: examFindings,
        }
      );
      
      // 设置返回的分析、治疗和预后
      setAnalysis(response.data.analysis);
      setTreatment(response.data.treatment);
      setPrognosis(response.data.prognosis);
    } catch (error) {
      console.error("Error fetching analysis:", error);
    }
  };

  return (
    <div className="App">
      <h1>宠物病历分析</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>主诉:</label>
          <textarea
            value={chiefComplaint}
            onChange={(e) => setChiefComplaint(e.target.value)}
            required
          />
        </div>
        <div>
          <label>既往史:</label>
          <textarea
            value={history}
            onChange={(e) => setHistory(e.target.value)}
          />
        </div>
        <div>
          <label>体检/化验摘要:</label>
          <textarea
            value={examFindings}
            onChange={(e) => setExamFindings(e.target.value)}
          />
        </div>
        <button type="submit">提交分析</button>
      </form>

      {analysis && (
        <div>
          <h2>分析结果:</h2>
          <p>{analysis}</p>

          <h3>治疗建议:</h3>
          <p>{treatment}</p>

          <h3>预后:</h3>
          <p>{prognosis}</p>
        </div>
      )}
    </div>
  );
};

export default App;
