import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import * as api from "./api";
import { AccountCard } from "./components/AccountCard";
import { PlanPage } from "./components/PlanPage";
import { SettingsPage } from "./components/SettingsPage";
import { AUDIO_METER_EVENT } from "./audioMeter";
import { VoiceWaveform } from "./components/VoiceWaveform";
import { act } from "@testing-library/react";
import { PracticeRoom } from "./components/PracticeRoom";

vi.mock("./api", async importOriginal => ({
  ...await importOriginal<typeof import("./api")>(),
  getAccount: vi.fn(), saveAccount: vi.fn(), getScenarios: vi.fn(), addFavorite: vi.fn(), removeFavorite: vi.fn(),
  getTTSVoices: vi.fn(), startScenarioSession: vi.fn(), translateText: vi.fn(), playTTS: vi.fn(),
  getSessionHistory: vi.fn(), stopActiveAudio: vi.fn(),
}));
const account = { username: "Alice", avatar: "fox", avatars: { fox: "🦊", cat: "🐱" }, is_guest: false };
const scenario = { id: "free_talk", title: "自由对话", category: "自由", background: "自由练习", npc_role: "教练", learner_role: "学习者", objective: "练习", bands: [], difficulty: { level: "A2", vocabulary_range: "", sentence_complexity: "", target_functions: [] } };
beforeEach(() => {
  vi.clearAllMocks(); localStorage.clear(); sessionStorage.clear();
  Element.prototype.scrollIntoView = vi.fn();
  vi.mocked(api.getAccount).mockResolvedValue(account);
  vi.mocked(api.saveAccount).mockResolvedValue({ ...account, username: "Bob", avatar: "cat" });
  vi.mocked(api.getTTSVoices).mockResolvedValue({ voices: [], default_voice: "en-US-JennyNeural" });
  vi.mocked(api.getScenarios).mockResolvedValue({ scenarios: [{ ...scenario, id: "airport-check-in" }], categories: [], roles: [], tiers: [], derived_tier: null });
  vi.mocked(api.startScenarioSession).mockResolvedValue({ session: { id: 1, day_index: 0, topic: "自由对话" }, plan_day: null, turns: [{ id: 2, session_id: 1, turn_index: 1, speaker: "assistant", text: "Hello there.", input_mode: "voice" }] });
  vi.mocked(api.translateText).mockResolvedValue({ text: "Hello there.", translation_zh: "你好。" });
  vi.mocked(api.playTTS).mockResolvedValue();
});
afterEach(cleanup);

test("account edits only the clicked field and closes after saving or cancelling", async () => {
  render(<AccountCard />);
  await screen.findByText("Alice");
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("radio")).toBeNull();
  expect(screen.queryByRole("button", { name: "保存资料" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "更改用户名" }));
  fireEvent.change(screen.getByRole("textbox", { name: "用户名" }), { target: { value: " Bob " } });
  fireEvent.click(screen.getByRole("button", { name: "保存资料" }));
  await waitFor(() => expect(api.saveAccount).toHaveBeenCalledWith("Bob", "fox"));
  await screen.findByText("已保存");
  expect(screen.queryByRole("textbox")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "更改头像" }));
  fireEvent.click(screen.getByRole("radio", { name: "头像 🦊" }));
  fireEvent.click(screen.getByRole("button", { name: "取消" }));
  expect(screen.queryByRole("radio")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "更改头像" }));
  fireEvent.click(screen.getByRole("radio", { name: "头像 🦊" }));
  fireEvent.click(screen.getByRole("button", { name: "保存资料" }));
  await waitFor(() => expect(api.saveAccount).toHaveBeenCalledWith("Bob", "fox"));
  await screen.findByText("已保存");
  expect(screen.queryByRole("radio")).toBeNull();
});
test("scenario favorites work before a learning profile exists", async () => {
  render(<PlanPage onStartScenario={vi.fn()} />);
  const favorite = await screen.findByRole("button", { name: "收藏机场值机" });
  fireEvent.click(favorite);
  await waitFor(() => expect(api.addFavorite).toHaveBeenCalledWith("airport-check-in", undefined));
  expect(await screen.findByRole("button", { name: "取消收藏机场值机" })).toBeTruthy();
});
test("settings logs out through the app handler", async () => {
  const logout = vi.fn(); render(<SettingsPage onLogout={logout} />);
  fireEvent.click(screen.getByRole("button", { name: "退出登录" }));
  expect(logout).toHaveBeenCalledOnce();
  await waitFor(() => expect(api.getTTSVoices).toHaveBeenCalledOnce());
});
test("voice replies show English and translate only when requested", async () => {
  render(<PracticeRoom day={null} scenario={scenario} />);
  expect(await screen.findByText("Hello there.")).toBeTruthy();
  expect(api.translateText).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "点击播放语音" }));
  await waitFor(() => expect(api.playTTS).toHaveBeenCalledWith("Hello there.", undefined));
  fireEvent.click(screen.getByRole("button", { name: "翻译中文" }));
  expect(await screen.findByText("你好。")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "收起中文" }));
  expect(screen.queryByText("你好。")).toBeNull();
});
test("free talk places the knowledge entry before bilingual", async () => {
  render(<PracticeRoom day={null} scenario={scenario} />);
  const knowledge = await screen.findByRole("button", { name: "知识库" });
  const bilingual = screen.getByRole("button", { name: "双语 开" });
  expect(knowledge.compareDocumentPosition(bilingual) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(knowledge);
  expect(screen.getByText("知识库文件导入即将开放。")).toBeTruthy();
});


test("user voice messages have no Chinese translation control", async () => {
  vi.mocked(api.startScenarioSession).mockResolvedValueOnce({ session: { id: 1, day_index: 0, topic: "自由对话" }, plan_day: null, turns: [
    { id: 1, session_id: 1, turn_index: 1, speaker: "user", text: "My voice.", input_mode: "voice" },
    { id: 2, session_id: 1, turn_index: 2, speaker: "assistant", text: "Hello there.", input_mode: "voice" },
  ] });
  render(<PracticeRoom day={null} scenario={scenario} />);
  await screen.findByText("My voice.");
  expect(screen.getAllByRole("button", { name: "翻译中文" })).toHaveLength(1);
  expect(api.translateText).not.toHaveBeenCalled();
});

test("translation shows progress and allows retry after an empty response", async () => {
  let resolve!: (value: { text: string; translation_zh: string }) => void;
  vi.mocked(api.translateText).mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  render(<PracticeRoom day={null} scenario={scenario} />);
  fireEvent.click(await screen.findByRole("button", { name: "翻译中文" }));
  expect(screen.getByRole("button", { name: "翻译中…" }).hasAttribute("disabled")).toBe(true);
  resolve({ text: "Hello there.", translation_zh: "" });
  fireEvent.click(await screen.findByRole("button", { name: "重试翻译" }));
  expect(await screen.findByText("你好。")).toBeTruthy();
  expect(api.translateText).toHaveBeenCalledTimes(2);
});

test("voice bars and visible translations survive leaving and re-entering Chat", async () => {
  const first = render(<PracticeRoom day={null} scenario={scenario} />);
  fireEvent.click(await screen.findByRole("button", { name: "翻译中文" }));
  await screen.findByText("你好。");
  first.unmount();
  // Even a legacy response without mode metadata can use this session's display cache.
  vi.mocked(api.startScenarioSession).mockResolvedValueOnce({ session: { id: 1, day_index: 0, topic: "自由对话" }, plan_day: null, turns: [{ id: 2, session_id: 1, turn_index: 1, speaker: "assistant", text: "Hello there." }] });
  render(<PracticeRoom day={null} scenario={scenario} />);
  expect(await screen.findByRole("button", { name: "点击播放语音" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "收起中文" })).toBeTruthy();
  expect(screen.getByText("你好。")).toBeTruthy();
  expect(api.translateText).toHaveBeenCalledTimes(1);
});

test("voice choices start collapsed and preview the matching character and voice", async () => {
  const guy = { id: "en-US-GuyNeural", name: "Guy", gender: "男", accent: "美式", description: "爽朗明亮的美式男声" };
  vi.mocked(api.getTTSVoices).mockResolvedValueOnce({ voices: [guy], default_voice: guy.id });
  render(<SettingsPage onLogout={vi.fn()} />);
  const picker = await screen.findByRole("button", { name: /当前音色：Guy/ });
  expect(picker.getAttribute("aria-expanded")).toBe("false");
  expect(screen.queryByRole("radiogroup", { name: "陪练老师音色" })).toBeNull();
  fireEvent.click(picker);
  fireEvent.click(screen.getByRole("radio", { name: /Guy/ }));
  await waitFor(() => expect(api.playTTS).toHaveBeenCalledWith("Hello, I am Guy.", guy.id));
  expect(localStorage.getItem("speakmate-voice")).toBe(guy.id);
});


test("account load failure retains avatars and supports a real reload", async () => {
  vi.mocked(api.getAccount).mockRejectedValueOnce(new Error("账号接口尚未更新，请重启后端后重试"));
  render(<AccountCard />);
  const retry = await screen.findByRole("button", { name: "重新加载账号资料" });
  expect(screen.queryByRole("radio")).toBeNull();
  expect(screen.getByRole("button", { name: "更改头像" }).hasAttribute("disabled")).toBe(true);
  fireEvent.click(retry);
  await screen.findByText("Alice");
  expect(screen.getByRole("button", { name: "更改用户名" }).hasAttribute("disabled")).toBe(false);
  expect(screen.queryByRole("button", { name: "重新加载账号资料" })).toBeNull();
});

test("waveform follows measured levels only on the playing voice bar and resets", () => {
  const result = render(<><VoiceWaveform active={true} /><VoiceWaveform active={false} /></>);
  act(() => { window.dispatchEvent(new CustomEvent(AUDIO_METER_EVENT, { detail: { playing: true, levels: [0, .25, .5, 1] } })); });
  const bars = result.container.querySelectorAll(".voice-bubble-bars");
  expect((bars[0].children[3] as HTMLElement).style.height).toBe("100%");
  expect((bars[0].children[0] as HTMLElement).style.height).toBe("15%");
  expect((bars[1].children[3] as HTMLElement).style.height).toBe("");
  act(() => { window.dispatchEvent(new CustomEvent(AUDIO_METER_EVENT, { detail: { playing: false, levels: [] } })); });
  expect((bars[0].children[3] as HTMLElement).style.height).toBe("");
});
