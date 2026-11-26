import { afterEach, expect, test, vi } from "vitest";
import { sendUserTurnStream } from "./api";

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

test("renders first SSE text while metadata is still pending and handles split CRLF frames", async () => {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const stream = new ReadableStream<Uint8Array>({ start(value) { controller = value; } });
  vi.spyOn(window, "fetch").mockResolvedValue({ ok: true, status: 200, body: stream } as Response);
  const chunks: string[] = [];
  let first!: () => void;
  const firstText = new Promise<void>(resolve => { first = resolve; });
  const result = sendUserTurnStream(1, "Hi", text => { chunks.push(text); first(); });
  const encode = (text: string) => new TextEncoder().encode(text);
  controller.enqueue(encode('data: {"type":"text","content":"H"}\r'));
  controller.enqueue(encode('\n\r\n'));
  await firstText;
  expect(chunks).toEqual(["H"]);
  controller.enqueue(encode('data: {"type":"text","content":"ello"}\n\n'));
  controller.enqueue(encode('data: {"type":"meta","hints":[],"inline_feedback":[],"assistant_turn":{"text":"Hello"}}'));
  controller.close();
  const meta = await result;
  expect(chunks.join("")).toBe("Hello");
  expect(meta.assistant_turn.text).toBe("Hello");
});
