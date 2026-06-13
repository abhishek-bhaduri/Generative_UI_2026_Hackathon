"""PROVISIONAL hard-blocker rubric for the RFP intake agent.

⚠️  PROVISIONAL — awaiting final rubric from the technical-sales teammate.
    Every rule here is a best-guess placeholder derived from common deal-loss
    patterns. Do NOT treat as production-ready critical-info logic. Replace with
    war-story-derived rules when the real rubric arrives from the team.

A hard-blocker is a deal-killing gap: information without which the sales rep
cannot move the deal forward. The agent chases these first, in priority order,
and explains WHY each one matters to the customer.
"""

HARD_BLOCKERS: list[dict] = [
    {
        "field": "success_criteria",
        "label": "Success Criteria",
        "why_it_matters": (
            "Without measurable outcomes, the customer cannot evaluate whether "
            "the solution delivered value — deals stall or get walked back at renewal."
        ),
        "priority": 1,
    },
    {
        "field": "decision_process",
        "label": "Decision Process & Stakeholders",
        "why_it_matters": (
            "Deals that reach procurement without a known champion or sign-off chain "
            "routinely go dark. Who approves, who blocks, who influences?"
        ),
        "priority": 2,
    },
    {
        "field": "technical_constraints",
        "label": "Technical Constraints",
        "why_it_matters": (
            "Cloud lock-in, compliance requirements, or stack dependencies discovered "
            "post-scoping can make a solution technically infeasible — late and expensive."
        ),
        "priority": 3,
    },
    {
        "field": "why_now",
        "label": "Why Now / Forcing Event",
        "why_it_matters": (
            "Without a forcing event (contract expiry, compliance deadline, board mandate), "
            "deals have no urgency and slip quarter after quarter."
        ),
        "priority": 4,
    },
    {
        "field": "incumbent",
        "label": "Incumbent / Current Solution",
        "why_it_matters": (
            "Understanding what the customer is replacing — and why they're unhappy — "
            "reveals scope traps and shapes the winning narrative."
        ),
        "priority": 5,
    },
    {
        "field": "budget_authority",
        "label": "Budget & Approval Authority",
        "why_it_matters": (
            "'Budget in principle' with no approved PO path stalls at procurement. "
            "Who controls the budget and what's the sign-off chain?"
        ),
        "priority": 6,
    },
    {
        "field": "evaluation_criteria",
        "label": "Evaluation Criteria",
        "why_it_matters": (
            "Not knowing how the customer will score vendors means we can win on "
            "the wrong dimensions and lose on the ones that actually matter."
        ),
        "priority": 7,
    },
]

BLOCKER_FIELDS = {b["field"] for b in HARD_BLOCKERS}

BLOCKER_BY_FIELD = {b["field"]: b for b in HARD_BLOCKERS}
