"""RFP hard-blocker rubric — RTLS and MES archetypes.

# PROVISIONAL: real rubric from technical sales expert — swap when final sign-off received
PROVISIONAL = True

Swap seam: edit lists below + flip PROVISIONAL = False. Zero logic changes elsewhere.
"""

# PROVISIONAL: real rubric from technical sales expert — swap when final sign-off received
PROVISIONAL = True

# ─── Archetype triage signals ─────────────────────────────────────────────────

RTLS_SIGNALS = [
    "rtls", "tracking", "location", "tags", "zones", "warehouse",
    "asset tracking", "real-time location", "uwb", "ble beacon",
]

MES_SIGNALS = [
    "mes", "manufacturing execution", "production", "oee",
    "traceability", "plc", "shop floor", "scada", "line efficiency",
    "work order", "quality management",
]

VALID_ARCHETYPES = {"RTLS", "MES", "UNKNOWN"}


# ─── Universal hard blockers (both archetypes, chased first) ─────────────────

UNIVERSAL_BLOCKERS = [
    {
        "id": "U1",
        "name": "business_objective",
        "label": "Business Objective",
        "why_it_matters": "No measurable goal = no way to define winning. Vague objectives cause scope creep and disputed success.",
        "low_answer": "We want a system / vague efficiency claim",
        "high_answer": "Quantified KPIs with targets (e.g. OEE +8%, scrap -12%)",
        "red_flag_phrases": ["we'll define kpis later", "we want to improve", "general improvement"],
        "priority": 1,
    },
    {
        "id": "U2",
        "name": "success_criteria",
        "label": "Success Criteria",
        "why_it_matters": "Undefined success causes disputes at UAT. 'We'll know it when we see it' always ends in a failed project politically.",
        "low_answer": "We'll know it when we see it",
        "high_answer": "Quantified UAT and acceptance metrics agreed upfront",
        "red_flag_phrases": ["we'll know when we see it", "general satisfaction", "feels right"],
        "priority": 2,
    },
    {
        "id": "U3",
        "name": "decision_makers",
        "label": "Decision Makers / Scope Ownership",
        "why_it_matters": "Unknown buyers = proposal disappears. Without named individuals, there is no one to champion the deal internally.",
        "low_answer": "Departments named but no individuals",
        "high_answer": "Executive sponsor + technical owner + commercial decision chain named",
        "red_flag_phrases": ["everyone will decide together", "the team will decide", "committee"],
        "priority": 3,
    },
    {
        "id": "U4",
        "name": "security_it_constraints",
        "label": "Security & IT Constraints",
        "why_it_matters": "Discovering IT blockers late kills deals. A security review surfacing in week 10 adds 6 weeks minimum.",
        "low_answer": "Never discussed",
        "high_answer": "IT/security policies, on-prem/cloud limits, approval process defined",
        "red_flag_phrases": ["security review later", "it will handle it", "it will sort it"],
        "priority": 4,
    },
]

# ─── RTLS hard blockers ───────────────────────────────────────────────────────

RTLS_BLOCKERS = [
    {
        "id": "R1",
        "name": "customer_problem_definition",
        "label": "Customer Problem Definition",
        "why_it_matters": "No problem = no proposal. 'We want RTLS' is a solution, not a problem. Everything is speculation without a stated business problem.",
        "low_answer": "We want a tracking system",
        "high_answer": "Clear business problem with operational impact stated",
        "red_flag_phrases": ["we want rtls", "we need tracking", "we need a system"],
        "priority": 5,
    },
    {
        "id": "R2",
        "name": "site_information",
        "label": "Site Information",
        "why_it_matters": "Cannot scope RTLS without the physical environment. Machine list, building layout, and production areas define hardware and anchor placement.",
        "low_answer": "No machine/site details",
        "high_answer": "Detailed machine list, PLC types, production areas, site details",
        "red_flag_phrases": ["we have a few buildings", "standard warehouse", "normal facility"],
        "priority": 6,
    },
    {
        "id": "R3",
        "name": "network_infrastructure",
        "label": "Network Infrastructure",
        "why_it_matters": "RTLS lives on the wireless backbone. Unknown network = unbiddable. Roaming, latency, VLANs, and firewall rules all affect the solution.",
        "low_answer": "There is Wi-Fi",
        "high_answer": "Roaming, latency, VLAN, firewall, coverage, security requirements defined",
        "red_flag_phrases": ["it will check later", "we have good wi-fi", "standard network"],
        "priority": 7,
    },
    {
        "id": "R4",
        "name": "rtls_requirements",
        "label": "RTLS Requirements",
        "why_it_matters": "Accuracy, refresh rate, and tag density define the hardware spec. Vague requirements mean the wrong technology gets selected.",
        "low_answer": "We want tracking",
        "high_answer": "Accuracy, refresh rate, tag density, zone structure defined",
        "red_flag_phrases": ["we need real-time tracking", "accurate tracking", "good accuracy"],
        "priority": 8,
    },
    {
        "id": "R5",
        "name": "erp_system_integration",
        "label": "ERP & System Integration",
        "why_it_matters": "Integration is typically 40% of RTLS work. Discovering requirements late means rework, budget overrun, and delay.",
        "low_answer": "There is an ERP system",
        "high_answer": "ERP version, API method, data flow, responsible teams defined",
        "red_flag_phrases": ["erp team not involved yet", "we'll integrate later", "standard erp"],
        "priority": 9,
    },
]

# ─── MES hard blockers ────────────────────────────────────────────────────────

MES_BLOCKERS = [
    {
        "id": "M1",
        "name": "production_process_definition",
        "label": "Production Process Definition",
        "why_it_matters": "MES scope depends entirely on process flow. Cannot spec without a full production flow — 'every line works differently' is a red flag.",
        "low_answer": "No process definition",
        "high_answer": "Full production flow with stations, routing, approvals documented",
        "red_flag_phrases": ["every line works differently", "standard process", "normal manufacturing"],
        "priority": 5,
    },
    {
        "id": "M2",
        "name": "machine_connectivity_readiness",
        "label": "Machine Connectivity Readiness",
        "why_it_matters": "Technical feasibility gate. Unknown PLC access = unbiddable. Machine age, brand, and protocol determine whether connectivity is possible.",
        "low_answer": "No machine info / We have machines",
        "high_answer": "PLC brands, protocols, connectivity feasibility validated",
        "red_flag_phrases": ["we'll check machine access later", "standard machines", "modern equipment"],
        "priority": 6,
    },
    {
        "id": "M3",
        "name": "erp_integration_scope",
        "label": "ERP Integration Scope",
        "why_it_matters": "Biggest source of rework in MES deals. Data ownership, transaction mapping, and ERP team involvement must be established before scoping.",
        "low_answer": "We have SAP",
        "high_answer": "Data ownership, APIs, transactions mapped, ERP team involved",
        "red_flag_phrases": ["erp team not involved yet", "we'll figure out erp later", "standard sap"],
        "priority": 7,
    },
    {
        "id": "M4",
        "name": "ot_network_infrastructure",
        "label": "OT Network Infrastructure",
        "why_it_matters": "MES projects fail on OT network frequently. VLAN segmentation, firewall rules between OT and IT, and latency requirements must be validated.",
        "low_answer": "Unknown network",
        "high_answer": "VLAN, firewall, latency, segmentation validated",
        "red_flag_phrases": ["it will handle it later", "standard network", "good network"],
        "priority": 8,
    },
    {
        "id": "M5",
        "name": "traceability_requirement",
        "label": "Traceability Requirement",
        "why_it_matters": "Defines architecture complexity. Serialization is a fundamentally different system from batch genealogy. Getting this wrong means rebuilding the core.",
        "low_answer": "Need tracking",
        "high_answer": "Full genealogy + serialization model defined",
        "red_flag_phrases": ["maybe later phases", "basic traceability", "standard tracking"],
        "priority": 9,
    },
    {
        "id": "M6",
        "name": "timeline_realism",
        "label": "Timeline Realism",
        "why_it_matters": "'ASAP' or '4 weeks' on a MES project is a warning sign. Unrealistic timelines destroy delivery and damage the relationship before go-live.",
        "low_answer": "ASAP / Go live in 4 weeks",
        "high_answer": "Pilot, go-live, rollout milestones defined with realistic buffer",
        "red_flag_phrases": ["go live in 4 weeks", "asap", "as soon as possible", "immediately"],
        "priority": 10,
    },
    {
        "id": "M7",
        "name": "poc_expectations",
        "label": "PoC Expectations",
        "why_it_matters": "Undefined PoC creates political risk. Without agreed success criteria before the PoC starts, vendors lose even when the technology works.",
        "low_answer": "No PoC definition",
        "high_answer": "Measurable PoC success criteria defined upfront",
        "red_flag_phrases": ["just show something impressive", "show us what you can do", "surprise us"],
        "priority": 11,
    },
]

# ─── Readiness scoring thresholds ─────────────────────────────────────────────

READINESS_THRESHOLDS = {
    "universal_only": 0.40,
    "archetype_partial": 0.65,
    "all_filled": 0.85,
    "all_confirmed": 0.95,
    "gate_passed": 1.00,
}

# ─── Lookup helpers ───────────────────────────────────────────────────────────

UNIVERSAL_BLOCKER_NAMES = {b["name"] for b in UNIVERSAL_BLOCKERS}
RTLS_BLOCKER_NAMES = {b["name"] for b in RTLS_BLOCKERS}
MES_BLOCKER_NAMES = {b["name"] for b in MES_BLOCKERS}

ALL_BLOCKERS_BY_NAME: dict = {
    b["name"]: b
    for b in UNIVERSAL_BLOCKERS + RTLS_BLOCKERS + MES_BLOCKERS
}


def get_blockers_for_archetype(archetype: str) -> list[dict]:
    if archetype == "RTLS":
        return UNIVERSAL_BLOCKERS + RTLS_BLOCKERS
    if archetype == "MES":
        return UNIVERSAL_BLOCKERS + MES_BLOCKERS
    return UNIVERSAL_BLOCKERS


def compute_readiness(deal_fields: dict, archetype: str) -> float:
    blockers = get_blockers_for_archetype(archetype)
    if not blockers:
        return 0.0

    universal_names = {b["name"] for b in UNIVERSAL_BLOCKERS}
    archetype_names = {b["name"] for b in blockers} - universal_names

    def is_filled(name: str) -> bool:
        f = deal_fields.get(name, {})
        return bool(f.get("value")) and f.get("status") in ("STATED", "INFERRED", "CONFIRMED")

    def is_confirmed(name: str) -> bool:
        f = deal_fields.get(name, {})
        return bool(f.get("value")) and f.get("status") == "CONFIRMED"

    universal_filled = all(is_filled(n) for n in universal_names)
    if not universal_filled:
        done = sum(1 for n in universal_names if is_filled(n))
        return round(done / max(len(universal_names), 1) * 0.40, 3)

    archetype_filled_count = sum(1 for n in archetype_names if is_filled(n))
    if archetype_filled_count < 3:
        return round(0.40 + (archetype_filled_count / 3) * 0.25, 3)

    all_names = universal_names | archetype_names
    all_filled = all(is_filled(n) for n in all_names)
    if not all_filled:
        done = sum(1 for n in all_names if is_filled(n))
        return round(0.65 + (done / len(all_names)) * 0.20, 3)

    all_confirmed = all(is_confirmed(n) for n in all_names)
    if not all_confirmed:
        return READINESS_THRESHOLDS["all_filled"]

    return READINESS_THRESHOLDS["all_confirmed"]
