import { useEffect, useState } from "react";

const QUERY = "(max-width: 600px)";

function matches(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof window.matchMedia !== "function") return false; // 测试环境（jsdom）兜底
  return window.matchMedia(QUERY).matches;
}

/** 是否处于手机断点（≤600px）。与 styles.css 的移动端媒体查询保持一致。 */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(matches);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mediaQuery = window.matchMedia(QUERY);
    const onChange = (event: MediaQueryListEvent) => setIsMobile(event.matches);
    setIsMobile(mediaQuery.matches);
    mediaQuery.addEventListener("change", onChange);
    return () => mediaQuery.removeEventListener("change", onChange);
  }, []);

  return isMobile;
}
