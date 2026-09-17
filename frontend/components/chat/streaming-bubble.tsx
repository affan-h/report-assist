import { useMemo } from "react";
import { Loader2, Zap } from "lucide-react";
import { TaskGraphView } from "../graph/task-graph-view"; // Ensure correct path
import { GraphState } from "@/lib/chat-utils";
import { cn } from "@/lib/utils";

interface StreamingBubbleProps {
  loadingStatus: string | null;
  graphState: GraphState | null | undefined;
}

export const StreamingBubble = ({
  loadingStatus,
  graphState,
}: StreamingBubbleProps) => {
  // Memoize structure to prevent graph re-layout on every status text update
  const graphStructure = useMemo(() => {
    if (!graphState) return null;
    return { nodes: graphState.nodes, edges: graphState.edges };
  }, [graphState]);

  return (
    <div className="flex gap-3 justify-start w-full max-w-3xl animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Bot Avatar */}
      <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 shadow-sm mt-1">
        <Zap className="w-4 h-4 text-white fill-white" />
      </div>

      <div className="flex flex-col gap-2 w-full max-w-[85%]">
        {/* THE UNIFIED BUBBLE */}
        <div className="bg-white border border-neutral-200 rounded-2xl rounded-tl-none shadow-sm overflow-hidden transition-all duration-500 ease-in-out">
          {/* Header: The Loading Status */}
          {
            <div className="p-4 flex items-center gap-3 bg-white/50 backdrop-blur-sm z-10 relative">
              <div className="relative flex items-center justify-center">
                <div className="absolute inset-0 bg-indigo-100 rounded-full animate-ping opacity-75" />
                {loadingStatus && (
                  <Loader2 className="h-4 w-4 text-indigo-600 animate-spin relative z-10" />
                )}
              </div>
              <span
                className={cn(
                  "text-sm font-medium text-neutral-600",
                  loadingStatus && "animate-pulse"
                )}
              >
                {loadingStatus ? loadingStatus : "Finalized Graph"}
              </span>
            </div>
          }

          {/* Body: The Graph (Animated Expansion) */}
          {/* We use grid-template-rows for a smooth height animation without hardcoding pixels */}
          <div
            className={`
              grid transition-[grid-template-rows, opacity] duration-700 ease-in-out
              ${
                graphState
                  ? "grid-rows-[1fr] opacity-100 border-t border-neutral-100"
                  : "grid-rows-[0fr] opacity-0"
              }
            `}
          >
            <div className="overflow-hidden min-h-0 bg-neutral-50/30">
              {graphStructure && graphState && (
                <div className="h-[400px] w-full p-2">
                  <TaskGraphView
                    initialData={graphStructure}
                    activeNodeId={graphState.activeNodeId}
                    activeStepId={graphState.activeStepId}
                    nodeStatuses={graphState.nodeStatuses}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Optional: Caption below bubble */}
        {graphState && (
          <p className="text-[10px] text-neutral-400 pl-2 animate-in fade-in delay-500">
            Live execution trace • {graphState.nodes.length} Steps
          </p>
        )}
      </div>
    </div>
  );
};
