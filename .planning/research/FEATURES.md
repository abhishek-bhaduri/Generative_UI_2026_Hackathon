# Features Research — RFP Intake Cockpit

**Domain:** Agent-driven RFP intake for technical B2B sales
**Researched:** 2026-06-13
**Confidence:** MEDIUM (synthesized from MEDDIC/MEDDPICC, BANT, SPICED, APMP/Loopio RFP-industry guidance, Gong/Clari signal taxonomies — validate hard-blocker rubric with technical-sales teammate before locking)

---

## Five-Group Taxonomy — VALIDATED

The five proposed groups map cleanly onto standard RFP anatomy and MEDDPICC.

### Group 1: Commercials
| Field | Always / Situational | Notes |
|-------|----------------------|-------|
| Budget range / band | Always | Refusal to share is itself a signal |
| Pricing model preference | Always | Drives proposal shape |
| Payment terms / billing cadence | Situational (enterprise = always) | NET-30/60/90, annual prepay |
| Currency & entity to contract with | Always for multinationals | Forgotten until late — blocks legal |
| Procurement vehicle | Situational | AWS/Azure marketplace credits reshape deals |
| Existing vendor spend to displace | Situational | High signal for ROI framing |

### Group 2: Scope & Success Criteria (highest-leverage elicitation target)
| Field | Always / Situational | Notes |
|-------|----------------------|-------|
| Problem statement / pain | Always | If missing, downstream is guesswork |
| In-scope use cases | Always | |
| Out-of-scope explicitly | Always (frequently omitted) | #1 source of scope creep |
| Success criteria / outcome metric | Always | Customers describe activities not outcomes — agent should chase the reframe |
| Volume / scale metrics | Always for technical deals | |
| Required integrations (named systems) | Always for technical deals | |
| Adjacent systems NOT to touch | Situational | Avoids political landmines |

### Group 3: Technical Constraints (strongest archetype-specific sub-fields)
| Field | Always / Situational | Notes |
|-------|----------------------|-------|
| Deployment model (SaaS / private cloud / on-prem / air-gapped / hybrid) | Always | Single biggest "no-go" filter |
| Data residency / sovereignty | Situational (EU, regulated = always) | GDPR, Schrems-II |
| Compliance & certification (SOC2, ISO 27001, HIPAA, PCI-DSS, FedRAMP) | Situational by industry | Hard filter |
| Identity / SSO / IdP | Always for enterprise | |
| Network constraints | Situational | Often surfaces only during security review |
| Encryption / KMS (BYOK, HYOK) | Situational (regulated) | |
| Existing tech stack to coexist with | Always | |
| Performance / SLO targets | Situational | |

### Group 4: Stakeholders & Process
| Field | Always / Situational | Notes |
|-------|----------------------|-------|
| Economic Buyer (signer) | Always — MEDDIC's central field | Single highest predictor of deal close |
| Champion | Always | If unknown, flag "no identified champion" |
| Decision process (committee, single signer, board) | Always | |
| Evaluation criteria / scoring rubric | Often absent in informal RFPs | High value to surface |
| Other vendors in eval | Situational | Customer often won't say — worth asking |
| Procurement / Legal / Security team involvement | Always for enterprise | These three gates kill more deals than product fit |

### Group 5: Timeline
| Field | Always / Situational | Notes |
|-------|----------------------|-------|
| Compelling event / why now | Always | Most-missing field. Chase: "what happens on date X if you don't have this?" |
| Target go-live / value-realization date | Always | |
| Decision date | Always | Often confused with go-live |
| Procurement / legal / security lead times | Always for enterprise | The 6-week security review nobody plans for |
| Pilot / POC window | Situational | |
| Budget cycle / fiscal year end | Situational | High signal — forcing function |

**Recommendation:** Do NOT add a sixth group. Absorb risks into Stakeholders (political) and Technical Constraints (technical). A sixth group breaks the five-block visual gestalt.

---

## Eight "Customer Almost Never Provides" Fields (prime elicitation targets)

1. Compelling event with a real date
2. Out-of-scope explicitly
3. Economic buyer (not just primary contact)
4. Success criteria as outcomes, not activities
5. Other vendors in evaluation
6. Procurement / security lead times
7. Data residency / sovereignty
8. Deployment model constraints

---

## Where Deals Stall — Top 10 Deal-Killer Gaps

1. **No identified Economic Buyer** — champion has no signing power; dies at "let me run this by my boss"
2. **No compelling event** — "interesting, let's revisit next quarter" — forever
3. **Security review surfaced late** — 6-week review starts week before quarter-end; deal slips
4. **Procurement vehicle mismatch** — customer can only buy via AWS marketplace; vendor isn't listed
5. **Data residency surfaced in legal review** — vendor has no EU region; deal pivots to competitor
6. **Integration to unsupported system** — discovered in POC week 3
7. **Success criteria never agreed** — POC ends; "we don't see the value"; nobody can adjudicate
8. **Out-of-scope never defined** — scope creep eats margin; CSM inherits unhappy customer
9. **Champion leaves / reorgs out** — no second relationship; deal restarts
10. **Budget approval cycle missed** — fiscal year ends; "let's revisit next FY"

**Demo implication:** agent's "why this matters" for each chase should reference exactly these patterns.

---

## Deal Archetype Taxonomy (8 types, ~85% coverage)

| Archetype | Trigger pattern | Archetype-specific fields |
|-----------|-----------------|---------------------------|
| **Infra Migration** | "We're moving from X to Y" | Source env inventory; cutover window; rollback plan; data egress costs; parallel-run period |
| **Security Tooling** | "We need to detect / prevent / comply" | Threat model; existing security stack; SOC team size; IR RACI; log retention; MITRE ATT&CK coverage |
| **Data Platform** | "We can't get a single source of truth" | Source systems & volumes; query patterns; semantic layer; data governance; consumer personas |
| **Managed Service** | "We don't want to run this ourselves" | What stays in-house vs hand-off; SLA tier; escalation path; exit / repatriation clause |
| **Developer Tooling** | "Engineers are slow / on-call burning out" | Developer count; tooling to displace; rollout model; license shape; IDE / language coverage |
| **SaaS Consolidation** | "Procurement is forcing consolidation" | Incumbents & renewal dates; historical-data migration; retraining budget; sunset timeline |
| **Compliance Tooling** | "Auditor said we need this by X" | Frameworks in scope (SOC2 / ISO / HIPAA / PCI / FedRAMP / DORA / NIS2); auditor identity; control owners |
| **AI / ML Platform** | "We need AI for X" | Use case maturity; data sensitivity; model choice; GPU / inference budget; eval & guardrails |

**Phase 1 recommendation:** Infra Migration + Security Tooling + Data Platform (broadest coverage, most demo-able).

### Archetype Inference Heuristics
- "migrate / lift-and-shift" → Infra Migration
- "detect / SIEM / SOC / MITRE" → Security Tooling
- "warehouse / pipeline / dashboard / data mesh" → Data Platform
- "GPU / inference / fine-tune / RAG / foundation model" → AI/ML Platform
- "auditor / SOC2 / ISO / compliance deadline" → Compliance Tooling
- "fully managed / don't want to manage" → Managed Service
- stated incumbent + replacement intent → SaaS Consolidation

---

## Success Criteria: Good vs Bad

A success criterion is a **falsifiable outcome statement**: measurable, attributable, tied to a baseline.

| Bad (activity-based) | Good (outcome-based) |
|----------------------|----------------------|
| "Deploy the SIEM" | "Reduce MTTD from 14h to 2h within 90 days of go-live" |
| "Migrate workloads to cloud" | "Decommission $1.2M/year of on-prem by FY-end; ≥99.9% availability through cutover" |
| "Improve developer experience" | "Reduce median PR merge time from 3.2d to 1d within Q2" |
| "Better data" | "Finance closes the books in 3d (today: 7); CFO signs off" |
| "Be secure" | "Pass SOC 2 Type II on date X with zero high-severity findings" |

**Elicitation reframe:** "If you deploy [activity] and nothing changes about [metric], have you succeeded? If not — what metric, by how much, by when?"

**Bad-pattern detectors:**
- Verb is "deploy / migrate / implement" → activity-based, chase outcome
- No date → chase "by when"
- No baseline → chase "from what"
- No owner / signoff authority → chase "who decides this is achieved?"

---

## Table Stakes Features

| Feature | Complexity | Notes |
|---------|------------|-------|
| Free-form requirements dump entry | Low | Chat panel already in starter |
| Extract structured fields from unstructured text | Med | Mirror `pdf_tools.py` pattern |
| Field status tagging (STATED / INFERRED / MISSING) | Low | Core to trust proposition |
| Grouped output by topic (five blocks) | Low | Already specified |
| Editable fields before finalization | Med | A2UI `updateComponents` ops |
| Completeness indicator | Low | Driven by hard-blocker rubric |
| Final artifact preview | Med | Phase 3 grouped sections |
| "Why this matters" rationale per elicited field | Low | One-line per field |
| Verification gate before finalization | Low | Already in Phase 2 |

---

## Differentiators

| Feature | Demo value | Complexity |
|---------|------------|------------|
| Archetype inference with visible badge | HIGH | Med |
| Archetype-specific fields appearing contextually | HIGH | Med |
| Gap elicitation with deal-killer rationale | HIGH | Low |
| Activity-to-outcome reframing for success criteria | HIGH | Med |
| Compelling-event chase ("what happens if you don't have this by X?") | HIGH | Low |
| STATED / INFERRED / MISSING ledger | HIGH | Low |
| Readiness indicator climbing as gaps close | MED | Low |
| Confirm-and-continue gate (customer owns artifact) | MED | Low |

### The 60-Second Demo "Whoa"
1. Judge pastes: *"We need to replace our SIEM by end of Q3 because of our auditor."*
2. Cockpit infers **archetype: Security Tooling**; badge appears.
3. Five grouped blocks render with ~40% MISSING fields tagged.
4. Agent batches three chases with "why this matters": EB (typically CISO for SIEM), success metric (MTTD? Coverage? Cost?), audit scope (SOC2? ISO? PCI? Date?).
5. Customer confirms; readiness climbs 40% → 95%; final RFP renders.

Impossible in a chat box; showcases the generative UI.

---

## Anti-Features (explicitly DO NOT build)

| Anti-feature | Why avoid |
|--------------|-----------|
| Pricing logic / quote generation | Vendor commitment; legal exposure |
| Proposal / response writing | Buyer's intake only; not vendor response |
| Feasibility judgement ("can't get SOC2 in 60d") | Wrong harms trust; not our data |
| Vendor recommendations / shortlists | Adjacent product; bias risk |
| Fabricating fields the customer didn't state | Violates Guardrail #1 |
| Silent finalization without verification | Violates Guardrail #4 |
| Wall-of-text output | Destroys gen-UI demo value |
| Auto-sending to vendors / external systems | Out of scope; legal/op risk |
| CRM integration / push to Salesforce | Out of scope; demo only |
| Real-time multi-user collab | Out of scope; single-session demo |
| Auth / accounts | Out of scope per PROJECT.md |
| Live audio / voice | Out of scope |
| Real customer / PII data | Out of scope; synthetic only |
| A2A interop | Track 1 only; not Track 2 |
| Won/lost/risky classification | Gong/Clari territory; out of scope |

---

## PROVISIONAL Hard-Blocker Rubric (pending teammate validation)

Recommended anchor: **MEDDPICC (8) + 3 universal technical fields = 11 fields**

1. Metrics / success criteria (outcome-based)
2. Economic Buyer named
3. Decision criteria shared
4. Decision process documented
5. Identify pain (problem statement)
6. Champion named
7. Paper process / procurement path
8. Competition / other vendors named
9. Deployment model defined
10. Integration surface documented
11. Compliance constraints documented

Mark PROVISIONAL until teammate confirms. Use `PROVISIONAL = True` flag in `agent/src/rfp_hard_blockers.py`.

---

## Open Questions for Teammate Validation

1. Final hard-blocker rubric — MEDDPICC + 3 technical fields, or different scaffold?
2. Which 3 archetypes for Phase 1 — Infra / Security / Data, or different priority?
3. Should "compelling event" be its own field or absorbed into Timeline?
4. Should archetype inference be visible & overridable, or silent? (Recommend: visible + one-click override)
