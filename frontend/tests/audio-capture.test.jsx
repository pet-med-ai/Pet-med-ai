import { test } from "node:test";
import assert from "node:assert/strict";
import { encodeWav, startCapture, toBase64 } from "../src/audioCapture";

test("actual WAV header and PCM duration at 30 seconds, clipping and non-finite input", () => {
  const bytes = encodeWav([new Float32Array(48000 * 30).fill(2)], 48000), view = new DataView(bytes.buffer);
  assert.equal(bytes.length, 960044); assert.equal(view.getUint32(24, true), 16000);
  assert.equal(view.getUint16(22, true), 1); assert.equal(view.getUint16(34, true), 16);
  assert.equal(view.getInt16(44, true), 32767);
  const silence = encodeWav([new Float32Array(16000).fill(NaN)], 16000);
  assert.equal(new DataView(silence.buffer).getInt16(44, true), 0);
  assert.deepEqual(new Uint8Array(Buffer.from(toBase64(bytes), "base64")), bytes);
});
test("short oversized and unsupported sample rates rejected", () => {
  for (const [n, rate] of [[1, 16000], [480001, 16000], [8000, 8000]]) assert.throws(() => encodeWav([new Float32Array(n)], rate));
});
test("cancel while permission dialog is pending stops late microphone stream", async () => {
  const controller = new AbortController(); let grant, stopped = 0;
  const promise = startCapture({ signal: controller.signal, mediaDevices: { getUserMedia: () => new Promise(r => { grant = r; }) }, AudioContextClass: class {}, NodeClass: class {} });
  controller.abort(); grant({ getTracks: () => [{ stop() { stopped++; } }] });
  await assert.rejects(promise); assert(stopped >= 1);
});
test("permission rejection cleans up and does not start a context", async () => {
  let created = 0;
  await assert.rejects(startCapture({ mediaDevices: { getUserMedia: async () => { throw Error("denied"); } }, AudioContextClass: class { constructor() { created++; } }, NodeClass: class {} }));
  assert.equal(created, 0);
});
test("worklet setup failure releases granted microphone and context", async () => {
  let stopped = 0, closed = 0;
  class Context { audioWorklet = { addModule: async () => { throw Error("unavailable"); } }; close() { closed++; return Promise.resolve(); } }
  await assert.rejects(startCapture({ mediaDevices: { getUserMedia: async () => ({ getTracks: () => [{ stop() { stopped++; } }] }) }, AudioContextClass: Context, NodeClass: class {} }));
  assert.equal(stopped, 1); assert.equal(closed, 1);
});
