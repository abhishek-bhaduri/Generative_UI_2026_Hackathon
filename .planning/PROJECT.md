# RFP Intake Cockpit

## What This Is

A generative-UI intake cockpit for technical sales built on the CopilotKit A2UI hackathon starter. A rep (or their customer) dumps a rough set of requirements; the system infers the deal archetype, context-drives the intake — chasing critical information customers usually omit — assembles grouped components for the customer to verify, and generates a final RFP the rep can trust.

**Hackathon track:** Generative UI (AG-UI + A2UI). Judged on originality, economic value, technical difficulty, and use of generative UI.

**Demo target ("the whoa"):** A judge watches a messy requirements dump become a complete, verified, grouped RFP that the agent assembled by chasing the critical gaps the customer never thought to provide — something a chat box plainly could not do.

## Core Value

The agent ELICITS and VERIFIES. It builds the requirements artifact; it does not write the proposal, quote pricing, or judge feasibility. The generative UI is the product — every output is a structured, interactive, grouped component.

## Context

**Codebase:** `generative-ui-london-hackathon-starter` — Next.js 16 + FastAPI + LangGraph + A2UI v0.9
- Two agents ship: `fixed_agent.py` (cockpit pattern) + `dynamic_agent.py` (gap elicitation pattern)
- 21-component A2UI catalog in `src/a2ui/catalog/`
- AG-UI transport via CopilotKit; Gemini 3.5 Flash via `langchain-google-genai` (FROZEN — do not upgrade)
- Redis NOT wired — on critical path for deal object persistence
- Runs locally only; no deployment

**Hard constraints:**
- Do NOT upgrade `@copilotkit/*`, `langchain*`, `langgraph*` — versions are frozen (see FROZEN.md)
- Do NOT swap the LLM — ChatGoogleGenerativeAI is required for Gemini 3.x thought-signature replay
- No A2A (Track 1) — that's a separate track; internal LangGraph nodes only

**Team context:**
- Hard-blocker rubric is PROVISIONAL — awaiting final list from technical-sales teammate
- All hard-blocker logic must be marked PROVISIONAL until real rubric arrives
- Synthetic data only — no real customer data, no PII

## Tech Stack

- **Frontend:** Next.js 16 (TypeScript), React 19, Tailwind 4, CopilotKit 1.57.4
- **Agent:** Python FastAPI + LangGraph 1.2.1, `langchain-google-genai`, A2UI v0.9 envelopes
- **Transport:** AG-UI (CopilotKit runtime), A2UI `createSurface` / `updateComponents` / `updateDataModel`
- **State:** MemorySaver (LangGraph) + in-memory DealStore; Redis wiring deferred
- **LLM:** Gemini 3.5 Flash (free tier, FROZEN)
- **Dev:** `pnpm dev` (Next.js :3000 + uvicorn :8123 concurrently)

## Customization Seams Used

1. **§5 agent flow** — `agent/src/rfp_agent.py` (new agent file alongside fixed/dynamic)
2. **§4 add a component** — `DealContextCard` in `src/a2ui/catalog/`; mirrored in `agent/src/catalog.py`
3. **§1/§2 theme & brand** — `src/a2ui/theme.css`, `Brand.tsx` (Phase 3 polish only)

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Phase 1 — Foundation: green baseline + new route + RFP agent skeleton + DealContextCard**
- [ ] Green baseline: pnpm install + doctor pass + existing pdf-analyst demo works
- [ ] New route `/rfp-intake` with split layout (chat left, canvas right) using existing pdf-analyst shell pattern
- [ ] New API route `/api/copilotkit-rfp` wired to new `rfp_agent` endpoint (:8123/rfp)
- [ ] `agent/src/rfp_agent.py` — archetype inference + seed field extraction + gap check against PROVISIONAL rubric
- [ ] `agent/src/deal_store.py` — in-memory DealStore (Redis-ready interface)
- [ ] `DealContextCard` A2UI component — fields with STATED/INFERRED/MISSING status tags
- [ ] `DealContextCard` renderer in `src/a2ui/catalog/renderers.tsx`
- [ ] End-to-end: paste requirements dump → DealContextCard surface renders in canvas

**Phase 2 — Gap Elicitation + Verification Cockpit**
- [ ] Gap-elicitation prompts surface (dynamic-agent pattern): chases missing critical fields, batched, each with "why this matters"
- [ ] Five grouped verification blocks (Commercials, Scope & success criteria, Technical constraints, Stakeholders & process, Timeline) — each field tagged STATED / INFERRED / MISSING and editable
- [ ] Readiness indicator climbing as hard-blockers close
- [ ] "Confirm & Continue" button gate — verification must complete before final RFP generates

**Phase 3 — Final RFP + Polish**
- [ ] Final RFP surface — generated only after confirmation gate, presented as reviewable grouped sections
- [ ] RFP brand theme (sales-appropriate colors, not pdf-analyst defaults)
- [ ] Hero demo cases: 2-3 polished input dumps for stage demo
- [ ] PROVISIONAL rubric replaced with real hard-blocker list from teammate (pending)
- [ ] `pnpm smoke` passes; visible completeness indicator on final artifact

### Out of Scope

- Writing the proposal or generating vendor commitments
- Pricing / quoting / feasibility judgement
- Live audio
- Real customer data or PII
- Auth / user accounts
- Deployment (local demo only)
- A2A Track 1 interop (separate hackathon track)
- Phase 2 specialist-node split (only if Phase 1 is solid, per brief)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single LangGraph agent for Phase 1 | "Lock first" principle from brief — working baseline before splitting | Phase 1 target |
| In-memory DealStore (Redis-ready interface) | Redis not wired in starter; abstraction lets us swap backend without changing callers | Implemented in deal_store.py |
| Compose Phase 1 surface from catalog + one bespoke component | Brief: "Compose from 21-component catalog first; only hand-build when nothing fits" — DealContextCard is domain-specific enough to warrant a bespoke renderer | DealContextCard added to catalog |
| PROVISIONAL hard-blocker rubric | Teammate rubric pending; AGENTS.md says "do NOT fabricate critical-info logic" | All blocker logic clearly marked PROVISIONAL |
| No A2A nodes for internal agent split | Brief: "these are internal graph nodes, NOT A2A" — A2A bolt-on is for cross-team interop track only | Internal LangGraph nodes only |
| New route group `(rfp)` parallel to `(pdf)` | Keeps RFP cockpit isolated; doesn't break pdf-analyst demo; follows existing route group pattern | `/app/(rfp)/rfp-intake/` |

## Guardrails (enforce hard)

1. **No fabrication** — Every line in the final RFP traces to something the customer stated or explicitly confirmed. STATED / INFERRED / MISSING tags are visible.
2. **Prioritized elicitation with stopping rule** — Chase critical gaps first, in impact order, say WHY. Batch follow-ups; cap per round. "Done" = all hard-blockers filled and verified.
3. **Stay in lane** — Intake only. No proposal writing, pricing, feasibility judgement, or vendor commitments.
4. **Mandatory verification gate** — Final RFP cannot generate until customer confirms grouped components. No silent finalization.
5. **Grouped output only** — All output is coherent grouped blocks. Never a wall of text.
6. **Visible completeness** — Readiness indicator driven by hard-blocker rubric.
7. **Commercial confidentiality** — Synthetic data only for demo; customer details scoped to session.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

---
*Last updated: 2026-06-13 after initialization*
