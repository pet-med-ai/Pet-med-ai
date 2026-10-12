export const MAX_SECONDS = 30;
// Average each source interval before downsampling; preserve finite signed PCM.
export function encodeWav(chunks, sourceRate) {
  if (!Number.isFinite(sourceRate) || sourceRate < 16000) throw Error("不支持此麦克风采样率");
  const count = chunks.reduce((n, c) => n + c.length, 0);
  if (count < sourceRate / 10 || count > sourceRate * MAX_SECONDS) throw Error("录音须为 0.1 至 30 秒");
  const pcm = new Float32Array(count);
  let offset = 0;
  for (const chunk of chunks) { pcm.set(chunk, offset); offset += chunk.length; }
  const frames = Math.floor(count * 16000 / sourceRate), buffer = new ArrayBuffer(44 + frames * 2), view = new DataView(buffer);
  const chars = (at, value) => [...value].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
  chars(0, "RIFF"); view.setUint32(4, buffer.byteLength - 8, true); chars(8, "WAVE"); chars(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true); view.setUint32(28, 32000, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  chars(36, "data"); view.setUint32(40, frames * 2, true);
  for (let i = 0; i < frames; i++) {
    const start = Math.floor(i * sourceRate / 16000), end = Math.floor((i + 1) * sourceRate / 16000);
    let value = 0;
    for (let j = start; j < end; j++) value += Number.isFinite(pcm[j]) ? pcm[j] : 0;
    value = Math.max(-1, Math.min(1, value / (end - start)));
    view.setInt16(44 + i * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
  }
  pcm.fill(0);
  return new Uint8Array(buffer);
}

export async function startCapture({ signal, onLimit = () => {}, mediaDevices = navigator.mediaDevices, AudioContextClass = window.AudioContext, NodeClass = window.AudioWorkletNode } = {}) {
  let stream, context, node, source, timer, stopped = false, chunks = [], frames = 0;
  const release = () => {
    clearTimeout(timer); stream?.getTracks().forEach(t => t.stop());
    if (node) { node.port.onmessage = null; node.disconnect(); }
    source?.disconnect(); context?.close().catch(() => {});
  };
  const cancel = () => { stopped = true; chunks = []; release(); };
  signal?.addEventListener("abort", cancel, { once: true });
  try {
    if (signal?.aborted) throw Error("已取消录音");
    if (!mediaDevices?.getUserMedia || !AudioContextClass || !NodeClass) throw Error("浏览器不支持录音，请使用手工输入");
    stream = await mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }, video: false });
    if (stopped || signal?.aborted) { release(); throw Error("已取消录音"); }
    context = new AudioContextClass();
    await context.audioWorklet.addModule(new URL("./audioCapture.worklet.js?no-inline", import.meta.url));
    if (stopped) { release(); throw Error("已取消录音"); }
    node = new NodeClass(context, "speech-pcm"); source = context.createMediaStreamSource(stream);
    node.port.onmessage = event => {
      if (stopped) return;
      const available = Math.max(0, MAX_SECONDS * context.sampleRate - frames);
      const chunk = event.data.slice(0, available); frames += chunk.length; chunks.push(chunk);
      if (frames >= MAX_SECONDS * context.sampleRate) onLimit();
    };
    source.connect(node); node.connect(context.destination); await context.resume();
    if (stopped) { release(); throw Error("已取消录音"); }
    timer = setTimeout(onLimit, MAX_SECONDS * 1000);
    return {
      cancel,
      stop() {
        if (stopped) throw Error("录音已结束");
        stopped = true; release(); signal?.removeEventListener("abort", cancel);
        try { return encodeWav(chunks, context.sampleRate); } finally { chunks = []; }
      },
    };
  } catch (error) { cancel(); signal?.removeEventListener("abort", cancel); throw error; }
}

export function toBase64(bytes) {
  let value = "";
  for (let i = 0; i < bytes.length; i += 8192) value += String.fromCharCode(...bytes.subarray(i, i + 8192));
  return btoa(value);
}
