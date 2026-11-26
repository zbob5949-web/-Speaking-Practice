/** Measure the audio actually being played; never synthesize random waveform motion. */
export const AUDIO_METER_EVENT = "speakmate:audio-meter";
export type AudioMeterFrame = { playing: boolean; levels: number[] };
let context: AudioContext | null = null;

function publish(frame: AudioMeterFrame) {
  window.dispatchEvent(new CustomEvent<AudioMeterFrame>(AUDIO_METER_EVENT, { detail: frame }));
}

export function prepareAudioMeter() {
  const AudioContextClass = window.AudioContext ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextClass) return;
  try { context ??= new AudioContextClass(); void context.resume().catch(() => {}); } catch { /* Ordinary playback still works. */ }
}

export function monitorAudio(audio: HTMLAudioElement): () => void {
  const AudioContextClass = window.AudioContext ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextClass) return () => {};
  let source: MediaElementAudioSourceNode | undefined;
  let analyser: AnalyserNode | undefined;
  let frameId = 0;
  let disposed = false;
  try {
    context ??= new AudioContextClass();
    const currentContext = context;
    source = currentContext.createMediaElementSource(audio);
    analyser = currentContext.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.65;
    source.connect(analyser);
    analyser.connect(currentContext.destination);
    void currentContext.resume().catch(() => {});
    const bins = new Uint8Array(analyser.frequencyBinCount);
    const bounds = [1, 5, 13, 33, 97];
    const sample = () => {
      if (disposed) return;
      if (audio.paused || audio.ended) {
        publish({ playing: false, levels: [] });
        frameId = 0;
        return;
      }
      analyser!.getByteFrequencyData(bins);
      const levels = bounds.slice(0, -1).map((from, index) => {
        const to = Math.min(bounds[index + 1], bins.length);
        let sum = 0;
        for (let bin = from; bin < to; bin++) sum += bins[bin];
        return Math.min(1, sum / Math.max(1, to - from) / 200);
      });
      publish({ playing: true, levels });
      frameId = requestAnimationFrame(sample);
    };
    const start = () => { if (!frameId && !disposed) frameId = requestAnimationFrame(sample); };
    audio.addEventListener("playing", start);
    if (!audio.paused) start();
    return () => {
      if (disposed) return;
      disposed = true;
      cancelAnimationFrame(frameId);
      audio.removeEventListener("playing", start);
      source?.disconnect(); analyser?.disconnect();
      publish({ playing: false, levels: [] });
    };
  } catch {
    // Preserve ordinary playback on browsers without working Web Audio support.
    analyser?.disconnect(); source?.disconnect();
    if (source && context) source.connect(context.destination);
    return () => { source?.disconnect(); publish({ playing: false, levels: [] }); };
  }
}
