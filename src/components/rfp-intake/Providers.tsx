"use client";

import { CopilotKit } from "@copilotkit/react-core/v2";
import { createMirrorActivityRenderer } from "@/a2ui/MirrorRenderer";

const RENDERERS = [createMirrorActivityRenderer("rfp_agent")];

export function RFPProviders({ children }: { children: React.ReactNode }) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit-rfp" renderActivityMessages={RENDERERS}>
      {children}
    </CopilotKit>
  );
}
