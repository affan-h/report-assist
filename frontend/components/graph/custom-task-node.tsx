import { memo } from "react";
import { Handle, Position, NodeProps, Node } from "@xyflow/react";
import {
  CheckCircle2,
  Circle,
  Loader2,
  Clock,
  CircleIcon,
  Check,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Define the data we expect for each node
export type TaskNodeData = {
  label: string;
  status: "pending" | "running" | "success" | "error";
  subSteps: { id: number; desc: string }[];
  description: string;
  activeStepId: number | null;
};

export type AppNode = Node<TaskNodeData>;

export const CustomTaskNode = memo(({ data }: NodeProps<AppNode>) => {
  const isRunning = data.status === "running";
  const isSuccess = data.status === "success";
  const isError = data.status === "error";
  const isPending = data.status === "pending";

  return (
    <div className="relative flex flex-col items-center justify-center w-20">
      {/* 2. THE CIRCLE NODE */}
      <div
        className={cn(
          "w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all duration-500 z-10 bg-white",
          // Status Styles
          isPending && "border-neutral-300 text-neutral-300",
          isRunning &&
            "border-blue-500 text-blue-600 shadow-[0_0_20px_rgba(59,130,246,0.5)] scale-110",
          isSuccess && "border-emerald-500 bg-emerald-50 text-emerald-600",
          isError && "border-red-500 bg-red-50 text-red-600"
        )}
      >
        {/* Icon inside the circle */}
        {isPending && <CircleIcon className="w-5 h-5 fill-neutral-100" />}
        {isRunning && <Loader2 className="w-6 h-6 animate-spin" />}
        {isSuccess && <Check className="w-6 h-6 stroke-[3]" />}
        {isError && <X className="w-6 h-6 stroke-[3]" />}
      </div>

      {/* 3. PULSING RING (Only when running) */}
      {isRunning && (
        <span className="absolute w-12 h-12 rounded-full border-4 border-blue-400 opacity-20 animate-ping top-0" />
      )}

      {/* 4. LABEL (Below the circle) */}
      <div
        className={cn(
          "absolute -bottom-8 w-32 text-center text-[10px] font-medium leading-tight px-1 py-0.5 rounded-md transition-colors",
          isRunning
            ? "text-blue-700 bg-blue-50/80 backdrop-blur-sm"
            : "text-neutral-500"
        )}
      >
        {data.label.replace(/_/g, " ")} {/* Clean up label text */}
      </div>

      {/* 5. CONNECTION HANDLES (Invisible) */}
      {/* Target (Input) on Top or Left? Left/Right usually looks better for timelines */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-transparent !border-0"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-transparent !border-0"
      />
    </div>
  );
});

CustomTaskNode.displayName = "CustomTaskNode";
