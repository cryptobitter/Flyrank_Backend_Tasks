"use client";

import React, { memo } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { TerminalNodeData } from "@/types/workflow";
import { Flag, ArrowRightCircle } from "lucide-react";

export const TerminalNode = memo(({ data, isConnectable }: NodeProps) => {
  const nodeData = data as unknown as TerminalNodeData;
  const status = nodeData.status || "idle";

  return (
    <div
      className={`relative w-64 rounded-xl border bg-slate-900/95 p-3.5 shadow-xl backdrop-blur-md transition-all duration-300 ${
        status === "completed"
          ? "border-emerald-500 shadow-emerald-500/20 bg-slate-900"
          : "border-slate-700/80 hover:border-slate-500"
      }`}
    >
      {/* Input Handle (Top) */}
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="!h-3.5 !w-3.5 !border-2 !border-slate-900 !bg-slate-400 hover:!bg-blue-400 transition-colors"
      />

      <div className="flex items-center gap-2 mb-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Flag className="h-3.5 w-3.5" />
        </div>
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-200">
          {nodeData.label || "Outcome Destination"}
        </span>
      </div>

      <div className="rounded bg-slate-950 p-2 text-xs font-medium text-slate-300 border border-slate-800 flex items-start gap-1.5">
        <ArrowRightCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
        <span>{nodeData.action || "Finalize flow execution"}</span>
      </div>
    </div>
  );
});

TerminalNode.displayName = "TerminalNode";
