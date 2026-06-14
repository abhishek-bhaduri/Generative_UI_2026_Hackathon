# STATE — RFP Intake Cockpit

**Project:** RFP Intake Cockpit
**Hackathon:** London A2A & A2UI Hackathon, June 13, 2026
**Build window:** 5 hours
**Last updated:** 2026-06-13 (post-hackathon)

---

## Project Reference

**Core value:** The agent ELICITS and VERIFIES. It turns a messy requirements dump into a grouped, verified RFP by chasing the critical fields B2B sales customers chronically omit — using generative UI that a chat box plainly cannot replicate.

**The "whoa":** Paste "replace our SIEM by Q3 because auditor" → archetype badge → field cards with STATED/INFERRED/MISSING tags → inline text inputs for gap answers → readiness score climbs as rep fills gaps.

**Final status:** Phase 1 shipped. Phases 2–3 not attempted within the build window.

---

## Final Position

**Phase:** 1 — Foundation ✅ Complete
**Status:** Shipped as demo artefact

| Phase | Status | Completed |
|-------|--------|-----------|
| 1. Foundation | ✅ Complete | June 13, 2026 |
| 2. Elicitation + Verification Cockpit | Not built | — |
| 3. Final RFP + Polish + Demo | Not built | — |

---

## What Was Built (Phase 1)

### Agent (`agent/src/`)
- **`rfp_agent.py`** (~950 lines) — LangGraph ReAct loop with tools: `extract_seed_fields`, `enrich_from_linkup`, `render_deal_context`. Full system prompt with archetype triage, field name table, and event handling for canvas TextInput submissions.
- **`rfp_hard_blockers.py`** — RTLS/MES hard-blocker rubric: 4 universal + 5 RTLS-specific + 7 MES-specific fields. `PROVISIONAL` flag for rubric swap seam.
- **`deal_store.py`** — Redis/in-memory dual-backend deal storage. Auto-selects Redis when `REDIS_URL` is set; falls back to in-memory dict.

### Frontend (`src/`)
- **`src/app/(rfp)/`** — Route group: `layout.tsx`, `rfp-cockpit.css` (full CSS token block), `rfp-intake/page.tsx` (split layout)
- **`src/app/api/copilotkit-rfp/route.ts`** — Dedicated CopilotKit runtime endpoint
- **`src/components/rfp-intake/Providers.tsx`** — CopilotKit provider with MirrorRenderer
- **`src/a2ui/catalog/definitions.ts`** — Added `TextInput`, `DealContextCard`, `ReadinessMeter`
- **`src/a2ui/catalog/renderers.tsx`** — React renderers for the above; `TextInput` dispatches `submit_field` events back to the agent
- **`agent/src/catalog.py`** — Python mirror updated with new components

### Infrastructure
- **`railway.toml`** — Railway deployment config (single Docker service)
- **`src/app/api/health/route.ts`** — Health check endpoint

### Bugs fixed during the session
1. A2UI component format (`{"type","props"}` → flat `{"component",...}`)
2. `update_components` argument (wrapped dict → plain list)
3. CSS tokens missing in `(rfp)` scope (`--orange`, `--red` not defined)
4. `thread_id` mismatch — fixed with `InjectedToolArg` / `RunnableConfig`
5. LLM calling `extract_seed_fields(fields=[])` — fixed by adding explicit field name table to system prompt
6. Canvas re-emitting `createSurface` on every turn — fixed with `surface_created` flag in deal state

---

## Accumulated Context

### Decisions Locked

| Decision | Confidence | Why it matters |
|----------|------------|----------------|
| Deal object lives in `deal_store.py`, NOT `AgentState` | HIGH | Phase 2 graph split = zero schema migration |
| Redis/in-memory dual backend | HIGH | Zero config locally; production-ready without code changes |
| PROVISIONAL rubric flag | HIGH | Swap seam: edit `rfp_hard_blockers.py`, flip flag — zero logic changes |
| `(rfp)` route group parallel to `(pdf)`, no cross-group imports | HIGH | Isolation; follows existing convention |
| TextInput dispatches `submit_field` events via A2UI dispatch | HIGH | Lets rep answer gap questions directly in canvas |
| Top-3 MISSING cap + "N more" footer | HIGH | Prevents overwhelming the canvas on cold dump |

### Active Constraints

- Stack is FROZEN: `@copilotkit/*` (1.57.4), `langchain` (1.3.1), `langchain-core` (1.4.0), `langgraph` (1.2.1), `next` (16.1.6), `react` (19.2.4)
- LLM is FROZEN: `ChatGoogleGenerativeAI` (Gemini 3.5 Flash) — no OpenAI compat
- PROVISIONAL rubric: every reference carries `# PROVISIONAL` comment

---

## If Continuing This Project

### To run locally
```
cp agent/.env.example agent/.env   # add GEMINI_API_KEY
pnpm dev
```
Open `http://localhost:3000/rfp-intake`

### Next logical step: Phase 2
- Add `chase_gaps` tool — batched gap questions with deal-killer rationale
- Add `VerificationGroup` catalog component — five grouped blocks (Commercials, Scope, Technical, Stakeholders, Timeline)
- Add `ReadinessMeter` live update — climbs 40%→95% as rep answers
- HITL confirm gate — `interrupt()` + data-model-write resume (hardest piece; see ROADMAP.md CR-5)

### To swap the PROVISIONAL rubric
1. Edit the lists in `agent/src/rfp_hard_blockers.py`
2. Set `PROVISIONAL = False`
3. `pnpm smoke` — zero logic changes needed elsewhere
