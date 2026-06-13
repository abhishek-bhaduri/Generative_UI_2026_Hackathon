# Requirements — RFP Intake Cockpit

**Project:** RFP Intake Cockpit
**Hackathon:** London A2A & A2UI Hackathon, June 13, 2026
**Build window:** 5 hours
**Last updated:** 2026-06-13

---

## Scope

Agent-driven generative UI intake cockpit for technical B2B sales. A rep or their customer pastes a rough requirements dump; the system infers the deal archetype, chases critical missing fields, assembles grouped components for verification, and generates a final structured RFP.

**Judging criteria:** Originality, economic value, technical difficulty, use of generative UI.

---

## Functional Requirements

### Foundation (Phase 1)

**FOUND-01** — Green baseline  
The existing pdf-analyst demo must remain fully functional throughout development. `pnpm doctor`, `pnpm verify-pins`, and `pnpm smoke` must pass before and after each scaffold step.

**FOUND-02** — RFP intake route  
A new route `/rfp-intake` must exist with a split layout: chat panel left, generative UI canvas right. This route group `(rfp)` must be parallel to and isolated from `(pdf)` — no cross-route-group imports.

**FOUND-03** — RFP API route  
A new Next.js API route `/api/copilotkit-rfp` must exist, wired to the `rfp_agent` endpoint at `:8123/rfp`. Must set `injectA2UITool: false`.

**FOUND-04** — RFP agent skeleton  
`agent/src/rfp_agent.py` must implement a single `create_agent` ReAct loop (copy `fixed_agent.py` shape). Must include `extract_seed_fields` and `render_deal_context` tools minimum. Must register at `/rfp` in `agent/main.py`.

**FOUND-05** — Deal store  
`agent/src/deal_store.py` must provide thread-scoped in-memory storage for deal objects with a Redis-ready Protocol interface (`get_deal`, `set_deal`, `update_deal`, `delete_deal`). Deal object must NOT live in `AgentState` — keyed by `thread_id`.

**FOUND-06** — PROVISIONAL hard-blocker rubric  
`agent/src/rfp_hard_blockers.py` must define the PROVISIONAL rubric (MEDDPICC + 3 universal technical fields = 11 fields). Must be flagged `PROVISIONAL = True`. Every reference must carry `# PROVISIONAL: replace at H+4` comment. Teammate swap is one-file change only.

**FOUND-07** — DealContextCard A2UI component  
A new `DealContextCard` component must be added to the A2UI catalog (definitions.ts + renderers.tsx + agent/src/catalog.py mirror). Must render deal fields with STATED / INFERRED / MISSING status badges. STATED fields must show `source_quote` on hover. MISSING fields must show "why we need this" copy.

**FOUND-08** — End-to-end Phase 1 flow  
Pasting a requirements dump into the RFP chat must cause a `DealContextCard` surface to render in the canvas within one agent turn.

---

### Gap Elicitation + Verification (Phase 2)

**FOUND-09** — Batched gap chases  
The agent must identify missing hard-blocker fields and emit gap elicitation prompts in batches (not one-by-one). Each chase must include a "why this matters" rationale referencing deal-killer patterns.

**FOUND-10** — Five-group verification surface  
A grouped verification surface must render with five blocks: Commercials, Scope & Success Criteria, Technical Constraints, Stakeholders & Process, Timeline. Each field must be tagged STATED / INFERRED / MISSING and be editable inline.

**FOUND-11** — Linkup company enrichment  
When a company name or website URL is detected in the requirements dump, the agent must trigger a background Linkup API call to research the company (industry, size, known tech stack, compliance certifications, recent news/context). The Linkup tool must be implemented as a Python agent tool (not frontend-injected). Company name/URL detection must be part of the `extract_seed_fields` tool or a dedicated `enrich_company_context` tool called in the same agent turn.

**FOUND-12** — Enriched inference from Linkup data  
Company context returned by Linkup must be used to:
(a) Increase archetype inference confidence (e.g. "known AWS customer" boosts Infra Migration probability);
(b) Pre-populate relevant technical constraints (e.g. known compliance certifications → Technical Constraints group) with INFERRED status and Linkup source attribution visible in the status badge hover.
Linkup-sourced fields must be clearly distinguishable from user-stated fields. If Linkup returns no results or errors, the agent must continue without Linkup data (graceful degradation).

**FOUND-13** — Readiness indicator  
A `ReadinessMeter` component must show overall completeness as a percentage, driven by hard-blocker close rate. Must climb visibly as gap-chasing progresses (40% → 95% in demo scenario).

**FOUND-14** — Confirm & Continue gate  
A verification confirm gate must exist before final RFP generation. Must use LangGraph `interrupt()` + data-model-write resume pattern (NOT frontend tool injection — orphan `function_call` trap). Surface must be emitted BEFORE interrupt. Resume must carry full `{action, deal}` payload for idempotency.

---

### Final RFP + Polish (Phase 3)

**FOUND-15** — Final RFP surface  
A final RFP surface must render only after the confirmation gate passes. Must present grouped sections matching the five-group taxonomy. Must be generated from verified deal fields only — no fabrication.

**FOUND-16** — RFP brand theme  
The RFP cockpit must have sales-appropriate colors distinct from the pdf-analyst defaults. Edit `src/a2ui/theme.css` and `src/app/(rfp)/rfp-intake.css` only.

**FOUND-17** — Hero demo cases  
2–3 polished hero input dumps must be paste-ready for the stage demo. Must cover: Security Tooling (the "60-second whoa"), Infra Migration, Data Platform archetypes.

**FOUND-18** — Rubric swap seam  
Swapping the PROVISIONAL rubric for the teammate's final rubric must require only: changing data in `rfp_hard_blockers.py`, flipping `PROVISIONAL = False`. Zero logic changes elsewhere.

---

## Non-Functional Requirements

**NFR-01 — Frozen stack:** Do NOT bump `@copilotkit/*` (1.57.4), `langchain` (1.3.1), `langchain-core` (1.4.0), `langgraph` (1.2.1), `next` (16.1.6), or `react` (19.2.4). Run `pnpm verify-pins` after any dependency change.

**NFR-02 — LLM frozen:** Use only `ChatGoogleGenerativeAI` (Gemini 3.5 Flash). Do not swap to `langchain-openai`. Required for Gemini 3.x thought-signature replay.

**NFR-03 — Typed arrays:** Every list parameter in agent tools must use a TypedDict element type (not `list[dict]` or `list[Any]`). Gemini silently picks no tool with untyped list params. Copy `fixed_agent.py:37-42` shape.

**NFR-04 — Surface deduplication:** The same `surfaceId` must not be emitted twice per session. Track emitted surfaces in agent state.

**NFR-05 — thread_id wiring:** CopilotKit's `threadId` must be used as LangGraph's `thread_id`. Wire explicitly in `main.py` at the `/rfp` endpoint.

**NFR-06 — Model budget:** Planning agents (gsd-project-researcher, gsd-research-synthesizer, gsd-roadmapper, gsd-plan-checker) use Opus. Execution agents (gsd-executor) use Sonnet.

**NFR-07 — No PII:** Synthetic data only for all demo inputs. No real customer data.

**NFR-08 — Local only:** No deployment. Demo runs on a single laptop. Cold-test at H+4.

---

## Guardrails (enforce hard)

1. **No fabrication** — Every RFP field traces to customer-stated, Linkup-sourced (with attribution), or explicitly confirmed data. STATED / INFERRED / MISSING tags must be visible.
2. **Prioritized elicitation with stopping rule** — Chase hard-blockers first in priority order with rationale. Batch follow-ups. Cap rounds. Stop when all hard-blockers are filled and verified.
3. **Stay in lane** — Intake only. No proposal writing, pricing, feasibility judgement, or vendor commitments.
4. **Mandatory verification gate** — Final RFP cannot generate until customer confirms grouped components via the HITL gate.
5. **Grouped output only** — All agent output is structured grouped blocks. Never a wall of text.
6. **Visible completeness** — Readiness indicator always visible; driven by PROVISIONAL rubric (or final rubric when delivered).
7. **Commercial confidentiality** — Synthetic data only; session-scoped; no external push.

---

## Anti-Features (explicitly out of scope)

- Pricing / quoting / feasibility judgement
- Proposal or vendor response writing
- Vendor shortlists or recommendations
- CRM push / Salesforce integration
- Auth / user accounts
- Multi-user collaboration
- Live audio / voice
- A2A Track 1 interop (separate hackathon track)
- Deployment (local demo only)
- Real customer / PII data

---

## Open Items

| Item | Status | Owner |
|------|--------|-------|
| Final hard-blocker rubric | PROVISIONAL — 11 fields (MEDDPICC + 3 technical) | Teammate delivers before Phase 3 |
| Linkup API key / auth method | Unconfirmed — check Linkup sponsor docs at hackathon | Abhishek |
| Archetype inference: visible badge vs. silent | Recommend visible + one-click override | Confirm with teammate |

---

## Definition of Done

**Phase 1:** Paste requirements dump → `DealContextCard` renders in canvas with archetype badge + STATED/INFERRED/MISSING fields. `pnpm smoke` passes.

**Phase 2:** Dump → card → batched gap chases with rationale (including Linkup-sourced context where available) → user answers → readiness climbs → Confirm gate → verified fields.

**Phase 3:** Full 60-second demo flow passes cold on demo laptop. PROVISIONAL rubric swappable in one file. Hero prompts paste-ready.

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 — Green baseline | Phase 1 | Pending |
| FOUND-02 — RFP intake route | Phase 1 | Pending |
| FOUND-03 — RFP API route | Phase 1 | Pending |
| FOUND-04 — RFP agent skeleton | Phase 1 | Pending |
| FOUND-05 — Deal store | Phase 1 | Pending |
| FOUND-06 — PROVISIONAL hard-blocker rubric | Phase 1 | Pending |
| FOUND-07 — DealContextCard A2UI component | Phase 1 | Pending |
| FOUND-08 — End-to-end Phase 1 flow | Phase 1 | Pending |
| FOUND-09 — Batched gap chases | Phase 2 | Pending |
| FOUND-10 — Five-group verification surface | Phase 2 | Pending |
| FOUND-11 — Linkup company enrichment | Phase 2 | Pending |
| FOUND-12 — Enriched inference from Linkup data | Phase 2 | Pending |
| FOUND-13 — Readiness indicator | Phase 2 | Pending |
| FOUND-14 — Confirm & Continue gate | Phase 2 | Pending |
| FOUND-15 — Final RFP surface | Phase 3 | Pending |
| FOUND-16 — RFP brand theme | Phase 3 | Pending |
| FOUND-17 — Hero demo cases | Phase 3 | Pending |
| FOUND-18 — Rubric swap seam | Phase 3 | Pending |
| NFR-01 — Frozen stack | Phase 1 | Pending |
| NFR-02 — LLM frozen | Phase 1 | Pending |
| NFR-03 — Typed arrays | Phase 1 | Pending |
| NFR-04 — Surface deduplication | Phase 1 | Pending |
| NFR-05 — thread_id wiring | Phase 1 | Pending |
| NFR-06 — Model budget | All phases | Pending |
| NFR-07 — No PII | All phases | Pending |
| NFR-08 — Local only | Phase 3 | Pending |
