'use client';

import React, { useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  Node,
  Edge,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { DecisionNode } from './DecisionNode';
import { TerminalNode } from './TerminalNode';
import { YesEdge } from './YesEdge';
import { NoEdge } from './NoEdge';

interface FlowEditorProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
}

export function FlowEditor({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
}: FlowEditorProps) {
  const nodeTypes = useMemo(
    () => ({
      decisionNode: DecisionNode,
      terminalNode: TerminalNode,
    }),
    []
  );

  const edgeTypes = useMemo(
    () => ({
      yesEdge: YesEdge,
      noEdge: NoEdge,
    }),
    []
  );

  return (
    <div className="w-full h-full relative bg-slate-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
        className="touch-none"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.5}
          color="#334155"
          className="opacity-50"
        />
        <Controls
          className="bg-slate-900 border border-slate-700/80 rounded-lg overflow-hidden shadow-xl fill-slate-300 stroke-slate-300 text-slate-300 [&>button]:border-slate-800 [&>button:hover]:bg-slate-800"
        />
        <MiniMap
          nodeStrokeWidth={3}
          nodeColor={(n: any) => {
            if (n.type === 'terminalNode') return '#3b82f6';
            if (n.data?.status === 'completed' && n.data?.decision === 'YES') return '#10b981';
            if (n.data?.status === 'completed' && n.data?.decision === 'NO') return '#ef4444';
            if (n.data?.status === 'running') return '#f59e0b';
            return '#6366f1';
          }}
          maskColor="rgba(15, 23, 42, 0.75)"
          className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-2xl !bottom-4 !right-4"
        />
      </ReactFlow>

      {/* Port Legend */}
      <div className="absolute top-4 left-4 z-10 flex items-center gap-3 bg-slate-900/90 backdrop-blur-md border border-slate-800 px-3.5 py-2 rounded-xl text-xs shadow-xl pointer-events-none">
        <span className="text-slate-400 font-medium">Port Legend:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
          <span className="text-emerald-400 font-semibold">YES Port (Bottom Left)</span>
        </div>
        <span className="text-slate-600">|</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"></span>
          <span className="text-rose-400 font-semibold">NO Port (Bottom Right)</span>
        </div>
      </div>
    </div>
  );
}

export default FlowEditor;
