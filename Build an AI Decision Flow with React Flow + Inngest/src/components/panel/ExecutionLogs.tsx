"use client";

import React, { useState } from "react";
import { ExecutionLog } from "@/types/workflow";
import { Terminal, CheckCircle2, XCircle, AlertCircle, Info, ChevronRight, Trash2 } from "lucide-react";

interface ExecutionLogsProps {
  logs: ExecutionLog[];
  onClear: () => void;
  isRunning: boolean;
}

export function ExecutionLogs({ logs, onClear, isRunning }: ExecutionLogsProps) {
  const [filter, setFilter] = useState<"all" | "decision" | "error">("all");
  const [selectedLog, setSelectedLog] = useState<ExecutionLog | null>(null);

  const filteredLogs = logs.filter((log) => {
    if (filter === "decision") return log.level === "decision";
    if (filter === "error") return log.level === "error" || log.level === "warn";
    return true;
  });

  return (
    <div className="flex h-full flex-col bg-slate-950/95 border-l border-slate-800 text-slate-200">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-blue-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-100">
            Execution Logs &amp; Inngest Steps
          </span>
          {isRunning && (
            <span className="flex h-2 w-2 rounded-full bg-blue-500 animate-ping" />
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Filters */}
          <div className="flex rounded-md bg-slate-900 p-0.5 border border-slate-800 text-[11px]">
            <button
              onClick={() => setFilter("all")}
              className={`px-2 py-0.5 rounded ${
                filter === "all" ? "bg-slate-800 text-slate-100 font-semibold" : "text-slate-400"
              }`}
            >
              All ({logs.length})
            </button>
            <button
              onClick={() => setFilter("decision")}
              className={`px-2 py-0.5 rounded ${
                filter === "decision" ? "bg-slate-800 text-emerald-400 font-semibold" : "text-slate-400"
              }`}
            >
              Decisions
            </button>
          </div>

          <button
            onClick={onClear}
            className="text-slate-500 hover:text-slate-300 p-1 rounded hover:bg-slate-900 transition-colors"
            title="Clear logs"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Log Stream */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-xs">
        {filteredLogs.length === 0 ? (
          <div className="flex h-48 flex-col items-center justify-center text-slate-600 text-center px-4">
            <Terminal className="h-8 w-8 mb-2 stroke-[1.2]" />
            <p className="text-xs">No execution logs yet.</p>
            <p className="text-[11px] text-slate-500 mt-1">
              Click &quot;Run Workflow&quot; to test AI decision branching.
            </p>
          </div>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              onClick={() => setSelectedLog(selectedLog?.id === log.id ? null : log)}
              className={`cursor-pointer rounded-lg border p-2.5 transition-all ${
                log.level === "decision"
                  ? log.details?.decision === "YES"
                    ? "border-emerald-500/30 bg-emerald-950/20 hover:border-emerald-500/50"
                    : "border-rose-500/30 bg-rose-950/20 hover:border-rose-500/50"
                  : log.level === "success"
                  ? "border-emerald-500/40 bg-slate-900/80"
                  : log.level === "error"
                  ? "border-rose-500/50 bg-rose-950/30 text-rose-200"
                  : "border-slate-800/80 bg-slate-900/50 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                <span className="flex items-center gap-1.5 font-sans font-semibold text-slate-300">
                  {log.level === "decision" && (
                    <span
                      className={`inline-block h-1.5 w-1.5 rounded-full ${
                        log.details?.decision === "YES" ? "bg-emerald-400" : "bg-rose-400"
                      }`}
                    />
                  )}
                  {log.nodeLabel}
                </span>
                <span>{log.timestamp}</span>
              </div>

              <div className="text-slate-200 leading-relaxed text-[11px]">{log.message}</div>

              {/* Collapsible Details */}
              {selectedLog?.id === log.id && log.details && (
                <div className="mt-2.5 pt-2 border-t border-slate-800/60 text-[10px] space-y-1 text-slate-400 bg-slate-950/70 p-2 rounded">
                  {log.details.question && (
                    <div>
                      <span className="text-slate-300 font-bold">Prompt: </span>
                      &quot;{log.details.question}&quot;
                    </div>
                  )}
                  {log.details.decision && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-300 font-bold">Decision: </span>
                      <span
                        className={`font-extrabold ${
                          log.details.decision === "YES" ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {log.details.decision}
                      </span>
                      {log.details.confidence && (
                        <span>({(log.details.confidence * 100).toFixed(0)}% confidence)</span>
                      )}
                    </div>
                  )}
                  {log.details.reasoning && (
                    <div>
                      <span className="text-slate-300 font-bold">Reasoning: </span>
                      {log.details.reasoning}
                    </div>
                  )}
                  {log.details.durationMs && (
                    <div>
                      <span className="text-slate-300 font-bold">Latency: </span>
                      {log.details.durationMs}ms
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Footer Info */}
      <div className="border-t border-slate-800/80 px-4 py-2.5 text-[11px] text-slate-400 flex items-center justify-between bg-slate-950">
        <span>Inngest Dev Server</span>
        <span className="flex items-center gap-1.5 text-emerald-400 font-mono font-medium">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          http://localhost:8288
        </span>
      </div>
    </div>
  );
}
