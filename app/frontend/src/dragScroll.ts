/**
 * 全局滚动增强（滚轮 + 鼠标左键拖动）。
 *
 * 之前的问题：只在“最近的可滚祖先”上滚，若那层其实滚不动（高度够、或被固定布局限制），
 * 事件就被吞掉，用户看到的就是「滑不动」。
 *
 * 现在的策略：从指针所在元素往上收集所有候选容器，**逐个真的滚一下**，
 * 谁真的动了就用谁；都没动就滚页面本身。滚轮与拖动共用同一套。
 * 只处理鼠标；触屏交给原生。
 */

const INTERACTIVE =
  "button, a, input, textarea, select, label, [contenteditable='true'], .voice-hold-button";

function isScrollableStyle(el: HTMLElement): boolean {
  const oy = window.getComputedStyle(el).overflowY;
  return oy === "auto" || oy === "scroll" || oy === "overlay" || oy === "hidden";
}

function hasOverflow(el: HTMLElement): boolean {
  return el.scrollHeight - el.clientHeight > 2;
}

/** 从目标元素往上收集候选滚动容器（由内到外），最后附上页面滚动容器 */
function collectCandidates(target: EventTarget | null): HTMLElement[] {
  const list: HTMLElement[] = [];
  let el = target as HTMLElement | null;
  while (el && el !== document.documentElement) {
    if (isScrollableStyle(el) && hasOverflow(el)) list.push(el);
    el = el.parentElement;
  }
  const scroller = (document.scrollingElement as HTMLElement | null) ?? document.documentElement;
  if (scroller && hasOverflow(scroller)) list.push(scroller);
  else if (document.body && hasOverflow(document.body)) list.push(document.body);
  return list;
}

/** 依次尝试，返回真正滚动了的容器 */
function scrollAny(candidates: HTMLElement[], deltaY: number): HTMLElement | null {
  for (const el of candidates) {
    const before = el.scrollTop;
    el.scrollTop = before + deltaY;
    if (el.scrollTop !== before) return el;
  }
  return null;
}

export function installDragScroll(): () => void {
  // 自查工具：控制台执行 __scrollInfo() 可以看到每一层的滚动状态
  (window as unknown as Record<string, unknown>).__scrollInfo = () => {
    const rows: string[] = [];
    let el: HTMLElement | null = document.querySelector(".app-main");
    while (el) {
      const cs = window.getComputedStyle(el);
      rows.push(
        `${el.tagName.toLowerCase()}${el.className ? "." + String(el.className).split(" ").join(".") : ""} | overflowY=${cs.overflowY} | sh=${el.scrollHeight} ch=${el.clientHeight} | canScroll=${el.scrollHeight - el.clientHeight > 2}`,
      );
      el = el.parentElement;
    }
    const doc = document.scrollingElement as HTMLElement | null;
    rows.push(`scrollingElement=${doc?.tagName} sh=${doc?.scrollHeight} ch=${doc?.clientHeight}`);
    rows.push(`window.scrollY=${window.scrollY} body.scrollTop=${document.body.scrollTop} docEl.scrollTop=${document.documentElement.scrollTop}`);
    console.table(rows);
    return rows;
  };

  let dragging = false;
  let candidates: HTMLElement[] = [];
  let startY = 0;
  let lastY = 0;
  let moved = false;

  const onPointerDown = (event: PointerEvent) => {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    const origin = event.target as HTMLElement | null;
    if (origin?.closest(INTERACTIVE)) return;
    candidates = collectCandidates(event.target);
    if (candidates.length === 0) return;
    dragging = true;
    moved = false;
    startY = event.clientY;
    lastY = event.clientY;
  };

  const onPointerMove = (event: PointerEvent) => {
    if (!dragging) return;
    const dy = lastY - event.clientY;
    if (!moved && Math.abs(event.clientY - startY) < 3) return;
    if (!moved) {
      moved = true;
      document.body.style.cursor = "grabbing";
      document.body.style.userSelect = "none";
    }
    if (scrollAny(candidates, dy)) {
      lastY = event.clientY;
      event.preventDefault();
    }
  };

  const endDrag = () => {
    if (!dragging) return;
    dragging = false;
    candidates = [];
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  };

  const onWheel = (event: WheelEvent) => {
    if (event.ctrlKey) return;
    const candidatesNow = collectCandidates(event.target);
    if (candidatesNow.length === 0) return;
    if (scrollAny(candidatesNow, event.deltaY)) {
      event.preventDefault();
    }
  };

  window.addEventListener("pointerdown", onPointerDown, { passive: true });
  window.addEventListener("pointermove", onPointerMove, { passive: false });
  window.addEventListener("pointerup", endDrag);
  window.addEventListener("pointercancel", endDrag);
  window.addEventListener("wheel", onWheel, { passive: false });

  return () => {
    window.removeEventListener("pointerdown", onPointerDown);
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", endDrag);
    window.removeEventListener("pointercancel", endDrag);
    window.removeEventListener("wheel", onWheel);
  };
}
