"""
LLM Observatory — Streamlit Dashboard
Compatible with Streamlit 1.58 + Plotly 6.x + Pandas 3.x

Run with:
    streamlit run dashboard/app.py
"""

from typing import Optional

import re
import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8000/api/v1"

PROVIDER_COLORS = {
    "groq":    "#00C9A7",
    "cerebras": "#FF6B6B",
    "mistral": "#FF6B35",
}

st.set_page_config(
    page_title="LLM Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .alert-box {
        background: #2d1b1b;
        border-left: 4px solid #ef4444;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin: 0.4rem 0;
        font-size: 0.85rem;
    }
    .success-box {
        background: #1b2d1e;
        border-left: 4px solid #22c55e;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        margin: 0.4rem 0;
    }
    .stButton>button {
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
    }
    /* Hide Streamlit top-right toolbar (Share / Deploy) */
    div[data-testid="stToolbar"],
    button[title="Share"],
    button[aria-label="Share"] {
        display: none !important;
    }
    h1 { color: #a5b4fc !important; }
    h2 { color: #c4b5fd !important; }
    h3 { color: #ddd6fe !important; }
</style>
""", unsafe_allow_html=True)

# ── Chart layout defaults ─────────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="#0e1117",
    plot_bgcolor="#1c1f2e",
    margin=dict(t=40, l=10, r=10, b=10),
    font=dict(color="#e2e8f0"),
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def api_get(endpoint: str) -> Optional[list]:
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({endpoint}): {e}")
        return None


def api_post(endpoint: str, payload: dict) -> Optional[dict]:
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({endpoint}): {e}")
        return None


def badge(provider: str) -> str:
    colors = {"groq": "00C9A7", "cerebras": "FF6B6B", "mistral": "FF6B35"}
    c = colors.get(provider, "888888")
    return (
        f'<span style="background:#{c};color:white;padding:2px 8px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:600">'
        f'{provider.upper()}</span>'
    )


def score_bar(value: float, inverse: bool = False) -> str:
    v = (1 - value) if inverse else value
    color = "#22c55e" if v >= 0.7 else "#f59e0b" if v >= 0.4 else "#ef4444"
    return (
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<div style="flex:1;background:#2d3148;border-radius:4px;height:8px">'
        f'<div style="width:{v*100:.0f}%;background:{color};height:8px;border-radius:4px"></div>'
        f'</div>'
        f'<span style="color:{color};font-size:0.8rem;font-weight:600">{value:.2f}</span>'
        f'</div>'
    )


def strip_markdown(text: str) -> str:
    """Strip Markdown symbols so raw text previews cleanly inside an HTML <p> tag."""
    import re
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'={3,}', '', text)
    text = re.sub(r'-{3,}', '', text)
    text = re.sub(r'`{1,3}', '', text)
    return text.strip()


def render_markdown_to_html(md: str) -> str:
    """Minimal Markdown -> HTML renderer for common elements (headings, lists, code)."""
    if not md:
        return ""

    # Escape any HTML first
    s = html.escape(md)

    # Code fences ```...```
    def _code_fence_repl(m):
        code = m.group(1)
        return f"<pre><code>{code}</code></pre>"

    s = re.sub(r"```\s*\n(.*?)\n\s*```", lambda m: _code_fence_repl(m), s, flags=re.S)

    # Inline code `...`
    s = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", s)

    # Headings
    for i in range(6, 0, -1):
        s = re.sub(rf"^{{0,3}}{'#'*i}\s*(.+)$", rf"<h{i}>\1</h{i}>", s, flags=re.M)

    # Lists (unordered and ordered)
    lines = s.splitlines()
    out_lines = []
    in_ul = in_ol = False
    for line in lines:
        m_ul = re.match(r"^\s*[-*]\s+(.*)$", line)
        m_ol = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if m_ul:
            if not in_ul:
                out_lines.append("<ul>")
                in_ul = True
            out_lines.append(f"<li>{m_ul.group(1)}</li>")
            continue
        else:
            if in_ul:
                out_lines.append("</ul>")
                in_ul = False

        if m_ol:
            if not in_ol:
                out_lines.append("<ol>")
                in_ol = True
            out_lines.append(f"<li>{m_ol.group(2)}</li>")
            continue
        else:
            if in_ol:
                out_lines.append("</ol>")
                in_ol = False

        out_lines.append(line)

    if in_ul:
        out_lines.append("</ul>")
    if in_ol:
        out_lines.append("</ol>")

    s = "\n".join(out_lines)

    # Paragraphs: wrap lines separated by blank lines
    parts = re.split(r"\n\s*\n", s)
    parts = [p if p.strip().startswith("<") else f"<p>{p.strip()}</p>" for p in parts]
    return "\n".join(parts)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔭 LLM Observatory")
    st.markdown("---")

    health = api_get("/health")
    if health:
        st.success("✅ API Connected")
        st.caption(f"DB: {health.get('db','?')} | Models: {', '.join(health.get('models', []))}")
    else:
        st.error("❌ API Offline — start the backend first")

    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🚀 Run Evaluation", "📊 Dashboard", "⚖️ Model Leaderboard", "🚨 Alerts", "📋 Raw Traces"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Built by Aman Manikpuri")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — RUN EVALUATION
# ══════════════════════════════════════════════════════════════════════════════

if page == "🚀 Run Evaluation":
    st.title("🚀 Run LLM Evaluation")
    st.caption("Send a prompt to multiple LLMs simultaneously and compare quality metrics.")

    col1, col2 = st.columns([2, 1])

    with col1:
        prompt = st.text_area(
            "Your Prompt",
            placeholder="e.g. What is the capital of France and why is it significant?",
            height=120,
        )
        context = st.text_area(
            "RAG Context (optional)",
            placeholder="Paste a document/paragraph here for faithfulness evaluation…",
            height=100,
        )

    with col2:
        category = st.selectbox(
            "Category",
            ["factual", "rag", "instruction"],
            help="Affects which metrics are emphasised",
        )
        providers = st.multiselect(
            "Models to Compare",
            ["groq", "cerebras", "mistral"],
            default=["groq", "cerebras", "mistral"],
        )
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("⚡ Run Evaluation", use_container_width=True)

    # Quick test prompts
    st.markdown("**💡 Quick Test Prompts:**")
    qcols = st.columns(3)
    quick = {
        "Factual":     "Explain how transformers work in machine learning in simple terms.",
        "RAG":         "Based on the context provided, what are the key findings?",
        "Instruction": "List exactly 5 benefits of using vector databases. Use bullet points only.",
    }
    for i, (label, q) in enumerate(quick.items()):
        if qcols[i].button(label, use_container_width=True):
            st.session_state["quick_prompt"] = q

    if "quick_prompt" in st.session_state and not prompt:
        prompt = st.session_state.pop("quick_prompt")
        st.rerun()

    if run_btn:
        if not prompt.strip():
            st.warning("Please enter a prompt.")
        elif not providers:
            st.warning("Select at least one provider.")
        else:
            with st.spinner("⚡ Calling LLMs in parallel and evaluating…"):
                payload = {
                    "prompt":    prompt,
                    "context":   context or None,
                    "category":  category,
                    "providers": providers,
                }
                result = api_post("/run", payload)

            if result:
                best = result.get("best_provider", "?")
                st.success(f"✅ Evaluation complete! Best model: **{best.upper()}**")
                st.markdown("---")

                results = result.get("results", [])
                res_cols = st.columns(len(results))

                for i, res in enumerate(results):
                    with res_cols[i]:
                        provider = res["provider"]
                        alert    = res.get("alert_triggered")
                        border   = "#ef4444" if alert else "#2d3148"

                        preview = strip_markdown(res['response'])[:300]
                        st.markdown(f"""
                        <div style="border:1px solid {border};border-radius:12px;padding:1rem;background:#1c1f2e">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem">
                                {badge(provider)}
                                <span style="color:#94a3b8;font-size:0.75rem">{res['latency_ms']:.0f}ms</span>
                            </div>
                            <p style="font-size:0.82rem;color:#cbd5e1;margin-bottom:0.8rem;min-height:80px">
                                {preview}{'…' if len(res['response']) > 300 else ''}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown("**Scores**")
                        st.markdown(f"Overall {score_bar(res['overall_score'])}", unsafe_allow_html=True)
                        st.markdown(f"Hallucination {score_bar(res['hallucination_score'])}", unsafe_allow_html=True)
                        st.markdown(f"Relevance {score_bar(res['relevance_score'])}", unsafe_allow_html=True)
                        st.markdown(f"Toxicity {score_bar(res['toxicity_score'], inverse=True)}", unsafe_allow_html=True)
                        st.caption(f"Tokens: {res['total_tokens']} | Cost: ${res['cost_usd']:.5f}")

                        if alert:
                            st.markdown(
                                f'<div class="alert-box">⚠️ {res["alert_reason"]}</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown('<div class="success-box">✅ No alerts</div>', unsafe_allow_html=True)

                        with st.expander("Full Response"):
                            st.markdown(res["response"])


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📊 Dashboard":
    st.title("📊 Live Dashboard")

    evals_data  = api_get("/evals")
    traces_data = api_get("/traces")

    if not evals_data:
        st.info("No evaluation data yet. Run some evaluations first!")
        st.stop()

    evals  = pd.DataFrame(evals_data)
    traces = pd.DataFrame(traces_data) if traces_data else pd.DataFrame()

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Evaluations", len(evals))
    k2.metric("Avg Overall Score",  f"{evals['overall_score'].mean():.2f}")
    k3.metric("Avg Hallucination",  f"{evals['hallucination_score'].mean():.2f}")
    k4.metric("Alerts Triggered",   int(evals["alert_triggered"].sum()))
    if not traces.empty and "cost_usd" in traces.columns:
        k5.metric("Total Cost (USD)", f"${traces['cost_usd'].sum():.4f}")

    st.markdown("---")

    # Score trends
    st.subheader("📈 Score Trends Over Time")
    if "created_at" in evals.columns:
        evals["created_at"] = pd.to_datetime(evals["created_at"])
        fig = px.line(
            evals.sort_values("created_at"),
            x="created_at", y="overall_score", color="provider",
            color_discrete_map=PROVIDER_COLORS,
            title="Overall Score Over Time",
            template="plotly_dark",
        )
        fig.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig2 = px.box(
            evals, x="provider", y="hallucination_score",
            color="provider", color_discrete_map=PROVIDER_COLORS,
            title="Hallucination Score Distribution",
            template="plotly_dark",
        )
        fig2.update_layout(**CHART_LAYOUT, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        fig3 = px.violin(
            evals, x="provider", y="relevance_score",
            color="provider", color_discrete_map=PROVIDER_COLORS,
            title="Relevance Score Distribution",
            template="plotly_dark",
        )
        fig3.update_layout(**CHART_LAYOUT, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    if not traces.empty and "latency_ms" in traces.columns:
        st.subheader("⏱ Latency by Provider")
        fig4 = px.histogram(
            traces, x="latency_ms", color="provider",
            color_discrete_map=PROVIDER_COLORS,
            barmode="overlay", template="plotly_dark",
            title="Latency Distribution (ms)",
        )
        fig4.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MODEL LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════

elif page == "⚖️ Model Leaderboard":
    st.title("⚖️ Model Leaderboard")
    st.caption("Aggregated performance across all evaluations")

    summary_data = api_get("/summary")
    cost_data    = api_get("/cost")

    if not summary_data:
        st.info("No data yet. Run evaluations to populate the leaderboard.")
        st.stop()

    summary = pd.DataFrame(summary_data)

    # Radar chart
    st.subheader("🕸 Multi-Metric Radar")
    categories = ["avg_overall", "avg_hallucination", "avg_relevance"]
    fig_radar  = go.Figure()

    for _, row in summary.iterrows():
        provider = row["provider"]
        vals = [float(row.get(c, 0)) for c in categories]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=["Overall", "Hallucination", "Relevance", "Overall"],
            fill="toself",
            name=provider.upper(),
            line_color=PROVIDER_COLORS.get(provider, "#888"),
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        template="plotly_dark",
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # Leaderboard cards
    st.subheader("🏆 Rankings")
    medals = ["🥇", "🥈", "🥉"]
    for rank, (_, row) in enumerate(summary.iterrows(), 1):
        medal    = medals[rank - 1] if rank <= 3 else f"#{rank}"
        provider = row["provider"]
        st.markdown(f"""
        <div style="background:#1c1f2e;border-radius:10px;padding:1rem;margin:0.5rem 0;border:1px solid #2d3148">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:1.2rem">{medal} {badge(provider)}</span>
                <span style="color:#a5b4fc;font-size:1rem;font-weight:700">Overall: {row['avg_overall']:.3f}</span>
            </div>
            <div style="display:flex;gap:2rem;margin-top:0.6rem;font-size:0.82rem;color:#64748b">
                <span>Hallucination: <b style="color:#cbd5e1">{row['avg_hallucination']:.3f}</b></span>
                <span>Relevance: <b style="color:#cbd5e1">{row['avg_relevance']:.3f}</b></span>
                <span>Runs: <b style="color:#cbd5e1">{int(row['total_runs'])}</b></span>
                <span>Alerts: <b style="color:#ef4444">{int(row['alerts'])}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if cost_data:
        st.subheader("💸 Cost Comparison")
        cost_df = pd.DataFrame(cost_data)
        fig_cost = px.bar(
            cost_df, x="provider", y="avg_cost",
            color="provider", color_discrete_map=PROVIDER_COLORS,
            title="Average Cost per Query (USD)",
            template="plotly_dark",
        )
        fig_cost.update_layout(**CHART_LAYOUT, showlegend=False)
        st.plotly_chart(fig_cost, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — ALERTS
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🚨 Alerts":
    st.title("🚨 Alert Feed")
    st.caption("Evaluations that crossed quality or latency thresholds")

    alerts_data = api_get("/alerts")

    if not alerts_data:
        st.success("✅ No alerts triggered yet — all models performing well!")
        st.stop()

    alerts_df = pd.DataFrame(alerts_data)
    st.metric("Total Alerts", len(alerts_df))

    for _, row in alerts_df.iterrows():
        provider = row.get("provider", "?")
        reason   = row.get("alert_reason", "Unknown reason")
        created  = str(row.get("created_at", ""))[:19]
        st.markdown(f"""
        <div class="alert-box">
            <div style="display:flex;justify-content:space-between">
                <span>{badge(provider)} &nbsp; ⚠️ {reason}</span>
                <span style="color:#64748b;font-size:0.75rem">{created}</span>
            </div>
            <div style="margin-top:0.3rem;font-size:0.78rem;color:#94a3b8">
                Overall: {row.get('overall_score', 0):.2f} |
                Hallucination: {row.get('hallucination_score', 0):.2f} |
                Trace: {str(row.get('trace_id',''))[:8]}…
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — RAW TRACES
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📋 Raw Traces":
    st.title("📋 Raw Trace Logs")

    traces_data = api_get("/traces?limit=100")
    evals_data  = api_get("/evals?limit=100")

    if not traces_data:
        st.info("No traces yet.")
        st.stop()

    traces = pd.DataFrame(traces_data)
    evals  = pd.DataFrame(evals_data) if evals_data else pd.DataFrame()

    st.subheader("Traces")
    trace_cols = [c for c in [
        "trace_id", "provider", "model", "category",
        "latency_ms", "total_tokens", "cost_usd", "created_at"
    ] if c in traces.columns]
    st.dataframe(traces[trace_cols], use_container_width=True)

    if not evals.empty:
        st.subheader("Evaluation Scores")
        eval_cols = [c for c in [
            "trace_id", "provider", "overall_score",
            "hallucination_score", "relevance_score",
            "toxicity_score", "alert_triggered", "created_at"
        ] if c in evals.columns]
        st.dataframe(evals[eval_cols], use_container_width=True)

    st.subheader("⬇️ Export Data")
    dc1, dc2 = st.columns(2)
    dc1.download_button("Download Traces CSV", traces.to_csv(index=False), "traces.csv", "text/csv")
    if not evals.empty:
        dc2.download_button("Download Evals CSV", evals.to_csv(index=False), "evals.csv", "text/csv")