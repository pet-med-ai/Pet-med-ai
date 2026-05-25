import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
});

const isAuthRequest = (url = "") => url.startsWith("/auth/");
const isCaseListRequest = (method = "", url = "") =>
  method.toLowerCase() === "get" &&
  (url === "/api/cases" || url.startsWith("/api/cases?"));

// 请求拦截：带上 JWT；登录/注册接口不带旧 token，避免旧 token 干扰验收判断
api.interceptors.request.use((config) => {
  const url = config.url || "";
  const token = localStorage.getItem("token");

  if (token && !isAuthRequest(url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// 响应拦截：
// - /auth/login 的 401 交给页面显示“邮箱或密码错误”，不要弹“登录已过期”
// - /auth/signup 的 400/422/500 交给页面显示具体注册错误
// - 病例列表 GET /api/cases 的 401：静默处理，避免未登录首页反复弹窗
// - 其它 401：清 token 并提示登录状态失效
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url || "";
    const method = (err.config?.method || "").toLowerCase();

    if (status === 401) {
      if (isAuthRequest(url)) {
        return Promise.reject(err);
      }

      localStorage.removeItem("token");

      if (isCaseListRequest(method, url)) {
        console.warn("401 from case list, ignored for current consult workflow:", url);
        return Promise.reject(err);
      }

      alert("登录状态已失效，请重新登录");
    }

    return Promise.reject(err);
  }
);

export default api;
