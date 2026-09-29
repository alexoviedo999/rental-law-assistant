import json
from pathlib import Path

import gradio as gr

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


ENGINE = load_engine()
DEPS = None


def get_deps():
    global DEPS
    if DEPS is None:
        DEPS = ENGINE["live_deps"](directory=str(HERE))
    return DEPS


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
        choice, score = rows["hostile"]
        rows["hostile"] = (result.get("guardrail_reason"), score)
    return [[name, rows[name][0], _num(rows[name][1])] for name in CATEGORIES]


def respond(question, clarification):
    question = (question or "").strip()
    clarification = (clarification or "").strip()
    blank = judgment_rows({})
    if not question:
        return "", "Ask a residential rental question.", "", blank
    try:
        result = ENGINE["answer"](question, clarification, deps=get_deps())
    except Exception:
        return (
            "error",
            "The run stopped before a stamp was written. The Space needs the secrets TYPESAFE_API_KEY and OPENROUTER_API_KEY.",
            "",
            blank,
        )
    rows = judgment_rows(result)
    if result.get("awaiting_clarification"):
        asked = result.get("clarification_query") or ""
        return "(waiting for one fact)", asked, asked, rows
    return result.get("exit_reason") or "(none)", result.get("final_output") or "", "", rows


with gr.Blocks(title="Rental law assistant") as demo:
    gr.Markdown(
        "A tenant question goes in. One sentence comes out. "
        "The draft is shown only when the stamp is `success`. "
        "The table lists the Jev categories and scores for this run. "
        "The sufficiency score is the probability of that choice. "
        "Audit scores are 1 to 5, and a pass is 3.00 or higher. "
        "The first question embeds the policy and case PDFs, so it takes longer."
    )
    question = gr.Textbox(label="Question", lines=5)
    clarification = gr.Textbox(
        label="Clarification",
        lines=2,
        placeholder="Leave this empty unless the assistant asks for one fact.",
    )
    ask = gr.Button("Ask")
    stamp = gr.Textbox(label="Stamp")
    sentence = gr.Textbox(label="Sentence", lines=10)
    asked = gr.Textbox(label="Fact requested", lines=2)
    judgments = gr.Dataframe(
        headers=["Category", "Choice", "Score"],
        label="Jev judgments",
        interactive=False,
        value=judgment_rows({}),
    )
    ask.click(respond, [question, clarification], [stamp, sentence, asked, judgments])


if __name__ == "__main__":
    demo.launch()
