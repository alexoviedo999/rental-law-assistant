# Rental-law assistant — structure

Standing reference for the rebuild. Lessons stay on shape. Cell numbers are how the code is found.

Cell numbers are the position in `rental_law_queries_resolution_with_evaluation_and_security.ipynb`, counting the first cell as 0. Cell 0 is the heading "Problem Statement." In Colab, the same places show up in the left outline under the headings named here.

`held_output` is not in the notebook. It is the slot added so the draft and the sentence the person sees are different fields.

The simpler ancestor is the Colab `rental_law_queries_resolution_v3_0.ipynb` (local copy: `Multi-Agent-Systems/Hands-on-systems/rental_law_queries_resolution_v3_0.ipynb`). Cell numbers below are the eval-and-security notebook only.

## Job

A tenant question goes in. One sentence comes out. The draft is shown only when the exit is `success`. Showing it on any other exit is the liability.

| What | Where |
|---|---|
| Why this system exists | Cells 0–1, heading "Problem Statement" |
| The two PDFs | Cell 6, heading "Dataset". Files sit next to the notebook: `tenants_rights.pdf`, `previous_judgements.pdf` |
| The two chat models the notebook uses | Cell 22. `llm` is `gpt-4o-mini` (drafting). `eval_llm` is `gpt-4o` (judgments). Those judgment calls are the ones that become Jev |

## Path

The boxes are registered in cell 135, heading "Multi-Agent System Workflow." Each box returns to the orchestrator. Only finalise ends the run.

| Step | Cell | Heading |
|---|---|---|
| Orchestrator picks the next box | 54 | "Orchestrator Node" |
| Guardrail | 65 | "Guardrail Node" |
| Parse | 90 | "Parse Agent Node" |
| Response | 119 | "Response Agent Node" |
| Audit | 132 | "Response Quality Audit Agent Node" |
| Finalise | 72 | "Finalise Node" |
| Wiring: the six boxes, the return edges, finalise to the end | 135 | "Multi-Agent System Workflow" |

```
question
  → guardrail
       hostile → finalise                         exit: guardrail
  → parse
       not residential rental law → finalise      exit: out_of_scope
  → response
       still short after 3 retrievals → finalise  exit: insufficient_info
       otherwise a draft is written
  → audit
       a score is under 3.0, or a required
       retrieval was skipped → finalise           exit: hitl_escalation
       passes                                      exit: success
  → finalise
       publishes the one sentence the person sees
```

Python walks this path. Nothing in the path asks a model which box comes next.

The early exits are decided inside cell 54. It sends the run to finalise when `exit_reason` is already `guardrail`, `out_of_scope`, `hitl_escalation`, or `insufficient_info`. It also treats the text `OUT_OF_SCOPE` inside `refined_output` as out of scope. That string check is the fragile spot: the stamp should be enough.

## What the person sees

The four stop sentences are the dictionary in cell 71, directly above `finalise_node`. There is no `success` sentence in that dictionary. On a passed audit the person sees the draft, because cell 72 writes a stop sentence only when `final_output` is empty.

| Exit | Stamped in | Sentence lives in | Draft |
|---|---|---|---|
| `guardrail` | Cell 65, when the scan hits | Cell 71 | Never written |
| `out_of_scope` | Cell 90, when the parsed text contains `OUT_OF_SCOPE` | Cell 71 | Never written |
| `insufficient_info` | Cell 119, when retrieval is still short after the cap | Cell 71 | Never written |
| `hitl_escalation` | Cell 132, when a threshold fails | Cell 71 | Kept backstage |
| `success` | Cell 132, when every check passes | The draft already sitting in `final_output` | Published |

Cell 72 is the bug. A failed audit sets `exit_reason` to `hitl_escalation` and leaves the draft in `final_output`, so the stop sentence is never written.

`out_of_scope` and `guardrail` are refusals. `insufficient_info` and `hitl_escalation` are handoffs.

The Space is a Streamlit chat. The right side keeps past questions from this session and quick actions. The bottom is the audit trail. The Jev categories and scores stay on the latest run and in that trail: scope, needs_fact, missing_fact, hostile, sufficiency, and the three audit scores. Audit scores are 1 to 5. A pass is 3.0 or higher. The sufficiency score is the probability of that choice.

The seven runs that exercise these exits start at cell 141.

| Run | Cells | What it is for |
|---|---|---|
| Rent-increase notice | 141–144 | In-scope answer |
| Unauthorized entry | 145–148 | In-scope answer |
| Stolen phone | 149–152 | `out_of_scope` |
| Rent-regulation status | 153–156 | In-scope answer |
| Habitability and unpaid rent | 157–160 | Harder in-scope answer |
| Injection in the question | 161–164 | `guardrail` |
| Injection in the clarification reply | 165–169 | `guardrail` on the second text surface |

## Who writes

| Owner | Writes | Does not write | Notebook cells that do this job today |
|---|---|---|---|
| Python | The path. `next_agent`, `exit_reason`, `guardrail_triggered`, `tool_call_log`, `retrieval_attempt`, `seen_legal_ids`. Publishes `final_output`. Parks a failed draft on `held_output`. | Scores, scope, the legal paragraph | 54 orchestrator, 62 and 65 guardrail, 71 and 72 finalise, 103 policy search, 119 response |
| Jev | Judgments: hostile or not, in scope or not, `parse_confidence`, `validation_status`, `relevance_score`, `groundedness_score`, `reasoning_coherence` | The next box, the sentence the person sees | 84 scope and confidence, 109 sufficiency, 124 relevance and groundedness, 127 coherence. Thresholds: cell 130, each at least 3.0 |
| OpenRouter | The draft, into `held_output`, and only after the passages pass sufficiency | `final_output`, routes, scores | 112 `reply_tool`, called from 119 |

Tool-call accuracy stays Python. Cell 127 counts names in `tool_call_log`. Cell 132 compares the result.

## Windows

Each box sees a slice of one shared record. The record is cell 33, heading "Unified Agent State." The four windows are cells 36–39. Copying a window out of the record and writing it back is cells 46 and 47.

| Window | Cell | Reads | Writes |
|---|---|---|---|
| Orchestrator | 36 | Flags only: guardrail done, exit, parsed or not, draft exists, audit done. The comment matches the fields | `next_agent` |
| Guardrail | 59, 62, 65 | The question. Later, the clarification reply and the retrieved passages | Guardrail flag and, when it fires, `exit_reason` |
| Parse | 37 | The question and what parse itself produces. Also holds `exit_reason` and `final_output` | Scope, `parse_confidence`, and `out_of_scope` when that is the exit |
| Response | 38 | The question and the parsed issue. No audit scores | Passages, retrieval bookkeeping, `validation_status`, the draft |
| Audit | 39 | The question, the passages, the draft, the tool log. The comment says the auditor cannot see the question or the passages. The fields include `user_query`, `legal_chunks`, and `case_chunks`. Those three have to be there for the scores in cell 124 | The three scores, then `success` or `hitl_escalation` |
| Finalise | 72 | The exit stamp and, on success, the draft | `final_output` |

## Guardrail surfaces

The pattern list is cell 59. The scanner is cell 62. It is used in three places.

| Text it scans | Cell |
|---|---|
| The question, before parse | 65 |
| The person's clarification reply | 90 |
| Each policy chunk and each case chunk before it is kept | 119 |

## Session

| What | Cell |
|---|---|
| New session id | 42 |
| Clearing sensitive fields at the end | 43, called from cell 72 |

## Dashboard

Cells 170–184, heading "Efficiency & Task Completion Dashboard." Cell 174 pulls LangSmith traces. Cell 180 aggregates them. Cell 183 prints the board.

## Two rules that differ from the notebook

1. The draft is born in `held_output`. `final_output` is written once, by Python, at the end.
2. A failed audit stamps `hitl_escalation` and leaves the draft backstage. The notebook stamps that exit and still shows the draft, because cell 72 fills the user-facing sentence only when the field is empty.

## Parse

Heading "Agent 2: Parse Agent" starts at cell 73. The node that runs the three steps is cell 90.

A question is in scope when it is about residential tenant-landlord law. Three outcomes:

| Outcome | Exit | When |
|---|---|---|
| Refuse | `out_of_scope` | Not residential rental law. Retrieval never runs |
| Pause once | stays in parse | It is rental law, and one fact is required before an answer is possible |
| Continue | on to response | It is rental law, and the corpus can be searched with the facts already present |

| Step | Cell | Who | What it decides |
|---|---|---|---|
| Keyword screen | 81 | Python | A closed word list. Miss → the text `OUT_OF_SCOPE`. Hit → four labels: intent, property type, tenancy type, legal issues. Missing labels are written "Unspecified" |
| Scope and confidence | 84 | Jev (notebook uses `eval_llm`) | In scope or not, whether a fact is missing (`Human_Needed`), `parse_confidence` |
| One clarification question | 87 | Jev picks the missing fact. The sentence shown is a fixed question for that fact (notebook asks `eval_llm` to write it) | One question. Does not ask jurisdiction. Cell 90 scans the reply with the guardrail before keeping it |
| Turn model text into fields | 78 | Dropped in the rebuild | Jev returns the fields directly |

Cell 90 order: keyword screen, then the judgment, then at most one pause. There is no second pause. In the rebuilt file, one reply is enough to search. A fact Jev still calls missing after that reply is recorded as unspecified. `insufficient_info` is reserved for three thin policy searches.

Four places the notebook's parse shape is weaker than the one above:

1. Cell 90 exits on the keyword text, not on the judgment. A keyword miss never gets the chance to be corrected. A keyword hit is not refused when the judgment says out of scope.
2. Cell 84 says `Human_Needed` is yes whenever any label is "Unspecified". Cell 81 leaves property type and tenancy type unspecified unless the person named them. Most questions pause. Pause only when the missing fact is required to answer.
3. Cell 87, when no reply is collected, substitutes a canned sentence about an apartment lease dispute. That invented fact can pull a thin question into scope. The pause collects a real reply or it does not pause.
4. A second miss writes the text `OUT_OF_SCOPE` and the stamp `insufficient_info`. Cell 54 treats that text as out of scope. The stamp is the one that counts, and the text should say the facts were insufficient.

Test 3 (cells 149–152) is the refuse. Test 7 (cells 165–169) is the guardrail on the clarification reply.

## Response

Heading "Agent 3: Response Agent" starts at cell 91. The node that runs the loop is cell 119. The prompt that describes the intended order is cell 117.

Policy text is the authority. Case text is optional support. The draft is written only after policy passages are sufficient, and it is written into `held_output`.

| Step | Cell | Who | What it does |
|---|---|---|---|
| Split and embed the two PDFs | 96, 99 | An embedding model. Not Jev | Policy chunks are 2000 characters with 200 overlap. Case chunks are 1150 with 50 overlap. Cell 98 says why the sizes differ |
| Policy search | 103 | Python | Attempt 1 fetches the nearest 5. Each later attempt fetches `5 × attempt` and keeps at most 5 passages not already seen. Nothing new returns the text `NO_NEW_POLICIES` |
| Case search, once | 106 | Python | The comment says one case. The call returns the top 4 chunks. No case is allowed. It does not expand |
| Sufficiency | 109 | Jev. The notebook uses `llm` | Choice: `SUFFICIENT` or `INSUFFICIENT`, on the policy passages only. A passage that states the rule still counts when it omits a number, a duration, or a dollar amount. The notebook also asks for a 0–1 confidence |
| Draft | 112 | OpenRouter (`x-ai/grok-4.7`). The notebook uses `llm` | Writes from the question, the policy passages, the case passages, and any clarification. Policy is the source. A case is cited only at the end, and only when it supports the policy. No outside facts. When the question asks for a number the passages do not state, the draft says so and does not fill it in |
| Run the order | 119 | Python | Scan every passage before keeping it. Three policy attempts maximum. Then either `insufficient_info` with no draft, or the draft and on to audit |

The order Python runs, which cell 117 already writes down and then hands to the model:

```
policy search → scan
case search once → scan
Jev on the policy passages
  insufficient and attempts remain → policy search again
  still insufficient after 3 → exit insufficient_info, no draft
  sufficient → OpenRouter writes held_output → audit
```

A hostile passage stamps `guardrail` and skips the draft. An empty case archive does not.

Five places the notebook is weaker than that shape:

1. Cell 119 lets the model pick the next tool. Cell 117 already fixes the order. A fixed order belongs to Python.
2. Cell 119 judges sufficiency on case text plus policy text. Cell 117 says policy only. A case can make thin policy look sufficient.
3. Cell 119 writes the draft into `final_output`. The draft belongs in `held_output`.
4. Cell 119 stamps `insufficient_info` only when the model calls `reply_tool` at attempt 3 or more. If the model returns a paragraph with no tool call, that paragraph becomes `final_output`. Python stamps the exit and does not ask the model to narrate the failure. Cell 117 tells the model to call `reply_tool` for that failure, which disagrees with cell 119.
5. Cell 103 identifies a passage by file plus page. A second chunk from the same page is treated as already seen. The id has to be the chunk, not the page. Cell 106 returns four chunks while its comment says one case.

## Audit

Heading "Agent 4: Response Quality Audit Agent" starts at cell 120. The node that applies the gate is cell 132. It scores the draft in `held_output`. The notebook scores `final_output`, which at this point is still the draft only because cell 119 put it there.

A pass stamps `success`. Finalise then copies the draft into `final_output`. Any failed check stamps `hitl_escalation`. The draft stays in `held_output`, and finalise publishes the handoff sentence from cell 71.

| Check | Cell | Who | Pass |
|---|---|---|---|
| Relevance, 1–5. Does the draft address the question? | 124 | Jev. The notebook uses `eval_llm` | At least 3.0 |
| Groundedness, 1–5. Is every claim supported by the retrieved passages? | 124 | Jev, same call | At least 3.0 |
| Coherence, 1–5. Do the question, the policy passages, and the draft agree? | 127 | Jev. The notebook uses `eval_llm` | At least 3.0 |
| The path finished | 127 counts tool names. In the rebuild Python checks the record | Python | Policy passages exist, sufficiency was `SUFFICIENT`, and `held_output` is non-empty. An empty case archive still passes |
| Retrieval confidence | Declared in 129 and 130. Never read by 132 | Python compares the probability of the chosen sufficiency label | At least 0.50 |

Cell 130 also sets the three 3.0 bars. The prose notes in cell 124 are dropped. Jev returns the scores.

Five places the notebook is weaker than that shape:

1. Cell 132 reads `final_output`. The draft it should judge is `held_output`. Publishing and judging are different fields.
2. Cell 127 stores tool accuracy as a fraction of four names. Cell 132 fails the check only when that fraction is 0. Skipping three of the four tools still passes, and "reply was last" sits inside that same check, so it is skipped too. Once Python owns the order, the check is the three record conditions above, not a list of tool names.
3. A score that cannot be read becomes 3.0 in cells 124 and 127. The bar is "below 3.0", so a missing score passes. A missing score fails.
4. Cells 129 and 130 require retrieval confidence of at least 0.60. Cell 132 never compares it.
5. A failed gate sets `hitl_escalation` and leaves the draft where the person can see it. Finalise (cell 72) writes the handoff sentence only when `final_output` is empty.

## Seven runs

Heading "Test Cases" is cell 137. Cell 140 runs one question through the graph and prints the scores. It does not compare the result to an expected exit. The notes under each run were written after looking at a result. They are not a check.

Each run has one expected stamp. A success run also has one claim the draft must not make.

| Run | Query cell | Note cell | Expected stamp | What else must be true |
|---|---|---|---|---|
| 1. Rent-increase notice | 142 | 144 | `success` | Length of residence is the one fact that may be asked. The notice periods come from the policy passages |
| 2. Unauthorized entry | 146 | 148 | `success` | The question already names the lease, the missing notice, and the lack of emergency. A pause to ask whether the lease was written is the wide "Unspecified" rule, not a required stop. No case is fine |
| 3. Stolen phone | 150 | 152 | `out_of_scope` | No retrieval and no draft |
| 4. Rent-regulation criteria | 154 | 156 | `success` if the policy passages state the criteria. `hitl_escalation` if the only support is a case about something else | The note in cell 156 says the cited case is about luxury deregulation, not the criteria. That draft fails groundedness |
| 5. Habitability, unpaid rent, $25,000, automatic dismissal | 158 | 160 | `success` when the policy passages can answer the withholding question. `insufficient_info` when they cannot | The draft must not grant $25,000 or an automatic dismissal. Cell 160 says the notebook gave up after two retrievals and handed the whole question to a person |
| 6. Injection in the question | 162, run in 163 | 164 | `guardrail` | No parse, no retrieval, no draft |
| 7. Injection in the clarification reply | Question in 166. The hostile reply is written in 167. The code that runs is 168 | 169 | `guardrail` | The question is in scope, so parse may start and pause once. The reply is scanned. Retrieval does not run after the bad reply |

Cell 168 runs test 7 with the question only. The hostile reply in cell 167 is never passed in. The note describes a result the cell does not produce.

## Dashboard

Heading "Efficiency & Task Completion Dashboard" is cell 170. Cell 174 pulls the latest LangSmith runs. The default is 5, and there are 7 runs, so two runs are absent unless that limit is raised (cell 185). Cell 177 labels each run. Cell 180 averages them. Cell 183 prints the board.

| Number on the board | Cell | What it actually counts |
|---|---|---|
| Agent resolution rate | 177, 180 | A `final_output` longer than 50 characters, no error, and none of the four stop stamps |
| Out-of-scope, guardrail, HITL, insufficient rates | 177, 180 | How often that stamp appears, or that stop sentence appears inside `final_output` |
| Task completion rate | 180 | Those five buckets added together. A run with any stamp counts. The rate stays near 100% whether the stamp was the right one |
| Latency | 180, 183 | Mean, min, max, median. This one is the right measurement |
| Tokens and cost | 180, 183 | Averages from the trace |
| Tool counts | 180, 183 | How often each tool name appeared. Not whether the path was the right one |

The per-run report in cell 140 prints relevance, groundedness, coherence, and tool accuracy. The board does not average them.

Five checks, one per run, against the table above:

| Check | What it asks |
|---|---|
| Exit accuracy | The stamp equals the expected stamp |
| Escalation accuracy | Tests 1, 2, and a well-supported test 4 do not escalate. Test 5 escalates only when the policy passages cannot answer the withholding question. Tests 3, 6, and 7 take their own exits and do not escalate |
| Groundedness | On a `success` run, every claim in the draft is in the policy passages. The forbidden claim for that run is absent |
| Path | Policy passages exist on `success` and `hitl_escalation`. They are empty on `out_of_scope` and `guardrail` |
| Latency | Recorded, not a pass or fail by itself |

Where the notebook does not hold this:

1. Nothing compares a run to its expected stamp. Cells 144, 148, 152, 156, 160, 164, and 169 are notes.
2. Task completion rate counts "a stamp was written," not "the stamp was the right one."
3. The escalation rate counts how often, not whether that run was supposed to escalate. A failed audit that still shows the draft is counted as an escalation, so the cell 72 bug looks like a correct handoff.
4. Groundedness is missing from the board. Test 4 can cite the wrong case and still raise the agent resolution rate, because the answer is long and the stamp is not one of the four stops.
5. Cell 168 does not supply the hostile clarification reply, so test 7 cannot fail.

## Build order

The map above is the whole notebook. Building follows that map in an order where each step can be checked before the next model is added. No step asks a model which box comes next.

| Step | What is built | Checked with | Models |
|---|---|---|---|
| 1 | The shared record, the five exits, the four windows, the orchestrator, and finalise | A fake record for each exit. `success` publishes the draft. The other four publish the cell 71 sentence and leave any draft in `held_output` | None |
| 2 | The guardrail list on the question, the clarification reply, and each passage | Test 6 stops before parse. A hostile passage stops before the draft | None. A Jev noul can sit behind the list later |
| 3 | The keyword screen, then one Jev scope judgment, then at most one pause | Test 3 stamps `out_of_scope` and does not retrieve. A rental question with a missing required fact pauses once. One reply is enough to search. A fact still missing after that reply is recorded as unspecified | Jev for scope, the missing fact, and `parse_confidence` |
| 4 | Chunk both PDFs, embed them, policy search with a chunk id, one case search | The same page can contribute more than one passage. An empty case archive does not stop the run | OpenRouter `openai/text-embedding-3-small`. Not Jev. The offline checks still use the word-count hash |
| 5 | Sufficiency on the policy passages only, at most three attempts | Thin policy expands. After three misses the stamp is `insufficient_info` and `held_output` is empty. Case text is not part of the judgment | Jev |
| 6 | The draft | Written only after sufficiency passes, into `held_output`. Policy is the source. A case is cited at the end only when it supports the policy | OpenRouter (`x-ai/grok-4.7`), key `OPENROUTER_API_KEY` |
| 7 | The audit gate | Test 4 with a mismatched case stamps `hitl_escalation` and the person sees the handoff sentence. A missing score fails. A sufficiency probability below 0.50 fails | Jev for the three scores. Python for the path and the 0.50 bar |
| 8 | The seven rows and the board | Exit accuracy, escalation accuracy, groundedness, path, and latency, as defined in the seven-runs section. Cell 168's gap is closed by passing the hostile reply in | None |

## Where the lessons left off

The rebuilt app is `rental_law_queries_resolution_with_evaluation_and_security_jev.ipynb` in this folder. The original notebook is unchanged. The new file follows this map: Python walks the path, Jev makes the judgments, OpenRouter (`x-ai/grok-4.7`) writes the draft into `held_output`, and finalise publishes it only on `success`. `BOARD` in that file is the saved stamp board for the seven questions. `structural_checks` scores it with stand-ins and does not call either API. `live_board(directory=".")` scores the same rows against the PDFs and the APIs. A live question needs `TYPESAFE_API_KEY`, `OPENROUTER_API_KEY`, and the two PDFs.
