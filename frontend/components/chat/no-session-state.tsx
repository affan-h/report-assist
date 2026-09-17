import { useState, useRef, type FC } from "react";
import {
  FileSpreadsheet,
  Sparkles,
  TrendingUp,
  X,
  Paperclip,
  ArrowRight,
  PieChart,
  TestTube2,
} from "lucide-react";
import { Card } from "@/components/ui/card"; // Assuming you have shadcn Card
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface NoSessionStateProps {
  onStart: (prompt: string, files: File[]) => void;
}

export const NoSessionState: FC<NoSessionStateProps> = ({ onStart }) => {
  const [prompt, setPrompt] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  const handleSubmit = () => {
    if (!prompt.trim() && uploadedFiles.length === 0) return;
    onStart(prompt, uploadedFiles);
  };

  const handleSuggestionClick = async (
    promptText: string,
    demoFilePath?: string
  ) => {
    if (demoFilePath) {
      try {
        // 1. Fetch the file from the public directory
        // In Next.js/React, files in 'public' are served at the root '/'
        const response = await fetch(demoFilePath);

        if (!response.ok) {
          throw new Error(`Failed to fetch demo file: ${response.statusText}`);
        }

        // 2. Convert response to Blob
        const blob = await response.blob();

        // 3. Convert Blob to File object
        const filename = demoFilePath.split("/").pop() || "data.csv";
        const file = new File([blob], filename, { type: blob.type });

        // 4. Start analysis
        onStart(promptText, [file]);
      } catch (error) {
        console.error("Error loading demo file:", error);
      } finally {
      }
    } else {
      // Standard behavior (no file)
      onStart(promptText, []);
    }
  };

  const suggestions = [
    {
      icon: <TrendingUp className="h-5 w-5 text-blue-600" />,
      title: "Sales Trend Analysis",
      prompt:
        "Analyze the monthly sales trend from this dataset and identify seasonality.",
    },
    // {
    //   icon: <PieChart className="h-5 w-5 text-purple-600" />,
    //   title: "Customer Segmentation",
    //   prompt:
    //     "Segment customers based on purchasing behavior and suggest marketing strategies.",
    // },
    {
      icon: <FileSpreadsheet className="h-5 w-5 text-emerald-600" />,
      title: "Data Cleaning",
      prompt:
        "Check this file for missing values and anomalies, then summarize the columns.",
    },
    {
      icon: <TestTube2 className="h-5 w-5 text-orange-600" />,
      title: "Debug / Demo Mode",
      prompt: "Find the relationship between Silver and Bitcoin price.",
      demoFile: "/data.csv",
    },
  ];

  return (
    <div className="flex flex-col h-full w-full items-center justify-center p-8 bg-neutral-50/50">
      <div className="max-w-2xl w-full flex flex-col items-center space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        {/* Header Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-4 bg-white rounded-full shadow-sm mb-4">
            <Sparkles className="h-8 w-8 text-neutral-800" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight text-neutral-900">
            report-assist
          </h1>
          <p className="text-lg text-neutral-500 max-w-[600px]">
            Autonomous multi-agent data science and neutral interpretation platform.
            Upload your dataset to generate executable analysis and unbiased insights.
          </p>
        </div>

        {/* Main Input Section */}
        <div className="w-full relative bg-white rounded-2xl shadow-lg border border-neutral-200/60 p-2 transition-all focus-within:ring-2 focus-within:ring-neutral-200">
          <Textarea
            placeholder="Describe your data or ask a question..."
            className="w-full border-none shadow-none resize-none min-h-[80px] text-base p-4 focus-visible:ring-0 bg-transparent"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />

          {/* File Pills */}
          {uploadedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 px-4 pb-2">
              {uploadedFiles.map((f, i) => (
                <Badge key={i} variant="secondary" className="pl-2 pr-1 py-1">
                  <span className="truncate max-w-[150px]">{f.name}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-4 w-4 ml-2 hover:bg-neutral-200 rounded-full"
                    onClick={() => setUploadedFiles([])}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          )}

          <div className="flex justify-between items-center px-2 pb-2">
            <div className="flex gap-2">
              <input
                type="file"
                multiple
                ref={fileInputRef}
                className="hidden"
                onChange={handleFileChange}
              />
              <Button
                variant="ghost"
                size="sm"
                className="text-neutral-500 gap-2"
                onClick={() => fileInputRef.current?.click()}
              >
                <Paperclip className="h-4 w-4" />
                <span className="text-xs font-medium">Add Data</span>
              </Button>
            </div>

            <Button
              onClick={handleSubmit}
              disabled={!prompt && uploadedFiles.length === 0}
              className="bg-neutral-900 text-white hover:bg-neutral-800"
            >
              Start Analysis <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Starter Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full pt-4">
          {suggestions.map((item, idx) => (
            <Card
              key={idx}
              className="p-4 cursor-pointer hover:bg-white hover:shadow-md transition-all border-neutral-200/60 bg-white/40"
              onClick={() => handleSuggestionClick(item.prompt, item?.demoFile)}
            >
              <div className="flex flex-col gap-3">
                <div className="p-2 w-fit rounded-lg bg-neutral-100">
                  {item.icon}
                </div>
                <div>
                  <h3 className="font-semibold text-neutral-900 text-sm mb-1">
                    {item.title}
                  </h3>
                  <p className="text-xs text-neutral-500 line-clamp-2">
                    {item.prompt}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};
