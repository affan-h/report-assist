"use-client";

import { useRef, useEffect, type FC } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStream } from "@/hooks/use-chat-stream";
import { generateMessageId, Session, Message } from "@/lib/chat-utils";
import { ChatInput } from "./chat-input";
import { MessageBubble } from "./message-bubble";
import { StreamingBubble } from "./streaming-bubble";
import { ChatHeader } from "./header";

interface ChatPanelProps {
  session: Session;
  onUpdateSession: (updatedSession: Session) => void;
  shouldAutoConnect?: boolean;
}

export const ChatPanel: FC<ChatPanelProps> = ({
  session,
  onUpdateSession,
  shouldAutoConnect = false,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Custom Hook for Streaming
  const { isStreaming, loadingStatus, connectToStream } = useChatStream(
    session,
    onUpdateSession
  );

  // Auto-Connect Effect
  useEffect(() => {
    if (shouldAutoConnect && session.id) connectToStream(session.id);
  }, [session.id, shouldAutoConnect, connectToStream]);

  // Auto-Scroll Effect
  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
  }, [session.messages, loadingStatus]);

  // Handle Sending
  const handleSendMessage = async (prompt: string, files: File[]) => {
    // 1. Optimistic Update
    const userMsg: Message = {
      id: generateMessageId(),
      role: "user",
      content: prompt,
      fileNames: files.map((f) => f.name),
    };
    onUpdateSession({ ...session, messages: [...session.messages, userMsg] });

    // 2. API Call
    const formData = new FormData();
    formData.append("prompt", prompt);
    formData.append("session_id", session.id);
    formData.append("analyze_only", "true");
    files.forEach((f) => formData.append("files", f));

    try {
      const res = await fetch("/api/process", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("API Request Failed");

      // 3. Connect Stream
      connectToStream(session.id);
    } catch (error) {
      console.error(error);
      const errorMsg: Message = {
        id: generateMessageId(),
        role: "bot",
        content:
          "I encountered an error processing your request. Please try again.",
      };
      onUpdateSession({
        ...session,
        messages: [...session.messages, userMsg, errorMsg],
      });
    }
  };

  return (
    <div className="relative flex flex-col h-full w-full bg-neutral-50/30">
      <ChatHeader session={session} />

      {/* Messages Area */}
      <ScrollArea className="flex-1 h-full py-4">
        <div className="flex flex-col gap-6 p-4 py-16 max-w-4xl mx-auto">
          {session.messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} session={session} />
          ))}

          <StreamingBubble
            loadingStatus={loadingStatus}
            graphState={session.graphState}
          />

          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <ChatInput isDisabled={isStreaming} onSend={handleSendMessage} />
    </div>
  );
};
