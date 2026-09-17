import { useState, useRef, type FC } from "react";
import { Paperclip, Send, X } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ChatInputProps {
  isDisabled: boolean;
  onSend: (text: string, files: File[]) => void;
}

export const ChatInput: FC<ChatInputProps> = ({ isDisabled, onSend }) => {
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const MAX_FILES = 3;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      if (files.length + newFiles.length > MAX_FILES) {
        alert(`Maximum ${MAX_FILES} files allowed.`);
        return;
      }
      setFiles((prev) => [...prev, ...newFiles]);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = () => {
    if (!prompt.trim() && files.length === 0) return;
    onSend(prompt, files);
    setPrompt("");
    setFiles([]);
  };

  return (
    <div className="fixed bottom-4 left-0 right-0 px-4 w-full max-w-4xl mx-auto z-20">
      <div className="bg-white/80 backdrop-blur-xl border border-white/20 rounded-3xl shadow-lg ring-1 ring-black/5">
        <div className="relative p-2">
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="Ask specific questions or upload data..."
            className="pr-24 min-h-[56px] max-h-[200px] resize-none border-0 bg-transparent focus-visible:ring-0 text-base py-3 placeholder:text-neutral-400"
          />

          <div className="absolute top-1/2 -translate-y-1/2 right-3 flex items-center gap-1">
            <input
              type="file"
              multiple
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => fileInputRef.current?.click()}
              className="text-neutral-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-full h-9 w-9 transition-colors"
            >
              <Paperclip className="h-5 w-5" />
            </Button>
            <Button
              size="icon"
              disabled={isDisabled || (!prompt && files.length === 0)}
              onClick={handleSubmit}
              className="rounded-full h-9 w-9 bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-all disabled:opacity-50"
            >
              <Send className="h-4 w-4 text-white" />
            </Button>
          </div>
        </div>

        {files.length > 0 && (
          <div className="px-4 pb-3 flex flex-wrap gap-2 animate-in slide-in-from-bottom-2">
            {files.map((f, i) => (
              <Badge
                key={i}
                variant="secondary"
                className="pl-2 pr-1 py-1 gap-1 text-neutral-600 bg-neutral-100 border border-neutral-200 hover:bg-neutral-200"
              >
                <span className="truncate max-w-[120px]">{f.name}</span>
                <button
                  onClick={() =>
                    setFiles((prev) => prev.filter((_, idx) => idx !== i))
                  }
                  className="hover:bg-neutral-300 rounded-full p-0.5 transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
