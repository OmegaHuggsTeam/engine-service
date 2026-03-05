"""
Neural Link Monitor Dashboard - Phase 6
Real-time monitoring of Neo4j graph, agent health, and system metrics.
Powered by Streamlit + Plotly.

Usage:
    streamlit run src/interface/monitor_dashboard.py --server.port 8501
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ================================================================
# PAGE CONFIG
# ================================================================

st.set_page_config(
    page_title="Neural Link Monitor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark-themed dashboard
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5em;
        font-weight: bold;
        color: #e94560;
    }
    .metric-label {
        font-size: 0.9em;
        color: #a0a0b0;
        margin-top: 4px;
    }
    .status-healthy {
        color: #00e676;
        font-weight: bold;
    }
    .status-degraded {
        color: #ffab00;
        font-weight: bold;
    }
    .status-critical {
        color: #ff1744;
        font-weight: bold;
    }
    .agent-card {
        background: #1a1a2e;
        border-left: 4px solid #0f3460;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .agent-card.domain { border-left-color: #00e676; }
    .agent-card.operator { border-left-color: #448aff; }
    .agent-card.specialist { border-left-color: #e94560; }
    .header-banner {
        background: linear-gradient(90deg, #0f3460, #e94560, #0f3460);
        background-size: 200% 100%;
        animation: gradient-shift 3s ease infinite;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 24px;
    }
    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ================================================================
# DATA FETCHERS
# ================================================================

@st.cache_resource
def get_graph_manager():
    """Get or create GraphManager singleton."""
    try:
        from src.neural_link.graph.manager import GraphManager
        gm = GraphManager.from_env()
        if gm.verify_connectivity():
            return gm
    except Exception:
        pass
    return None


def fetch_node_counts(gm) -> dict:
    """Fetch count of each node label."""
    if not gm:
        return {}
    try:
        results = gm.execute_read(
            "MATCH (n) WITH labels(n) AS lbls UNWIND lbls AS l "
            "RETURN l AS label, count(*) AS cnt ORDER BY cnt DESC"
        )
        return {r["label"]: r["cnt"] for r in results}
    except Exception as e:
        return {"error": str(e)}


def fetch_agents(gm) -> list[dict]:
    """Fetch all agents with their details."""
    if not gm:
        return []
    try:
        return gm.execute_read(
            "MATCH (a:Agent) "
            "RETURN a.id AS id, a.name AS name, a.type AS type, "
            "       a.capabilities AS capabilities, a.status AS status, "
            "       a.success_rate AS success_rate, a.module_path AS module_path "
            "ORDER BY a.type, a.name"
        )
    except Exception:
        return []


def fetch_concepts(gm) -> list[dict]:
    """Fetch concepts with connection counts."""
    if not gm:
        return []
    try:
        return gm.execute_read(
            "MATCH (c:Concept) "
            "OPTIONAL MATCH (c)-[r:RELATED_TO]-() "
            "RETURN c.name AS name, c.domain AS domain, "
            "       c.confidence AS confidence, count(r) AS connections "
            "ORDER BY connections DESC"
        )
    except Exception:
        return []


def fetch_relationships(gm) -> dict:
    """Fetch relationship type counts."""
    if not gm:
        return {}
    try:
        results = gm.execute_read(
            "MATCH ()-[r]->() "
            "RETURN type(r) AS rel_type, count(r) AS cnt "
            "ORDER BY cnt DESC"
        )
        return {r["rel_type"]: r["cnt"] for r in results}
    except Exception:
        return {}


def fetch_recent_tasks(gm) -> list[dict]:
    """Fetch recent tasks."""
    if not gm:
        return []
    try:
        return gm.execute_read(
            "MATCH (t:Task) "
            "RETURN t.id AS id, t.description AS description, "
            "       t.status AS status, t.type AS type, "
            "       t.created_at AS created_at "
            "ORDER BY t.created_at DESC LIMIT 10"
        )
    except Exception:
        return []


def fetch_health_checks(gm) -> list[dict]:
    """Fetch recent health check results."""
    if not gm:
        return []
    try:
        return gm.execute_read(
            "MATCH (h:HealthCheck) "
            "RETURN h.timestamp AS timestamp, h.overall AS overall, "
            "       h.check_time_ms AS check_time_ms, h.details AS details "
            "ORDER BY h.timestamp DESC LIMIT 5"
        )
    except Exception:
        return []


def run_live_health_check() -> dict:
    """Execute a live health check via DevOps Agent."""
    try:
        from src.agents.devops_agent import DevOpsAgent
        agent = DevOpsAgent()
        return agent.full_health_check()
    except Exception as e:
        return {"overall": "ERROR", "error": str(e)}


# ================================================================
# DASHBOARD LAYOUT
# ================================================================

def render_header():
    st.markdown(
        '<div class="header-banner">'
        '<h1 style="color: white; margin: 0;">NEURAL LINK MONITOR</h1>'
        '<p style="color: #d0d0e0; margin: 4px 0 0 0;">Phase 6 - Real-Time System Observatory</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_system_pulse(gm):
    """Top row: key system metrics."""
    st.subheader("System Pulse")

    node_counts = fetch_node_counts(gm)
    relationships = fetch_relationships(gm)
    total_nodes = sum(v for v in node_counts.values() if isinstance(v, int))
    total_rels = sum(relationships.values())

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Nodes", total_nodes, help="All nodes in Neo4j")
    with col2:
        st.metric("Agents", node_counts.get("Agent", 0), help="Registered agents")
    with col3:
        st.metric("Concepts", node_counts.get("Concept", 0), help="Knowledge concepts")
    with col4:
        st.metric("Relationships", total_rels, help="Graph edges")
    with col5:
        neo4j_status = "ONLINE" if gm else "OFFLINE"
        st.metric("Neo4j", neo4j_status)

    return node_counts, relationships


def render_node_distribution(node_counts):
    """Pie chart of node types."""
    if not node_counts or "error" in node_counts:
        st.warning("No node data available")
        return

    labels = list(node_counts.keys())
    values = list(node_counts.values())

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker=dict(
            colors=["#e94560", "#448aff", "#00e676", "#ffab00", "#ab47bc", "#26c6da", "#ff7043"],
            line=dict(color="#0e1117", width=2),
        ),
        textinfo="label+value",
        textfont=dict(size=13, color="white"),
    )])
    fig.update_layout(
        title=dict(text="Node Distribution", font=dict(color="white", size=16)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(font=dict(color="white")),
        height=350,
        margin=dict(t=40, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_relationship_chart(relationships):
    """Bar chart of relationship types."""
    if not relationships:
        st.info("No relationships yet")
        return

    types = list(relationships.keys())
    counts = list(relationships.values())

    fig = go.Figure(data=[go.Bar(
        x=types,
        y=counts,
        marker=dict(
            color=counts,
            colorscale=[[0, "#0f3460"], [0.5, "#e94560"], [1, "#ff6b6b"]],
        ),
        text=counts,
        textposition="outside",
        textfont=dict(color="white"),
    )])
    fig.update_layout(
        title=dict(text="Relationship Types", font=dict(color="white", size=16)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        xaxis=dict(gridcolor="#1a1a2e"),
        yaxis=dict(gridcolor="#1a1a2e"),
        height=350,
        margin=dict(t=40, b=20, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_agent_roster(agents):
    """Agent health cards with status indicators."""
    st.subheader("Agent Roster")

    if not agents:
        st.warning("No agents found in graph")
        return

    type_colors = {"domain": "#00e676", "operator": "#448aff", "specialist": "#e94560"}
    type_icons = {"domain": "🟢", "operator": "🔵", "specialist": "🔴"}

    # Group by type
    by_type = {}
    for agent in agents:
        t = agent.get("type", "unknown")
        by_type.setdefault(t, []).append(agent)

    for agent_type, group in by_type.items():
        color = type_colors.get(agent_type, "#888")
        icon = type_icons.get(agent_type, "⚪")
        st.markdown(f"**{icon} {agent_type.upper()} AGENTS** ({len(group)})")

        cols = st.columns(min(len(group), 3))
        for i, agent in enumerate(group):
            with cols[i % 3]:
                rate = float(agent.get("success_rate") or 1.0)
                status = agent.get("status", "active")
                caps = agent.get("capabilities", [])
                if isinstance(caps, str):
                    caps = [caps]

                rate_color = "#00e676" if rate >= 0.7 else "#ffab00" if rate >= 0.5 else "#ff1744"
                status_class = "healthy" if status == "active" else "degraded"

                st.markdown(
                    f'<div class="agent-card {agent_type}">'
                    f'<strong style="color: {color};">{agent["name"]}</strong><br>'
                    f'<span class="status-{status_class}">● {status}</span> '
                    f'| <span style="color: {rate_color};">Success: {rate:.0%}</span><br>'
                    f'<small style="color: #808090;">{", ".join(caps[:4])}'
                    f'{"..." if len(caps) > 4 else ""}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


def render_concept_network(concepts):
    """Concept bubble chart."""
    st.subheader("Concept Network")

    if not concepts:
        st.info("No concepts discovered yet")
        return

    names = [c["name"] for c in concepts]
    connections = [c.get("connections", 0) for c in concepts]
    confidence = [float(c.get("confidence") or 0.5) for c in concepts]

    fig = go.Figure(data=[go.Scatter(
        x=list(range(len(names))),
        y=connections,
        mode="markers+text",
        marker=dict(
            size=[max(20, c * 8) for c in connections],
            color=confidence,
            colorscale=[[0, "#0f3460"], [0.5, "#e94560"], [1, "#00e676"]],
            colorbar=dict(title="Confidence", tickfont=dict(color="white"), titlefont=dict(color="white")),
            line=dict(width=1, color="#fff"),
        ),
        text=names,
        textposition="top center",
        textfont=dict(color="white", size=12),
    )])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        xaxis=dict(visible=False),
        yaxis=dict(title="Connections", gridcolor="#1a1a2e"),
        height=350,
        margin=dict(t=20, b=20, l=40, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_live_health():
    """Live health check panel."""
    st.subheader("Live Health Check")

    if st.button("Run Health Check Now", type="primary"):
        with st.spinner("Running diagnostics..."):
            result = run_live_health_check()

        overall = result.get("overall", "UNKNOWN")
        color_map = {"HEALTHY": "#00e676", "DEGRADED": "#ffab00", "CRITICAL": "#ff1744"}
        color = color_map.get(overall, "#888")

        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-value" style="color: {color};">{overall}</div>'
            f'<div class="metric-label">Overall Status | {result.get("check_time_ms", "?")}ms</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        components = result.get("components", {})
        if components:
            cols = st.columns(len(components))
            for i, (name, info) in enumerate(components.items()):
                with cols[i]:
                    comp_status = info.get("status", "unknown")
                    comp_color = color_map.get(comp_status.upper(), "#888")
                    details = []
                    for k, v in info.items():
                        if k != "status":
                            details.append(f"{k}: {v}")
                    detail_str = "<br>".join(details[:3])
                    st.markdown(
                        f'<div class="metric-card">'
                        f'<strong style="color: {comp_color};">{name.upper()}</strong><br>'
                        f'<span class="status-{comp_status}" style="font-size: 1.4em;">'
                        f'{"●" if comp_status == "healthy" else "▲" if comp_status == "degraded" else "✖"} '
                        f'{comp_status}</span><br>'
                        f'<small style="color: #a0a0b0;">{detail_str}</small>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )


def render_recent_tasks(tasks):
    """Recent tasks table."""
    st.subheader("Recent Tasks")
    if not tasks:
        st.info("No tasks recorded yet")
        return

    for task in tasks:
        status = task.get("status", "unknown")
        status_icon = {"completed": "✅", "failed": "❌", "in_progress": "⏳", "pending": "🔲"}.get(status, "❓")
        st.markdown(
            f"- {status_icon} **{task.get('type', 'unknown')}** | "
            f"{task.get('description', 'N/A')[:80]} | "
            f"`{status}`"
        )


def render_sidebar_controls():
    """Sidebar with refresh controls and system info."""
    with st.sidebar:
        st.markdown("### Controls")
        auto_refresh = st.checkbox("Auto-refresh (10s)", value=False)
        if auto_refresh:
            time.sleep(10)
            st.rerun()

        st.markdown("---")
        st.markdown("### System Info")
        st.markdown(f"- **Time**: {datetime.now().strftime('%H:%M:%S')}")
        st.markdown(f"- **Python**: {sys.version.split()[0]}")
        st.markdown(f"- **Project**: mcp-engine-service")
        st.markdown(f"- **Phase**: 6 - Dashboard")

        st.markdown("---")
        st.markdown("### Quick Actions")
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.markdown(
            '<small style="color: #606070;">'
            'Neural Link Orchestrator v0.1.0<br>'
            'Phase 6 - Monitor Dashboard'
            '</small>',
            unsafe_allow_html=True,
        )


# ================================================================
# MAIN
# ================================================================

def main():
    render_header()
    render_sidebar_controls()

    gm = get_graph_manager()

    if not gm:
        st.error(
            "Neo4j is not available. Start the container:\n\n"
            "```bash\ndocker compose -f infra/docker-compose.yml up neo4j -d\n```"
        )
        return

    # Row 1: System Pulse
    node_counts, relationships = render_system_pulse(gm)

    st.markdown("---")

    # Row 2: Charts
    col_left, col_right = st.columns(2)
    with col_left:
        render_node_distribution(node_counts)
    with col_right:
        render_relationship_chart(relationships)

    st.markdown("---")

    # Row 3: Agent Roster
    agents = fetch_agents(gm)
    render_agent_roster(agents)

    st.markdown("---")

    # Row 4: Concepts + Health
    col_left2, col_right2 = st.columns(2)
    with col_left2:
        concepts = fetch_concepts(gm)
        render_concept_network(concepts)
    with col_right2:
        render_live_health()

    st.markdown("---")

    # Row 5: Recent Tasks
    tasks = fetch_recent_tasks(gm)
    render_recent_tasks(tasks)

    # Footer
    st.markdown(
        '<div style="text-align: center; color: #404050; margin-top: 40px;">'
        f'Neural Link Monitor | {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | '
        f'{sum(v for v in node_counts.values() if isinstance(v, int))} nodes | '
        f'{len(agents)} agents online'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
