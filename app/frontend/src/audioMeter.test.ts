import { afterEach, expect, test, vi } from "vitest";
import { AUDIO_METER_EVENT, monitorAudio } from "./audioMeter";

afterEach(() => vi.unstubAllGlobals());

test("audio meter samples live frequency bands and stops on cleanup", () => {
  const frames: Array<{playing: boolean; levels: number[]}> = [];
  const source = { connect: vi.fn(), disconnect: vi.fn() };
  const analyser = { fftSize: 0, smoothingTimeConstant: 0, frequencyBinCount: 128, connect: vi.fn(), disconnect: vi.fn(), getByteFrequencyData: (bins: Uint8Array) => bins.forEach((_, i) => { bins[i] = i < 13 ? 40 : 160; }) };
  vi.stubGlobal("AudioContext", class {
    destination = {};
    createMediaElementSource() { return source; }
    createAnalyser() { return analyser; }
    resume() { return Promise.resolve(); }
  });
  const callbacks: FrameRequestCallback[] = [];
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => { callbacks.push(callback); return callbacks.length; });
  vi.stubGlobal("cancelAnimationFrame", vi.fn());
  const audio = new EventTarget() as HTMLAudioElement;
  Object.defineProperties(audio, { paused: { value: false }, ended: { value: false } });
  const listener = (event: Event) => frames.push((event as CustomEvent).detail);
  window.addEventListener(AUDIO_METER_EVENT, listener);
  try {
    const stop = monitorAudio(audio);
    callbacks.shift()!(0);
    expect(frames[0]).toEqual({ playing: true, levels: [.2, .2, .8, .8] });
    stop(); stop();
    expect(frames[frames.length - 1]).toEqual({ playing: false, levels: [] });
    expect(source.disconnect).toHaveBeenCalledOnce();
    expect(analyser.disconnect).toHaveBeenCalledOnce();
  } finally { window.removeEventListener(AUDIO_METER_EVENT, listener); }
});
