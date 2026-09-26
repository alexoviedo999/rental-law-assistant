import json
from pathlib import Path

import gradio as gr

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / "rental_law_queries_resolution_with_evaluation_and_security_jev.ipynb"

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


def respond(question, clarification):
    question = (question or "").strip()
    clarification = (clarification or "").strip()
    if not question:
        return "", "Ask a residential rental question.", ""
    try:
        result = ENGINE["answer"](question, clarification, deps=get_deps())
    except Exception:
        return (
            "error",
            "The run stopped before a stamp was written. The Space needs the secrets TYPESAFE_API_KEY and OPENROUTER_API_KEY.",
            "",
        )
    if result.get("awaiting_clarification"):
        asked = result.get("clarification_query") or ""
        return "(waiting for one fact)", asked, asked
    return result.get("exit_reason") or "(none)", result.get("final_output") or "", ""


with gr.Blocks(title="Rental law assistant") as demo:
    gr.Markdown(
        "A tenant question goes in. One sentence comes out. "
        "The draft is shown only when the stamp is `success`. "
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
    ask.click(respond, [question, clarification], [stamp, sentence, asked])


if __name__ == "__main__":
    demo.launch()
