export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const generateMessageId = (): string =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `id_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 9)}`;

// --- Shared Types ---
export interface FigureMetadata {
  filename?: string;
  sessId?: string;
  runId?: string;
  explanation?: string;
}

export interface Persona {
  role: string;
  icon?: string;
  bias: string;
  content: string | { summary: string };
}

export interface BiasMetrics {
  bias_score: number; // -1.0 to 1.0
  neutrality_index: number; // 0.0 to 1.0
  polarity: number; // -1.0 to 1.0
}

export interface AgentEvaluationResult {
  role: string;
  icon: string;
  bias: string;
  content: string | { summary: string };
  metrics: BiasMetrics;
}

export interface Message {
  id: string;
  role: "user" | "bot";
  content: string;
  runId?: string;
  perspectives?: AgentEvaluationResult[];
  fileNames?: string[];
}

// Graph
export interface GraphNode {
  id: string;
  label: string;
  description: string;
  sub_steps: { id: number; desc: string }[];
  status: "pending" | "running" | "success" | "error";
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphState {
  nodes: GraphNode[];
  edges: GraphEdge[];
  activeNodeId: string | null;
  activeStepId: number | null;
  nodeStatuses: Record<string, "pending" | "running" | "success" | "error">;
}

export interface Session {
  id: string;
  title: string;
  messages: Message[];
  graphState?: GraphState | null;
}

export const EXAMPLE_SESSIONS: Session[] = [
  {
    id: "session-1",
    title: "Data Analyst",
    messages: [
      {
        id: "msg-1",
        role: "user",
        content: "Analyse the correlation between gold price and gold volume",
        fileNames: ["data.csv"],
      },
      {
        id: "msg-2",
        role: "bot",
        content: "...Initiating Task",
      },
      {
        id: "msg-22",
        role: "bot",
        content: "...Analysing Diagrams",
      },
      {
        id: "msg-23",
        role: "bot",
        content: "...Fabricating Final Answer",
      },
      {
        id: "msg-3",
        role: "bot",
        content: `Short summary of what the data already suggests
- There is an average negative association between gold price and traded volume: higher volumes tend to occur with lower prices.  
- The relationship is weak and unstable: scatter points are widely spread with clusters and outliers, residuals from a simple linear fit show curvature and changing spread, and residuals have heavy tails.  
- Time structure matters: price trends upward while volume tends downward with spikes. The price–volume link appears to change over time (nonstationarity / regime changes).

Key caution
- Dont trust a single simple OLS fit for inference or causal claims. The OLS assumptions are violated (nonlinearity, heteroscedasticity, non-normal errors, and time dependence), so p-values and confidence intervals from naive OLS are unreliable.`,
      },
    ],
  },
];
