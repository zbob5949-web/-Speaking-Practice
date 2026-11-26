import { useEffect, useState } from "react";
import { AUDIO_METER_EVENT, type AudioMeterFrame } from "../audioMeter";

export function VoiceWaveform({ active }: { active: boolean }) {
  const [levels, setLevels] = useState<number[]>([]);
  useEffect(() => {
    if (!active) { setLevels([]); return; }
    const update = (event: Event) => {
      const frame = (event as CustomEvent<AudioMeterFrame>).detail;
      setLevels(frame.playing ? frame.levels : []);
    };
    window.addEventListener(AUDIO_METER_EVENT, update);
    return () => window.removeEventListener(AUDIO_METER_EVENT, update);
  }, [active]);
  return <span className="voice-bubble-bars" aria-hidden="true" data-playing={active && levels.length > 0}>
    {[0, 1, 2, 3].map(index => <i key={index} style={active && levels.length ? { height: `${15 + (levels[index] ?? 0) * 85}%` } : undefined} />)}
  </span>;
}
