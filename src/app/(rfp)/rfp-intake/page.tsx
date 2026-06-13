"use client";

import { CopilotChat } from "@copilotkit/react-core/v2";
import { SurfaceCanvas, CanvasEmptyState } from "@/components/pdf-analyst/SurfaceCanvas";
import { Split } from "@/components/pdf-analyst/Split";

const AGENT_ID = "rfp_agent";

export default function RFPIntakePage() {
  return (
    <div className="h-screen flex flex-col bg-[var(--bg)]">
      {/* Nav */}
      <nav className="rfp-nav">
        <span className="rfp-nav-logo">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
            <rect x="9" y="3" width="6" height="4" rx="1" />
            <line x1="9" y1="12" x2="15" y2="12" />
            <line x1="9" y1="16" x2="13" y2="16" />
          </svg>
          RFP Intake Cockpit
        </span>
        <span className="rfp-nav-badge">RTLS · MES</span>
      </nav>

      <div className="flex-1 min-h-0 flex">
        <Split
          persistKey="rfp.split"
          initialLeftFraction={0.38}
          left={
            <div className="h-full flex flex-col copilot-chat-wrapper">
              <CopilotChat
                agentId={AGENT_ID}
                labels={{
                  chatInputPlaceholder:
                    "Paste your requirements here — describe the project, company, timeline, anything you have…",
                  welcomeMessageText:
                    "Paste a rough requirements dump and I'll infer the archetype, extract what I can, and chase the critical gaps you need to close the deal.",
                }}
              />
            </div>
          }
          right={
            <SurfaceCanvas
              channel={AGENT_ID}
              emptyState={
                <CanvasEmptyState
                  title="Canvas is empty"
                  subtitle="Paste a requirements dump in the chat. The cockpit will infer your deal archetype, tag every field as STATED, INFERRED, or MISSING, and chase the gaps that kill deals."
                  hint={
                    <span className="mono text-[11px] uppercase tracking-[0.14em] text-[var(--ink-2)]">
                      try: "We need RTLS for our warehouse by Q3, auditor is pushing us."
                    </span>
                  }
                />
              }
            />
          }
        />
      </div>
    </div>
  );
}
