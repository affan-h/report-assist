import { useState } from "react";
import {
  Users,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Activity,
  Scale,
} from "lucide-react";
import { parseMessageContent } from "@/utils/messageParser";
import { ArtifactViewer } from "./artifact-viewer";
import { Persona, AgentEvaluationResult } from "@/lib/chat-utils";
import { cn } from "@/lib/utils";
import { BiasSpectrum, getNeutralityColor } from "./bio-spectrum";

// --- Sub-Component: Individual Persona Card ---
const PersonaCard = ({
  persona,
  style,
  runId,
  sessionId,
}: {
  persona: AgentEvaluationResult;
  style: string;
  runId: string | undefined;
  sessionId: string | undefined;
}) => {
  // Requirement 2: Independent dropdown state for this card
  const [isOpen, setIsOpen] = useState(false);

  const contentString =
    typeof persona.content === "object"
      ? JSON.stringify(persona.content.summary)
      : persona.content;

  return (
    <div
      className={cn(
        "rounded-xl border flex flex-col transition-all duration-300 hover:shadow-md bg-white",
        style
      )}
    >
      {/* Card Header */}
      <div
        className="p-4 flex flex-col gap-3 cursor-pointer select-none"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 font-semibold min-w-0">
            <span className="text-2xl filter drop-shadow-sm">
              {persona.icon}
            </span>
            <span className="truncate text-sm">{persona.role}</span>
          </div>

          {/* Neutrality Score Badge (University Metric) */}
          <div
            className={cn(
              "text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase tracking-tight flex items-center gap-1.5",
              getNeutralityColor(persona.metrics.neutrality_index)
            )}
          >
            <Scale className="w-3 h-3" />
            N-Index: {persona.metrics.neutrality_index.toFixed(2)}
          </div>
        </div>

        {/* Toggle Indicator */}
        <div className="flex items-center justify-between text-xs opacity-60 mt-1">
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3" />
            View Analysis & Bias Metrics
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </div>
      </div>

      {/* Card Body */}
      {isOpen && (
        <div className="px-4 pb-4 animate-in slide-in-from-top-1 fade-in duration-200">
          {/* 1. The Bias Spectrum Visualization */}
          <div className="mb-5 p-3 rounded-lg bg-neutral-50 border border-neutral-100">
            <div className="font-bold opacity-70 text-[10px] uppercase tracking-wider mb-1 text-neutral-500">
              Bias Vector Projection
            </div>
            <BiasSpectrum
              score={persona.metrics.bias_score}
              icon={persona.icon}
            />
            <div className="mt-2 text-[10px] text-right text-neutral-400 font-mono">
              Raw Bias Score: {persona.metrics.bias_score.toFixed(3)}
            </div>
          </div>

          <div className="h-px w-full bg-black/5 mb-4" />

          {/* 2. Content */}
          <div className="text-sm opacity-90 leading-relaxed overflow-hidden text-neutral-700">
            {parseMessageContent(contentString, (filename, i) => (
              <ArtifactViewer
                key={`${persona.role}-${runId}-${filename}-${i}`}
                type={filename.includes("heat") ? "heatmap" : "bar"}
                figureData={{
                  filename,
                  runId,
                  sessId: sessionId,
                  explanation: filename,
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// --- Main Component: Grid Container ---
export const PersonaGrid = ({
  perspectives,
  runId,
  sessionId,
}: {
  perspectives: AgentEvaluationResult[];
  runId: string | undefined;
  sessionId: string | undefined;
}) => {
  // Global toggle for the entire section
  const [isSectionExpanded, setIsSectionExpanded] = useState(true);

  const cardStyles = [
    "bg-blue-50/50 border-blue-100 text-blue-900",
    "bg-emerald-50/50 border-emerald-100 text-emerald-900",
    "bg-rose-50/50 border-rose-100 text-rose-900",
    "bg-amber-50/50 border-amber-100 text-amber-900",
    "bg-violet-50/50 border-violet-100 text-violet-900",
  ];

  if (!perspectives?.length) return null;

  return (
    <div className="mb-4 w-full rounded-xl border border-neutral-200 bg-white overflow-hidden shadow-sm">
      {/* Global Header */}
      <button
        onClick={() => setIsSectionExpanded(!isSectionExpanded)}
        className="w-full flex items-center justify-between p-3 px-4 bg-neutral-50/80 hover:bg-neutral-100 transition-colors"
      >
        <div className="flex items-center gap-2 text-xs font-semibold text-neutral-600 uppercase tracking-wide">
          <Users className="w-4 h-4 text-indigo-500" />
          {perspectives.length} Agent Perspectives
        </div>
        {isSectionExpanded ? (
          <ChevronDown className="w-4 h-4 text-neutral-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-neutral-400" />
        )}
      </button>

      {/* Grid Area */}
      {isSectionExpanded && (
        <div className="p-4 bg-white grid grid-cols-1 md:grid-cols-2 gap-3 animate-in slide-in-from-top-2 duration-200">
          {perspectives.map((persona, idx) => (
            <PersonaCard
              key={`${persona.role}-${idx}`}
              persona={persona}
              style={cardStyles[idx % cardStyles.length]}
              runId={runId}
              sessionId={sessionId}
            />
          ))}
        </div>
      )}
    </div>
  );
};
