"""RFP Intake Cockpit agent.

Single create_agent ReAct loop (copy of fixed_agent.py pattern).
Phase 1: archetype triage → seed field extraction → DealContextCard render.
Phase 2: gap chasing + Linkup enrichment + verification surface + HITL gate.

CUSTOMIZATION SEAM #5 (agent flow) — see HACKATHON.md §5.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Annotated, Literal, TypedDict

import httpx
from copilotkit import CopilotKitMiddleware, a2ui
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

from src.catalog import CATALOG_ID, CATALOG_PROMPT
from src.deal_store import get_deal, set_deal
from src.rfp_hard_blockers import (
    PROVISIONAL,
    RTLS_SIGNALS,
    MES_SIGNALS,
    compute_readiness,
    get_blockers_for_archetype,
)

log = logging.getLogger(__name__)

SURFACE_DEAL = "rfp-deal"


# ─── Typed parameter classes (Gemini typed-array fix — see fixed_agent.py:37) ─

class DealField(TypedDict):
    name: str
    label: str
    value: str
    status: Literal["STATED", "INFERRED", "MISSING"]
    source_quote: str
    why_it_matters: str


# ─── thread_id helper ─────────────────────────────────────────────────────────

def _thread_id(config: RunnableConfig) -> str:
    """Extract LangGraph thread_id from injected RunnableConfig."""
    return config.get("configurable", {}).get("thread_id", "default")


# ─── Tools ────────────────────────────────────────────────────────────────────

@tool
def extract_seed_fields(
    archetype: Literal["RTLS", "MES", "UNKNOWN"],
    company_name: str,
    company_website: str,
    fields: list[DealField],
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Extract and store seed fields from the customer's requirements dump.

    Call this as your FIRST action on every new requirements input.

    Args:
        archetype: Inferred archetype — "RTLS", "MES", or "UNKNOWN" if ambiguous.
        company_name: Company name if mentioned, else empty string.
        company_website: Website/URL if mentioned, else empty string.
        fields: Extracted fields. Each field has:
            - name: snake_case field name matching a blocker id
            - label: Human-readable label
            - value: Extracted value (empty string if MISSING)
            - status: "STATED" (verbatim from dump), "INFERRED" (derived), or "MISSING"
            - source_quote: Verbatim quote from dump for STATED fields; empty for others
            - why_it_matters: One-sentence deal-killer rationale for MISSING fields
    """
    tid = _thread_id(config)
    deal = get_deal(tid) or {}
    deal["archetype"] = archetype
    deal["company_name"] = company_name
    deal["company_website"] = company_website
    deal.setdefault("surface_created", False)

    existing_fields = deal.get("fields", {})
    for f in fields:
        existing_fields[f["name"]] = {
            "label": f["label"],
            "value": f["value"],
            "status": f["status"],
            "source_quote": f.get("source_quote", ""),
            "why_it_matters": f.get("why_it_matters", ""),
        }

    blockers = get_blockers_for_archetype(archetype)
    for b in blockers:
        if b["name"] not in existing_fields:
            existing_fields[b["name"]] = {
                "label": b["label"],
                "value": "",
                "status": "MISSING",
                "source_quote": "",
                "why_it_matters": b["why_it_matters"],
            }

    deal["fields"] = existing_fields
    deal["readiness"] = compute_readiness(existing_fields, archetype)
    set_deal(tid, deal)

    missing = [
        b for b in blockers
        if existing_fields.get(b["name"], {}).get("status") == "MISSING"
    ]
    return json.dumps({
        "ok": True,
        "archetype": archetype,
        "fields_stored": len(fields),
        "missing_blockers": [b["name"] for b in missing],
        "readiness": deal["readiness"],
        "linkup_pending": bool(company_name or company_website),
    })


@tool
def enrich_from_linkup(
    query: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Call Linkup to research the company and enrich deal fields.

    Call this after extract_seed_fields when company_name or company_website
    was detected. Gracefully degrades if LINKUP_API_KEY is missing or errors.

    Args:
        query: Search query — typically the company name or website URL.
    """
    api_key = os.getenv("LINKUP_API_KEY", "")
    if not api_key:
        log.info("[rfp_agent] LINKUP_API_KEY not set — skipping enrichment")
        return json.dumps({"ok": False, "reason": "LINKUP_API_KEY not configured"})

    tid = _thread_id(config)
    try:
        resp = httpx.post(
            "https://api.linkup.so/v1/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"q": query, "depth": "standard", "outputType": "sourcedAnswer"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("answer", "") or data.get("output", "")

        deal = get_deal(tid) or {}
        deal["linkup_context"] = answer
        deal["linkup_query"] = query
        set_deal(tid, deal)

        log.info("[rfp_agent] Linkup enrichment ok for query=%r", query)
        return json.dumps({"ok": True, "context_chars": len(answer), "preview": answer[:300]})

    except Exception as exc:  # noqa: BLE001
        log.warning("[rfp_agent] Linkup enrichment failed: %s", exc)
        return json.dumps({"ok": False, "reason": str(exc)})


@tool
def render_deal_context(
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Render the DealContextCard surface in the canvas.

    Call this AFTER extract_seed_fields (and optionally enrich_from_linkup).
    Call ONCE per turn.
    """
    tid = _thread_id(config)
    deal = get_deal(tid) or {}
    archetype = deal.get("archetype", "UNKNOWN")
    fields = deal.get("fields", {})
    readiness = deal.get("readiness", 0.0)
    company_name = deal.get("company_name", "")
    linkup_context = deal.get("linkup_context", "")
    surface_created = deal.get("surface_created", False)

    blockers = get_blockers_for_archetype(archetype)
    field_list = [
        {
            "name": b["name"],
            "label": fields.get(b["name"], {}).get("label", b["label"]),
            "value": fields.get(b["name"], {}).get("value", ""),
            "status": fields.get(b["name"], {}).get("status", "MISSING"),
            "source_quote": fields.get(b["name"], {}).get("source_quote", ""),
            "why_it_matters": fields.get(b["name"], {}).get("why_it_matters", b["why_it_matters"]),
        }
        for b in blockers
    ]

    payload = {
        "archetype": archetype,
        "company_name": company_name,
        "linkup_enriched": bool(linkup_context),
        "readiness": readiness,
        "readiness_pct": f"{int(readiness * 100)}%",
        "provisional": PROVISIONAL,
        "fields": field_list,
    }

    components = _build_components(archetype, company_name, readiness, field_list)

    ops: list = [
        a2ui.update_components(SURFACE_DEAL, components),
        a2ui.update_data_model(SURFACE_DEAL, payload),
    ]
    if not surface_created:
        ops = [a2ui.create_surface(SURFACE_DEAL, catalog_id=CATALOG_ID)] + ops
        deal["surface_created"] = True
        set_deal(tid, deal)

    return a2ui.render(operations=ops)


def _build_components(
    archetype: str,
    company_name: str,
    readiness: float,
    field_list: list[dict],
) -> list[dict]:
    """Build the flat A2UI component list (no 'props' wrapper — flat keys per spec)."""
    stated = [f for f in field_list if f["status"] == "STATED"]
    inferred = [f for f in field_list if f["status"] == "INFERRED"]
    missing = [f for f in field_list if f["status"] == "MISSING"]
    readiness_pct = int(readiness * 100)

    title = f"{archetype} RFP Intake" if archetype != "UNKNOWN" else "RFP Intake"
    if company_name:
        title = f"{company_name} — {title}"

    comps: list[dict] = []

    # Root
    section_ids = ["header-section", "progress-row"]
    if stated:
        section_ids.append("stated-section")
    if inferred:
        section_ids.append("inferred-section")
    if missing:
        section_ids.append("missing-section")
    comps.append({"id": "root", "component": "Stack", "children": section_ids, "gap": "md"})

    # Header section
    arch_tone = {"RTLS": "info", "MES": "positive", "UNKNOWN": "warning"}.get(archetype, "neutral")
    comps.append({"id": "header-section", "component": "Section", "title": title, "eyebrow": f"ARCHETYPE · {archetype}", "child": "header-row"})
    comps.append({"id": "header-row", "component": "Row", "children": ["arch-badge"], "gap": "sm"})
    comps.append({"id": "arch-badge", "component": "Badge", "label": archetype, "tone": arch_tone})

    # Readiness row
    r_tone = "danger" if readiness_pct < 50 else "warning" if readiness_pct < 85 else "positive"
    comps.append({"id": "progress-row", "component": "Row", "children": ["r-label", "r-badge"], "gap": "sm", "align": "center"})
    comps.append({"id": "r-label", "component": "Text", "text": "Readiness", "size": "sm", "tone": "muted"})
    comps.append({"id": "r-badge", "component": "Badge", "label": f"{readiness_pct}%", "tone": r_tone})

    def add_field_card(f: dict) -> None:
        fid = f["name"]
        s_tone = {"STATED": "positive", "INFERRED": "warning", "MISSING": "danger"}.get(f["status"], "neutral")
        card_tone = "default" if f["status"] in ("STATED", "CONFIRMED") else "warning" if f["status"] == "INFERRED" else "default"

        body_text = f["value"] if f["status"] in ("STATED", "INFERRED") and f.get("value") else f.get("why_it_matters", "Required — not yet captured.")

        comps.append({"id": f"card-{fid}", "component": "Card", "child": f"inner-{fid}", "tone": card_tone})
        comps.append({"id": f"inner-{fid}", "component": "Stack", "children": [f"badge-{fid}", f"text-{fid}"], "gap": "xs"})
        comps.append({"id": f"badge-{fid}", "component": "Badge", "label": f["label"] + " · " + f["status"], "tone": s_tone})
        comps.append({"id": f"text-{fid}", "component": "Text", "text": body_text, "size": "sm", "tone": "muted" if f["status"] == "MISSING" else "default"})

    # STATED
    if stated:
        comps.append({"id": "stated-section", "component": "Section", "title": f"Captured ({len(stated)})", "child": "stated-stack"})
        comps.append({"id": "stated-stack", "component": "Stack", "children": [f"card-{f['name']}" for f in stated], "gap": "sm"})
        for f in stated:
            add_field_card(f)

    # INFERRED
    if inferred:
        comps.append({"id": "inferred-section", "component": "Section", "title": f"Inferred ({len(inferred)})", "child": "inferred-stack"})
        comps.append({"id": "inferred-stack", "component": "Stack", "children": [f"card-{f['name']}" for f in inferred], "gap": "sm"})
        for f in inferred:
            add_field_card(f)

    # MISSING — show top 3 priority gaps only; summarise the rest
    if missing:
        top_missing = missing[:3]
        rest_count = len(missing) - len(top_missing)
        section_title = f"Top gaps to chase ({len(missing)} total)"
        comps.append({"id": "missing-section", "component": "Section", "title": section_title, "child": "missing-stack"})
        stack_children = [f"card-{f['name']}" for f in top_missing]
        if rest_count:
            stack_children.append("missing-more")
        comps.append({"id": "missing-stack", "component": "Stack", "children": stack_children, "gap": "sm"})
        for f in top_missing:
            add_field_card(f)
        if rest_count:
            comps.append({"id": "missing-more", "component": "Text", "text": f"+ {rest_count} more gaps — answer the questions above to unlock them.", "size": "sm", "tone": "muted"})

    return comps


# ─── System prompt ────────────────────────────────────────────────────────────

_PROVISIONAL_NOTE = "⚠️ PROVISIONAL rubric — RTLS/MES hard blockers from technical sales expert. Awaiting final sign-off." if PROVISIONAL else ""

SYSTEM_PROMPT = f"""\
You are the RFP Intake Cockpit — an expert B2B technical sales intake agent for RTLS
(Real-Time Location Systems) and MES (Manufacturing Execution Systems) deals.

Your job: turn a messy requirements dump into a complete, verified, grouped RFP by chasing
the critical fields customers chronically omit. You ELICIT and VERIFY. You do NOT write
proposals, quote pricing, or judge feasibility.

{_PROVISIONAL_NOTE}

## Your turn flow

### Step 1 — Archetype triage (ALWAYS first)
Classify the dump as "RTLS", "MES", or "UNKNOWN".
  - RTLS signals: {', '.join(RTLS_SIGNALS[:6])}
  - MES signals: {', '.join(MES_SIGNALS[:6])}
  - If ambiguous, ask ONE clarifying question before calling extract_seed_fields.

### Step 2 — Extract seed fields
Call `extract_seed_fields` with:
  - archetype ("RTLS", "MES", or "UNKNOWN")
  - company_name and company_website if mentioned (else empty string)
  - fields: extract EVERY field you can identify using THESE EXACT field names:

**Universal fields (both archetypes):**
  - business_objective — measurable KPI / goal (e.g. "OEE +8%", "asset loss -30%")
  - success_criteria — agreed UAT acceptance metrics
  - decision_makers — executive sponsor + technical owner + sign-off chain
  - security_it_constraints — IT/security policies, on-prem vs cloud, approval process

**RTLS-specific fields:**
  - customer_problem_definition — the business problem (NOT the solution)
  - site_information — building count, sq footage, zones, machine types, PLC brands
  - network_infrastructure — Wi-Fi/wireless details, VLANs, latency, coverage
  - rtls_requirements — accuracy target, refresh rate, tag count, zone structure
  - erp_system_integration — ERP name + version, API method, data flow, team

**MES-specific fields:**
  - production_process_definition — process flow, stations, routing, approvals
  - machine_connectivity_readiness — PLC brands, protocols, connectivity feasibility
  - erp_integration_scope — ERP name, data ownership, transactions, ERP team involved
  - ot_network_infrastructure — VLAN, firewall OT/IT segmentation, latency
  - traceability_requirement — genealogy model, serialization vs batch
  - timeline_realism — pilot, go-live, rollout milestones (flag ASAP/4-week answers)
  - poc_expectations — measurable PoC success criteria

Extract EVERYTHING you can from the dump. Use status="STATED" for verbatim facts,
"INFERRED" for derived facts, and include a why_it_matters only for "MISSING" fields.
The value for MISSING fields must be an empty string "".

For STATED fields: include the verbatim source_quote from the dump.
For INFERRED fields: set value to your inference and source_quote to your reasoning.

### Step 3 — Enrich from Linkup (if company detected)
If company_name or company_website was provided, call `enrich_from_linkup` with the
company name or URL as the query. Use returned context to upgrade MISSING → INFERRED
where the research fills gaps. Re-call extract_seed_fields with updated fields.

### Step 4 — Render the deal context card
Call `render_deal_context` — no arguments needed. Call ONCE per turn.

### Step 5 — Chase missing blockers
After rendering, ask about the top 2–3 MISSING hard blockers. Batch your questions.
For each, explain WHY it matters using the deal-killer rationale. One clear ask per blocker.

## Hard rules
- Call `extract_seed_fields` BEFORE `render_deal_context` on every turn with new info.
- Call `render_deal_context` ONCE per turn. No arguments — it reads from session state.
- Never fabricate field values. STATED = verbatim from customer. INFERRED = you derived it.
- Never skip archetype triage.
- Never write proposals, pricing, or vendor recommendations.
- Grouped output only — no wall of text.

## Field status rules
- STATED: customer said it; include source_quote.
- INFERRED: you derived it from context or Linkup; explain basis.
- MISSING: customer hasn't provided it; show why_it_matters.

{CATALOG_PROMPT}
"""


# ─── Agent factory ────────────────────────────────────────────────────────────

def _build_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=os.getenv("MODEL", "gemini-3.5-flash"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


def build_rfp_agent():
    if os.getenv("OFFLINE") == "1":
        from src.offline_fixed import build_offline_fixed_agent
        return build_offline_fixed_agent(render_deal_context, SYSTEM_PROMPT)

    return create_agent(
        model=_build_model(),
        tools=[extract_seed_fields, enrich_from_linkup, render_deal_context],
        middleware=[CopilotKitMiddleware()],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )


graph = build_rfp_agent()
