import { useEffect, useState } from "react";
import { getGrowthSummary } from "../api";
import type { GrowthSummary } from "../types";

export function GrowthPage({ profileId }: { profileId?: number }) {
  const [summary, setSummary] = useState<GrowthSummary | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    getGrowthSummary(profileId)
      .then((result) => {
        if (!cancelled) {
          setSummary(result);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const latestReview = summary?.latest_review;
  const memory = summary?.active_memory ?? [];
  const adjustments = summary?.active_adjustments ?? [];
  const strengths = latestReview?.structured_analysis?.strengths ?? [];
  const weaknesses = latestReview?.structured_analysis?.weaknesses ?? [];

  return (
    <div className="growth-page">
      <header className="page-header">
        <h1>成长</h1>
        <p className="muted">教练的长期记忆、复盘记录与自适应训练重点。</p>
      </header>

      {status === "loading" ? (
        <div className="growth-content">
          <p className="muted">正在加载教练记忆…</p>
        </div>
      ) : null}

      {status === "error" ? (
        <div className="growth-content">
          <p className="muted">暂时无法加载成长总结，请稍后再试。</p>
        </div>
      ) : null}

      {status === "ready" ? (
      <div className="growth-content">
        <div className="growth-grid">
          <section className="growth-card">
            <p className="section-label">最近复盘</p>
            <h2>{latestReview?.user_report?.summary ?? "还没有复盘记录"}</h2>
            <p className="muted">
              {latestReview?.user_report?.next_focus ?? "完成一次练习后，这里会生成你的第一份复盘。"}
            </p>
            {latestReview?.review_date ? <span className="growth-date">{latestReview.review_date}</span> : null}
          </section>

          <section className="growth-card">
            <p className="section-label">下一步重点</p>
            {adjustments.length === 0 ? (
              <p className="muted">还没有自适应计划调整。</p>
            ) : (
              adjustments.map((item) => (
                <article className="growth-mini-card" key={item.id}>
                  <strong>{item.title}</strong>
                  <p>{item.instruction}</p>
                  {item.rationale ? <small>{item.rationale}</small> : null}
                </article>
              ))
            )}
          </section>

          <section className="growth-card">
            <p className="section-label">教练记忆</p>
            {memory.length === 0 ? (
              <p className="muted">还没有长期教练记忆。</p>
            ) : (
              memory.map((item) => (
                <article className="growth-mini-card" key={item.id}>
                  <strong>{item.category}</strong>
                  <p>{item.content}</p>
                  {typeof item.confidence === "number" ? (
                    <small>置信度 {Math.round(item.confidence * 100)}%</small>
                  ) : null}
                </article>
              ))
            )}
          </section>

          <section className="growth-card">
            <p className="section-label">学习信号</p>
            {strengths.length === 0 && weaknesses.length === 0 ? (
              <p className="muted">完成每日复盘后会出现学习信号。</p>
            ) : (
              <>
                {strengths.map((item) => (
                  <article className="growth-mini-card" key={`strength-${item}`}>
                    <strong>优势</strong>
                    <p>{item}</p>
                  </article>
                ))}
                {weaknesses.map((item) => (
                  <article className="growth-mini-card" key={`weakness-${item}`}>
                    <strong>待改进</strong>
                    <p>{item}</p>
                  </article>
                ))}
              </>
            )}
          </section>
        </div>
      </div>
      ) : null}
    </div>
  );
}
