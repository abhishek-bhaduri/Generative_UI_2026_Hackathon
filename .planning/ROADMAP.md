# ROADMAP — RFP Intake Cockpit

**Project:** RFP Intake Cockpit
**Hackathon:** London A2A & A2UI Hackathon, June 13, 2026
**Build window:** 5 hours
**Granularity:** Fine (3 phases, natural delivery boundaries driven by demo-ability)
**Coverage:** 18/18 v1 requirements mapped (FOUND-01 through FOUND-18 + NFR-01 through NFR-08)
**Last updated:** 2026-06-13

---

## Phases

- [ ] **Phase 1: Foundation** — Green baseline + scaffold + DealContextCard renders in canvas
- [ ] **Phase 2: Elicitation + Verification Cockpit** — Gap chases + Linkup enrichment + five-group verification + HITL gate
- [ ] **Phase 3: Final RFP + Polish + Demo** — finalize_rfp tool + brand theme + hero cases + rubric swap seam

---

## Phase Details

### Phase 1: Foundation
**Goal**: A rep can paste a raw requirements dump and see a `DealContextCard` surface render in the canvas with an archetype badge, STATED/INFERRED/MISSING field tags, and a readiness seed — within one agent turn.
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, FOUND-08, NFR-01, NFR-02, NFR-03, NFR-04, NFR-05, NFR-06, NFR-07, NFR-08
**Success Criteria** (what must be TRUE):
  1. `pnpm doctor`, `pnpm verify-pins`, and `pnpm smoke` pass without errors; the existing pdf-analyst demo still loads and responds.
  2. Navigating to `/rfp-intake` shows a split layout (chat left, generative UI canvas right) wired to a separate CopilotKit runtime endpoint (`/api/copilotkit-rfp`).
  3. Pasting any free-form requirements text into the RFP chat causes a `DealContextCard` to appear in the canvas within one agent turn, showing at minimum: an archetype badge, two or more STATED fields (extracted from the dump), and at least one MISSING field with a "why we need this" line.
  4. STATED fields show the source quote on hover; INFERRED fields show a confidence indicator; MISSING fields are visually distinct and carry rationale copy.
  5. The `DealContextCard` does not re-emit `createSurface` on subsequent turns (dedupe tracked in agent state); updates arrive via `updateComponents` / `updateDataModel` only.
**Plans**: TBD
**UI hint**: yes

**Task sketch (critical path — do not reorder):**
1. Green baseline: `pnpm install`, doctor pass, `pnpm smoke` → green
2. Move `src/components/pdf-analyst/SurfaceCanvas.tsx` → `src/components/shared/SurfaceCanvas.tsx`; update the two imports that reference it
3. Add `DealContextCard` to `src/a2ui/catalog/definitions.ts` (Zod schema: archetype, customer?, title, fields[], readiness?)
4. Add `DealContextCard` renderer to `src/a2ui/catalog/renderers.tsx` (status badge color mapping + hover copy)
5. Mirror `DealContextCard` one-liner in `agent/src/catalog.py` `CATALOG_PROMPT`
6. Write `agent/src/deal_store.py` — `DealStore` Protocol + in-memory `dict[thread_id, DealObject]`
7. Write `agent/src/rfp_hard_blockers.py` — PROVISIONAL MEDDPICC + 3-technical = 11 fields; `PROVISIONAL = True`; every reference carries `# PROVISIONAL: replace at H+4`
8. Write `agent/src/rfp_agent.py` — single `create_agent` ReAct loop (copy `fixed_agent.py` shape); tools: `extract_seed_fields`, `render_deal_context` (Phase 1 minimum); TypedDict list params only (CR-3); `tool_choice="auto"` (MD-5); surface-ID deduplication tracked in state (CR-4)
9. Mount `/rfp` endpoint in `agent/main.py`; wire CopilotKit `threadId` → LangGraph `thread_id` explicitly (NFR-05 / MD-2)
10. Write `src/app/api/copilotkit-rfp/route.ts` (clone of `copilotkit-pdf`; `injectA2UITool: false`)
11. Write `src/components/rfp-cockpit/Providers.tsx` (CopilotKit provider for RFP channel)
12. Write `src/app/(rfp)/layout.tsx` + `src/app/(rfp)/rfp-intake/page.tsx` (split layout, no cross-(pdf) imports)
13. End-to-end test: paste Security Tooling dump → DealContextCard renders → verify pitfall matrix (CR-1 through CR-7, MD-2, MD-6, MD-8)

**Pitfalls owned by this phase:** CR-1 (version drift), CR-2 (LLM swap), CR-3 (typed-array), CR-4 (duplicate createSurface), CR-6 (zod pin), CR-7 (Section.title), MD-2 (thread_id mismatch), MD-5 (forced tool_choice), MD-6 (empty state), MD-8 (PROVISIONAL rubric leaks)

---

### Phase 2: Elicitation + Verification Cockpit
**Goal**: After seeing the initial card, the rep can watch the agent identify and chase the most critical missing fields (with deal-killer rationale and Linkup-sourced company context where available), see completeness climb on a `ReadinessMeter`, edit any field inline, and hit a "Confirm & Continue" gate — at which point the verification surface is locked and Phase 3 can proceed.
**Depends on**: Phase 1
**Requirements**: FOUND-09, FOUND-10, FOUND-11, FOUND-12, FOUND-13, FOUND-14
**Success Criteria** (what must be TRUE):
  1. After the initial card renders, the agent emits a batched set of gap-chase questions (not one-by-one) targeting the highest-priority MISSING hard-blocker fields, each with a "why this matters" rationale tied to a specific deal-killer pattern.
  2. If the requirements dump includes a company name or URL, the agent enriches the deal with Linkup company context (industry, known tech stack, compliance signals) in the same or immediately following turn; Linkup-sourced fields show INFERRED status with attribution visible on badge hover; Linkup failure causes graceful degradation (no crash, agent continues).
  3. A `ReadinessMeter` component is visible on the verification surface; it starts below 50% for a gap-heavy dump and climbs visibly as the rep supplies answers (the 40% → 95% scenario must be demo-able).
  4. Five grouped `VerificationGroup` blocks (Commercials, Scope & Success Criteria, Technical Constraints, Stakeholders & Process, Timeline) render; every field is tagged STATED / INFERRED / MISSING and is editable inline; editing a field re-renders the group in place without duplicating the surface.
  5. The "Confirm & Continue" button is disabled until readiness reaches the threshold; clicking it uses LangGraph `interrupt()` + data-model-write resume (NOT a frontend-injected tool) and carries a full `{action, deal}` payload for idempotency; the agent does NOT advance to final RFP until this gate passes.
**Plans**: TBD
**UI hint**: yes

**Task sketch:**
1. Add `chase_gaps` tool to `rfp_agent.py` — reads `deal_store`, picks top-N MISSING hard-blockers in priority order, emits batched ChoiceChips + TextInput catalog primitives under a new "Open questions" Section on the `rfp-deal` surface (update ops only — surface already created)
2. Add `enrich_company_context` tool (or extend `extract_seed_fields`) — Linkup API call when company name / URL detected; writes enrichment to `deal_store` with `source: "linkup"` attribution; graceful degradation on error (NFR pattern: never crash on enrichment failure)
3. Add `render_verification` tool — emits new `rfp-verify` surface (track in emitted_surfaces to avoid CR-4); renders five `VerificationGroup` components + `ReadinessMeter`; action contract: `edit_field`, `approve_group`, `confirm_continue`
4. Add `VerificationGroup` component to catalog (definitions.ts + renderers.tsx + catalog.py mirror); editable fields use catalog `TextInput`; "approve group" button bulk-promotes INFERRED → STATED
5. Add `ReadinessMeter` component to catalog (check if existing `Progress` primitive suffices; build bespoke only if not)
6. Wire HITL gate in `rfp_agent.py`: emit `rfp-verify` surface BEFORE calling `interrupt()`; resume path reads `decision.action` — `"confirm"` → goto final_rfp, `"edit"` → goto gap_check
7. Multi-surface verify: confirm SurfaceCanvas handles `rfp-deal` + `rfp-verify` simultaneously in the same channel (close-before-open if needed; document decision)
8. Extend system prompt with 5-stage state-machine logic; add recursion limit guard (MD-1); ensure action handler re-reads deal_store on every `log_a2ui_event` result

**Pitfalls owned by this phase:** CR-4 (peak risk — re-emit on edit), CR-5 (orphan function_call — confirm gate), MD-1 (infinite loop), MD-3 (surface bus timing), MD-7 (HITL race), MD-8 (PROVISIONAL rubric references)

---

### Phase 3: Final RFP + Polish + Demo
**Goal**: After the Confirm gate, the judge sees a complete, grouped, verified Final RFP surface render — sourced only from confirmed deal fields. The cockpit has sales-appropriate branding, paste-ready hero demo inputs covering three archetypes, and the PROVISIONAL rubric is swappable in one file when the teammate delivers the real one.
**Depends on**: Phase 2
**Requirements**: FOUND-15, FOUND-16, FOUND-17, FOUND-18
**Success Criteria** (what must be TRUE):
  1. Clicking "Confirm & Continue" causes a `rfp-final` surface to render — a grouped artifact matching the five-group taxonomy, composed only from STATED and confirmed-INFERRED fields; no fabricated content.
  2. The `/rfp-intake` shell has sales-appropriate accent colors (distinct from the pdf-analyst blue defaults) applied only via `src/a2ui/theme.css` + `src/app/(rfp)/rfp-cockpit.css` — no other files changed.
  3. At least two paste-ready hero input dumps exist (Security Tooling "auditor" scenario and one other); the 60-second demo flow (dump → card → gap chases → answers → readiness climbs → confirm → final RFP) runs end-to-end without prompting from the operator.
  4. Swapping the PROVISIONAL rubric requires only: editing the list in `agent/src/rfp_hard_blockers.py` and flipping `PROVISIONAL = False` — zero logic changes elsewhere; `pnpm smoke` passes before and after the swap.
**Plans**: TBD
**UI hint**: yes

**Task sketch:**
1. Wire `finalize_rfp` tool in `rfp_agent.py` — gated on `confirmation_state == "confirmed"`; composes Section / Card / BulletList tree from verified deal fields only; emits `rfp-final` surface (one-time createSurface)
2. Edit `src/a2ui/theme.css` — sales-appropriate accent tokens (navy/slate + green CTA, not pdf-analyst purple)
3. Create `src/app/(rfp)/rfp-cockpit.css` + `src/components/rfp-cockpit/Brand.tsx` — shell brand for RFP route (company logo placeholder, "RFP Intake Cockpit" header)
4. Write 2-3 hero demo cases in `.planning/demo-cases/` — Security Tooling ("replace our SIEM by Q3 / auditor"), Infra Migration, Data Platform; plausible company names and jargon; paste-ready
5. If teammate delivers final rubric: edit `agent/src/rfp_hard_blockers.py` list + flip `PROVISIONAL = False`; run `pnpm smoke` to confirm zero logic changes needed
6. H+4 cold-test: restart `pnpm dev` from cold; run each hero dump end-to-end on demo laptop; confirm `pnpm smoke` is green
7. H+4.5 rehearse 60-second pitch (narrate the "whoa": messy dump → grouped verified RFP, agent chases the gaps a chat box can't)

**Pitfalls owned by this phase:** MD-7 (confirm gate race — finalize_rfp must not run until confirmation_state set), MD-8 (final rubric swap), MN-1 (brand CSS bleed), MN-3 (synthetic data realism), H-2/H-3/H-4/H-6 (demo day)

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/1 | Not started | - |
| 2. Elicitation + Verification Cockpit | 0/1 | Not started | - |
| 3. Final RFP + Polish + Demo | 0/1 | Not started | - |

---

## Requirement Coverage

### Functional Requirements

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

### Non-Functional Requirements

| Requirement | Phase | Notes |
|-------------|-------|-------|
| NFR-01 — Frozen stack | Phase 1 | pnpm verify-pins on every dep change |
| NFR-02 — LLM frozen | Phase 1 | ChatGoogleGenerativeAI locked in rfp_agent.py |
| NFR-03 — Typed arrays | Phase 1 | TypedDict element types in all tool params |
| NFR-04 — Surface deduplication | Phase 1 | emitted_surfaces set in agent state |
| NFR-05 — thread_id wiring | Phase 1 | CopilotKit threadId → LangGraph thread_id in main.py |
| NFR-06 — Model budget | All | Planning agents = Opus; execution = Sonnet |
| NFR-07 — No PII | All | Synthetic data only; enforced in hero case authoring |
| NFR-08 — Local only | Phase 3 | Cold-test at H+4 on demo laptop |

**Coverage total: 18/18 functional requirements + 8/8 non-functional requirements. No orphans.**

---

## Critical Risk Register

| Risk | Severity | Mitigation | Phase |
|------|----------|------------|-------|
| CR-5: Orphan function_call (Confirm gate) | FATAL | Use `interrupt()` + data-model-write resume; never useCopilotAction for gate | 2 |
| CR-3: Gemini typed-array rejects untyped list params | FATAL | TypedDict on every list; copy fixed_agent.py:37-42 shape | 1 |
| CR-4: Duplicate createSurface wipes canvas | FATAL | Track emitted_surfaces in state; update-only after first emit | 1, 2 |
| MD-2: thread_id mismatch (multi-turn resets) | HIGH | Wire CopilotKit threadId explicitly in main.py at /rfp | 1 |
| MD-7: HITL race (RFP generates before confirm) | HIGH | Explicit interrupt node; finalize_rfp gated on confirmation_state | 2, 3 |
| Linkup key unavailable | MEDIUM | Graceful degradation — agent continues without Linkup; check sponsor docs at H+0 | 2 |
| PROVISIONAL rubric not delivered | MEDIUM | 11-field MEDDPICC anchor is defensible standalone; swap seam ready | 3 |

---

## Scope Freeze Schedule

| Time | Gate |
|------|------|
| H+0 | Phase 1 begins — green baseline first |
| H+2 | Phase 2 begins — Phase 1 must be demo-able |
| H+3.5 | **Hard scope freeze** — no new features after this point |
| H+4 | Phase 3 complete — cold-test on demo laptop |
| H+4.5 | Demo rehearsal — 60-second pitch, paste-ready inputs only |
| H+5 | Demo time |
