import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "https://pet-med-ai-backend.onrender.com",
});

// 请求拦截：带上 JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截：401 时清 token 并提示
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("token");
      alert("登录已过期，请重新登录");
      // 这里可以触发一个全局状态/刷新
    }
    return Promise.reject(err);
  }
);

export default api;
