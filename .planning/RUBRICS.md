# Hard-Blocker Rubrics — RFP Intake Cockpit

> Source: Technical sales expert interview, June 13 2026.  
> Status: PROVISIONAL — awaiting final sign-off from teammate.  
> These replace the generic MEDDPICC placeholder in `agent/src/rfp_hard_blockers.py`.

---

## Archetype Triage

The agent MUST infer archetype as its first step. Archetype determines which rubric loads.

| Signal in dump | Inferred archetype |
|---|---|
| "tracking", "RTLS", "location", "tags", "zones", "warehouse", "asset tracking" | RTLS |
| "MES", "manufacturing execution", "production", "OEE", "traceability", "PLC", "shop floor" | MES |
| Ambiguous / both signals | Ask one clarifying question before loading rubric |

---

## Universal Hard Blockers (both archetypes)

These are chased first, regardless of archetype.

| # | Field | Why it matters | Low answer (red flag) | High answer (what good looks like) | Red flag phrases |
|---|---|---|---|---|---|
| U1 | Business Objective | No measurable goal = no way to define winning | "We want a system" / vague efficiency claim | Quantified KPIs with targets (e.g. OEE +8%, scrap -12%) | "We'll define KPIs later" |
| U2 | Success Criteria | Undefined success causes disputes at UAT | "We'll know it when we see it" | Quantified UAT and acceptance metrics agreed upfront | "We'll know when we see it" / "General satisfaction" |
| U3 | Decision Makers / Scope Ownership | Unknown buyers = proposal disappears | Departments named but no individuals | Executive sponsor + technical owner + commercial decision chain named | "Everyone will decide together" / "The team will decide" |
| U4 | Security & IT Constraints | Discovering IT blockers late kills deals | Never discussed | IT/security policies, on-prem/cloud limits, approval process defined | "Security review later" / "IT will handle it" |

---

## RTLS Hard Blockers (load when archetype = RTLS)

Chase after universal blockers, in this order.

| # | Field | Why it matters | Low answer (red flag) | High answer (what good looks like) | Red flag phrases |
|---|---|---|---|---|---|
| R1 | Customer Problem Definition | No problem = no proposal. Everything is speculation. | "We want a tracking system" | Clear business problem with operational impact stated | "We want RTLS" (solution, not problem) |
| R2 | Site Information | Cannot scope RTLS without physical environment | No machine/site details | Detailed machine list, PLC types, production areas, site details | "We have a few buildings" |
| R3 | Network Infrastructure | RTLS lives on the wireless backbone. Unknown = unbiddable. | "There is Wi-Fi" | Roaming, latency, VLAN, firewall, coverage, security requirements defined | "IT will check later" / "We have good Wi-Fi" |
| R4 | RTLS Requirements | Accuracy, refresh rate, tag density define the hardware spec. Vague = wrong solution. | "We want tracking" | Accuracy, refresh rate, tag density, zone structure defined | "We need real-time tracking" (no spec) |
| R5 | ERP & System Integration | Integration is typically 40% of the work. Discovering late = rework. | "There is an ERP system" | ERP version, API method, data flow, responsible teams defined | "ERP team not involved yet" |

**RTLS Round 2 (Important — chase after Round 1 clear):**
Wireless Restrictions, Deployment Preference, Downtime Constraints, Compliance Requirements, PoC Expectations, Procurement Process

---

## MES Hard Blockers (load when archetype = MES)

Chase after universal blockers, in this order.

| # | Field | Why it matters | Low answer (red flag) | High answer (what good looks like) | Red flag phrases |
|---|---|---|---|---|---|
| M1 | Production Process Definition | MES scope depends entirely on process flow. Can't spec without it. | No process definition | Full production flow with stations, routing, approvals documented | "Every line works differently" |
| M2 | Machine Connectivity Readiness | Technical feasibility gate. Unknown PLC access = unbiddable. | No machine info / "We have machines" | PLC brands, protocols, connectivity feasibility validated | "We'll check machine access later" |
| M3 | ERP Integration Scope | Biggest source of rework in MES deals. Discovering late = budget overrun. | "We have SAP" | Data ownership, APIs, transactions mapped, ERP team involved | "ERP team not involved yet" |
| M4 | OT Network Infrastructure | MES/RTLS projects fail here frequently. | Unknown network | VLAN, firewall, latency, segmentation validated | "IT will handle it later" |
| M5 | Traceability Requirement | Defines architecture complexity. Serialization = different system than batch. | "Need tracking" | Full genealogy + serialization model defined | "Maybe later phases" |
| M6 | Timeline Realism | Unrealistic timelines destroy delivery and damage the relationship. | "ASAP" / "Go live in 4 weeks" | Pilot, go-live, rollout milestones defined with realistic buffer | "Go live in 4 weeks" / "ASAP" |
| M7 | PoC Expectations | Undefined PoC creates political risk. Success criteria must be agreed before PoC starts. | No PoC definition | Measurable PoC success criteria defined upfront | "Just show something impressive" |

**MES Round 2 (Important — chase after Round 1 clear):**
Data Accessibility, Wireless Restrictions, Reporting Expectations, User Roles & Authorization, Downtime Management Logic, MES Deployment Model, Change Management Readiness, Compliance Requirements, Rollout Strategy, Vendor Dependency Mapping, Production Scheduling Integration

---

## Readiness Scoring

Readiness indicator climbs as hard blockers are filled and confirmed.

| State | Score | Indicator |
|---|---|---|
| Universal blockers only filled | 40% | Red |
| Universal + 3 archetype blockers | 65% | Amber |
| All hard blockers filled (STATED or confirmed INFERRED) | 85% | Amber-green |
| All hard blockers confirmed by customer | 95% | Green |
| Verify gate passed (Confirm & Continue clicked) | 100% | Green — RFP unlocked |

---

## PROVISIONAL flag

Every reference to this rubric in code must carry:
```python
# PROVISIONAL: real rubric from technical sales expert — swap when final sign-off received
PROVISIONAL = True
```

Swap seam: edit `agent/src/rfp_hard_blockers.py` list + flip `PROVISIONAL = False`. Zero logic changes elsewhere.
