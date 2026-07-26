from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db import get_db_connection
from generate_answers import (
    AnswerOutput,
    build_instructions,
    build_user_prompt,
    prepare_chunk_context,
    validate_answer_chunk_ids,
)
from llm_client import get_default_model, llm_structured_retry
from pricing import estimate_token_cost_usd
from retrieve_vector import retrieve_chunks_vector

APP_TITLE = "aus-ai-security-navigator"
DEFAULT_TOP_K = 5

SIZE_OPTIONS = [
    "all_sizes",
    "small_business",
    "medium_business",
    "large_enterprise_gov_critical",
]

ROLE_OPTIONS = [
    "ai_consumer",
    "ai_builder",
]

SIZE_LABEL_MAP = {
    "all_sizes": "All organisation sizes",
    "small_business": "Small business",
    "medium_business": "Medium business",
    "large_enterprise_gov_critical": "Large enterprise / government / critical infrastructure",
}

ROLE_LABEL_MAP = {
    "any": "Any role",
    "ai_consumer": "AI consumer",
    "ai_builder": "AI builder",
}


def run_live_answer(
    question: str,
    size_tag: str | None,
    role_tag: str | None,
    top_k: int,
    model: str | None = None,
) -> tuple[dict[str, Any], Any]:
    retrieved = retrieve_chunks_vector(
        query=question,
        limit=top_k,
        size_tag=None if size_tag == "all_sizes" else size_tag,
        role_tag=role_tag,
    )
    retrieved_context = prepare_chunk_context(retrieved)

    question_row = {
        "question": question,
        "target_size": size_tag,
        "target_role": role_tag,
    }

    parsed, usage = llm_structured_retry(
        instructions=build_instructions(),
        user_prompt=build_user_prompt(question_row, retrieved_context),
        output_type=AnswerOutput,
        model=model,
    )

    validated_answer_chunk_ids = validate_answer_chunk_ids(
        returned_ids=parsed.answer_chunk_ids,
        retrieved_context=retrieved_context,
    )

    grounded = parsed.grounded
    answer_text = parsed.answer_text.strip()

    if grounded and not validated_answer_chunk_ids:
        grounded = False
        answer_text = "I don't know based on the retrieved context."

    if not grounded and not answer_text:
        answer_text = "I don't know based on the retrieved context."

    if not grounded and "i don't know based on the retrieved context" in answer_text.lower():
        answer_text = "I don't know based on the retrieved context."

    result = {
        "question": question,
        "target_size": size_tag,
        "target_role": role_tag,
        "retrieved_context": retrieved_context,
        "retrieved_count": len(retrieved_context),
        "answer_text": answer_text,
        "answer_chunk_ids": validated_answer_chunk_ids,
        "grounded": grounded,
        "model_id": model or get_default_model(),
        "top_k": top_k,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage, "total_tokens", 0) or 0,
        },
    }
    return result, usage


def save_conversation(result: dict[str, Any], response_time: float) -> tuple[int, float, bool]:
    usage = result["usage"]
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    total_tokens = usage.get("total_tokens", 0) or 0

    cost, pricing_found = estimate_token_cost_usd(
        model_id=result["model_id"],
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (
                    question,
                    answer,
                    model,
                    target_size,
                    target_role,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    response_time,
                    cost,
                    timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    result["question"],
                    result["answer_text"],
                    result["model_id"],
                    result.get("target_size"),
                    result.get("target_role"),
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    response_time,
                    cost,
                    datetime.now(timezone.utc),
                ),
            )
            conversation_id = cur.fetchone()[0]
        conn.commit()
        return conversation_id, cost, pricing_found
    finally:
        conn.close()


def save_feedback(conversation_id: int, score: int) -> None:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feedback (conversation_id, score, timestamp)
                VALUES (%s, %s, %s)
                """,
                (conversation_id, score, datetime.now(timezone.utc)),
            )
        conn.commit()
    finally:
        conn.close()


def fetch_dashboard_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    question,
                    answer,
                    model,
                    target_size,
                    target_role,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    response_time,
                    cost,
                    timestamp
                FROM conversations
                ORDER BY timestamp ASC
                """
            )
            conversations_rows = cur.fetchall()
            conversations_columns = [desc[0] for desc in cur.description]

            cur.execute(
                """
                SELECT
                    id,
                    conversation_id,
                    score,
                    timestamp
                FROM feedback
                ORDER BY timestamp ASC
                """
            )
            feedback_rows = cur.fetchall()
            feedback_columns = [desc[0] for desc in cur.description]
    finally:
        conn.close()

    conversations_df = pd.DataFrame(conversations_rows, columns=conversations_columns)
    feedback_df = pd.DataFrame(feedback_rows, columns=feedback_columns)

    return conversations_df, feedback_df


def render_evidence(result: dict[str, Any]) -> None:
    retrieved_context = result.get("retrieved_context", [])
    answer_chunk_ids = set(result.get("answer_chunk_ids", []))

    st.subheader("Retrieved evidence")
    if not retrieved_context:
        st.info("No chunks were retrieved.")
        return

    for chunk in retrieved_context:
        heading_path = " > ".join(chunk.get("heading_path", [])) or "(no heading path)"
        similarity = chunk.get("similarity")
        distance = chunk.get("cosine_distance")
        is_used = chunk["chunk_id"] in answer_chunk_ids

        label = f"#{chunk['rank']} - {chunk.get('document_title') or 'Untitled'}"
        if is_used:
            label += " ✅ used in answer"

        with st.expander(label, expanded=False):
            st.markdown(f"**Chunk ID:** `{chunk['chunk_id']}`")
            st.markdown(f"**Heading path:** {heading_path}")
            st.markdown(
                f"**Similarity:** {similarity:.4f}" if similarity is not None else "**Similarity:** n/a"
            )
            st.markdown(
                f"**Cosine distance:** {distance:.4f}" if distance is not None else "**Cosine distance:** n/a"
            )
            st.markdown(f"**Size tag:** `{chunk.get('size_audience_tag')}`")
            st.markdown(f"**Role tags:** `{chunk.get('role_audience_tags', [])}`")
            st.text_area(
                "Chunk text",
                value=chunk.get("chunk_text", ""),
                height=180,
                disabled=True,
                key=f"chunk_text_{chunk['chunk_id']}",
            )


def render_feedback_controls() -> None:
    conversation_id = st.session_state.get("conversation_id")
    feedback_saved = st.session_state.get("feedback_saved", False)

    if not conversation_id:
        return

    st.subheader("Feedback")
    if feedback_saved:
        st.success("Feedback recorded.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Helpful", width="stretch", key="feedback_helpful"):
            save_feedback(conversation_id, 1)
            st.session_state["feedback_saved"] = True
            st.rerun()

    with col2:
        if st.button("👎 Not helpful", width="stretch", key="feedback_not_helpful"):
            save_feedback(conversation_id, -1)
            st.session_state["feedback_saved"] = True
            st.rerun()


def render_navigator_tab() -> None:
    st.header("AI Navigator")
    st.write("Ask a question about ACSC AI security guidance and inspect the grounded evidence.")

    active_model = get_default_model()

    with st.sidebar:
        st.subheader("Filters")
        size_tag = st.selectbox(
            "Organisation size",
            options=SIZE_OPTIONS,
            index=0,
            format_func=lambda key: SIZE_LABEL_MAP.get(key, key),
        )
        role_option = st.selectbox(
            "Role",
            options=["any"] + ROLE_OPTIONS,
            index=0,
            format_func=lambda key: ROLE_LABEL_MAP.get(key, key),
        )
        role_tag = None if role_option == "any" else role_option
        top_k = st.slider("Top-k retrieved chunks", min_value=3, max_value=10, value=DEFAULT_TOP_K, step=1)
        st.caption(f"Model: {active_model}")

    question = st.text_area(
        "Question",
        placeholder="Example: What should a medium-sized organisation do to secure AI data used in model development?",
        height=120,
    )

    if st.button("Generate answer", type="primary", width="stretch", key="generate_answer"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            st.session_state["feedback_saved"] = False
            st.session_state["conversation_id"] = None
            st.session_state["last_pricing_found"] = True
            st.session_state["last_cost"] = 0.0

            with st.spinner("Retrieving guidance and generating answer..."):
                start = time.perf_counter()
                result, _usage = run_live_answer(
                    question=question.strip(),
                    size_tag=size_tag,
                    role_tag=role_tag,
                    top_k=top_k,
                    model=active_model,
                )
                response_time = time.perf_counter() - start
                conversation_id, cost, pricing_found = save_conversation(result, response_time)

            st.session_state["last_result"] = result
            st.session_state["response_time"] = response_time
            st.session_state["conversation_id"] = conversation_id
            st.session_state["last_pricing_found"] = pricing_found
            st.session_state["last_cost"] = cost
            st.rerun()

    result = st.session_state.get("last_result")
    if result:
        st.subheader("Grounded answer")
        if result.get("grounded"):
            st.success("Answer grounded in retrieved ACSC context.")
        else:
            st.warning("The system could not fully ground the answer in the retrieved context.")

        st.write(result["answer_text"])
        st.caption(f"Retrieved chunks: {result.get('retrieved_count', 0)}")

        usage = result.get("usage", {})
        response_time = st.session_state.get("response_time", 0.0)
        last_cost = st.session_state.get("last_cost", 0.0)
        pricing_found = st.session_state.get("last_pricing_found", True)

        if not pricing_found:
            st.warning(
                f"No pricing entry was found for model `{result['model_id']}`. "
                "Cost was recorded as $0.00. Update src/pricing.py to enable cost tracking.",
                icon="⚠️",
            )

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Prompt tokens", usage.get("prompt_tokens", 0))
        col2.metric("Completion tokens", usage.get("completion_tokens", 0))
        col3.metric("Total tokens", usage.get("total_tokens", 0))
        col4.metric("Latency (s)", f"{response_time:.2f}")
        col5.metric("Estimated cost (USD)", f"${last_cost:.6f}")

        render_evidence(result)
        render_feedback_controls()


def render_dashboard_tab() -> None:
    st.header("Monitoring Dashboard")
    conversations_df, feedback_df = fetch_dashboard_frames()

    if conversations_df.empty:
        st.info("No conversation logs yet. Submit a question in the AI Navigator tab first.")
        return

    total_conversations = len(conversations_df)
    avg_latency = float(conversations_df["response_time"].mean()) if "response_time" in conversations_df else 0.0
    total_cost = float(conversations_df["cost"].sum()) if "cost" in conversations_df else 0.0
    thumbs_up = int((feedback_df["score"] == 1).sum()) if not feedback_df.empty else 0
    thumbs_down = int((feedback_df["score"] == -1).sum()) if not feedback_df.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total conversations", total_conversations)
    m2.metric("Average latency (s)", f"{avg_latency:.2f}")
    m3.metric("Total cost (USD)", f"${total_cost:.6f}")
    m4.metric("Feedback", f"👍 {thumbs_up} / 👎 {thumbs_down}")

    conversations_df["timestamp"] = pd.to_datetime(conversations_df["timestamp"])
    if not feedback_df.empty:
        feedback_df["timestamp"] = pd.to_datetime(feedback_df["timestamp"])

    missing_price_models = sorted(
        conversations_df.loc[conversations_df["cost"] == 0, "model"].dropna().unique().tolist()
    )
    if missing_price_models:
        st.warning(
            "Some logged rows have $0.00 cost. This may be valid for tiny requests, but it can also mean "
            f"pricing is not configured for: {', '.join(missing_price_models)}",
            icon="⚠️",
        )

    display_df = conversations_df.copy().reset_index(drop=True)
    display_df["Query Number"] = [f"Q{i + 1}" for i in range(len(display_df))]

    st.subheader("Response time per query")
    fig_latency = px.line(
        display_df,
        x="Query Number",
        y="response_time",
        markers=True,
        labels={
            "response_time": "Response Time (seconds)",
            "Query Number": "Query sequence",
        },
    )
    fig_latency.update_yaxes(rangemode="tozero", title="Response time (seconds)")
    fig_latency.update_xaxes(title="Query sequence", type="category")
    fig_latency.update_traces(hovertemplate="Query %{x}<br>Response time: %{y:.2f} s<extra></extra>")
    st.plotly_chart(fig_latency, width="stretch")

    st.subheader("Cost per query")
    fig_cost = px.line(
        display_df,
        x="Query Number",
        y="cost",
        markers=True,
        labels={
            "cost": "Estimated Cost ($ USD)",
            "Query Number": "Query sequence",
        },
    )
    fig_cost.update_yaxes(rangemode="tozero", tickformat="$.4f", title="Estimated cost ($ USD)")
    fig_cost.update_xaxes(title="Query sequence", type="category")
    fig_cost.update_traces(hovertemplate="Query %{x}<br>Cost: $%{y:.4f}<extra></extra>")
    st.plotly_chart(fig_cost, width="stretch")

    st.subheader("Feedback counts")
    feedback_counts = pd.DataFrame(
        {
            "label": ["Thumbs up", "Thumbs down"],
            "count": [thumbs_up, thumbs_down],
        }
    ).set_index("label")
    st.bar_chart(feedback_counts)

    st.subheader("Token usage per request")
    token_chart = display_df.set_index("Query Number")[["prompt_tokens", "completion_tokens", "total_tokens"]]
    st.bar_chart(token_chart)

    st.subheader("Conversations per hour")
    volume_chart = conversations_df.copy()
    volume_chart["hour_bucket"] = volume_chart["timestamp"].dt.strftime("%H:00")
    volume_chart = volume_chart.groupby("hour_bucket").size().reset_index(name="query_count")
    fig_volume = px.bar(
        volume_chart,
        x="hour_bucket",
        y="query_count",
        labels={
            "hour_bucket": "Hour",
            "query_count": "Number of queries",
        },
    )
    fig_volume.update_xaxes(type="category", title="Hour")
    fig_volume.update_yaxes(rangemode="tozero", title="Number of queries", dtick=1)
    fig_volume.update_traces(hovertemplate="Hour %{x}<br>Queries: %{y}<extra></extra>")
    st.plotly_chart(fig_volume, width="stretch")

    st.subheader("Queries by organisation size")
    size_counts = (
        conversations_df["target_size"]
        .fillna("unspecified")
        .map(lambda key: SIZE_LABEL_MAP.get(key, key))
        .value_counts()
        .to_frame("count")
    )
    st.bar_chart(size_counts)

    st.subheader("Queries by role")
    role_counts = (
        conversations_df["target_role"]
        .fillna("unspecified")
        .map(lambda key: ROLE_LABEL_MAP.get(key, key))
        .value_counts()
        .to_frame("count")
    )
    st.bar_chart(role_counts)

    st.subheader("Recent conversations")
    recent_df = conversations_df.sort_values("timestamp", ascending=False).head(10).copy()
    recent_df["answer_snippet"] = recent_df["answer"].astype(str).str.slice(0, 180)
    recent_df["target_size_display"] = recent_df["target_size"].fillna("unspecified").map(
        lambda key: SIZE_LABEL_MAP.get(key, key)
    )
    recent_df["target_role_display"] = recent_df["target_role"].fillna("unspecified").map(
        lambda key: ROLE_LABEL_MAP.get(key, key)
    )
    st.dataframe(
        recent_df[
            [
                "timestamp",
                "question",
                "target_size_display",
                "target_role_display",
                "answer_snippet",
                "response_time",
                "cost",
                "total_tokens",
            ]
        ].rename(
            columns={
                "target_size_display": "organisation_size",
                "target_role_display": "role",
                "response_time": "latency_seconds",
                "cost": "cost_usd",
            }
        ),
        width="stretch",
        hide_index=True,
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="wide")

    st.title("🛡️ aus-ai-security-navigator")
    st.caption("Interactive ACSC AI security RAG assistant with evidence inspection and monitoring.")

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None
    if "conversation_id" not in st.session_state:
        st.session_state["conversation_id"] = None
    if "feedback_saved" not in st.session_state:
        st.session_state["feedback_saved"] = False
    if "response_time" not in st.session_state:
        st.session_state["response_time"] = 0.0
    if "last_pricing_found" not in st.session_state:
        st.session_state["last_pricing_found"] = True
    if "last_cost" not in st.session_state:
        st.session_state["last_cost"] = 0.0

    tab1, tab2 = st.tabs(["AI Navigator", "Monitoring Dashboard"])
    with tab1:
        render_navigator_tab()
    with tab2:
        render_dashboard_tab()


if __name__ == "__main__":
    main()