import csv
import datetime
import html
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / "rental_law_queries_resolution_with_evaluation_and_security_jev.ipynb"

CATEGORIES = (
    "scope",
    "needs_fact",
    "missing_fact",
    "hostile",
    "sufficiency",
    "relevance",
    "groundedness",
    "coherence",
)

QUICK_ACTIONS = {
    "📅 Move-out notice": (
        "how long before I move, do I need to tell my landlord I'm leaving?  "
        "my lease is oral and month to month"
    ),
    "💵 Deposit return": "How do I get my security deposit back?",
    "📈 Rent increase": (
        "If my rent is being increased by more than 5%, is the landlord expected "
        "to provide the advance written notice based on how long I've lived in the apartment?"
    ),
    "🚪 Unlawful entry": (
        "My landlord entered my apartment without giving prior notice. "
        "There was no emergency and I did not consent. This was during my fixed-term lease."
    ),
    "🔧 Unrepaired heat": "My landlord has not fixed the heating. What are my rights?",
}

STAMP_COLORS = {
    "success": "#E8F5E9",
    "insufficient_info": "#FFF8E1",
    "hitl_escalation": "#FFF3E0",
    "(waiting for one fact)": "#E3F2FD",
    "guardrail": "#F3E5F5",
    "out_of_scope": "#F5F5F5",
    "error": "#FFEBEE",
}

SECRET_STOP = (
    "The run stopped before a stamp was written. "
    "The Space needs the secrets TYPESAFE_API_KEY and OPENROUTER_API_KEY."
)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_engine():
    notebook = json.loads(NOTEBOOK.read_text())
    namespace = {"__name__": "space"}
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if source.strip().endswith("structural_checks()"):
            source = source[: source.rfind("structural_checks()")]
        exec(source, namespace)
    return namespace


def _num(value):
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def judgment_rows(result):
    result = result or {}
    rows = {
        "scope": (result.get("scope_choice") or "", result.get("parse_confidence")),
        "needs_fact": ("", result.get("needs_fact_noul")),
        "missing_fact": (result.get("missing_fact") or "", result.get("missing_fact_confidence")),
        "hostile": ("", result.get("hostile_noul")),
        "sufficiency": (result.get("validation_status") or "", result.get("rag_chunks_confidence")),
        "relevance": ("", result.get("relevance_score")),
        "groundedness": ("", result.get("groundedness_score")),
        "coherence": ("", result.get("reasoning_coherence")),
    }
    if result.get("exit_reason") == "guardrail" and result.get("guardrail_reason"):
        rows["hostile"] = (result.get("guardrail_reason"), rows["hostile"][1])
    return [[name, rows[name][0], _num(rows[name][1])] for name in CATEGORIES]


def split_turn(pending, text):
    if pending:
        return pending, text
    return text, ""


def visible_reply(result, question):
    if result.get("awaiting_clarification"):
        return "(waiting for one fact)", result.get("clarification_query") or "", question
    return result.get("exit_reason") or "(none)", result.get("final_output") or "", ""


def judgment_html(result):
    body = []
    for name, choice, score in judgment_rows(result):
        body.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{html.escape(choice)}</td>"
            f"<td>{html.escape(score)}</td>"
            "</tr>"
        )
    return (
        "<table style=\"width:100%;border-collapse:collapse;font-size:.92em;\">"
        "<thead><tr>"
        "<th style=\"text-align:left;padding:4px 6px;\">Category</th>"
        "<th style=\"text-align:left;padding:4px 6px;\">Choice</th>"
        "<th style=\"text-align:left;padding:4px 6px;\">Score</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def audit_csv(rows):
    fields = [
        "time", "stamp", "question", "clarification", "scope", "scope_score",
        "needs_fact", "missing_fact", "missing_fact_score", "hostile",
        "sufficiency", "sufficiency_score", "relevance", "groundedness",
        "coherence", "tools", "sentence",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def audit_html(rows):
    columns = [
        ("time", "Time"),
        ("stamp", "Stamp"),
        ("question", "Question"),
        ("sufficiency", "Sufficiency"),
        ("sufficiency_score", "Sufficiency score"),
        ("relevance", "Relevance"),
        ("groundedness", "Groundedness"),
        ("coherence", "Coherence"),
        ("scope", "Scope"),
        ("needs_fact", "Needs fact"),
        ("missing_fact", "Missing fact"),
        ("hostile", "Hostile"),
        ("tools", "Tools"),
        ("sentence", "Sentence"),
    ]
    head = "".join(f"<th style=\"text-align:left;padding:6px;\">{label}</th>" for _, label in columns)
    body = []
    for row in rows:
        background = STAMP_COLORS.get(row.get("stamp", ""), "#FFFFFF")
        cells = "".join(
            f"<td style=\"padding:6px;vertical-align:top;\">{html.escape(str(row.get(key) or ''))}</td>"
            for key, _label in columns
        )
        body.append(f"<tr style=\"background:{background};color:#1a1a1a;\">{cells}</tr>")
    return (
        "<div style=\"overflow-x:auto;\">"
        "<table style=\"width:100%;border-collapse:collapse;font-size:.85em;\">"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def audit_row(when, question, clarification, result, stamp, sentence):
    by_name = {row[0]: row for row in judgment_rows(result)}
    tools = result.get("tool_call_log") or []
    return {
        "time": when,
        "stamp": stamp,
        "question": question,
        "clarification": clarification,
        "scope": by_name["scope"][1],
        "scope_score": by_name["scope"][2],
        "needs_fact": by_name["needs_fact"][2],
        "missing_fact": by_name["missing_fact"][1],
        "missing_fact_score": by_name["missing_fact"][2],
        "hostile": by_name["hostile"][2],
        "sufficiency": by_name["sufficiency"][1],
        "sufficiency_score": by_name["sufficiency"][2],
        "relevance": by_name["relevance"][2],
        "groundedness": by_name["groundedness"][2],
        "coherence": by_name["coherence"][2],
        "tools": ", ".join(tools),
        "sentence": sentence,
    }


def main():
    import streamlit as st

    st.set_page_config(
        page_title="Rental Law Assistant",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(
        """
        <style>
        .main-header {
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white; padding: 20px 30px; border-radius: 10px; margin-bottom: 20px;
        }
        .badge-success { background:#4CAF50; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:.85em; }
        .badge-wait { background:#1565C0; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:.85em; }
        .badge-hand { background:#EF6C00; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:.85em; }
        .badge-stop { background:#c62828; color:white; padding:4px 12px; border-radius:20px; font-weight:bold; font-size:.85em; }
        .fact-banner { background:#E3F2FD; border-left:4px solid #1565C0; padding:10px 15px; border-radius:4px; margin:10px 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    @st.cache_resource
    def engine():
        return load_engine()

    @st.cache_resource
    def deps():
        return engine()["live_deps"](directory=str(HERE))

    def init_session():
        defaults = {
            "messages": [],
            "pending_question": "",
            "audit": [],
            "past": [],
            "latest": {},
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def handle_turn(text):
        text = (text or "").strip()
        if not text:
            return
        question, clarification = split_turn(st.session_state.pending_question, text)
        when = utc_now()
        st.session_state.messages.append({"role": "user", "content": text, "timestamp": when})
        try:
            result = engine()["answer"](question, clarification, deps=deps())
        except Exception:
            result = {
                "exit_reason": "error",
                "final_output": SECRET_STOP,
                "awaiting_clarification": False,
            }
        stamp, content, pending = visible_reply(result, question)
        st.session_state.pending_question = pending
        st.session_state.latest = result
        st.session_state.messages.append({
            "role": "assistant",
            "content": content,
            "stamp": stamp,
            "timestamp": when,
        })
        st.session_state.past.append({
            "timestamp": when,
            "question": question,
            "clarification": clarification,
            "stamp": stamp,
            "sentence": content,
        })
        st.session_state.audit.append(
            audit_row(when, question, clarification, result, stamp, content)
        )

    init_session()

    st.markdown(
        """
        <div class="main-header">
            <h1 style="margin:0;font-size:1.8em;">🏠 Rental Law Assistant</h1>
            <p style="margin:6px 0 0 0;opacity:.9;">A tenant question goes in. One sentence comes out. The draft is shown only when the stamp is success.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("## This chat")
        st.caption(
            "The first question embeds the policy and case handbooks, so it takes longer. "
            "If the assistant asks for one fact, answer it in the next message."
        )
        stamp = ""
        if st.session_state.messages:
            for message in reversed(st.session_state.messages):
                if message["role"] == "assistant" and message.get("stamp"):
                    stamp = message["stamp"]
                    break
        st.markdown("### Last stamp")
        if not stamp:
            st.caption("No question yet.")
        elif stamp == "success":
            st.markdown(f'<span class="badge-success">success</span>', unsafe_allow_html=True)
        elif stamp == "(waiting for one fact)":
            st.markdown(f'<span class="badge-wait">waiting for one fact</span>', unsafe_allow_html=True)
        elif stamp in {"insufficient_info", "hitl_escalation"}:
            st.markdown(f'<span class="badge-hand">{stamp}</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="badge-stop">{stamp}</span>', unsafe_allow_html=True)
        st.divider()
        if st.button("Reset session", width="stretch"):
            for key in ("messages", "pending_question", "audit", "past", "latest"):
                st.session_state.pop(key, None)
            init_session()
            st.rerun()
        st.caption("Sufficiency is a probability. Audit scores are 1 to 5. A pass is 3.00 or higher.")

    col_chat, col_info = st.columns([2, 1])

    with col_chat:
        if st.session_state.pending_question:
            st.markdown(
                '<div class="fact-banner">The assistant is waiting for one fact. Reply in the chat.</div>',
                unsafe_allow_html=True,
            )
        st.markdown("### Chat")
        if not st.session_state.messages:
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    "Ask a residential rental question. I answer from the tenant handbook and the case notes. "
                    "A draft is shown only when the stamp is success."
                ),
                "stamp": "",
                "timestamp": utc_now(),
            })
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "assistant" and message.get("stamp"):
                    st.caption(message["stamp"])
                st.write(message["content"])
        placeholder = (
            "Answer the one fact the assistant asked for..."
            if st.session_state.pending_question
            else "Ask a rental question..."
        )
        if user_input := st.chat_input(placeholder):
            with st.spinner("Reading the handbook..."):
                handle_turn(user_input)
            st.rerun()

    with col_info:
        st.markdown("### Jev judgments")
        st.markdown(judgment_html(st.session_state.latest), unsafe_allow_html=True)
        st.caption("Scores are for the latest run.")

        st.markdown("### Past interactions")
        with st.expander("View past questions", expanded=False):
            if st.session_state.past:
                for item in reversed(st.session_state.past):
                    st.markdown(f"**{item['timestamp'][:16]}** — `{item['stamp']}`")
                    st.caption(item["question"])
                    if item.get("clarification"):
                        st.caption(f"Fact: {item['clarification']}")
                    st.write(item["sentence"])
                    st.divider()
            else:
                st.info("No questions yet.")

        st.markdown("### Quick actions")
        for label, prompt in QUICK_ACTIONS.items():
            if st.button(label, width="stretch"):
                with st.spinner("Reading the handbook..."):
                    st.session_state.pending_question = ""
                    handle_turn(prompt)
                st.rerun()

        turns = len(st.session_state.past)
        if turns:
            st.markdown("### This session")
            st.metric("Questions", turns)

    st.divider()
    st.markdown("### Audit trail")
    with st.expander("View the audit trail", expanded=False):
        if st.session_state.audit:
            rows = st.session_state.audit
            successes = sum(1 for row in rows if row["stamp"] == "success")
            handoffs = sum(1 for row in rows if row["stamp"] in {"insufficient_info", "hitl_escalation"})
            refusals = sum(1 for row in rows if row["stamp"] in {"guardrail", "out_of_scope"})
            one, two, three, four = st.columns(4)
            one.metric("Questions", len(rows))
            two.metric("Successes", successes)
            three.metric("Handoffs", handoffs)
            four.metric("Refusals", refusals)
            st.markdown(audit_html(rows), unsafe_allow_html=True)
            st.download_button(
                "Download audit trail (CSV)",
                data=audit_csv(rows),
                file_name=f"rental_audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
            st.markdown(
                "**Colors:** green success · amber insufficient info · orange human review · "
                "blue waiting for one fact · purple guardrail · gray out of scope"
            )
        else:
            st.info("No audit rows yet. Ask a question.")

    st.divider()
    st.markdown(
        """
        <div style="text-align:center;color:#888;font-size:.8em;padding:10px">
            Rental law assistant · Jev judgments · Streamlit
            <br>The draft is published only when the stamp is success.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
