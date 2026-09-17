"use client";

import { useState, type FC } from "react";
import { Button } from "@/components/ui/button";
import { Loader2, Settings } from "lucide-react"; // Import Settings Icon
import { NoSessionState } from "./no-session-state";
import { ChatPanel } from "./chat-panel";
import { Session, generateMessageId, EXAMPLE_SESSIONS } from "@/lib/chat-utils";
import { SettingsDialog } from "@/components/settings-dialog"; // Import the new dialog

// =================================================================
// Main Layout Component
// =================================================================
export function ChatLayout() {
  const [sessions, setSessions] = useState<Session[]>(EXAMPLE_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [autoConnectId, setAutoConnectId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // NEW: State for Settings Dialog
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  // ... (Keep your addNewSession logic here) ...

  const handleStartSession = async (prompt: string, files: File[]) => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("prompt", prompt);
      files.forEach((f) => formData.append("files", f));

      const response = await fetch("/api/process", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Failed to initialize session");

      const data = await response.json();
      const newSessionId = data.session_id;

      const newSession: Session = {
        id: newSessionId,
        title: "report-assist Analyst",
        messages: [
          {
            id: generateMessageId(),
            role: "user",
            content: prompt,
            fileNames: files.map((f) => f.name),
          },
        ],
      };

      setSessions((prev) => [...prev, newSession]);
      setActiveSessionId(newSessionId);
      setAutoConnectId(newSessionId);
    } catch (error) {
      console.error("Initialization failed:", error);
      alert("Failed to start session. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSessionUpdate = (updatedSession: Session) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === updatedSession.id ? updatedSession : s))
    );
  };

  if (isLoading) {
    return (
      <div className="h-dvh flex items-center justify-center bg-neutral-50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-neutral-500 font-medium">
            Initializing Workspace...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-dvh overflow-hidden relative bg-neutral-50/30">
      {/* 1. Global Settings Trigger (Top Right) */}
      <div className="fixed top-4 right-4 z-50">
        <Button
          variant="outline"
          size="icon"
          className="bg-white/80 backdrop-blur-md shadow-sm hover:bg-white"
          onClick={() => setIsSettingsOpen(true)}
        >
          <Settings className="h-5 w-5 text-neutral-600" />
        </Button>
      </div>

      {/* 2. Settings Modal */}
      <SettingsDialog open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />

      {/* 3. Main Content */}
      <div className="h-full w-full">
        {activeSession ? (
          <ChatPanel
            key={activeSession.id}
            session={activeSession}
            onUpdateSession={handleSessionUpdate}
            shouldAutoConnect={activeSession.id === autoConnectId}
          />
        ) : (
          <NoSessionState onStart={handleStartSession} />
        )}
      </div>
    </div>
  );
}
