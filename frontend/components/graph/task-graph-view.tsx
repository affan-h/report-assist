"use client";

import { useMemo, useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType,
  NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { AppNode, CustomTaskNode, TaskNodeData } from "./custom-task-node";
import { getLayoutedElements } from "./graph-layout";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

const nodeTypes: any = {
  task: CustomTaskNode,
};

interface TaskGraphProps {
  initialData: {
    nodes: any[];
    edges: any[];
  } | null;
  activeNodeId: string | null;
  activeStepId: number | null;
  nodeStatuses: Record<string, "pending" | "running" | "success" | "error">;
}

export function TaskGraphView({
  initialData,
  activeNodeId,
  activeStepId,
  nodeStatuses,
}: TaskGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<AppNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // 1. State for Hover Logic
  const [hoveredNodeData, setHoveredNodeData] = useState<TaskNodeData | null>(
    null
  );

  // 2. Initialize Graph
  useEffect(() => {
    if (!initialData) return;

    const rawNodes: AppNode[] = initialData.nodes.map((n) => ({
      id: n.id,
      type: "task",
      data: {
        label: n.label,
        status: "pending",
        description: n.description || "",
        subSteps: n.sub_steps || [],
        activeStepId: null,
      },
      position: { x: 0, y: 0 },
    }));

    const rawEdges: Edge[] = initialData.edges.map((e, i) => ({
      id: `e-${i}`,
      source: e.source,
      target: e.target,
      animated: true,
      style: { stroke: "#94a3b8", strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
    }));

    const { nodes: layoutNodes, edges: layoutEdges } = getLayoutedElements(
      rawNodes,
      rawEdges
    );

    setNodes(layoutNodes);
    setEdges(layoutEdges);
  }, [initialData, setNodes, setEdges]);

  // 3. Handle Real-time Updates
  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        const currentStatus = nodeStatuses[node.id] || node.data.status;
        const currentActiveStep =
          node.id === activeNodeId ? activeStepId : null;

        if (
          node.data.status === currentStatus &&
          node.data.activeStepId === currentActiveStep
        ) {
          return node;
        }

        return {
          ...node,
          data: {
            ...node.data,
            status: currentStatus,
            activeStepId: currentActiveStep,
          },
        };
      })
    );
  }, [activeNodeId, activeStepId, nodeStatuses, setNodes]);

  // 4. Hover Handlers
  const onNodeMouseEnter: NodeMouseHandler = (_, node) => {
    // Only show card if we have real data
    setHoveredNodeData(node.data as TaskNodeData);
  };

  const onNodeMouseLeave: NodeMouseHandler = () => {
    setHoveredNodeData(null);
  };

  if (!initialData) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-neutral-50 border border-dashed rounded-xl">
        <p className="text-neutral-400">Waiting for plan generation...</p>
      </div>
    );
  }

  return (
    <div className="relative h-[400px] w-full border rounded-xl overflow-hidden bg-neutral-50/50">
      {/* 5. The Detail Card Overlay (Absolute Positioned) */}
      {hoveredNodeData && (
        <div className="absolute top-4 right-4 z-50 w-80 animate-in fade-in slide-in-from-right-4 duration-200">
          <DetailCard data={hoveredNodeData} />
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        // --- KEY SETTINGS ---
        nodesDraggable={false} // Disable dragging
        nodesConnectable={false}
        onNodeMouseEnter={onNodeMouseEnter} // Start hover
        onNodeMouseLeave={onNodeMouseLeave} // End hover
        // --------------------

        fitView
        minZoom={0.5}
        maxZoom={1.5}
        attributionPosition="bottom-left"
      >
        <Background gap={20} size={1} color="#e5e5e5" />
        {/* <Controls /> */}
      </ReactFlow>
    </div>
  );
}

// Helper Component for the Card
function DetailCard({ data }: { data: TaskNodeData }) {
  const statusColors = {
    pending: "text-neutral-500 bg-neutral-100",
    running: "text-blue-600 bg-blue-100",
    success: "text-emerald-600 bg-emerald-100",
    error: "text-red-600 bg-red-100",
  };

  const StatusIcon = {
    pending: Circle,
    running: Loader2,
    success: CheckCircle2,
    error: XCircle,
  }[data.status];

  return (
    <Card className="shadow-xl border-neutral-200/80 backdrop-blur-sm bg-white/95">
      <CardHeader className="pb-3 border-b border-neutral-100">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold text-wrap">
            {data.label}
          </CardTitle>
          <Badge
            variant="secondary"
            className={`gap-1 ${statusColors[data.status]}`}
          >
            <StatusIcon
              className={`w-3 h-3 ${
                data.status === "running" ? "animate-spin" : ""
              }`}
            />
            <span className="capitalize">{data.status}</span>
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-4 max-h-[300px] overflow-y-auto">
        <div className="space-y-3">
          <p className="text-sm text-neutral-400 italic">{data.description}</p>
          {/* {data.subSteps.length > 0 ? (
            data.subSteps.map((step) => {
              const isDone =
                data.status === "success" ||
                (data.activeStepId !== null && step.id < data.activeStepId);
              const isActive = data.activeStepId === step.id;

              return (
                <div key={step.id} className="flex gap-3 text-sm group">
                  <div className="mt-1 shrink-0">
                    {isDone ? (
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    ) : isActive ? (
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                    ) : (
                      <div className="w-1.5 h-1.5 rounded-full bg-neutral-200 group-hover:bg-neutral-300 transition-colors" />
                    )}
                  </div>
                  <p
                    className={`leading-relaxed ${
                      isDone
                        ? "text-neutral-400 line-through"
                        : "text-neutral-700"
                    }`}
                  >
                    {step.desc}
                  </p>
                </div>
              );
            })
          ) : (
            <p className="text-sm text-neutral-400 italic">
              No specific sub-tasks defined.
            </p>
          )} */}
        </div>
      </CardContent>
    </Card>
  );
}
