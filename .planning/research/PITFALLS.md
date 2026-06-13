# Domain Pitfalls — RFP Intake Cockpit

**Domain:** Generative-UI multi-turn intake agent on CopilotKit A2UI starter (LangGraph 1.2.1 + Gemini 3.5 Flash + A2UI v0.9)
**Researched:** 2026-06-13
**Confidence:** HIGH on stack-specific items (from AGENTS.md / FROZEN.md / PROJECT.md); MEDIUM on general LangGraph/HITL patterns; LOW where flagged.

This catalog is scoped to **this** stack and the **5-hour hackathon build window**. Generic "LLM hallucinates" advice has been omitted in favor of failure modes that will actually bite this team between t=0 and t=5h.

---

## Critical Pitfalls (cause demo failure on stage or force a rewrite)

### CR-1: Version Drift — `@copilotkit/*` / `langchain*` / `langgraph*` bumped mid-build
**What goes wrong:** A teammate runs `pnpm add` for an unrelated package; pnpm resolves a transitively newer `@copilotkit/*`. The pre-commit hook rejects the commit. Worse: if `--no-verify` is used, the A2UI envelope contract drifts and `SurfaceCanvas` stops rendering with no clear error.
**Warning signs:** `pnpm verify-pins` failing; pre-commit hook rejection mentioning `@copilotkit/*`; sudden "Cannot read properties of undefined" in `MirrorRenderer`; `createSurface` silently no-ops.
**Prevention:** Treat `FROZEN.md` as inviolable. Any new dependency = `pnpm verify-pins` immediately after. Never use `--no-verify`. If you need a new util, prefer copying 10 lines into the repo over adding a dep.
**Phase:** Phase 1, task 1 (green baseline). Run `pnpm verify-pins` as part of doctor pass.
**Confidence:** HIGH (AGENTS.md hard rule 1).

### CR-2: LLM Swap — replacing `ChatGoogleGenerativeAI` with `langchain-openai` compat
**What goes wrong:** Someone "fixes" a Gemini quirk by swapping to the OpenAI-compat path. Multi-turn tool calling breaks at turn 2 — Gemini 3.x's thought-signature replay is not implemented in `langchain-openai`. The agent appears to work for the first turn, then 500s or hallucinates on the elicitation follow-up.
**Warning signs:** First turn works, second turn returns malformed tool args, stack trace mentions thought_signature or content parts mismatch. Demo crashes precisely on the gap-elicitation step.
**Prevention:** Lock the `ChatGoogleGenerativeAI(...)` line in `rfp_agent.py`. Code-review any LLM-construction diff. Hardcode model id `gemini-3-flash` (or whatever FROZEN.md specifies) — never read from env without a default.
**Phase:** Phase 1, task 4 (rfp_agent.py skeleton).
**Confidence:** HIGH (AGENTS.md hard rule 4, FROZEN.md §LLM provider).

### CR-3: Gemini Typed-Array Tool Validator Rejects `list[dict]`
**What goes wrong:** You add a tool like `assemble_verification_blocks(blocks: list[dict])` to the LangGraph agent. The function-declaration validator on Gemini's side rejects the untyped array; the model never calls the tool; the canvas stays empty. The Python side raises no error — the LLM just silently picks no tool.
**Warning signs:** Agent monologues "I would now generate the verification blocks" but no `update_components` envelope arrives. No Python exception. `tool_calls` list is empty in the agent log.
**Prevention:** Every list parameter on every tool MUST use a `TypedDict` (or Pydantic `BaseModel`) for the element type. No bare `list[dict]`, no `list[Any]`. When in doubt: `list[VerificationBlock]` where `VerificationBlock` is a TypedDict with named fields.
**Phase:** Phase 1 task 4 (rfp_agent.py), Phase 2 verification block tool.
**Confidence:** HIGH (explicit user constraint, matches known Gemini function-declaration behavior).

### CR-4: Duplicate `createSurface` — MessageProcessor throws
**What goes wrong:** The RFP agent emits `createSurface` for the same surface ID on a re-entry (e.g., user edits a field, agent re-runs the verification node). `MessageProcessor` throws; the surface is wiped from the canvas; the demo shows a blank panel.
**Warning signs:** Console throw mentioning duplicate surface or "Surface already exists"; canvas was rendering, now empty after a user action; turn 2+ specifically.
**Prevention:** Emit `createSurface` **exactly once per surface ID per session**. All subsequent updates must use `updateComponents` / `updateDataModel`. Track emitted surface IDs in agent state (`state["emitted_surfaces"]: set[str]`). Pattern to copy: `dynamic_agent.py:generate_a2ui` does this correctly.
**Phase:** Phase 1 task 7 (end-to-end render), Phase 2 verification cockpit (re-render risk highest here).
**Confidence:** HIGH (explicit user constraint).

### CR-5: Orphan `function_call` — frontend tool injected, no resolution path
**What goes wrong:** Someone tries to make a "Confirm & Continue" button trigger by registering a frontend tool via CopilotKit's React hook, but the agent never sees a resolution event. The agent hangs awaiting tool output. UI shows "thinking…" forever.
**Warning signs:** Button click does nothing visible; agent log stuck in "awaiting tool result"; AG-UI stream emits a `function_call` event with no matching `function_call_result`.
**Prevention:** Do HITL via **agent-side polling on a data model field**, not frontend tool injection. The Button's `onAction` writes `data.confirmation_state = "confirmed"` via `updateDataModel`; the LangGraph node reads the data model on its next turn. Copy `dynamic_agent.py`'s server-side tool pattern, not an injected frontend tool. AGENTS.md explicitly flags the "orphan-`function_call` trap."
**Phase:** Phase 2 task 4 ("Confirm & Continue" gate).
**Confidence:** HIGH (AGENTS.md canonical example warning).

### CR-6: Zod Version Mismatch — `zod@^3.25` required by `@copilotkit/a2ui-renderer`
**What goes wrong:** You add a dep that pulls `zod@^4` into the lockfile. The A2UI renderer's prop validation breaks with cryptic `ZodError: undefined` on every surface. Looks like an A2UI bug; is actually a peer-dep mismatch.
**Warning signs:** All surfaces render as error placeholders; console has `ZodError`s mentioning `.parse is not a function` or schema shape mismatch.
**Prevention:** Pin `zod` to `^3.25` explicitly in `package.json`. Run `pnpm why zod` after any dep change. The `DealContextCard` Zod schema in `definitions.ts` MUST be authored against zod v3 API.
**Phase:** Phase 1 task 6 (DealContextCard definition).
**Confidence:** HIGH (explicit user constraint).

### CR-7: `Section.title` Binding to Data Model Path — silent breakage
**What goes wrong:** You write `Section.title = "$.deal.company_name"` expecting path interpolation. `Section.title` is `z.string()` only — the literal string `$.deal.company_name` is rendered. Demo shows raw paths in headers.
**Warning signs:** Headers reading literal `$.foo.bar`; or static title that never updates as data changes.
**Prevention:** For dynamic titles, use a component whose title field is `stringOrPath`, or compute the title agent-side and pass it as a string prop. Audit every `Section` you author — if the title is supposed to be dynamic, restructure.
**Phase:** Phase 2 task 2 (grouped verification blocks — Sections are the natural container).
**Confidence:** HIGH (explicit user constraint).

---

## Moderate Pitfalls (eat 30-60 min if hit; rarely fatal)

### MD-1: LangGraph Infinite Loop — node re-enters itself on tool error
**What goes wrong:** Gap-elicitation node calls a tool, tool raises, node catches and loops to retry. Without a max-iteration guard or recursion limit override, you burn API quota and the user sees nothing.
**Prevention:** Set `graph.compile(checkpointer=memory).invoke(..., {"recursion_limit": 25})`. Add a turn counter in state; bail with a user-visible error after N retries. Never let the agent loop on tool errors silently.
**Phase:** Phase 1 task 4 (agent skeleton), Phase 2 (elicitation loop).
**Confidence:** MEDIUM (general LangGraph pattern; LOW that it bites in 5h, but if it does it's brutal).

### MD-2: MemorySaver Thread ID Mismatch — turn 2 starts fresh
**What goes wrong:** Each request to `/rfp` uses a new `thread_id`, so MemorySaver checkpoints are isolated per turn. The agent has no memory of what it just elicited; asks the same gap question again.
**Warning signs:** Agent repeats itself; deal object resets between turns; verification block list is empty on the second turn even though you filled it on the first.
**Prevention:** Use the CopilotKit `threadId` from the AG-UI session as the LangGraph `thread_id`. Wire it explicitly in `main.py` at the `/rfp` endpoint. Verify by logging `thread_id` on every invocation.
**Phase:** Phase 1 task 3 (API route wiring).
**Confidence:** HIGH (this is the #1 LangGraph multi-turn footgun).

### MD-3: Surface Bus Timing — `updateComponents` arrives before `createSurface`
**What goes wrong:** The agent's tool emits both ops in one shot, but the AG-UI stream interleaves them with chat tokens. `updateComponents` for a not-yet-existent surface is silently dropped (existing SurfaceCanvas deduplicates ops but does NOT buffer pre-create updates).
**Warning signs:** Surface appears empty; data model has values but no rendered components; subsequent updates work fine.
**Prevention:** Always emit `createSurface` → `updateComponents` → `updateDataModel` in that order in a single tool return. Don't split across multiple tool calls. Don't await between them.
**Phase:** Phase 1 task 7 (end-to-end render), Phase 2 task 2 (grouped blocks).
**Confidence:** MEDIUM (inferred from constraint that SurfaceCanvas dedupes but no buffering mentioned).

### MD-4: MirrorRenderer Doesn't Pick Up Ops — mirror pill stays empty
**What goes wrong:** MirrorRenderer reads from the chat message stream's tool-call results, not the SurfaceCanvas state. If your agent emits A2UI ops via streaming custom events rather than a tool return, the chat pill won't mirror.
**Warning signs:** Canvas renders the surface, but the inline chat pill is blank or shows "no surface".
**Prevention:** Emit A2UI envelopes as the **return value of a LangGraph tool**, not as side-channel events. Pattern: `dynamic_agent.py:generate_a2ui` returns the envelope dict; the tool result carries it; MirrorRenderer picks it up.
**Phase:** Phase 1 task 4 (agent emits surface).
**Confidence:** MEDIUM.

### MD-5: Forced `tool_choice` on Gemini 3.5 Flash — multi-turn replay breaks
**What goes wrong:** You set `tool_choice="render_deal_context"` to force the agent to call a specific tool. On turn 2, the thought-signature for the prior turn doesn't match the forced-choice constraint and the model rejects the history.
**Warning signs:** Turn 1 works (forced tool fires), turn 2 returns an InvalidArgument or empty response.
**Prevention:** Use `tool_choice="auto"` and steer via the system prompt. If you need to force a tool, only do it on the FIRST turn (when there's no history to replay). Branch your graph so forced-tool nodes are entry-points only.
**Phase:** Phase 1 task 4 (rfp_agent.py).
**Confidence:** MEDIUM (consistent with Gemini 3.x thought-signature constraint from AGENTS.md rule 4).

### MD-6: Empty State vs Broken State — judge can't tell
**What goes wrong:** A surface renders but data is empty (`fields: []`). Looks identical to a render failure. Judge thinks the demo broke.
**Prevention:** Every renderer must have an explicit empty-state with copy ("Awaiting requirements dump…" / "All fields verified"). Never let a component degenerate to a blank div.
**Phase:** Phase 1 task 6 (DealContextCard renderer), Phase 2 verification blocks.
**Confidence:** HIGH (demo-craft fundamental).

### MD-7: HITL Confirmation Race — agent advances before user clicks
**What goes wrong:** Agent emits the verification surface AND moves to the "generate final RFP" node in the same graph turn, expecting the next user input to be confirmation. But CopilotKit re-streams the agent before user interaction completes, and the RFP generates before the user clicks "Confirm".
**Warning signs:** Final RFP renders without user confirmation; verification gate is bypassed.
**Prevention:** Use a LangGraph **interrupt** node (or graph-level pause) keyed on `data.confirmation_state != "confirmed"`. Don't rely on turn boundaries to gate progression. The graph should have an explicit pause state that only the data-model-write resumes.
**Phase:** Phase 2 task 4 (Confirm & Continue gate), Phase 3 task 1 (Final RFP).
**Confidence:** MEDIUM (general HITL pattern; the precise primitive depends on LangGraph 1.2.1 API which the team will verify).

### MD-8: PROVISIONAL Rubric Treated As Real
**What goes wrong:** Halfway through Phase 2, someone wires the readiness indicator to PROVISIONAL hard-blocker logic and forgets to mark it. Teammate's real rubric arrives at hour 4; swapping breaks downstream gating.
**Prevention:** Every hard-blocker reference in code MUST have a `# PROVISIONAL: replace at H+4` comment. Centralize the rubric in ONE module (`agent/src/rubric.py`); never inline hard-blocker conditions.
**Phase:** Phase 1 task 4 (agent uses rubric), Phase 3 task 4 (swap).
**Confidence:** HIGH (PROJECT.md guardrail).

---

## Minor Pitfalls (10-20 min cost)

### MN-1: Brand CSS leaks pdf-analyst styles into RFP route
**What goes wrong:** `(rfp)` route group inherits global styles from `(pdf)/pdf-analyst.css` via a shared `layout.tsx` or global import.
**Prevention:** Scope shell CSS to its route group's `layout.tsx`. Don't touch theme until Phase 3 polish.
**Phase:** Phase 3 task 2.

### MN-2: TypeScript Errors Block `pnpm smoke` Right Before Demo
**Prevention:** Run `pnpm typecheck` every 30 min. Don't save TS errors for "the end."
**Phase:** All phases.

### MN-3: Synthetic Data Looks Fake — judge dismisses
**Prevention:** Spend 15 min in Phase 3 on 2-3 realistic-looking input dumps. Use plausible company names ("Northwind Logistics"), believable jargon, varied lengths.
**Phase:** Phase 3 task 3.

### MN-4: Catalog Mirror Drift — `agent/src/catalog.py` out of sync with `definitions.ts`
**What goes wrong:** You add `DealContextCard` to `definitions.ts` but forget to mirror it in `CATALOG_PROMPT`. Agent doesn't know the component exists and never emits it.
**Prevention:** AGENTS.md §4 explicitly requires both sides. Add a grep step to your checklist.
**Phase:** Phase 1 task 6.

### MN-5: Worktree env Loading — agent boots without `GEMINI_API_KEY`
**Prevention:** Per AGENTS.md worktree section, copy `.env` into the worktree root or export inline. Doctor pass catches this.
**Phase:** Phase 1 task 1.

---

## Hackathon-Specific Failure Modes (last 2 hours of build)

### H-1: Scope Creep at H+3 — "we should add a Slack integration"
**Prevention:** Hard freeze at H+3 (end of Phase 2). Phase 3 is polish + demo only. Anything not on the Phase 3 list is out.

### H-2: "It Worked On My Machine" — demo on a different laptop
**Prevention:** Demo on the SAME machine you built on. Have a backup laptop with the repo cloned + `.env` set + `pnpm dev` cold-tested at H+4.

### H-3: Cold-Start Stage Crash — first prompt of the day fails
**What goes wrong:** Gemini cold-start, network hiccup, or a stale dev server from yesterday. First prompt on stage 500s.
**Prevention:** Run the demo end-to-end 5 minutes before stage time. Keep `pnpm dev` running. Have one of the polished input dumps in your clipboard.

### H-4: Live Typing on Stage — typo derails demo
**Prevention:** All hero inputs are paste-ready in a text file or clipboard manager. Never live-type a hero prompt.

### H-5: Smoke Gate Skipped to Save Time
**What goes wrong:** Pre-commit hook rejected something; team disabled the hook to commit. Now a real issue lands silently.
**Prevention:** Never bypass `pnpm smoke` or pre-commit. If it fails, fix it — it takes 5 min. Skipping it costs 30+ min of demo debug.

### H-6: Demo Narrative Not Rehearsed
**What goes wrong:** Tech works; presenter fumbles "what is this?" Judge tunes out.
**Prevention:** Write the 60-second pitch in Phase 3. Rehearse it twice before stage. "Messy dump → grouped verified RFP, agent chases gaps a chat box can't" — that's the whoa.

---

## Phase-Specific Warnings Matrix

| Phase / Task | Top Pitfall | Mitigation |
|---|---|---|
| P1.1 Green baseline | CR-1 (version drift), MN-5 (env) | Run doctor + verify-pins first |
| P1.3 API route wire | MD-2 (thread_id mismatch) | Pass CopilotKit threadId through to LangGraph |
| P1.4 rfp_agent.py | CR-2 (LLM swap), CR-3 (typed-array), MD-1 (loops), MD-5 (tool_choice), MD-8 (rubric) | Copy `dynamic_agent.py` shape exactly; centralize rubric |
| P1.6 DealContextCard | CR-6 (zod), CR-7 (Section.title), MN-4 (catalog mirror) | Pin zod ^3.25; audit Section title sources; update CATALOG_PROMPT |
| P1.7 End-to-end render | CR-4 (duplicate createSurface), MD-3 (op order), MD-4 (mirror), MD-6 (empty state) | Emit ops in fixed order, once; explicit empty states |
| P2.1 Gap elicitation | MD-1 (loops), MD-8 (PROVISIONAL rubric) | Recursion limit; PROVISIONAL comments |
| P2.2 Grouped blocks | CR-4 (dup surface on re-edit), CR-7 (Section.title), MD-6 (empty) | Track emitted surface IDs; agent-computed titles |
| P2.4 Confirm gate | CR-5 (orphan function_call), MD-7 (HITL race) | Use data-model-write + graph interrupt, not frontend tool |
| P3.1 Final RFP | MD-7 (race), MD-8 (rubric swap) | Gate explicitly on confirmation_state |
| P3.3 Hero cases | MN-3 (synthetic looks fake), H-4 (live typing) | Paste-ready realistic dumps |
| P3.5 Smoke | H-5 (skipped gate) | Run `pnpm smoke` — non-negotiable |
| Stage demo | H-2, H-3, H-6 | Same laptop, cold-test at H+4, rehearse pitch |

---

## Sources

- `AGENTS.md` (hackathon starter agent guide) — HIGH confidence, project-of-record
- `.planning/PROJECT.md` (project brief) — HIGH confidence
- User-provided constraints (typed-array, duplicate createSurface, Section.title, zod pin, Gemini OpenAI-compat trap) — HIGH confidence
- General LangGraph 1.2.1 multi-turn patterns (MemorySaver thread_id, recursion limit, interrupt nodes) — MEDIUM confidence, common LangGraph footguns
- Hackathon demo-craft (H-series) — MEDIUM confidence, generalized from prior hackathon post-mortems
