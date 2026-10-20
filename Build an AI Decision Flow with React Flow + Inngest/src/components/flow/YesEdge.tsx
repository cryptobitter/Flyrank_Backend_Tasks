"use client";

import React from "react";
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getSmoothStepPath } from "@xyflow/react";

export function YesEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    borderRadius: 16,
  });

  const isActive = data?.isActive;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: isActive ? "#10b981" : "#059669",
          strokeWidth: isActive ? 3.5 : 2,
          strokeDasharray: isActive ? "6,6" : "none",
          filter: isActive ? "drop-shadow(0 0 6px rgba(16, 185, 129, 0.6))" : "none",
        }}
        className={isActive ? "animate-flow-dash" : ""}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
          }}
          className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider shadow-md transition-all ${
            isActive
              ? "bg-emerald-500 text-slate-950 scale-110 shadow-emerald-500/50"
              : "bg-emerald-950 text-emerald-400 border border-emerald-800"
          }`}
        >
          <span>✓</span>
          <span>YES</span>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
