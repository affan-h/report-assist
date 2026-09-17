"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import {
  Loader2,
  Save,
  Plus,
  Trash2,
  UserCog,
  Users,
  Settings2,
  CircuitBoard,
} from "lucide-react";
import {
  AppSettings,
  DEFAULT_SETTINGS,
  PersonaConfig,
} from "@/lib/settings-types";
import { Switch } from "./ui/switch";
import { NullableNumberInput } from "@/components/ui/nullable-number-input";

const NumberInput = ({
  value,
  onChange,
  ...props
}: {
  value: number | null;
  onChange: (val: number | null) => void;
  className?: string;
  placeholder?: string;
}) => (
  <Input
    type="number"
    {...props}
    value={value === null ? "" : value}
    onChange={(e) => {
      const val = e.target.value;
      onChange(val === "" ? null : Number(val));
    }}
  />
);

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setLoading(true);
      fetch("/api/settings")
        .then((res) => res.json())
        .then((data) => setSettings(data))
        .catch((err) => console.error(err))
        .finally(() => setLoading(false));
    }
  }, [open]);

  // --- Handlers ---
  const handlePromptChange = (agent: string, key: string, value: string) => {
    setSettings((prev) => ({
      ...prev,
      prompts: {
        ...prev.prompts,
        [agent]: { ...prev.prompts[agent], [key]: value },
      },
    }));
  };

  const handlePersonaChange = (
    index: number,
    field: keyof PersonaConfig,
    value: string,
  ) => {
    const updatedPersonas = [...settings.personas];
    updatedPersonas[index] = { ...updatedPersonas[index], [field]: value };
    setSettings((prev) => ({ ...prev, personas: updatedPersonas }));
  };

  const addPersona = () => {
    setSettings((prev) => ({
      ...prev,
      personas: [
        ...prev.personas,
        { role: "New Agent", icon: "🤖", bias_instruction: "" },
      ],
    }));
  };

  const removePersona = (index: number) => {
    setSettings((prev) => ({
      ...prev,
      personas: prev.personas.filter((_, i) => i !== index),
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      onOpenChange(false);
    } catch (e) {
      alert("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleLLMChange = (
    key: keyof AppSettings["llm_config"],
    value: any,
  ) => {
    setSettings((prev) => ({
      ...prev,
      llm_config: { ...prev.llm_config, [key]: value },
    }));
  };

  const handleGraphChange = (
    key: keyof AppSettings["graph_config"],
    value: number,
  ) => {
    setSettings((prev) => ({
      ...prev,
      graph_config: { ...prev.graph_config, [key]: value },
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[85vh] flex flex-col p-0 overflow-hidden">
        {/* Header */}
        <DialogHeader className="px-6 py-4 border-b bg-neutral-50/50">
          <DialogTitle>Workflow Configuration</DialogTitle>
          <DialogDescription>
            Manage Agent Personas and System Prompts
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : (
          /* Main Tabs: Personas vs Prompts */
          <Tabs
            defaultValue="personas"
            className="flex-1 flex flex-col overflow-hidden"
          >
            <div className="px-6 pt-4">
              <TabsList className="grid w-full grid-cols-3">
                {/* 1. Main Config Tab */}
                <TabsTrigger value="config" className="gap-2">
                  <Settings2 className="h-4 w-4" /> Model & Graph
                </TabsTrigger>
                {/* 2. Personas Tab */}
                <TabsTrigger value="personas" className="gap-2">
                  <Users className="h-4 w-4" /> Personas
                </TabsTrigger>
                {/* 3. Prompts Tab */}
                <TabsTrigger value="prompts" className="gap-2">
                  <UserCog className="h-4 w-4" /> System Prompts
                </TabsTrigger>
              </TabsList>
            </div>

            {/* --- TAB 1: PERSONAS --- */}
            <TabsContent
              value="personas"
              className="flex-1 overflow-y-auto px-6 py-4 space-y-4"
            >
              <div className="flex justify-end mb-2">
                <Button
                  size="sm"
                  onClick={addPersona}
                  className="gap-2 bg-indigo-600 hover:bg-indigo-700"
                >
                  <Plus className="h-4 w-4" /> Add Persona
                </Button>
              </div>

              <div className="space-y-3">
                {settings.personas.map((persona, idx) => (
                  <div
                    key={idx}
                    className="flex gap-4 p-4 border rounded-xl bg-white shadow-sm hover:shadow-md transition-shadow items-start group"
                  >
                    <div className="flex flex-col gap-2 w-16 text-center">
                      <Label className="text-[10px] text-neutral-400 uppercase font-bold">
                        Icon
                      </Label>
                      <Input
                        className="text-center text-2xl h-12 p-0 bg-neutral-50"
                        value={persona.icon}
                        onChange={(e) =>
                          handlePersonaChange(idx, "icon", e.target.value)
                        }
                      />
                    </div>

                    <div className="flex-1 space-y-3">
                      <div className="grid grid-cols-3 gap-4">
                        <div className="col-span-1 space-y-1">
                          <Label className="text-[10px] text-neutral-400 uppercase font-bold">
                            Role Name
                          </Label>
                          <Input
                            value={persona.role}
                            onChange={(e) =>
                              handlePersonaChange(idx, "role", e.target.value)
                            }
                            className="font-medium bg-neutral-50"
                          />
                        </div>
                        <div className="col-span-2 space-y-1">
                          <Label className="text-[10px] text-neutral-400 uppercase font-bold">
                            Bias Instruction
                          </Label>
                          <Input
                            value={persona.bias_instruction}
                            onChange={(e) =>
                              handlePersonaChange(
                                idx,
                                "bias_instruction",
                                e.target.value,
                              )
                            }
                            className="bg-neutral-50 text-sm"
                            placeholder="e.g. Focus on risks..."
                          />
                        </div>
                      </div>
                    </div>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-neutral-300 hover:text-red-500 hover:bg-red-50"
                      onClick={() => removePersona(idx)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </TabsContent>

            {/* --- TAB 2: SYSTEM PROMPTS (NESTED TABS) --- */}
            <TabsContent
              value="prompts"
              className="flex-1 flex flex-col overflow-hidden px-6 pb-4"
            >
              <Tabs
                defaultValue={Object.keys(settings.prompts)[0] || "master"}
                className="flex-1 flex flex-col h-full"
              >
                {/* 1. Agent Selector Bar */}
                <div className="border-b mb-4">
                  <TabsList className="bg-transparent h-auto p-0 justify-start gap-6 rounded-none w-full overflow-x-auto">
                    {Object.keys(settings.prompts).map((agentKey) => (
                      <TabsTrigger
                        key={agentKey}
                        value={agentKey}
                        className="rounded-none border-b-2 border-transparent data-[state=active]:border-b-indigo-600 data-[state=active]:text-indigo-600 data-[state=active]:shadow-none px-2 py-3 capitalize font-medium text-neutral-500 hover:text-neutral-700 transition-colors"
                      >
                        {agentKey} Agent
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </div>

                {/* 2. Scrollable Editor Area */}
                <div className="flex-1 overflow-y-auto pr-2">
                  {Object.keys(settings.prompts).map((agentKey) => (
                    <TabsContent
                      key={agentKey}
                      value={agentKey}
                      className="space-y-6 mt-0"
                    >
                      {Object.entries(settings.prompts[agentKey]).map(
                        ([promptKey, promptValue]) => (
                          <div key={promptKey} className="space-y-2 group">
                            <Label className="flex items-center gap-2 text-xs font-mono text-neutral-500 uppercase tracking-wider group-focus-within:text-indigo-600 transition-colors">
                              {promptKey.replace(/_/g, " ")}
                            </Label>
                            <Textarea
                              className="font-mono text-xs min-h-[120px] leading-relaxed bg-neutral-50 border-neutral-200 focus:border-indigo-300 focus:ring-4 focus:ring-indigo-50/50 resize-y"
                              value={promptValue}
                              onChange={(e) =>
                                handlePromptChange(
                                  agentKey,
                                  promptKey,
                                  e.target.value,
                                )
                              }
                              spellCheck={false}
                            />
                          </div>
                        ),
                      )}
                    </TabsContent>
                  ))}
                </div>
              </Tabs>
            </TabsContent>

            {/* ========================================================= */}
            {/* TAB: MODEL & GRAPH CONFIG                                 */}
            {/* ========================================================= */}
            <TabsContent
              value="config"
              className="flex-1 overflow-y-auto px-6 py-6"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* LEFT COLUMN: LLM SETTINGS */}
                <div className="space-y-6">
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <CircuitBoard className="h-4 w-4 text-indigo-500" />
                    <h3 className="font-semibold text-sm uppercase tracking-wide text-neutral-600">
                      LLM Engine
                    </h3>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <Label className="text-xs font-medium text-neutral-500">
                        Model Name (Google Gemini)
                      </Label>
                      <Input
                        value={settings.llm_config.GEMINI_MODEL || settings.llm_config.OPENAI_MODEL || "gemini-2.5-flash"}
                        onChange={(e) => {
                          handleLLMChange("GEMINI_MODEL", e.target.value);
                          handleLLMChange("OPENAI_MODEL", e.target.value);
                        }}
                        placeholder="e.g. gemini-2.5-flash, gemini-2.0-flash"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <Label className="text-xs font-medium text-neutral-500">
                          Max Retries
                        </Label>
                        <NumberInput
                          value={settings.llm_config.LLM_MAX_RETRIES ?? settings.llm_config.MAX_RETRIES ?? 2}
                          onChange={(v) =>
                            handleLLMChange("LLM_MAX_RETRIES", v)
                          }
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label className="text-xs font-medium text-neutral-500">
                          Timeout (sec)
                        </Label>
                        <NumberInput
                          value={settings.llm_config.TIMEOUT}
                          onChange={(v) => handleLLMChange("TIMEOUT", v)}
                          placeholder="None"
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <Label className="text-xs font-medium text-neutral-500">
                        Max Completion Tokens
                      </Label>

                      <NullableNumberInput
                        value={settings.llm_config.MAX_COMPLETION_TOKENS}
                        onChange={(val) =>
                          handleLLMChange("MAX_COMPLETION_TOKENS", val)
                        }
                        placeholder="None (Unlimited)"
                      />
                      <p className="text-[10px] text-neutral-400">
                        Leave empty to set as None (unlimited).
                      </p>
                    </div>

                    <div className="space-y-3 pt-2">
                      <div className="flex justify-between">
                        <Label className="text-xs font-medium text-neutral-500">
                          Temperature: {settings.llm_config.TEMPERATURE}
                        </Label>
                      </div>
                      <Slider
                        defaultValue={[settings.llm_config.TEMPERATURE]}
                        max={1}
                        step={0.1}
                        onValueChange={(vals) =>
                          handleLLMChange("TEMPERATURE", vals[0])
                        }
                        className="py-2"
                      />
                    </div>

                    <div className="flex items-center justify-between border p-3 rounded-lg bg-neutral-50">
                      <Label className="text-sm font-medium">
                        Enable Caching
                      </Label>
                      <Switch
                        checked={settings.llm_config.CACHE}
                        onCheckedChange={(c) => handleLLMChange("CACHE", c)}
                      />
                    </div>
                  </div>
                </div>

                {/* RIGHT COLUMN: GRAPH SETTINGS */}
                <div className="space-y-6">
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <Settings2 className="h-4 w-4 text-emerald-500" />
                    <h3 className="font-semibold text-sm uppercase tracking-wide text-neutral-600">
                      Graph Generation
                    </h3>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <Label className="text-xs font-medium text-neutral-500">
                        Action Graph Retries
                      </Label>
                      <NumberInput
                        value={settings.graph_config.ACTION_GRAPH_MAX_RETRIES}
                        onChange={(v) =>
                          handleGraphChange("ACTION_GRAPH_MAX_RETRIES", v || 0)
                        }
                      />
                      <p className="text-[10px] text-neutral-400">
                        Attempt limit to regenerate the code for each Action
                        Node when fails to run code.
                      </p>
                    </div>

                    <div className="space-y-1.5">
                      <Label className="text-xs font-medium text-neutral-500">
                        Task Graph Retries
                      </Label>
                      <NumberInput
                        value={settings.graph_config.TASK_GRAPH_MAX_RETRIES}
                        onChange={(v) =>
                          handleGraphChange("TASK_GRAPH_MAX_RETRIES", v || 0)
                        }
                      />
                      <p className="text-[10px] text-neutral-400">
                        Attempts to regenerate the task graph if action graph
                        fails to run code within limit.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        )}

        {/* Footer */}
        <DialogFooter className="px-6 py-4 border-t bg-white">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || loading}
            className="min-w-[120px]"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
