export interface AgentPrompts {
  [key: string]: { [key: string]: string };
}

export interface PersonaConfig {
  role: string;
  icon: string;
  bias_instruction: string;
}

export interface LLMConfig {
  MAX_RETRIES?: number;
  LLM_MAX_RETRIES?: number;
  LLM_PROVIDER?: string;
  GEMINI_MODEL?: string;
  OPENAI_MODEL?: string;
  TIMEOUT: number | null;
  CACHE?: boolean;
  TEMPERATURE: number;
  MAX_COMPLETION_TOKENS?: number | null;
}

export interface GraphConfig {
  ACTION_GRAPH_MAX_RETRIES: number;
  TASK_GRAPH_MAX_RETRIES: number;
}

export interface AppSettings {
  prompts: AgentPrompts;
  personas: PersonaConfig[];
  llm_config: LLMConfig;
  graph_config: GraphConfig;
}

export const DEFAULT_SETTINGS: AppSettings = {
  prompts: {
    analysis: { system_prompt: "", prompt_user_instruction: "" },
    code: { system_prompt: "", system_prompt_replan: "" },
    master: { system_prompt: "" },
  },
  personas: [
    {
      role: "The Optimistic",
      icon: "📈",
      bias_instruction: "Focus strictly on growth metrics, upside potential, and opportunities. Highlight positive momentum and ignore risks."
    },
    {
      role: "The Pessimistic",
      icon: "📉",
      bias_instruction: "Focus strictly on liabilities, downside risks, cost pressures, and volatility. Be skeptical of growth metrics."
    },
    {
      role: "The Skeptic",
      icon: "🕵️",
      bias_instruction: "Doubt data integrity and methodology. Look for anomalies, small sample sizes, and spurious correlations."
    }
  ],
  llm_config: {
    MAX_RETRIES: 2,
    LLM_PROVIDER: "gemini",
    GEMINI_MODEL: "gemini-2.5-flash",
    TIMEOUT: 300,
    TEMPERATURE: 0.3,
  },
  graph_config: {
    ACTION_GRAPH_MAX_RETRIES: 5,
    TASK_GRAPH_MAX_RETRIES: 3,
  },
};
