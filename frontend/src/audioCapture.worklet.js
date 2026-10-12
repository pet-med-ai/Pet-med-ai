// Bounded PCM forwarding; no file/cache/network access in the worklet.
class SpeechPCM extends AudioWorkletProcessor {
  process(inputs) {
    const samples = inputs[0]?.[0];
    if (samples) this.port.postMessage(samples.slice());
    return true;
  }
}
registerProcessor("speech-pcm", SpeechPCM);
