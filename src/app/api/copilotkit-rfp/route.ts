import {
  CopilotRuntime,
  createCopilotRuntimeHandler,
} from "@copilotkit/runtime/v2";
import { HttpAgent } from "@ag-ui/client";

const RFP_AGENT_URL =
  process.env.RFP_AGENT_URL ?? "http://localhost:8123/rfp";

const rfpAgent = new HttpAgent({ url: RFP_AGENT_URL });

const runtime = new CopilotRuntime({
  agents: {
    default: rfpAgent,
    rfp_agent: rfpAgent,
  },
  // Same pattern as copilotkit-pdf: injectA2UITool=false so the agent's
  // Python tools own A2UI envelope emission (avoids orphan function_call).
  a2ui: {
    injectA2UITool: false,
  },
});

const handler = createCopilotRuntimeHandler({
  runtime,
  basePath: "/api/copilotkit-rfp",
  mode: "single-route",
});

export { handler as POST };
