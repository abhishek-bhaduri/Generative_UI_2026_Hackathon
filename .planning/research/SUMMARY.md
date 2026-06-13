# Research Summary — RFP Intake Cockpit

**Synthesized:** 2026-06-13
**Build window:** 5 hours (hackathon)
**Overall confidence:** HIGH on stack/architecture/pitfalls; MEDIUM on rubric (PROVISIONAL pending teammate)
**Mode:** Subsequent milestone on frozen stack — no swaps; patterns only

---

## Executive Summary

The RFP Intake Cockpit is a generative-UI agent that turns a messy requirements dump into a grouped, verified RFP by chasing the critical fields B2B sales customers chronically omit. Research converged on a **deceptively boring architecture**: a single LangGraph `create_agent` (ReAct loop, copy `fixed_agent.py` shape), the deal object stored **outside** graph state in `agent/src/deal_store.py` keyed by `thread_id`, three new bespoke A2UI components (`DealContextCard`, `VerificationGroup`, `ReadinessMeter`) added to the shared catalog, and a new route group `(rfp)` parallel to `(pdf)`.

**Five things make or break this build:**
1. **Deal state in `deal_store.py`, NOT `AgentState`** — keeps Phase 2 split cheap (no schema migration), Redis swap behind a Protocol interface
2. **PROVISIONAL MEDDPICC + 3-technical = 11-field rubric** — centralized in `agent/src/rubric.py` with `PROVISIONAL = True`; teammate swap is one-file only
3. **Three Phase 1 archetypes** (Infra Migration, Security Tooling, Data Platform) — broadest demo coverage
4. **Five-group taxonomy validated** — Commercials / Scope / Tech / Stakeholders / Timeline confirmed against MEDDPICC + APMP norms; do NOT add a sixth
5. **The 60-second whoa demo** must land: paste a "replace our SIEM by Q3 because auditor" dump → archetype badge → five blocks with ~40% MISSING → batched 3 chases with rationale → readiness climbs 40%→95% → final RFP renders

The **highest-risk task** is the HITL confirm gate: LangGraph `interrupt()` + data-model-write resume, NOT a CopilotKit frontend-tool injection (that's the orphan-`function_call` trap).

---

## Key Findings

### Stack (HIGH confidence)
- All versions FROZEN — copy existing patterns, do not invent
- `RFPState(MessagesState)` with TypedDict — but deal object lives in `deal_store.py`, not graph state
- HITL pattern: `interrupt()` AFTER emitting the surface; carry full `{action, deal}` through resume
- Redis: `langgraph-checkpoint-redis` v0.3.2 is a drop-in for `MemorySaver`; out of Phase 1 scope
- STATED/INFERRED/MISSING: compose existing `Badge` + theme tokens; consider 4th state CONFIRMED in Phase 2

### Features (MEDIUM-HIGH confidence)
- Five-group taxonomy validated against MEDDPICC + APMP/Loopio norms ✓
- PROVISIONAL hard-blocker rubric: MEDDPICC (8) + 3 universal technical fields = 11 fields
- Phase 1 archetypes: Infra Migration, Security Tooling, Data Platform
- Success-criteria reframe is the highest-value elicitation move (activity → outcome)
- Eight fields customers almost never provide: compelling event, out-of-scope, economic buyer, outcome-based success criteria, other vendors, procurement lead times, data residency, deployment model
- Anti-features: no pricing, no proposals, no feasibility judgement, no vendor recommendations, no fabrication, no wall-of-text, no auto-send, no CRM push, no auth, no voice, no PII

### Architecture (HIGH confidence)
- Phase 1: single `create_agent` ReAct loop — 5 tools: `extract_seed_fields`, `render_deal_context`, `chase_gaps`, `render_verification`, `finalize_rfp`. Copy `fixed_agent.py` exactly.
- First refactor: move `SurfaceCanvas` to `src/components/shared/` so `(rfp)` doesn't import from `(pdf)`
- Three new catalog components: `DealContextCard`, `VerificationGroup`, `ReadinessMeter`
- HITL action transport: reuse `forwardedProps.a2uiAction` → `log_a2ui_event` pattern from `dynamic_agent.py`
- Phase 2 (optional): `StateGraph` specialist nodes; spike nested-graph `thread_id` propagation first (30-min task)

### Pitfalls (HIGH confidence)

**Critical (will crash or break demo):**
1. **CR-1 Version drift** — `@copilotkit/*` / `langchain*` / `langgraph*` bumps break A2UI envelope contract; run `pnpm verify-pins` after any dep change
2. **CR-2 LLM swap** — replacing `ChatGoogleGenerativeAI` with `langchain-openai` breaks Gemini 3.x thought-signature replay on turn 2
3. **CR-3 Gemini typed-array** — `list[dict]` or `list[Any]` makes model pick no tool silently; every list param needs TypedDict element type; copy `fixed_agent.py:37-42`
4. **CR-4 Duplicate `createSurface`** — same surfaceId on re-entry throws and wipes canvas; emit once per surface per session; track in agent state
5. **CR-5 Orphan `function_call`** — frontend tool injection for Confirm button hangs agent; use agent-side `interrupt()` + data-model-write resume instead

**Also critical:** CR-6 zod pinned to `^3.25`; CR-7 `Section.title` is `z.string()` only (no path binding)

**Moderate:**
- **MD-2 `thread_id` mismatch** — use CopilotKit's `threadId` as LangGraph `thread_id`; wire explicitly in `main.py` at `/rfp`; #1 multi-turn footgun
- **MD-8 PROVISIONAL rubric** — every reference carries `# PROVISIONAL: replace at H+4` comment

**Hackathon-specific:**
- Hard scope freeze at H+3 (no new features)
- Demo on same laptop; cold-test at H+4; paste-ready hero prompts; rehearse 60-second pitch

---

## Roadmap Implications

### Phase 1 — Foundation
**Goal:** paste dump → DealContextCard renders in canvas

Critical path steps:
1. Green baseline + `pnpm verify-pins` + doctor pass
2. Move `SurfaceCanvas` to `src/components/shared/`
3. Add `DealContextCard` to `definitions.ts` + `renderers.tsx` + mirror in `catalog.py`
4. New `agent/src/deal_store.py` (in-memory dict + Protocol interface)
5. New `agent/src/rubric.py` (PROVISIONAL flag + 11-field list)
6. New `agent/src/rfp_agent.py` — single `create_agent` ReAct loop, 5 tools
7. Mount `/rfp` endpoint in `agent/main.py`
8. New `src/app/api/copilotkit-rfp/route.ts`
9. New `src/app/(rfp)/` route group + Providers + page
10. End-to-end test: dump → surface renders

Pitfalls owned: CR-1, CR-2, CR-3, CR-4, CR-6, CR-7, MD-2, MD-8

**Research needed for Phase 1 planning:** NO — copy `fixed_agent.py` shape; all patterns documented

### Phase 2 — Elicitation + Verification
**Goal:** dump → card → batched gap chases → user answers → readiness climbs → Confirm gate

- `VerificationGroup` + `ReadinessMeter` components
- `chase_gaps` + `render_verification` tools
- **Confirm & Continue gate via `interrupt()` + data-model write** (HIGHEST-RISK TASK)
- Idempotent action handlers (`edit_field`, `approve_group`, `answer_question`, `confirm_continue`)

Pitfalls owned: CR-4 (peak risk), CR-5 (Confirm gate), MD-1, MD-3, MD-5, MD-7

**Research needed for Phase 2 planning:** YES — verify LangGraph 1.2.x `interrupt()` exact API surface + idempotent re-entry pattern

### Phase 3 — Final RFP + Polish + Demo
**Goal:** complete, verified grouped RFP; polished for stage

- `finalize_rfp` tool (composes Section/Card/BulletList from verified deal)
- RFP brand theme (sales-appropriate colors)
- 2-3 polished hero input dumps
- Swap PROVISIONAL rubric when teammate delivers (flip `PROVISIONAL = False`, swap list, zero logic change)
- H+4 cold-test; H+4.5 rehearse 60-second pitch

**Research needed for Phase 3 planning:** NO — composition + polish; no new patterns

---

## Gaps Requiring Validation

| Gap | Impact | Action |
|-----|--------|--------|
| Final hard-blocker rubric | HIGH | Teammate delivers before Phase 3; swap via `agent/src/rubric.py` |
| Multi-surface dedupe | MEDIUM | Verify SurfaceCanvas handles `rfp-deal` + `rfp-verify` simultaneously; may need close-before-open |
| Nested-graph `thread_id` propagation | MEDIUM | 30-min spike before Phase 2 StateGraph split (only if splitting into specialist nodes) |
| CONFIRMED 4-state status | LOW | Defer to Phase 2 polish |
| Session restart UX | LOW | Phase 1 demo is one continuous session until Redis lands; document, never restart mid-demo |

---

## Decision Register

| Decision | Confidence | Rationale |
|----------|------------|-----------|
| Deal state in `deal_store.py`, not `AgentState` | HIGH | Phase 2 graph split = zero schema migration; Redis swap = one Protocol impl change |
| Phase 1 = single `create_agent` ReAct loop (copy `fixed_agent.py`) | HIGH | "Lock first" principle; no novel patterns needed |
| Three Phase 1 archetypes: Infra / Security / Data | MEDIUM-HIGH | Broadest demo coverage; teammate may adjust priority |
| Five-group taxonomy = final (no sixth group) | HIGH | Validated against MEDDPICC + APMP norms; sixth dilutes cockpit clarity |
| PROVISIONAL rubric = MEDDPICC + 3 technical = 11 fields | MEDIUM | Defensible to any technical-sales practitioner; awaiting teammate validation |
| HITL confirm gate = `interrupt()` + data-model write | HIGH | Only pattern that avoids orphan `function_call` trap |
| New `(rfp)` route group parallel to `(pdf)` | HIGH | Isolation; follows existing convention; no cross-route-group imports |
| Move `SurfaceCanvas` to `src/components/shared/` | HIGH | Zero behavior change; required for clean `(rfp)` wiring |
| Archetype inference = visible + one-click override | MEDIUM | High demo value; teammate may want silent inference |
