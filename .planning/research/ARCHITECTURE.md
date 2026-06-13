# Architecture: RFP Intake Cockpit

**Domain:** Generative-UI intake cockpit (LangGraph + A2UI v0.9 + AG-UI)
**Researched:** 2026-06-13
**Confidence:** HIGH for existing-pattern recapture; MEDIUM for novel deal-state + multi-node patterns (training data + observed codebase only — Context7 not consulted for langgraph 1.2.x specific MemorySaver edge-cases; recommend a 30-min spike if Phase 2 graph-split is reached).

---

## 1. System Architecture (one diagram)

```
┌─────────────── Browser (Next.js 16, React 19) ───────────────┐
│                                                              │
│  src/app/(rfp)/rfp-intake/page.tsx        ← NEW route group  │
│    ├─ Providers (RFP)        (NEW, copy pdf-analyst pattern) │
│    │    └─ CopilotKit runtime endpoint: /api/copilotkit-rfp  │
│    │    └─ MirrorRenderer (reused from a2ui-renderer)        │
│    ├─ Chat pane (CopilotChat, channel="rfp")                 │
│    └─ SurfaceCanvas channel="rfp"   ← REUSED unchanged       │
│         └─ A2UIProvider catalog={catalog} onAction=…         │
│              └─ A2UIRenderer  (renders surface from bus)     │
│                                                              │
│  src/a2ui/catalog/                                           │
│    ├─ definitions.ts  ← MODIFIED (add DealContextCard +      │
│    │                    VerificationGroup + ReadinessMeter)  │
│    ├─ renderers.tsx   ← MODIFIED (mirror renderers)          │
│    └─ surface-bus.ts  ← REUSED unchanged                     │
│                                                              │
│  src/app/api/copilotkit-rfp/route.ts   ← NEW (clone of       │
│    copilotkit-pdf, points at :8123/rfp)                      │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ AG-UI transport (CopilotKit runtime)
                           │ forwardedProps.a2uiAction on chip/button
                           ▼
┌──────────────── FastAPI (uvicorn :8123) ─────────────────────┐
│  agent/main.py        ← MODIFIED (mount /rfp endpoint)       │
│                                                              │
│  agent/src/rfp_agent.py    ← NEW                             │
│    Phase 1: single create_agent (ReAct loop)                 │
│      tools = [extract_seed_fields,                           │
│               render_deal_context,                           │
│               chase_gaps,                                    │
│               render_verification,                           │
│               finalize_rfp]                                  │
│    Phase 2: StateGraph with specialist nodes (see §4)        │
│                                                              │
│  agent/src/deal_store.py   ← NEW (in-memory dict +           │
│                              Redis-ready Protocol interface) │
│                                                              │
│  agent/src/catalog.py      ← MODIFIED (CATALOG_PROMPT lines  │
│                              for the 3 new components)       │
│                                                              │
│  Gemini 3.5 Flash via ChatGoogleGenerativeAI (FROZEN)        │
│  MemorySaver checkpointer keyed by thread_id (= session)     │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component Boundaries (what owns what)

| Concern | Owner | Why |
|---|---|---|
| **Conversation state (messages)** | LangGraph `MemorySaver` keyed by `thread_id` | Built-in; CopilotKit runtime already injects `thread_id` per session. No extra wiring. |
| **Deal object (typed business state)** | `deal_store.py` (in-memory `dict[thread_id, Deal]`) keyed by same `thread_id` | Persisting the deal *inside* LangGraph state forces a State schema migration every time the deal shape changes. A side-store keeps the LangGraph state messages-only and lets you swap to Redis behind the same Protocol. |
| **Field STATED/INFERRED/MISSING provenance** | Deal object (per-field metadata: `{value, source, confidence, last_updated}`) | Provenance is a guardrail-critical invariant (per PROJECT.md §1). It must travel with the value, not as a parallel array — otherwise it desyncs. |
| **Hard-blocker rubric** | `agent/src/rubric.py` (NEW) — module-level `PROVISIONAL_RUBRIC: list[BlockerSpec]` | Single source of truth so the readiness meter and the gap-chaser read the same list. Marked PROVISIONAL until teammate delivers. |
| **A2UI envelope emission** | The tool's return value (same shape as `render_dashboard` in fixed_agent.py) | Proven path. No frontend-tool injection. Survives Gemini's tool-arg parser. |
| **User action routing** | Existing `SurfaceCanvas.onAction` → `forwardedProps.a2uiAction` → `log_a2ui_event` tool result | Already battle-tested by fixed_agent. Zero changes needed. |
| **Surface lifecycle (createSurface dedupe)** | `SurfaceCanvas` `createdSurfacesRef` | Already handles "second batch with same surfaceId" — critical for our multi-turn flow where every turn may re-emit `createSurface`. |

---

## 3. Data Flow (one intake session, turn by turn)

```
Turn 1 (paste dump)
  User → chat: "<requirements dump>"
  Agent (rfp_agent ReAct):
    ① extract_seed_fields(dump_text)
        → returns {archetype, fields:[{key, value, source:"stated|inferred",
                                        confidence}], gaps:[...]}
        → side-effect: deal_store.upsert(thread_id, deal)
    ② render_deal_context(thread_id)
        → reads deal_store, emits ops:
             createSurface("rfp-deal", catalog_id)
             updateComponents("rfp-deal", [DealContextCard tree])
             updateDataModel("rfp-deal", {deal payload})
  Canvas: renders DealContextCard with STATED/INFERRED/MISSING tags

Turn 2 (gap chase — agent-initiated)
  Agent (same turn as above, or follow-up):
    ③ chase_gaps(thread_id)
        → reads deal_store, picks top-N missing critical fields
        → emits ops on surface "rfp-deal" updating a "Open questions"
          Section with one Card per question + ChoiceChips + TextInput
          (using catalog primitives; NO bespoke component needed)
  User: answers via chips OR types in chat OR clicks a button
        → SurfaceCanvas onAction → forwardedProps.a2uiAction
        → log_a2ui_event tool result with {name, surfaceId, context:{field, value}}

Turn 3 (user supplies answer)
  Agent:
    ① extract_seed_fields(answer_text)  ← reused tool; merges into deal
    ② render_deal_context (re-render in place — same surfaceId)
    ③ chase_gaps  (now fewer questions)
  Loop until rubric satisfied.

Turn N (verification gate)
  Agent:
    ④ render_verification(thread_id)
        → emits NEW surfaceId "rfp-verify" with 5 VerificationGroup
          components (Commercials | Scope | Tech | Stakeholders | Timeline)
        → each field editable (TextInput from catalog)
        → readiness meter (ReadinessMeter component) bound to deal.readiness
        → "Confirm & Continue" Button at bottom (disabled until readiness=100%)
  User edits → onAction edit_field → agent merges → re-renders verify surface.
  User clicks Confirm → onAction confirm_continue → agent:
    ⑤ finalize_rfp(thread_id)
        → emits surfaceId "rfp-final" with grouped Section/Card tree
        → marks deal.status = "confirmed" in deal_store
```

**Key invariant:** every render reads from `deal_store` — the tools never carry mutable deal state in args. This makes turn N a pure function of `deal_store[thread_id]`, which is the only way the multi-turn flow stays sane.

---

## 4. LangGraph Patterns

### 4.1 Phase 1 — single `create_agent` (ReAct loop)

Copy `fixed_agent.py` exactly. The system prompt has a 5-stage state machine ("if deal not yet seeded → call extract_seed_fields; if seeded but gaps remain → chase_gaps; if rubric satisfied → render_verification; if verification confirmed → finalize_rfp"). The ReAct loop + MemorySaver handles the rest. **Do not split into nodes yet.**

```python
def build_rfp_agent():
    return create_agent(
        model=_build_model(),
        tools=[extract_seed_fields, render_deal_context, chase_gaps,
               render_verification, finalize_rfp],
        middleware=[CopilotKitMiddleware()],
        system_prompt=RFP_SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )
```

**State schema:** the default `AgentState` (messages only) is sufficient. Don't subclass — the deal lives in `deal_store`, not in graph state. This is the single most important architectural decision: it keeps the Phase 2 graph split trivial because no state-schema migration is needed.

**thread_id source:** CopilotKit runtime passes a stable `thread_id` per session via `configurable={"thread_id": ...}`. Read it inside tools via `runtime.config["configurable"]["thread_id"]` (same access pattern `generate_a2ui` uses for `runtime.state`).

### 4.2 Phase 2 — specialist nodes (only if Phase 1 is solid)

Use `StateGraph` with conditional edges. The minimal split:

```
START → router → { elicitation | verification | assembly | END }
       (LLM picks)         │            │            │
                           └────────────┴────────────┴→ END
```

- **router node:** small LLM call that classifies "what does this turn need?" by reading the deal_store state — outputs `Literal["elicit", "verify", "assemble", "stop"]`.
- **elicitation node:** has `extract_seed_fields` + `chase_gaps` + `render_deal_context` tools only.
- **verification node:** has `render_verification` + `edit_field` tools only.
- **assembly node:** has `finalize_rfp` tool only.

Wire with `graph.add_conditional_edges("router", route_fn, {...})`. Each specialist is itself a `create_agent` sub-graph (LangGraph supports nested graphs as nodes). MemorySaver at the top level checkpoints across the whole thing.

**Why split:** smaller per-node toolsets = sharper prompts + fewer hallucinated tool calls. The router is the seam where a future A2A handoff could hook in (out of scope per PROJECT.md but the seam is free).

**Pitfall flag:** LangGraph 1.2.x `MemorySaver` requires `thread_id` in `configurable` on every `invoke`. CopilotKit handles this for top-level graphs; verify it propagates to nested sub-graphs (spike: build smallest possible nested graph, log `runtime.config` from a tool inside the nested one). Spike before committing Phase 2.

---

## 5. A2UI Catalog — New Components

### 5.1 `DealContextCard` (bespoke — required)

Compose a field-list with per-field status tags. Catalog primitives can almost do this (Stack + Row + Text + Badge) but the agent would have to assemble the tree every turn, costing tokens and rendering jitter. A bespoke component keeps the agent payload tiny.

**Prop schema (Zod, in `definitions.ts`):**

```typescript
DealContextCard: {
  description:
    "Deal snapshot card. Shows archetype + seed fields with per-field " +
    "provenance tags. Use as the persistent left-rail surface during intake.",
  props: z.object({
    archetype: z.string(),                       // "SaaS sales", "Pro services", …
    customer: z.string().optional(),
    title: z.string(),                           // e.g. "Acme — Q3 platform refresh"
    fields: z.array(z.object({
      key: z.string(),                           // "budget", "deadline", …
      label: z.string(),                         // human label
      value: z.string().optional(),              // empty when MISSING
      status: z.enum(["stated", "inferred", "missing"]),
      confidence: z.number().min(0).max(1).optional(),  // for INFERRED only
      whyMatters: z.string().optional(),         // for MISSING only
    })),
    readiness: z.number().min(0).max(100).optional(),
  }),
}
```

**Renderer (`renderers.tsx`):** Tailwind classes from existing `a2ui-surface` tokens. Status mapping:
- `stated` → green `Badge` "Stated"
- `inferred` → amber `Badge` "Inferred · NN%" (show confidence inline)
- `missing` → red `Badge` "Missing" + small italic `whyMatters` line beneath

**Agent payload (tiny):**
```python
a2ui.update_components(SURFACE, [
    {"id": "root", "component": "DealContextCard",
     "archetype": deal.archetype, "title": deal.title,
     "fields": [...], "readiness": deal.readiness}
])
```
Single-node tree. No nested Stack/Row gymnastics on the agent side.

### 5.2 `VerificationGroup` (bespoke — recommended)

Five of these stack on the verification surface. Each is an editable group: a `Section`-like header + a list of editable fields with inline tags + an "approve group" button.

**Why bespoke vs. Section+Card+TextInput composition:** the "edit + approve + re-tag from INFERRED→STATED on approve" interaction loop is too chatty for plain primitives. Bespoke renderer batches the state into one onAction call.

**Prop schema:**
```typescript
VerificationGroup: {
  description:
    "Editable verification group (Commercials / Scope / Tech / Stakeholders / Timeline). " +
    "Each field is editable inline; approving the group bulk-promotes INFERRED→STATED.",
  props: z.object({
    groupKey: z.enum(["commercials", "scope", "tech", "stakeholders", "timeline"]),
    title: z.string(),
    fields: z.array(z.object({
      key: z.string(),
      label: z.string(),
      value: z.string(),
      status: z.enum(["stated", "inferred", "missing"]),
      editable: z.boolean().default(true),
    })),
    approved: z.boolean().default(false),
  }),
}
```

### 5.3 `ReadinessMeter` (bespoke — light)

A simple horizontal bar with rubric segments. Could be a `Progress` primitive if the catalog has one — check `definitions.ts` first. If yes, skip this and use the primitive with a tooltip.

**Action contract (all three components):** all `onAction` events emit `{name: "edit_field"|"approve_group"|"confirm_continue", surfaceId, context: {groupKey?, fieldKey?, value?}}`. The `rfp_agent` handles `log_a2ui_event` results by inspecting `context.name` and routing to the right tool.

### 5.4 Catalog mirror — `agent/src/catalog.py`

Add three one-liners to `CATALOG_PROMPT`:
```
- DealContextCard: deal snapshot with per-field STATED/INFERRED/MISSING tags
- VerificationGroup: editable group of fields with bulk-approve
- ReadinessMeter: 0–100 progress meter driven by hard-blocker rubric
```

---

## 6. HITL Action Pattern (multi-step intake)

The existing pattern (`forwardedProps.a2uiAction` → `log_a2ui_event` tool result) is already the right primitive. **Do not invent a new transport.** The pattern for chaining:

**Convention for action names:**

| Action name | Emitted by | Context shape | Agent reaction |
|---|---|---|---|
| `edit_field` | TextInput on VerificationGroup | `{groupKey, fieldKey, value}` | call `extract_seed_fields` on the single value; re-render `rfp-verify` |
| `approve_group` | Button on VerificationGroup | `{groupKey}` | bulk-promote INFERRED→STATED in deal_store; re-render `rfp-verify` |
| `answer_question` | ChoiceChips on `rfp-deal` Open-questions card | `{fieldKey, value}` | merge into deal; re-render `rfp-deal` + `chase_gaps` |
| `confirm_continue` | Button on `rfp-verify` footer | `{}` | call `finalize_rfp`; emit `rfp-final` surface |

**Key rule:** every action is **idempotent** — the agent re-reads `deal_store` and re-emits the full surface. No partial-update protocol. This is verbose on the wire but eliminates entire bug classes (partial-update ordering, lost edits on reconnect).

**System-prompt guard:** "On every `log_a2ui_event` result, re-read the deal via internal tool calls; never assume the current message is the full deal state." Without this, Gemini will try to take shortcuts.

---

## 7. Route Group Isolation

The `(pdf)` group is the canonical pattern. Mirror it.

| Concern | pdf-analyst | RFP cockpit | Coupling? |
|---|---|---|---|
| Route group | `src/app/(pdf)/` | `src/app/(rfp)/` NEW | None (route groups are isolated by Next.js) |
| API route | `src/app/api/copilotkit-pdf/route.ts` | `src/app/api/copilotkit-rfp/route.ts` NEW | None (separate endpoints) |
| FastAPI endpoint | `:8123/fixed`, `:8123/dynamic` | `:8123/rfp` NEW | Same uvicorn process, separate graph |
| Providers | `src/components/pdf-analyst/Providers.tsx` | `src/components/rfp-cockpit/Providers.tsx` NEW | None (one CopilotKit runtime URL per Provider) |
| SurfaceCanvas | `channel="pdf-…"` | `channel="rfp"` | **Shared component, separate channel** — the `surfaceBus` is keyed by channel, so two surfaces can co-exist with zero coupling |
| Catalog | `src/a2ui/catalog/` | **Same** | **Intentional coupling** — adding components grows the shared catalog. This is fine; the agents pick what they use via prompts. Components the RFP agent doesn't reference simply aren't emitted. |
| Theme | `src/app/(pdf)/pdf-analyst.css` | `src/app/(rfp)/rfp-cockpit.css` NEW (Phase 3) | Shared `src/a2ui/theme.css` tokens; only the shell-brand CSS forks |
| Brand shell | `src/components/pdf-analyst/Brand.tsx` | `src/components/rfp-cockpit/Brand.tsx` NEW (Phase 3) | None |

**Rule:** never `import` from `(pdf)` into `(rfp)` or vice versa. Both depend only on `src/a2ui/*` and `src/components/<group>/*`. SurfaceCanvas, A2UIProvider, surfaceBus are all in `src/a2ui` or `src/components/pdf-analyst/SurfaceCanvas.tsx` — **move SurfaceCanvas to `src/components/shared/SurfaceCanvas.tsx`** as a small first-task refactor (Phase 1, step 1) so neither group imports across boundaries. Zero behavioral change, just a path move + two updated imports.

---

## 8. Build Order (concrete, 3 phases)

### Phase 1 — Foundation (the critical path)

**Goal:** paste a dump → see a `DealContextCard` render in the canvas. Everything else is decoration.

| # | Files | Action | Why |
|---|---|---|---|
| 1 | `src/components/pdf-analyst/SurfaceCanvas.tsx` → `src/components/shared/SurfaceCanvas.tsx` | MOVE | Avoid `(rfp)` importing from `(pdf)` |
| 2 | `src/components/pdf-analyst/Providers.tsx` | MODIFY (2-line import) | Trail of move |
| 3 | `src/a2ui/catalog/definitions.ts` | MODIFY (add DealContextCard) | Catalog must exist before renderer |
| 4 | `src/a2ui/catalog/renderers.tsx` | MODIFY (add DealContextCard renderer) | Pair with definition |
| 5 | `agent/src/catalog.py` | MODIFY (add DealContextCard line to CATALOG_PROMPT) | Agent needs to know it exists |
| 6 | `agent/src/deal_store.py` | NEW | Side-store for deal state |
| 7 | `agent/src/rubric.py` | NEW | PROVISIONAL blocker list |
| 8 | `agent/src/rfp_agent.py` | NEW (copy fixed_agent.py shape) | Single ReAct loop, 5 tools |
| 9 | `agent/main.py` | MODIFY (mount `/rfp`) | Wire endpoint |
| 10 | `src/app/api/copilotkit-rfp/route.ts` | NEW (clone of copilotkit-pdf) | Frontend → FastAPI bridge |
| 11 | `src/components/rfp-cockpit/Providers.tsx` | NEW | CopilotKit provider for RFP |
| 12 | `src/app/(rfp)/rfp-intake/page.tsx` | NEW | Split layout (chat + canvas) |
| 13 | `src/app/(rfp)/layout.tsx` | NEW | Route group root |
| 14 | `pnpm validate-widget` + `pnpm smoke` | RUN | Green-gate |

**Phase 1 demo loop:** paste any dump → `extract_seed_fields` → `render_deal_context` → see card. Done. Don't gold-plate this.

### Phase 2 — Elicitation + Verification

| # | Files | Action |
|---|---|---|
| 1 | `agent/src/rfp_agent.py` | MODIFY (add `chase_gaps` + `render_verification` tools; expand system prompt with state-machine logic) |
| 2 | `src/a2ui/catalog/definitions.ts` + `renderers.tsx` | MODIFY (add `VerificationGroup` + `ReadinessMeter`) |
| 3 | `agent/src/catalog.py` | MODIFY (mirror new prompts) |
| 4 | Optional: split into `StateGraph` with 3 specialist nodes | NEW (`agent/src/rfp_graph.py`) — only if Phase 1 is rock-solid per PROJECT.md "Out of Scope" |

**Phase 2 demo loop:** dump → card → agent asks 2-3 batched gaps with "why this matters" → user answers → readiness climbs → verification cockpit appears → user edits + approves groups → Confirm gate enables.

### Phase 3 — Final RFP + Polish

| # | Files | Action |
|---|---|---|
| 1 | `agent/src/rfp_agent.py` | MODIFY (`finalize_rfp` tool — composes Section/Card/BulletList tree from confirmed deal) |
| 2 | `src/a2ui/theme.css` | MODIFY (sales-appropriate accent tokens) |
| 3 | `src/app/(rfp)/rfp-cockpit.css` + `src/components/rfp-cockpit/Brand.tsx` | NEW |
| 4 | Hero demo cases (2-3 synthetic dumps) | NEW (`.planning/demo-cases/*.md`) |
| 5 | Replace PROVISIONAL rubric in `rubric.py` | MODIFY (when teammate delivers) |

---

## 9. Patterns to Follow (anti-pattern table)

| Pattern | Why | Anti-pattern |
|---|---|---|
| Deal state lives in `deal_store`, NOT graph state | Lets you swap to Redis; no schema migration when deal shape evolves | Subclassing `AgentState` with `deal: Deal` field → every shape change is a migration |
| Every tool reads deal from `deal_store[thread_id]` | Stateless tools; idempotent re-render | Tools that take the full deal as an arg → token bloat + drift |
| Single bespoke component per surface zone | Agent payload tiny; renderer owns layout | Agent assembling Stack→Row→Card→Badge trees by hand → token cost + jitter |
| All actions idempotent — agent re-emits the full surface | Eliminates partial-update bug classes | Trying to emit "patch" operations on `updateComponents` |
| `forwardedProps.a2uiAction` is the ONLY action transport | Already proven in fixed_agent | Inventing a new `/api/rfp-action` endpoint |
| PROVISIONAL rubric is a module-level list | One file to swap | Inlining the rubric in the system prompt → can't share with readiness meter |
| Phase 1 = single `create_agent`. Phase 2 = `StateGraph` only if needed | "Lock first" per AGENTS.md | Starting with a 5-node graph to "be clean" → demo doesn't compile by hour 4 |

---

## 10. Scalability (not a Phase 1 concern — noted for completeness)

| Concern | Local demo (N=1 session) | Future (Redis-backed) |
|---|---|---|
| Deal persistence | `dict[thread_id, Deal]` in `deal_store.py` | Swap implementation behind `DealStore` Protocol → `RedisDealStore` |
| MemorySaver | Fine | Swap to `RedisSaver` from `langgraph.checkpoint.redis` (NOT in scope per FROZEN.md, but compatible) |
| Multi-tenant | N/A | `thread_id` already namespaces everything; add a `user_id` prefix |

---

## 11. Open Risks / Spike Candidates

1. **LangGraph nested-graph `thread_id` propagation** — verify before Phase 2 split. 30 min spike.
2. **Gemini tool-arg parser on the new tools** — `extract_seed_fields` returns a `dict[str, list[FieldDict]]`. Use the same `TypedDict` discipline as `fixed_agent.py`'s `Kpi`/`Point`/`Row` (see the "Gemini typed-array fix" comment at line 37 of `fixed_agent.py`). **Do not use `list[dict]`** anywhere.
3. **`createSurface` dedupe across surface IDs** — Phase 2 introduces `rfp-verify` as a *second* surface. SurfaceCanvas already handles dedupe per-surfaceId, but verify the multi-surface case (two simultaneous surfaces in the same channel) works — may need to widen the canvas to show both, or close `rfp-deal` when `rfp-verify` opens. Decision needed before Phase 2.
4. **Forced `tool_choice` across multi-turn replay** — only used in `dynamic_agent.py` for the secondary LLM. Phase 1's `rfp_agent` doesn't need it (the primary LLM picks from 5 tools). If Phase 2 introduces a sub-graph that wants to force a single tool, replicate the `_LazyRenderModel` pattern.

---

## 12. Sources

- HIGH: `agent/src/fixed_agent.py` (canonical fixed-schema pattern; the typed-array fix at L37-42 is critical)
- HIGH: `agent/src/dynamic_agent.py` (HITL action transport via `log_a2ui_event`; secondary-LLM pattern)
- HIGH: `src/components/pdf-analyst/SurfaceCanvas.tsx` (action onAction → forwardedProps; createSurface dedupe at L88-106)
- HIGH: `src/a2ui/catalog/definitions.ts` (Zod schema pattern for new components)
- HIGH: `.planning/PROJECT.md` (phase boundaries, guardrails, "lock first" principle)
- HIGH: `CLAUDE.md` (frozen versions, customization seams, anti-patterns)
- MEDIUM (training data): LangGraph 1.2.x `StateGraph` + conditional edges + nested-graph patterns; `MemorySaver` thread_id keying. Recommend Context7 lookup `langchain-ai/langgraph` topic "StateGraph conditional edges nested graphs" before starting Phase 2.
