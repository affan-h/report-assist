import { useState, useRef, useEffect, useCallback } from "react";
import { Session, GraphEdge, GraphNode } from "@/lib/chat-utils";
import { generateMessageId, API_URL } from "@/lib/chat-utils";
import { toast } from "sonner";

interface ProgressEvent {
  type: "progress";
  message: string;
}

interface ErrorEvent {
  type: "error";
  message: string;
}

interface ResponseEvent {
  type: "response";
  message: {
    run_id: string;
    text: string;
    perspectives: any[];
  };
}

export interface GraphInitEvent {
  type: "graph_init";
  message: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
}

export interface NodeUpdateEvent {
  type: "node_update";
  message: {
    node_id: string;
    status: "pending" | "running" | "success" | "error";
    active_sub_step: number | null;
    log?: string;
  };
}

export type StreamEvent =
  | ProgressEvent
  | ErrorEvent
  | ResponseEvent
  | GraphInitEvent
  | NodeUpdateEvent;

export const useChatStream = (
  session: Session,
  onUpdateSession: (s: Session) => void,
) => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string | null>(null);

  const sessionRef = useRef(session);
  const onUpdateSessionRef = useRef(onUpdateSession);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    onUpdateSessionRef.current = onUpdateSession;
  }, [onUpdateSession]);

  const connectToStream = useCallback((sessionId: string) => {
    setIsStreaming((prev) => {
      if (prev) return true;
      return true;
    });

    console.log(`[Stream] Connecting: ${sessionId}`);

    const eventSource = new EventSource(
      `${API_URL}/api/v1/process/events/${sessionId}`,
    );

    eventSource.onmessage = (event) => {
      if (event.data === "[DONE]") {
        eventSource.close();
        setIsStreaming(false);
        setLoadingStatus(null);
        return;
      }

      let data: StreamEvent;
      try {
        data = JSON.parse(event.data) as StreamEvent;
      } catch (e) {
        return;
      }

      const currentSession = sessionRef.current;
      const updateSession = onUpdateSessionRef.current;

      if (data.type === "error") {
        toast.error(data.message);
        setLoadingStatus(null);
        return;
      }

      if (data.type === "progress") {
        setLoadingStatus(data.message);
        return;
      }

      if (data.type === "graph_init") {
        const payload = (data as any).data || (data as any).message;

        console.log(payload);
        if (!payload) return;

        updateSession({
          ...currentSession,
          graphState: {
            nodes: payload.nodes,
            edges: payload.edges,
            activeNodeId: null,
            activeStepId: null,
            nodeStatuses: {},
          },
        });
        return;
      }

      if (data.type === "node_update") {
        const update = (data as any).data || (data as any).message;
        if (!currentSession.graphState || !update) return;

        const newStatuses = {
          ...currentSession.graphState.nodeStatuses,
          [update.node_id]: update.status,
        };

        updateSession({
          ...currentSession,
          graphState: {
            ...currentSession.graphState,
            activeNodeId: update.node_id,
            activeStepId: update.active_sub_step,
            nodeStatuses: newStatuses,
          },
        });
        return;
      }

      if (data.type === "response") {
        setLoadingStatus(null);
        const payload = data.message;

        updateSession({
          ...currentSession,
          messages: [
            ...currentSession.messages,
            {
              id: generateMessageId(),
              role: "bot",
              runId: payload.run_id,
              content: payload.text,
              perspectives: payload.perspectives,
            },
          ],
        });
        return;
      }
    };

    eventSource.onerror = (err) => {
      console.error("SSE Connection Error", err);
      eventSource.close();
      setIsStreaming(false);
      setLoadingStatus(null);
    };

    return () => {
      eventSource.close();
      setIsStreaming(false);
    };
  }, []);

  return { isStreaming, loadingStatus, connectToStream };
};
