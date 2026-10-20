"use client";

import React, { memo, useState } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { DecisionNodeData } from "@/types/workflow";
import { Brain, CheckCircle2, XCircle, Loader2, Edit3, Trash2, HelpCircle } from "lucide-react";

export const DecisionNode = memo(({ id, data, isConnectable }: NodeProps) => {
  const nodeData = data as unknown as DecisionNodeData;
  const [isEditing, setIsEditing] = useState(false);
  const [questionText, setQuestionText] = useState(nodeData.question || "");
  const [label, setLabel] = useState(nodeData.label || "Decision Step");

  const status = nodeData.status || "idle";
  const decision = nodeData.decision;

  const handleBlur = () => {
    setIsEditing(false);
    nodeData.question = questionText;
    nodeData.label = label;
  };

  return (
    <div
      className={`relative w-80 rounded-xl border bg-slate-900/95 p-4 shadow-2xl backdrop-blur-md transition-all duration-300 ${
        status === "running"
          ? "border-blue-500 shadow-blue-500/30 animate-pulse-glow"
          : decision === "YES"
          ? "border-emerald-500/80 shadow-emerald-500/20"
          : decision === "NO"
          ? "border-rose-500/80 shadow-rose-500/20"
          : "border-slate-700 hover:border-slate-500"
      }`}
    >
      {/* Input Handle (Top) */}
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="!h-3.5 !w-3.5 !border-2 !border-slate-900 !bg-slate-400 hover:!bg-blue-400 transition-colors"
      />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Brain className="h-4 w-4" />
          </div>
          {isEditing ? (
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              onBlur={handleBlur}
              className="bg-slate-800 px-1.5 py-0.5 text-xs font-semibold text-slate-100 rounded border border-slate-600 outline-none"
              autoFocus
            />
          ) : (
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              {label}
            </span>
          )}
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-1.5">
          {status === "running" && (
            <span className="flex items-center gap-1 rounded-full bg-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-400 border border-blue-500/30">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              Thinking...
            </span>
          )}
          {status === "completed" && decision && (
            <span
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold border ${
                decision === "YES"
                  ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                  : "bg-rose-500/20 text-rose-400 border-rose-500/30"
              }`}
            >
              {decision === "YES" ? (
                <CheckCircle2 className="h-3 w-3" />
              ) : (
                <XCircle className="h-3 w-3" />
              )}
              {decision}
            </span>
          )}
          {status === "idle" && (
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="text-slate-500 hover:text-slate-300 transition-colors p-1"
              title="Edit prompt"
            >
              <Edit3 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Decision Question Prompt */}
      <div className="mb-3">
        <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">
          AI Decision Prompt
        </label>
        {isEditing ? (
          <textarea
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            onBlur={handleBlur}
            rows={3}
            className="w-full resize-none rounded-md bg-slate-950 p-2 text-xs text-slate-100 border border-slate-700 outline-none focus:border-blue-500"
            placeholder="Type yes/no question for the LLM..."
          />
        ) : (
          <div
            onClick={() => setIsEditing(true)}
            className="cursor-pointer rounded-lg bg-slate-950/80 p-2.5 text-xs text-slate-200 border border-slate-800/80 hover:border-slate-700 transition-all font-mono leading-relaxed"
          >
            "{questionText || "Click to add a YES/NO question..."}"
          </div>
        )}
      </div>

      {/* Reasoning (if decided) */}
      {nodeData.reasoning && (
        <div className="mb-3 rounded bg-slate-950/60 p-2 border border-slate-800/50 text-[11px] text-slate-400">
          <span className="font-semibold text-slate-300">Rationale: </span>
          {nodeData.reasoning}
        </div>
      )}

      {/* Binary Output Ports (YES & NO Handles) */}
      <div className="relative mt-4 pt-3 border-t border-slate-800 flex justify-between items-center text-xs">
        {/* YES Output Port */}
        <div className="flex items-center gap-1.5 text-emerald-400 font-bold tracking-wider">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500" />
          YES
          <Handle
            type="source"
            position={Position.Bottom}
            id="yes"
            isConnectable={isConnectable}
            className="!left-[25%] !bottom-[-6px] !h-3.5 !w-3.5 !border-2 !border-slate-900 !bg-emerald-500 hover:scale-125 transition-transform"
          />
        </div>

        {/* NO Output Port */}
        <div className="flex items-center gap-1.5 text-rose-400 font-bold tracking-wider">
          NO
          <span className="inline-block h-2 w-2 rounded-full bg-rose-500 shadow-sm shadow-rose-500" />
          <Handle
            type="source"
            position={Position.Bottom}
            id="no"
            isConnectable={isConnectable}
            className="!left-[75%] !bottom-[-6px] !h-3.5 !w-3.5 !border-2 !border-slate-900 !bg-rose-500 hover:scale-125 transition-transform"
          />
        </div>
      </div>
    </div>
  );
});

DecisionNode.displayName = "DecisionNode";
