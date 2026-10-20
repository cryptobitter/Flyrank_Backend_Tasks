"use client";

import React, { useRef } from "react";
import {
  Plus,
  Play,
  RotateCcw,
  Save,
  Download,
  Upload,
  Brain,
  Flag,
  Sparkles,
  Layers,
} from "lucide-react";
import { DEFAULT_WORKFLOWS } from "@/lib/default-workflows";

interface WorkflowToolbarProps {
  onAddDecisionNode: () => void;
  onAddTerminalNode: () => void;
  onOpenRunModal: () => void;
  onResetGraph: () => void;
  onSaveGraph: () => void;
  onExportJson: () => void;
  onImportJson: (json: string) => void;
  onSelectPreset: (presetId: string) => void;
  isRunning: boolean;
}

export function WorkflowToolbar({
  onAddDecisionNode,
  onAddTerminalNode,
  onOpenRunModal,
  onResetGraph,
  onSaveGraph,
  onExportJson,
  onImportJson,
  onSelectPreset,
  isRunning,
}: WorkflowToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        onImportJson(content);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950 px-4 py-2.5 text-slate-100 z-10">
      {/* Brand & Preset Selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-md shadow-blue-500/30">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                AI Decision Flow
              </h1>
              <span className="rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-blue-400 border border-blue-500/20">
                React Flow + Inngest
              </span>
            </div>
            <p className="text-[10px] text-slate-400">Binary YES/NO LLM Branching Engine</p>
          </div>
        </div>

        {/* Preset Selector */}
        <div className="hidden md:flex items-center gap-1.5 pl-3 border-l border-slate-800 text-xs">
          <Layers className="h-3.5 w-3.5 text-slate-400" />
          <select
            onChange={(e) => onSelectPreset(e.target.value)}
            defaultValue="preset-support-sales"
            className="rounded-md bg-slate-900 border border-slate-700 px-2.5 py-1 text-xs text-slate-200 outline-none hover:border-slate-600 transition-colors cursor-pointer"
          >
            {DEFAULT_WORKFLOWS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-2">
        {/* Node Creation Buttons */}
        <button
          onClick={onAddDecisionNode}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-blue-500 hover:text-blue-400 transition-colors shadow-sm"
        >
          <Brain className="h-3.5 w-3.5 text-blue-400" />
          <span>Add Decision</span>
        </button>

        <button
          onClick={onAddTerminalNode}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-emerald-500 hover:text-emerald-400 transition-colors shadow-sm"
        >
          <Flag className="h-3.5 w-3.5 text-emerald-400" />
          <span>Add Outcome</span>
        </button>

        <div className="h-4 w-[1px] bg-slate-800 mx-1 hidden sm:block" />

        {/* Graph Storage & Export */}
        <button
          onClick={onSaveGraph}
          className="rounded-lg border border-slate-800 bg-slate-900/80 p-1.5 text-slate-400 hover:text-slate-100 hover:border-slate-700 transition-colors"
          title="Save to local storage"
        >
          <Save className="h-4 w-4" />
        </button>

        <button
          onClick={onExportJson}
          className="rounded-lg border border-slate-800 bg-slate-900/80 p-1.5 text-slate-400 hover:text-slate-100 hover:border-slate-700 transition-colors"
          title="Export JSON workflow"
        >
          <Download className="h-4 w-4" />
        </button>

        <button
          onClick={() => fileInputRef.current?.click()}
          className="rounded-lg border border-slate-800 bg-slate-900/80 p-1.5 text-slate-400 hover:text-slate-100 hover:border-slate-700 transition-colors"
          title="Import JSON workflow"
        >
          <Upload className="h-4 w-4" />
        </button>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".json"
          className="hidden"
        />

        <button
          onClick={onResetGraph}
          className="rounded-lg border border-slate-800 bg-slate-900/80 p-1.5 text-slate-400 hover:text-rose-400 hover:border-rose-900 transition-colors"
          title="Reset graph to preset default"
        >
          <RotateCcw className="h-4 w-4" />
        </button>

        {/* Primary Run Button */}
        <button
          onClick={onOpenRunModal}
          disabled={isRunning}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white shadow-lg shadow-emerald-600/25 hover:bg-emerald-500 transition-all disabled:opacity-50 ml-1.5"
        >
          <Play className="h-3.5 w-3.5 fill-current" />
          <span>{isRunning ? "Running..." : "Run Flow"}</span>
        </button>
      </div>
    </header>
  );
}
