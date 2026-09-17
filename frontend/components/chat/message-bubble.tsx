import { useMemo } from "react";
import { Paperclip, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Message, Session } from "@/lib/chat-utils";
import { parseMessageContent } from "@/utils/messageParser";
import { PersonaGrid } from "./persona-grid";
import { ArtifactViewer } from "./artifact-viewer";

export const MessageBubble = ({
  message,
  session,
}: {
  message: Message;
  session: Session;
}) => {
  const isUser = message.role === "user";

  const renderContent = useMemo(() => {
    if (isUser)
      return (
        <p className="text-white whitespace-pre-wrap">{message.content}</p>
      );

    return (
      <div className="flex flex-col w-full text-neutral-900 gap-4">
        {/* 1. Agent Perspectives */}
        {message.perspectives && message.perspectives.length > 0 && (
          <PersonaGrid
            key={`${message.id}-${message.runId}-${message.role}`}
            perspectives={message.perspectives}
            runId={message.runId}
            sessionId={session.id}
          />
        )}

        {/* 2. Main Report */}
        {message.content && (
          <div className="bg-white p-5 rounded-xl border border-neutral-200 shadow-sm">
            <div className="mb-4 text-xs font-semibold text-neutral-400 uppercase tracking-wider flex items-center gap-2 pb-2 border-b border-neutral-100">
              <BookOpen className="w-3.5 h-3.5" /> Consolidated Report
            </div>
            {/* Using prose to style generated markdown automatically */}
            <div className="prose prose-neutral prose-sm max-w-none text-neutral-700">
              {parseMessageContent(message.content, (filename, i) => (
                <ArtifactViewer
                  key={`Neutral-${message.id}-${filename}-${i}`}
                  type={filename.includes("heat") ? "heatmap" : "bar"}
                  figureData={{
                    filename,
                    runId: message.runId,
                    sessId: session.id,
                    explanation: filename,
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }, [message, session.id, isUser]);

  return (
    <div
      className={cn(
        "flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[85%] rounded-2xl p-4 shadow-sm",
          isUser
            ? "bg-indigo-600 text-white rounded-br-none"
            : "bg-transparent pl-0 shadow-none"
        )}
      >
        {renderContent}

        {/* File Attachments (User Side) */}
        {message.fileNames && message.fileNames.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {message.fileNames.map((f) => (
              <Badge
                key={f}
                variant="outline"
                className={cn(
                  "font-normal",
                  isUser
                    ? "border-white/20 text-indigo-100"
                    : "border-neutral-200"
                )}
              >
                <Paperclip className="h-3 w-3 mr-1.5" /> {f}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
