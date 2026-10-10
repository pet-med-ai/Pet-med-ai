import React, { useEffect, useState } from 'react';
import api from '../api';

const runtime = {
  enabled: import.meta.env.VITE_DOCTOR_TRIAL === '1',
  api: import.meta.env.VITE_API_BASE,
  session: import.meta.env.VITE_DOCTOR_TRIAL_SESSION,
  head: import.meta.env.VITE_DOCTOR_TRIAL_HEAD,
  source_sha256: import.meta.env.VITE_DOCTOR_TRIAL_SOURCE,
};
const schema = 'clinical-doctor-trial-cw-b26-v1';
const headerNames = { session: 'X-PMAI-Trial-Session', head: 'X-PMAI-Trial-Head', source_sha256: 'X-PMAI-Trial-Source' };

export function validTrialConfig(config) {
  try {
    const url = new URL(config.api);
    return url.protocol === 'http:' && url.hostname === '127.0.0.1' && !!url.port
      && url.pathname === '/' && !url.search && !url.hash && !url.username && !url.password
      && /^[a-f0-9]{64}$/.test(config.session || '')
      && /^[a-f0-9]{40}$/.test(config.head || '') && /^[a-f0-9]{64}$/.test(config.source_sha256 || '');
  } catch { return false; }
}

export function matchesTrial(data, config) {
  return data?.schema === schema && data?.synthetic_only === true
    && Object.keys(headerNames).every(key => data[key] === config[key])
    && Array.isArray(data.cases) && data.cases.length === 2
    && data.cases.every(row => Number.isSafeInteger(row.id) && row.id > 0 && typeof row.name === 'string')
    && Array.isArray(data.steps) && data.steps.every(row => typeof row === 'string')
    && Array.isArray(data.sample_files) && data.sample_files.every(row =>
      typeof row.name === 'string' && /^\/trial-samples\/(synthetic\.(png|pdf)|practice\.json)$/.test(row.path));
}

async function fetchIdentity(config, signal) {
  const response = await fetch(config.api + '/__doctor_trial', { signal, cache: 'no-store', credentials: 'omit' });
  if (!response.ok) throw new Error('Trial identity unavailable');
  return response.json();
}

export default function ClinicalDoctorTrialGate({ children, config = runtime, readIdentity = fetchIdentity }) {
  const [state, setState] = useState({ status: 'checking' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!config.enabled) return undefined;
    let alive = true, failed = false;
    const pending = new Set();
    setState({ status: 'checking' });
    const block = () => {
      failed = true;
      if (alive) setState({ status: 'blocked' });
    };
    async function verify() {
      if (!alive || failed || !validTrialConfig(config)) throw new Error('Trial blocked');
      const controller = new AbortController();
      pending.add(controller);
      const timer = setTimeout(() => controller.abort(), 3000);
      try {
        const data = await readIdentity(config, controller.signal);
        if (!alive || failed || !matchesTrial(data, config)) throw new Error('Trial mismatch');
        return data;
      } finally {
        clearTimeout(timer);
        pending.delete(controller);
      }
    }
    // Verify identity before every business request, including login and writes.
    const request = api.interceptors.request.use(async value => {
      try {
        const target = new URL(value.url, value.baseURL || config.api);
        if (target.origin !== new URL(config.api).origin) throw new Error('Trial target mismatch');
        await verify();
        for (const [key, header] of Object.entries(headerNames)) value.headers[header] = config[key];
        return value;
      } catch (error) { block(); throw error; }
    });
    const response = api.interceptors.response.use(value => {
      if (!Object.entries(headerNames).every(([key, header]) => value.headers?.[header.toLowerCase()] === config[key])) {
        block();
        throw new Error('Trial response identity mismatch');
      }
      return value;
    }, error => {
      // Existing pages cancel superseded reads while logging in or navigating.
      // Cancellation does not mean the backend identity changed.
      if (error.code !== 'ERR_CANCELED' && (!error.response
        || error.response.status === 409 && error.response.data?.detail === 'Trial identity mismatch')) block();
      return Promise.reject(error);
    });
    async function check() {
      try {
        const data = await verify();
        if (alive) setState({ status: 'ready', data });
      } catch { block(); }
    }
    check();
    const timer = setInterval(() => { if (!failed) check(); }, 5000);
    const focus = () => { if (!failed) check(); };
    window.addEventListener('focus', focus);
    return () => {
      alive = false;
      clearInterval(timer);
      for (const controller of pending) controller.abort();
      window.removeEventListener('focus', focus);
      api.interceptors.request.eject(request);
      api.interceptors.response.eject(response);
    };
  }, [config, readIdentity, attempt]);
  if (!config.enabled) return children;
  const ready = state.status === 'ready';
  return <>
    <aside aria-label="合成病例练习" style={{ position: 'sticky', top: 0, zIndex: 100, padding: '10px 16px',
      background: '#fff4d6', borderBottom: '2px solid #946200', color: '#402c00', overflowWrap: 'anywhere' }}>
      <strong>合成病例练习，不录入真实资料</strong>
      <span> · 仅本机临时保存，结束后清理</span>
      {ready && <details style={{ marginTop: 6 }}>
        <summary>练习步骤与犬猫样例</summary>
        <p>用启动终端给出的本次账号登录。重新启动后，请使用新账号；旧会话不能继续保存。</p>
        <nav aria-label="合成病例入口" style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
          {state.data.cases.map(row => <a key={row.id} href={'/cases/' + row.id}>{row.name}</a>)}
          <a href="/cases/new/edit">手工新建合成病例</a>
          <a href="/followup-plans">复查工作清单</a>
        </nav>
        <ol>{state.data.steps.map((step, index) => <li key={index}>{step}</li>)}</ol>
        <p>下载后可将合成原件上传到检查资料；不使用真实患者文件。</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
          {state.data.sample_files.map(file => <a key={file.path} href={file.path} download>{file.name}</a>)}
        </div>
      </details>}
    </aside>
    {ready ? children : <section role={state.status === 'blocked' ? 'alert' : 'status'}
      aria-label="试用环境核对" style={{ padding: 24, maxWidth: 720, margin: 'auto' }}>
      {state.status === 'blocked' ? <>
        <h1>试用环境未通过核对</h1>
        <p>连接已断开，或本次会话、候选版本不一致。页面已停止操作。请先核对保存结果，再检查启动终端；重新启动后使用新地址和账号。</p>
        <button type="button" onClick={() => setAttempt(value => value + 1)}>重新核对本次环境</button>
      </> : <p>正在核对本机合成环境……</p>}
    </section>}
  </>;
}
