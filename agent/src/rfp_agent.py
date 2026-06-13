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
from typing import Literal, TypedDict

import httpx
from copilotkit import CopilotKitMiddleware, a2ui
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver

from src.catalog import CATALOG_ID, CATALOG_PROMPT
from src.deal_store import get_deal, set_deal, update_deal
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


# ─── Tools ────────────────────────────────────────────────────────────────────

@tool
def extract_seed_fields(
    thread_id: str,
    archetype: Literal["RTLS", "MES", "UNKNOWN"],
    company_name: str,
    company_website: str,
    fields: list[DealField],
) -> str:
    """Extract and store seed fields from the customer's requirements dump.

    Call this as your FIRST action on every new requirements input.

    Args:
        thread_id: The current conversation thread ID (from system context).
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
    deal = get_deal(thread_id) or {}
    deal["archetype"] = archetype
    deal["company_name"] = company_name
    deal["company_website"] = company_website
    deal["surface_created"] = deal.get("surface_created", False)

    existing_fields = deal.get("fields", {})
    for f in fields:
        existing_fields[f["name"]] = {
            "label": f["label"],
            "value": f["value"],
            "status": f["status"],
            "source_quote": f.get("source_quote", ""),
            "why_it_matters": f.get("why_it_matters", ""),
        }
    deal["fields"] = existing_fields

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

    deal["readiness"] = compute_readiness(existing_fields, archetype)
    set_deal(thread_id, deal)

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
    thread_id: str,
    query: str,
) -> str:
    """Call Linkup to research the company and enrich deal fields.

    Call this after extract_seed_fields when company_name or company_website
    was detected. Returns enrichment context or empty string on failure.
    Gracefully degrades if LINKUP_API_KEY is missing or the API errors.

    Args:
        thread_id: Current thread ID.
        query: Search query — typically the company name or website URL.
    """
    api_key = os.getenv("LINKUP_API_KEY", "")
    if not api_key:
        log.info("[rfp_agent] LINKUP_API_KEY not set — skipping enrichment")
        return json.dumps({"ok": False, "reason": "LINKUP_API_KEY not configured"})

    try:
        resp = httpx.post(
            "https://api.linkup.so/v1/search",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "q": query,
                "depth": "standard",
                "outputType": "sourcedAnswer",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("answer", "") or data.get("output", "")

        deal = get_deal(thread_id) or {}
        deal["linkup_context"] = answer
        deal["linkup_query"] = query
        set_deal(thread_id, deal)

        log.info("[rfp_agent] Linkup enrichment ok for query=%r", query)
        return json.dumps({"ok": True, "context_chars": len(answer), "preview": answer[:300]})

    except Exception as exc:  # noqa: BLE001
        log.warning("[rfp_agent] Linkup enrichment failed: %s", exc)
        return json.dumps({"ok": False, "reason": str(exc)})


@tool
def render_deal_context(
    thread_id: str,
) -> str:
    """Render the DealContextCard surface in the canvas.

    Call this AFTER extract_seed_fields (and optionally enrich_from_linkup).
    Emits createSurface on the first call; updateComponents + updateDataModel
    on subsequent calls within the same session (deduplication handled by
    SurfaceCanvas on the frontend, but we track here for correctness).

    Args:
        thread_id: Current thread ID.
    """
    deal = get_deal(thread_id) or {}
    archetype = deal.get("archetype", "UNKNOWN")
    fields = deal.get("fields", {})
    readiness = deal.get("readiness", 0.0)
    company_name = deal.get("company_name", "")
    linkup_context = deal.get("linkup_context", "")
    surface_created = deal.get("surface_created", False)

    blockers = get_blockers_for_archetype(archetype)
    blocker_names = [b["name"] for b in blockers]

    field_list = []
    for name in blocker_names:
        f = fields.get(name, {})
        field_list.append({
            "name": name,
            "label": f.get("label", name),
            "value": f.get("value", ""),
            "status": f.get("status", "MISSING"),
            "source_quote": f.get("source_quote", ""),
            "why_it_matters": f.get("why_it_matters", ""),
        })

    payload = {
        "archetype": archetype,
        "company_name": company_name,
        "linkup_enriched": bool(linkup_context),
        "readiness": readiness,
        "readiness_pct": f"{int(readiness * 100)}%",
        "provisional": PROVISIONAL,
        "fields": field_list,
    }

    schema = _build_deal_context_schema(archetype, company_name, readiness, field_list)

    ops = [a2ui.update_components(SURFACE_DEAL, schema), a2ui.update_data_model(SURFACE_DEAL, payload)]
    if not surface_created:
        ops = [a2ui.create_surface(SURFACE_DEAL, catalog_id=CATALOG_ID)] + ops
        deal["surface_created"] = True
        set_deal(thread_id, deal)

    return a2ui.render(operations=ops)


def _build_deal_context_schema(
    archetype: str,
    company_name: str,
    readiness: float,
    field_list: list[dict],
) -> dict:
    stated = [f for f in field_list if f["status"] == "STATED"]
    inferred = [f for f in field_list if f["status"] == "INFERRED"]
    missing = [f for f in field_list if f["status"] == "MISSING"]
    readiness_pct = int(readiness * 100)

    title = f"{archetype} RFP Intake" if archetype != "UNKNOWN" else "RFP Intake"
    if company_name:
        title = f"{company_name} — {title}"

    def field_card_id(f: dict) -> str:
        return f"field-{f['name']}"

    def field_row(f: dict, idx: int) -> list[dict]:
        status_tone = {"STATED": "positive", "INFERRED": "warning", "MISSING": "danger"}.get(f["status"], "neutral")
        card_id = field_card_id(f)
        text_id = f"text-{f['name']}"
        badge_id = f"badge-{f['name']}"
        reason_id = f"reason-{f['name']}"

        components = [
            {"id": badge_id, "type": "Badge", "props": {"label": f["status"], "tone": status_tone}},
        ]

        if f["status"] in ("STATED", "INFERRED") and f.get("value"):
            components.append({"id": text_id, "type": "Text", "props": {"text": f["value"], "size": "sm"}})
        else:
            components.append({"id": text_id, "type": "Text", "props": {"text": f.get("why_it_matters", "Required"), "size": "sm", "tone": "muted"}})

        components.append({
            "id": card_id,
            "type": "Card",
            "props": {
                "child": f"row-inner-{f['name']}",
                "tone": "warning" if f["status"] == "MISSING" else "default",
            },
        })
        components.append({
            "id": f"row-inner-{f['name']}",
            "type": "Stack",
            "props": {"children": [badge_id, text_id], "gap": "xs"},
        })
        return components

    all_components: list[dict] = []

    # Root stack
    section_ids = ["header-section", "progress-row"]
    if stated:
        section_ids.append("stated-section")
    if inferred:
        section_ids.append("inferred-section")
    if missing:
        section_ids.append("missing-section")

    all_components.append({"id": "root", "type": "Stack", "props": {"children": section_ids, "gap": "md"}})

    # Header
    all_components.append({"id": "header-section", "type": "Section", "props": {"title": title, "eyebrow": f"ARCHETYPE: {archetype}", "child": "header-badge-row"}})
    all_components.append({"id": "header-badge-row", "type": "Row", "props": {"children": ["arch-badge"], "gap": "sm"}})
    arch_tone = {"RTLS": "info", "MES": "positive", "UNKNOWN": "warning"}.get(archetype, "neutral")
    all_components.append({"id": "arch-badge", "type": "Badge", "props": {"label": archetype, "tone": arch_tone}})

    # Readiness row
    readiness_tone = "danger" if readiness_pct < 50 else "warning" if readiness_pct < 85 else "positive"
    all_components.append({"id": "progress-row", "type": "Row", "props": {"children": ["readiness-label", "readiness-badge"], "gap": "sm", "align": "center"}})
    all_components.append({"id": "readiness-label", "type": "Text", "props": {"text": "Readiness", "size": "sm", "tone": "muted"}})
    all_components.append({"id": "readiness-badge", "type": "Badge", "props": {"label": f"{readiness_pct}%", "tone": readiness_tone}})

    # STATED fields
    if stated:
        stated_field_ids = [field_card_id(f) for f in stated]
        all_components.append({"id": "stated-section", "type": "Section", "props": {"title": f"Captured ({len(stated)})", "child": "stated-stack"}})
        all_components.append({"id": "stated-stack", "type": "Stack", "props": {"children": stated_field_ids, "gap": "sm"}})
        for f in stated:
            for comp in field_row(f, 0):
                all_components.append(comp)

    # INFERRED fields
    if inferred:
        inferred_field_ids = [field_card_id(f) for f in inferred]
        all_components.append({"id": "inferred-section", "type": "Section", "props": {"title": f"Inferred ({len(inferred)})", "child": "inferred-stack"}})
        all_components.append({"id": "inferred-stack", "type": "Stack", "props": {"children": inferred_field_ids, "gap": "sm"}})
        for f in inferred:
            for comp in field_row(f, 0):
                all_components.append(comp)

    # MISSING fields
    if missing:
        missing_field_ids = [field_card_id(f) for f in missing]
        all_components.append({"id": "missing-section", "type": "Section", "props": {"title": f"Missing — chase these ({len(missing)})", "child": "missing-stack"}})
        all_components.append({"id": "missing-stack", "type": "Stack", "props": {"children": missing_field_ids, "gap": "sm"}})
        for f in missing:
            for comp in field_row(f, 0):
                all_components.append(comp)

    return {"components": all_components}


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
  - thread_id from system context
  - archetype ("RTLS", "MES", or "UNKNOWN")
  - company_name and company_website if mentioned (else empty string)
  - All fields you can identify: STATED (verbatim), INFERRED (derived), or MISSING

For STATED fields: include the verbatim source_quote.
For MISSING fields: include a one-sentence why_it_matters deal-killer rationale.

### Step 3 — Enrich from Linkup (if company detected)
If company_name or company_website was provided, call `enrich_from_linkup` immediately
after extract_seed_fields. Use the returned context to upgrade MISSING fields to INFERRED
where the company research fills gaps. Re-call extract_seed_fields with the updated fields.

### Step 4 — Render the deal context card
Call `render_deal_context` to push the DealContextCard surface to the canvas.

### Step 5 — Chase missing blockers
After rendering, in the same response, ask about the top 2-3 MISSING hard blockers.
Batch your questions. For each one, explain WHY it matters using the deal-killer rationale.
Keep questions focused — one clear ask per blocker.

## Hard rules
- Call `extract_seed_fields` BEFORE `render_deal_context` on every turn with new info.
- Call `render_deal_context` ONCE per turn.
- Never fabricate field values. STATED = customer said it verbatim. INFERRED = you derived it.
- Never skip the archetype triage step.
- Never write proposals, pricing, or vendor recommendations.
- Grouped output only — no wall-of-text responses.
- Chase hard blockers first, in priority order.

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
        # Reuse the fixed-agent offline stub: drives the same create_agent
        # ReAct loop without a Gemini API key. Only the render_deal_context
        # tool is called in the offline path (no API key needed).
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
