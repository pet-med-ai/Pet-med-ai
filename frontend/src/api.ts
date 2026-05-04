import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
});

// 请求拦截：带上 JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截：
// - 病例列表 GET /api/cases 的 401：当前阶段静默处理，避免首页反复弹窗
// - 其他 401：仍提示登录过期
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url || "";
    const method = (err.config?.method || "").toLowerCase();

    if (status === 401) {
      localStorage.removeItem("token");

      const isCaseListRequest =
        method === "get" &&
        (url === "/api/cases" || url.startsWith("/api/cases?"));

      if (isCaseListRequest) {
        console.warn("401 from case list, ignored for current consult workflow:", url);
        return Promise.reject(err);
      }

      alert("登录已过期，请重新登录");
    }

    return Promise.reject(err);
  }
);

export default api;
