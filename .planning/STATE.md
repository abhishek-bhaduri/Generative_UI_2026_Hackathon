# STATE — RFP Intake Cockpit

**Project:** RFP Intake Cockpit
**Hackathon:** London A2A & A2UI Hackathon, June 13, 2026
**Build window:** 5 hours
**Last updated:** 2026-06-13

---

## Project Reference

**Core value:** The agent ELICITS and VERIFIES. It turns a messy requirements dump into a grouped, verified RFP by chasing the critical fields B2B sales customers chronically omit — using generative UI that a chat box plainly cannot replicate.

**The "whoa":** Paste "replace our SIEM by Q3 because auditor" → archetype badge → five grouped blocks with ~40% MISSING → batched gap chases with deal-killer rationale → readiness climbs 40%→95% → Confirm gate → final RFP renders.

**Current focus:** Phase 1 — Foundation (planning complete; build not started)

---

## Current Position

**Phase:** 1 — Foundation
**Plan:** Not started
**Status:** Planning complete
**Progress:** [----------] 0%

| Phase | Status | Completed |
|-------|--------|-----------|
| 1. Foundation | Not started | - |
| 2. Elicitation + Verification Cockpit | Not started | - |
| 3. Final RFP + Polish + Demo | Not started | - |

---

## Accumulated Context

### Decisions Locked

| Decision | Confidence | Why it matters |
|----------|------------|----------------|
| Deal object lives in `deal_store.py`, NOT `AgentState` | HIGH | Phase 2 graph split = zero schema migration; Redis swap = one Protocol change |
| Phase 1 = single `create_agent` ReAct loop (copy `fixed_agent.py` shape) | HIGH | "Lock first" — working baseline before any split |
| Five-group taxonomy is final (no sixth group) | HIGH | Validated against MEDDPICC + APMP norms; sixth group breaks cockpit gestalt |
| HITL confirm gate = `interrupt()` + data-model-write resume | HIGH | Only pattern that avoids orphan `function_call` trap (CR-5) |
| `(rfp)` route group parallel to `(pdf)`, no cross-group imports | HIGH | Isolation; follows existing convention |
| Move `SurfaceCanvas` to `src/components/shared/` | HIGH | First task of Phase 1; zero behavior change; required for `(rfp)` wiring |
| Archetypes Phase 1: Infra Migration, Security Tooling, Data Platform | MEDIUM-HIGH | Broadest demo coverage |
| Archetype inference is visible + one-click override | MEDIUM | High demo value; teammate may want silent — confirm if available |
| PROVISIONAL rubric = MEDDPICC + 3 technical = 11 fields | MEDIUM | Swap seam ready; awaiting teammate validation |

### Active Constraints

- Stack is FROZEN: never bump `@copilotkit/*` (1.57.4), `langchain` (1.3.1), `langchain-core` (1.4.0), `langgraph` (1.2.1), `next` (16.1.6), `react` (19.2.4), `zod` (^3.25)
- LLM is FROZEN: `ChatGoogleGenerativeAI` (Gemini 3.5 Flash) only — no OpenAI compat (CR-2)
- Every list param in agent tools MUST use a TypedDict element type — never `list[dict]` or `list[Any]` (CR-3)
- `createSurface` emitted exactly once per surface ID per session — track in `emitted_surfaces` set (CR-4)
- PROVISIONAL rubric: every reference in code carries `# PROVISIONAL: replace at H+4` comment (MD-8)
- No PII; synthetic data only; local demo only; no deployment

### Open Items

| Item | Status | Owner | Deadline |
|------|--------|-------|----------|
| Final hard-blocker rubric | PROVISIONAL — 11 fields (MEDDPICC + 3 technical) | Teammate | Before Phase 3 |
| Linkup API key / auth method | Unconfirmed — check sponsor docs at hackathon H+0 | Abhishek | H+0 |
| Archetype inference: visible vs silent | Recommend visible + one-click override | Confirm with teammate | Phase 1 |
| Multi-surface dedupe (`rfp-deal` + `rfp-verify` simultaneously) | Unverified — may need close-before-open | Abhishek | Phase 2 |

### Blockers

None at planning complete. First blocker risk: Linkup API key availability at H+0.

---

## Performance Metrics

**Requirements coverage:** 18/18 functional, 8/8 non-functional
**Critical pitfalls mitigated in plan:** CR-1, CR-2, CR-3, CR-4, CR-5, CR-6, CR-7, MD-2, MD-5, MD-6, MD-7, MD-8 (all documented in ROADMAP.md risk register)
**Highest-risk task:** FOUND-14 — Confirm & Continue gate (LangGraph `interrupt()` + data-model-write resume)

---

## Session Continuity

### To resume work, read:
1. This file (STATE.md) — current position + decisions
2. `.planning/ROADMAP.md` — Phase 1 task sketch (critical path, 13 steps)
3. `.planning/research/ARCHITECTURE.md` §3 (data flow) + §4.1 (Phase 1 `create_agent` pattern)
4. `.planning/research/PITFALLS.md` — Phase-specific warnings matrix (bottom of file)
5. `agent/src/fixed_agent.py` — canonical pattern to copy for `rfp_agent.py`
6. `agent/src/dynamic_agent.py` — HITL action transport pattern (`log_a2ui_event`)

### Next action:
Run `pnpm doctor` and `pnpm smoke` to establish the green baseline. Then start Phase 1 task 2 (move SurfaceCanvas).

### Demo laptop checklist (fill in at H+4):
- [ ] `pnpm dev` cold-start confirmed
- [ ] Hero input 1 (Security Tooling) paste-ready in clipboard manager
- [ ] Hero input 2 (Infra Migration or Data Platform) paste-ready
- [ ] `pnpm smoke` passes on demo machine
- [ ] 60-second pitch rehearsed twice
- [ ] Backup laptop: repo cloned + `.env` set + cold-tested
