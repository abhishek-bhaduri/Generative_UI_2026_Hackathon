# Stack Research — RFP Intake Cockpit

**Milestone:** RFP Intake Cockpit (subsequent milestone on existing frozen stack)
**Researched:** 2026-06-13
**Mode:** Working-within-frozen-stack (no swaps; patterns only)
**Overall confidence:** HIGH on LangGraph + Redis checkpointer patterns; HIGH on CopilotKit HITL; MEDIUM on RFP data-model norms; MEDIUM on STATUS-tag precedent

## Stack Reaffirmation (FROZEN)

Nothing changes. All recommendations are about HOW to use what's already pinned:
- Next.js 16 / React 19 / Tailwind 4 / TypeScript (frontend)
- FastAPI + LangGraph 1.2.1 + `langchain-google-genai` (Gemini 3.5 Flash) (agent)
- CopilotKit 1.57.4 + A2UI v0.9 over AG-UI transport
- `MemorySaver` + in-memory `DealStore` (today; Redis swap deferred)

---

## Q1 — Stateful "Deal Object" Across Turns in LangGraph 1.2.x

**Recommended pattern:** TypedDict state extending `MessagesState` + thread-scoped checkpointer.

```python
from typing import TypedDict, Literal
from langgraph.graph import MessagesState

FieldStatus = Literal["STATED", "INFERRED", "MISSING"]

class DealField(TypedDict):
    value: str | None
    status: FieldStatus
    source_quote: str | None   # for STATED — traceability per Guardrail #1
    confidence: float | None   # for INFERRED

class DealObject(TypedDict, total=False):
    archetype: str | None
    commercials: dict[str, DealField]
    scope: dict[str, DealField]
    technical: dict[str, DealField]
    stakeholders: dict[str, DealField]
    timeline: dict[str, DealField]

class RFPState(MessagesState):    # inherits messages: Annotated[..., add_messages]
    deal: DealObject
    readiness: float              # 0..1 — hard-blocker close rate
    elicitation_round: int        # round cap, per Guardrail #2
```

**Why this shape (HIGH confidence):**
- `MessagesState` brings the right reducer for chat history out of the box
- TypedDicts default to **overwrite** for non-Annotated keys — right for "current deal snapshot"
- `total=False` lets groups fill progressively
- Reserve `Annotated[..., reducer]` only for accumulating keys (messages; optionally `gap_history`)

**Anti-pattern:** Don't store the deal as JSON in the last message's `content`. Gemini's thought-signature replay can normalize/strip it. Keep `deal` as a first-class state key.

---

## Q2 — Real-World RFP Intake Data Model

**Verdict:** The five proposed groups (Commercials, Scope & success criteria, Technical constraints, Stakeholders & process, Timeline) are well-aligned with industry norms — keep them.

They map cleanly to the **MEDDPICC** sales qualification framework:

| Group | Typical fields | MEDDPICC mapping | Hard-blocker candidate |
|---|---|---|---|
| **Commercials** | budget range, budget-holder, capex/opex/subscription, payment terms | Metrics + Economic buyer | budget exists (funded, not aspirational) |
| **Scope & success criteria** | problem statement, in-scope, out-of-scope, success metrics, "done" definition | Identify pain + Metrics | ≥1 measurable success criterion |
| **Technical constraints** | existing stack, integration surface, compliance (GDPR/SOC2/HIPAA), NFRs, security review | Decision criteria | compliance hard-line |
| **Stakeholders & process** | economic buyer, technical champion, end-user persona, evaluation committee, paper process | Economic buyer + Champion + Decision/Paper process | named economic buyer; decision date |
| **Timeline** | trigger event, go-live target, evaluation milestones, signature target, procurement lead time | Decision process | go-live or signature target |

**Common "missing-by-default" fields (strong PROVISIONAL hard-blocker candidates):**
1. Decision / paper process (procurement timeline, signature authority)
2. Out-of-scope / non-goals
3. Existing-stack integration surface (specifics, not just "Salesforce")
4. Compliance constraints (always surface too late)
5. Success metrics ("faster" is not a number)
6. Economic buyer (champion is named; economic buyer often isn't)

---

## Q3 — A2UI v0.9 / CopilotKit HITL Patterns

**Recommended pattern:** LangGraph `interrupt()` + A2UI verification surface. (HIGH confidence.)

```python
from langgraph.types import Command, interrupt

def verification_gate(state: RFPState):
    # Emit surface BEFORE interrupting so canvas is on-screen
    emit_a2ui_surface(state["deal"])

    decision = interrupt({
        "instruction": "Verify the grouped intake before final RFP generation.",
        "deal": state["deal"],
        "open_blockers": [k for k in HARD_BLOCKERS if is_missing(state["deal"], k)],
    })

    if decision.get("action") == "confirm":
        return Command(update={"deal": decision.get("deal", state["deal"])},
                       goto="final_rfp_surface")
    elif decision.get("action") == "edit":
        return Command(update={"deal": decision["deal"]}, goto="gap_check")
    else:
        return Command(goto="elicit_or_finalize")
```

**HITL design rules:**
1. **Emit surface BEFORE interrupt** — a paused agent with no UI is broken UX
2. **Carry full decision payload through resume** — pass `{action, deal}` for idempotency
3. **Idempotent re-entry** — code before `interrupt()` re-runs on resume; no side effects pre-interrupt
4. **One interrupt for grouped verification** — fewer round-trips, matches "grouped output only" guardrail

**Anti-patterns:**
- Don't use `useCopilotAction` for the verification gate — that's for frontend tools the agent calls
- Don't poll `deal_store.py` from React — read via `useCoAgent` state stream or A2UI data model
- Don't free-text-confirm — the verification surface IS the gate; the button IS the confirmation

---

## Q4 — Redis Checkpoint Backend for LangGraph 1.2.1

**Verdict: YES — `langgraph-checkpoint-redis` is compatible. (HIGH confidence.)**

Package: `langgraph-checkpoint-redis` (redis-developer, v0.3.2) — drop-in for `MemorySaver`.

```python
from langgraph.checkpoint.redis import RedisSaver

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

with RedisSaver.from_conn_string(REDIS_URL) as saver:
    saver.setup()   # idempotent — creates RediSearch indices
    graph = builder.compile(checkpointer=saver)
```

**Requires:** Redis Stack or Redis 7.2+ with Search module (not stock Redis). Document this when Redis lands.

**Migration path (two independent layers):**

| Layer | Today | Redis-wired |
|---|---|---|
| Agent state (RFPState) | `MemorySaver` | `RedisSaver` (drop-in swap) |
| Renderer projection | in-memory `DealStore` | Redis hash/JSON via existing `DealStore` interface |

Ship Phase 1 on MemorySaver + in-memory store; migrate when persistence-across-restart is needed.

---

## Q5 — STATED / INFERRED / MISSING Status Tagging in Generative UI

**Verdict:** No direct named precedent, but the provenance-tag-per-field pattern is well-established in adjacent domains. (MEDIUM confidence.)

| Domain | Equivalent pattern |
|---|---|
| Document-grounded QA / RAG | grounded vs hallucinated attribution badges |
| Data cleaning / ETL | column-level provenance (source / derived / imputed / missing) |
| Salesforce / CRM | field-level "verified", "needs review", "synced" |
| Legal document analysis | "extracted from doc" vs "inferred" vs "user-provided" |

**Implementation:** Don't build a new A2UI primitive for status alone. Compose existing catalog:
- `Badge` for the status tag
- Three semantic theme tokens: `--a2ui-status-stated`, `--a2ui-status-inferred`, `--a2ui-status-missing`
- **STATED** → `source_quote` is the hover content ("you said: '…'") — enforces Guardrail #1 traceability
- **INFERRED** → show inference rationale
- **MISSING** → render with "why we need this" copy — enforces Guardrail #2 ("say WHY")

**Consider adding CONFIRMED (4-state) in Phase 2:** INFERRED promoted by user is different from originally STATED.

**Anti-patterns:**
- Don't use color alone (a11y) — tag word + color
- Don't hide MISSING fields — show them with "why" copy
- Don't auto-promote INFERRED → STATED on display — requires user click

---

## Cross-Cutting Notes

**Pattern consistency with existing agents:**

| Concern | Existing pattern | RFP agent applies |
|---|---|---|
| State shape | TypedDict (fixed_agent.py) | `RFPState(MessagesState)` with `DealObject` |
| Checkpointer | `MemorySaver()` at compile | Same Phase 1; `RedisSaver` later |
| Tool for UI emission | server-side tool (`render_dashboard`) | `render_deal_context_card` server-side tool |
| A2UI envelopes | createSurface + updateComponents + updateDataModel | Same three |
| Frontend wiring | catalog + theme; mirror prompt in `agent/src/catalog.py` | Add `DealContextCard` to all three places |

**Session restart UX:** MemorySaver + in-memory DealStore reset on server restart. Document Phase 1 demo runs as one continuous session until Redis lands.

**PROVISIONAL rubric handling:** Mark `agent/src/rfp_hard_blockers.py` with `PROVISIONAL = True` module flag; surface in readiness indicator copy. When teammate's rubric arrives — swap data, flip flag, zero logic changes.
