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
import re
import uuid
from typing import Annotated, Any, Literal, TypedDict

import httpx
from copilotkit import CopilotKitMiddleware, a2ui
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

from src.catalog import CATALOG_ID
from src.deal_store import get_deal, set_deal
from src.rfp_hard_blockers import (
    PROVISIONAL,
    RTLS_SIGNALS,
    MES_SIGNALS,
    ALL_BLOCKERS_BY_NAME,
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


class FieldUpdate(TypedDict):
    fieldName: str
    value: str
    status: Literal["STATED", "CONFIRMED"]


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
    tid = _thread_id(config)
    deal = get_deal(tid) or {}
    if not api_key:
        log.info("[rfp_agent] LINKUP_API_KEY not set — skipping enrichment")
        deal["linkup_status"] = "skipped"
        deal["linkup_error"] = "Company lookup unavailable; continuing from provided requirements."
        set_deal(tid, deal)
        return json.dumps({"ok": False, "reason": "LINKUP_API_KEY not configured"})

    if deal.get("linkup_query") == query and deal.get("linkup_context"):
        return json.dumps({
            "ok": True,
            "cached": True,
            "context_chars": len(deal["linkup_context"]),
            "preview": deal["linkup_context"][:300],
        })

    try:
        resp = httpx.post(
            "https://api.linkup.so/v1/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"q": query, "depth": "standard", "outputType": "sourcedAnswer"},
            timeout=4.0,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("answer", "") or data.get("output", "")

        deal["linkup_context"] = answer
        deal["linkup_query"] = query
        deal["linkup_status"] = "enriched"
        deal["linkup_error"] = ""
        set_deal(tid, deal)

        log.info("[rfp_agent] Linkup enrichment ok for query=%r", query)
        return json.dumps({"ok": True, "context_chars": len(answer), "preview": answer[:300]})

    except Exception as exc:  # noqa: BLE001
        log.warning("[rfp_agent] Linkup enrichment failed: %s", exc)
        deal["linkup_status"] = "unavailable"
        deal["linkup_error"] = "Company lookup unavailable; continuing from provided requirements."
        set_deal(tid, deal)
        return json.dumps({"ok": False, "reason": str(exc)})


@tool
def apply_canvas_updates(
    fields: list[FieldUpdate],
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """Apply one or more answers submitted from the canvas.

    Use this when a log_a2ui_event arrives with event name "submit_field",
    "submit_fields", or "confirm_field". Then call render_deal_context.
    """
    tid = _thread_id(config)
    deal = get_deal(tid) or {}
    archetype = deal.get("archetype", "UNKNOWN")
    existing_fields = deal.get("fields", {})

    updated: list[str] = []
    for update in fields:
        name = update["fieldName"]
        value = update["value"].strip()
        if not name or not value:
            continue

        blocker = ALL_BLOCKERS_BY_NAME.get(name, {})
        prior = existing_fields.get(name, {})
        status = update.get("status", "STATED")
        existing_fields[name] = {
            "label": prior.get("label") or blocker.get("label", name.replace("_", " ").title()),
            "value": value,
            "status": status,
            "source_quote": value,
            "why_it_matters": prior.get("why_it_matters") or blocker.get("why_it_matters", ""),
        }
        updated.append(name)

    deal["fields"] = existing_fields
    deal["readiness"] = compute_readiness(existing_fields, archetype)
    set_deal(tid, deal)

    return json.dumps({
        "ok": True,
        "updated": updated,
        "readiness": deal["readiness"],
    })


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
    linkup_query = deal.get("linkup_query", "")
    linkup_status = deal.get("linkup_status", "")
    linkup_error = deal.get("linkup_error", "")
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
        "linkup_query": linkup_query,
        "linkup_context": linkup_context,
        "linkup_status": linkup_status,
        "linkup_error": linkup_error,
        "readiness": readiness,
        "readiness_pct": f"{int(readiness * 100)}%",
        "provisional": PROVISIONAL,
        "fields": field_list,
    }

    components = _build_components(
        archetype,
        company_name,
        readiness,
        field_list,
        linkup_context,
        linkup_error,
    )

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
    linkup_context: str = "",
    linkup_error: str = "",
) -> list[dict]:
    """Build the flat A2UI component list (no 'props' wrapper — flat keys per spec)."""
    stated = [f for f in field_list if f["status"] == "STATED"]
    inferred = [f for f in field_list if f["status"] == "INFERRED"]
    missing = [f for f in field_list if f["status"] == "MISSING"]
    top_missing = missing[:3]
    readiness_pct = int(readiness * 100)

    title = f"{archetype} RFP Intake" if archetype != "UNKNOWN" else "RFP Intake"
    if company_name:
        title = f"{company_name} — {title}"

    comps: list[dict] = []

    # Root
    section_ids = ["header-section", "summary-card"]
    if linkup_context or linkup_error:
        section_ids.append("company-section")
    if stated:
        section_ids.append("stated-section")
    if inferred:
        section_ids.append("inferred-section")
    if missing:
        section_ids.append("missing-section")
    if inferred or top_missing:
        section_ids.append("review-section")
    comps.append({"id": "root", "component": "Stack", "children": section_ids, "gap": "lg"})

    # Header section
    arch_tone = {"RTLS": "info", "MES": "positive", "UNKNOWN": "warning"}.get(archetype, "neutral")
    comps.append({"id": "header-section", "component": "Section", "title": title, "eyebrow": f"ARCHETYPE · {archetype}", "child": "header-row"})
    comps.append({"id": "header-row", "component": "Row", "children": ["arch-badge", "rubric-badge"], "gap": "sm"})
    comps.append({"id": "arch-badge", "component": "Badge", "label": archetype, "tone": arch_tone})
    comps.append({"id": "rubric-badge", "component": "Badge", "label": "PROVISIONAL RUBRIC" if PROVISIONAL else "RUBRIC LOCKED", "tone": "warning" if PROVISIONAL else "positive"})

    # Readiness summary
    r_tone = "danger" if readiness_pct < 50 else "warning" if readiness_pct < 85 else "positive"
    comps.append({"id": "summary-card", "component": "Card", "child": "summary-stack", "tone": "lilac"})
    comps.append({"id": "summary-stack", "component": "Stack", "children": ["summary-meter", "summary-row"], "gap": "sm"})
    comps.append({"id": "summary-meter", "component": "ReadinessMeter", "pct": readiness_pct, "label": "Intake readiness", "tone": r_tone})
    comps.append({"id": "summary-row", "component": "Row", "children": ["captured-badge", "inferred-badge", "gap-badge"], "gap": "sm", "align": "center"})
    comps.append({"id": "captured-badge", "component": "Badge", "label": f"{len(stated)} captured", "tone": "positive"})
    comps.append({"id": "inferred-badge", "component": "Badge", "label": f"{len(inferred)} inferred", "tone": "warning" if inferred else "neutral"})
    comps.append({"id": "gap-badge", "component": "Badge", "label": f"{len(missing)} open gaps", "tone": "danger" if missing else "positive"})

    if linkup_context or linkup_error:
        preview = (linkup_context or linkup_error).strip().replace("\n", " ")
        if len(preview) > 520:
            preview = preview[:517].rstrip() + "..."
        comps.append({"id": "company-section", "component": "Section", "title": "Company research", "eyebrow": "LINKUP", "child": "company-card"})
        comps.append({"id": "company-card", "component": "Card", "child": "company-stack", "tone": "info" if linkup_context else "default"})
        comps.append({"id": "company-stack", "component": "Stack", "children": ["company-badge", "company-text"], "gap": "xs"})
        comps.append({
            "id": "company-badge",
            "component": "Badge",
            "label": "Background context" if linkup_context else "Lookup skipped",
            "tone": "info" if linkup_context else "neutral",
        })
        comps.append({"id": "company-text", "component": "Text", "text": preview, "size": "sm", "tone": "default" if linkup_context else "muted"})

    def add_field_card(f: dict) -> None:
        fid = f["name"]
        comps.append({
            "id": f"card-{fid}",
            "component": "DealContextCard",
            "fieldName": fid,
            "label": f["label"],
            "value": f.get("value", ""),
            "status": f["status"],
            "sourceQuote": f.get("source_quote", ""),
            "whyItMatters": f.get("why_it_matters", "Required — not yet captured."),
        })

    # STATED
    if stated:
        comps.append({"id": "stated-section", "component": "Section", "title": f"Captured ({len(stated)})", "child": "stated-stack"})
        comps.append({"id": "stated-stack", "component": "Grid", "children": [f"card-{f['name']}" for f in stated], "columns": 2, "gap": "sm"})
        for f in stated:
            add_field_card(f)

    # INFERRED
    if inferred:
        comps.append({"id": "inferred-section", "component": "Section", "title": f"Inferred ({len(inferred)})", "child": "inferred-stack"})
        comps.append({"id": "inferred-stack", "component": "Grid", "children": [f"card-{f['name']}" for f in inferred], "columns": 2, "gap": "sm"})
        for f in inferred:
            add_field_card(f)

    # MISSING — show top 3 priority gaps only; summarise the rest
    if missing:
        rest_count = len(missing) - len(top_missing)
        section_title = f"Top gaps to chase ({len(missing)} total)"
        comps.append({"id": "missing-section", "component": "Section", "title": section_title, "child": "missing-stack"})
        stack_children = [f"card-{f['name']}" for f in top_missing]
        if rest_count:
            stack_children.append("missing-more")
        comps.append({"id": "missing-stack", "component": "Grid", "children": stack_children, "columns": 2, "gap": "sm"})
        for f in top_missing:
            add_field_card(f)
        if rest_count:
            comps.append({"id": "missing-more", "component": "Text", "text": f"+ {rest_count} more gaps — answer the questions above to unlock them.", "size": "sm", "tone": "muted"})

    if inferred or top_missing:
        comps.append({"id": "review-section", "component": "Section", "title": "Review or add information", "child": "review-form"})
        comps.append({
            "id": "review-form",
            "component": "MultiFieldForm",
            "inferredFields": [
                {
                    "fieldName": f["name"],
                    "label": f["label"],
                    "value": f.get("value", ""),
                }
                for f in inferred
            ],
            "fields": [
                {
                    "fieldName": f["name"],
                    "label": f["label"],
                    "placeholder": f"Answer {f['label'].lower()}…",
                }
                for f in top_missing
            ],
            "submitLabel": "Update cockpit",
        })

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

### Step 3 — Enrich from LinkUp (if company detected)
If company_name or company_website was provided, call `enrich_from_linkup` with the
company name or URL as the query. This is supporting company context only: do not wait
on it to fabricate blockers. If it succeeds, the canvas will show the LinkUp context.
If it fails or is missing a key, continue normally.

### Step 4 — Render the deal context card
Call `render_deal_context` — no arguments needed. Call ONCE per turn.

### Step 5 — Chase missing blockers in chat
After rendering, ask about the top 2–3 MISSING hard blockers. Batch your questions.
For each, explain WHY it matters using the deal-killer rationale. One clear ask per blocker.
The canvas already shows a review form where users can confirm/correct inferred fields
and answer multiple gaps before updating the cockpit once.

### Handling canvas events (log_a2ui_event)
When you receive a `log_a2ui_event` tool result:
- "submit_fields": extract context.fields, call `apply_canvas_updates` with every
  non-empty field, then call `render_deal_context`.
After any canvas update, acknowledge briefly and ask only for the next most important gap.

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

The canvas surface is fixed for this demo. Use the tools to store deal fields, optionally
fetch company context, then render the cockpit. Do not generate custom A2UI schemas.
"""


# ─── Deterministic demo model ─────────────────────────────────────────────────

def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def _latest_user_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            text = _message_text(message).strip()
            if text:
                return text
    return ""


def _demo_company_name(text: str) -> str:
    patterns = [
        r"(?:company|customer|client)\s*(?:is|:)\s*([A-Z][A-Za-z0-9&.,' -]{2,60})",
        r"\bfor\s+([A-Z][A-Za-z0-9&.,' -]{2,60})",
        r"\bat\s+([A-Z][A-Za-z0-9&.,' -]{2,60})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            name = re.split(r"[,.;\n]", match.group(1).strip())[0].strip()
            if name and len(name.split()) <= 6:
                return name
    return "Acme Precision Manufacturing"


def _demo_archetype(text: str) -> Literal["RTLS", "MES", "UNKNOWN"]:
    lower = text.lower()
    mes_hits = sum(1 for signal in MES_SIGNALS if signal in lower)
    rtls_hits = sum(1 for signal in RTLS_SIGNALS if signal in lower)
    if mes_hits > rtls_hits:
        return "MES"
    if rtls_hits:
        return "RTLS"
    return "RTLS"


def _demo_field(
    name: str,
    value: str,
    status: Literal["STATED", "INFERRED", "MISSING"],
    source_quote: str,
) -> DealField:
    blocker = ALL_BLOCKERS_BY_NAME[name]
    return {
        "name": name,
        "label": blocker["label"],
        "value": value,
        "status": status,
        "source_quote": source_quote,
        "why_it_matters": blocker["why_it_matters"] if status == "MISSING" else "",
    }


def _demo_extract_args(text: str) -> dict[str, Any]:
    archetype = _demo_archetype(text)
    company = _demo_company_name(text)
    lower = text.lower()

    fields: list[DealField] = [
        _demo_field(
            "business_objective",
            "Reduce asset search time and audit exposure before the next operational review.",
            "STATED" if any(word in lower for word in ["audit", "lost", "search", "warehouse", "asset"]) else "INFERRED",
            text[:220],
        ),
        _demo_field(
            "security_it_constraints",
            "IT/security review is required before rollout; deployment constraints need confirmation.",
            "INFERRED",
            "Enterprise operational system implies IT/security review before production rollout.",
        ),
    ]

    if "q3" in lower or "quarter" in lower:
        fields.append(_demo_field(
            "success_criteria",
            "Target go-live timing is tied to Q3; acceptance metrics still need to be made explicit.",
            "INFERRED",
            "Timeline pressure implies acceptance criteria are needed before scope can lock.",
        ))

    if archetype == "RTLS":
        fields.extend([
            _demo_field(
                "customer_problem_definition",
                "The customer needs real-time visibility into warehouse assets and zones.",
                "STATED" if "warehouse" in lower or "tracking" in lower or "rtls" in lower else "INFERRED",
                text[:220],
            ),
            _demo_field(
                "rtls_requirements",
                "RTLS is required; accuracy, refresh rate, tag count, and zone model are not yet confirmed.",
                "INFERRED",
                "RTLS/tracking request gives the solution direction, but not the technical spec.",
            ),
            _demo_field(
                "site_information",
                "",
                "MISSING",
                "",
            ),
            _demo_field(
                "network_infrastructure",
                "",
                "MISSING",
                "",
            ),
            _demo_field(
                "erp_system_integration",
                "",
                "MISSING",
                "",
            ),
        ])
    else:
        fields.extend([
            _demo_field(
                "production_process_definition",
                "Manufacturing execution scope is implied; station flow and routing need confirmation.",
                "INFERRED",
                "MES request implies process-flow scope, but the process definition is not complete.",
            ),
            _demo_field(
                "machine_connectivity_readiness",
                "",
                "MISSING",
                "",
            ),
            _demo_field(
                "erp_integration_scope",
                "",
                "MISSING",
                "",
            ),
            _demo_field(
                "poc_expectations",
                "",
                "MISSING",
                "",
            ),
        ])

    return {
        "archetype": archetype,
        "company_name": company,
        "company_website": "",
        "fields": fields,
    }


class DemoRFPModel(BaseChatModel):
    """Deterministic RFP model for recording mode.

    It drives the real tools, but does not call Gemini. This keeps the A2UI
    surface, deal store, readiness scoring, and batch-update loop intact while
    removing streaming failures from the demo-critical first turn.
    """

    @property
    def _llm_type(self) -> str:
        return "rfp-demo-stub"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "DemoRFPModel":
        return self

    def bind(self, **kwargs: Any) -> "DemoRFPModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        tool_names = [getattr(m, "name", "") for m in messages if isinstance(m, ToolMessage)]

        if "extract_seed_fields" not in tool_names:
            user_text = _latest_user_text(messages)
            message: BaseMessage = AIMessage(
                content="",
                tool_calls=[{
                    "name": "extract_seed_fields",
                    "args": _demo_extract_args(user_text),
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                }],
            )
        elif "enrich_from_linkup" not in tool_names:
            user_text = _latest_user_text(messages)
            query = _demo_company_name(user_text)
            message = AIMessage(
                content="",
                tool_calls=[{
                    "name": "enrich_from_linkup",
                    "args": {"query": query},
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                }],
            )
        elif "render_deal_context" not in tool_names:
            message = AIMessage(
                content="",
                tool_calls=[{
                    "name": "render_deal_context",
                    "args": {},
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                }],
            )
        else:
            message = AIMessage(
                content=(
                    "I built the intake cockpit on the right. Confirm or correct inferred "
                    "fields there, answer any gaps you know, then update the cockpit once."
                )
            )

        return ChatResult(generations=[ChatGeneration(message=message)])


# ─── Agent factory ────────────────────────────────────────────────────────────

def _build_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=os.getenv("MODEL", "gemini-3.5-flash"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


def build_rfp_agent():
    if os.getenv("RFP_LIVE_LLM") != "1":
        return create_agent(
            model=DemoRFPModel(),
            tools=[extract_seed_fields, enrich_from_linkup, apply_canvas_updates, render_deal_context],
            middleware=[CopilotKitMiddleware()],
            system_prompt=SYSTEM_PROMPT,
            checkpointer=MemorySaver(),
        )

    return create_agent(
        model=_build_model(),
        tools=[extract_seed_fields, enrich_from_linkup, apply_canvas_updates, render_deal_context],
        middleware=[CopilotKitMiddleware()],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )


graph = build_rfp_agent()
