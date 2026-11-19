"""管理端学习报告：错误类型分布、场景热度、水平分布、复习覆盖情况。

与 dashboard（概览数字）和 trends（时间序列）互补，
本模块回答「练得怎么样、错在哪、复习到不到位」。

接口：
    GET /admin/reports/overview
"""
from fastapi import APIRouter, Depends

from app.routers.admin.common import db, get_current_admin_user, ok

router = APIRouter(tags=["管理-报告"])


@router.get("/api/admin/reports/overview")
@router.get("/admin/reports/overview")
def reports_overview(_: dict = Depends(get_current_admin_user)) -> dict:
    """学习效果的结构化统计。"""
    with db() as conn:
        error_types = conn.execute(
            "SELECT error_type, COUNT(*) AS cnt FROM error_bank "
            "WHERE error_type IS NOT NULL AND error_type <> '' "
            "GROUP BY error_type ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

        feedback_types = conn.execute(
            "SELECT feedback_type, COUNT(*) AS cnt FROM inline_feedback GROUP BY feedback_type ORDER BY cnt DESC"
        ).fetchall()

        severity = conn.execute(
            "SELECT COALESCE(severity, 'unknown') AS severity, COUNT(*) AS cnt "
            "FROM inline_feedback GROUP BY severity ORDER BY cnt DESC"
        ).fetchall()

        hot_scenarios = conn.execute(
            "SELECT scenario_id, COUNT(*) AS cnt, AVG(overall_score) AS avg_score "
            "FROM daily_sessions WHERE scenario_id IS NOT NULL AND scenario_id <> '' "
            "GROUP BY scenario_id ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

        levels = conn.execute(
            "SELECT current_level, COUNT(*) AS cnt FROM user_profile GROUP BY current_level ORDER BY cnt DESC"
        ).fetchall()

        reviewed = conn.execute(
            "SELECT COUNT(*) FROM error_bank WHERE review_count > 0"
        ).fetchone()[0]
        total_errors = conn.execute("SELECT COUNT(*) FROM error_bank").fetchone()[0]

        score_buckets = conn.execute(
            "SELECT "
            "  SUM(CASE WHEN overall_score >= 90 THEN 1 ELSE 0 END) AS excellent, "
            "  SUM(CASE WHEN overall_score >= 75 AND overall_score < 90 THEN 1 ELSE 0 END) AS good, "
            "  SUM(CASE WHEN overall_score >= 60 AND overall_score < 75 THEN 1 ELSE 0 END) AS pass, "
            "  SUM(CASE WHEN overall_score < 60 THEN 1 ELSE 0 END) AS poor "
            "FROM daily_sessions WHERE overall_score IS NOT NULL"
        ).fetchone()

    review_rate = round(reviewed / total_errors * 100, 1) if total_errors else 0.0

    return ok({
        "error_type_distribution": [
            {"error_type": row["error_type"], "count": row["cnt"]} for row in error_types
        ],
        "feedback_type_distribution": [
            {"feedback_type": row["feedback_type"], "count": row["cnt"]} for row in feedback_types
        ],
        "severity_distribution": [
            {"severity": row["severity"], "count": row["cnt"]} for row in severity
        ],
        "hot_scenarios": [
            {
                "scenario_id": row["scenario_id"],
                "count": row["cnt"],
                "avg_score": round(float(row["avg_score"]), 1) if row["avg_score"] is not None else None,
            }
            for row in hot_scenarios
        ],
        "level_distribution": [
            {"level": row["current_level"], "count": row["cnt"]} for row in levels
        ],
        "score_distribution": {
            "excellent": score_buckets["excellent"] or 0,
            "good": score_buckets["good"] or 0,
            "pass": score_buckets["pass"] or 0,
            "poor": score_buckets["poor"] or 0,
        },
        "review_coverage": {
            "total_errors": total_errors,
            "reviewed_errors": reviewed,
            "review_rate": review_rate,
        },
    })
