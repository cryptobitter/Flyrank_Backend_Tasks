'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
} from '@xyflow/react';
import { WorkflowToolbar } from '@/components/panel/WorkflowToolbar';
import { FlowEditor } from '@/components/flow/FlowEditor';
import { ExecutionLogs } from '@/components/panel/ExecutionLogs';
import { RunModal } from '@/components/panel/RunModal';
import { ExecutionLog, WorkflowExecutionResult } from '@/types/workflow';
import { DEFAULT_WORKFLOWS } from '@/lib/default-workflows';
import {
  saveWorkflowToStorage,
  loadWorkflowFromStorage,
  exportWorkflowToJson,
  importWorkflowFromJson,
  saveExecutionToHistory,
} from '@/lib/storage';

export default function WorkflowPage() {
  const initialPreset = DEFAULT_WORKFLOWS[0];
  const [nodes, setNodes, onNodesChange] = useNodesState(initialPreset.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialPreset.edges);

  const [activePresetId, setActivePresetId] = useState<string>(initialPreset.id);
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isRunModalOpen, setIsRunModalOpen] = useState<boolean>(false);
  const [isLogsPanelOpen, setIsLogsPanelOpen] = useState<boolean>(true);
  const [notification, setNotification] = useState<string | null>(null);

  const notificationTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const showNotification = (msg: string) => {
    if (notificationTimeoutRef.current) clearTimeout(notificationTimeoutRef.current);
    setNotification(msg);
    notificationTimeoutRef.current = setTimeout(() => setNotification(null), 3500);
  };

  // Restore saved state from localStorage if available
  useEffect(() => {
    const saved = loadWorkflowFromStorage();
    if (saved && saved.nodes && saved.nodes.length > 0) {
      setNodes(saved.nodes);
      setEdges(saved.edges);
      showNotification('Loaded saved workflow graph');
    }
  }, [setNodes, setEdges]);

  // Handle edge connections (Assigns custom yesEdge or noEdge depending on source port)
  const onConnect = useCallback(
    (params: Connection) => {
      const isYes = params.sourceHandle === 'yes';
      const edgeType = isYes ? 'yesEdge' : 'noEdge';

      const newEdge: Edge = {
        id: `e-${params.source}-${params.sourceHandle}-${params.target}-${Date.now()}`,
        source: params.source,
        target: params.target,
        sourceHandle: params.sourceHandle,
        targetHandle: params.targetHandle,
        type: edgeType,
        data: {
          decisionType: isYes ? 'YES' : 'NO',
          isActive: false,
        },
      };

      setEdges((eds) => addEdge(newEdge, eds));
      showNotification(`Connected via ${isYes ? 'YES (green)' : 'NO (red)'} path`);
    },
    [setEdges]
  );

  // Add Decision Node
  const handleAddDecisionNode = useCallback(() => {
    const newId = `node-${Date.now().toString().slice(-4)}`;
    const newNode: Node = {
      id: newId,
      type: 'decisionNode',
      position: { x: 320 + Math.random() * 80, y: 150 + Math.random() * 80 },
      data: {
        label: 'New AI Decision Step',
        question: 'Does this message require an immediate human escalation?',
        status: 'idle',
      },
    };
    setNodes((nds) => [...nds, newNode]);
    showNotification(`Added Decision Node: ${newId}`);
  }, [setNodes]);

  // Add Terminal Node
  const handleAddTerminalNode = useCallback(() => {
    const newId = `node-${Date.now().toString().slice(-4)}`;
    const newNode: Node = {
      id: newId,
      type: 'terminalNode',
      position: { x: 400 + Math.random() * 80, y: 380 + Math.random() * 80 },
      data: {
        label: 'Outcome Endpoint',
        action: 'Notify On-Call Engineering & Dispatch Webhook',
        status: 'idle',
      },
    };
    setNodes((nds) => [...nds, newNode]);
    showNotification(`Added Terminal Node: ${newId}`);
  }, [setNodes]);

  // Switch Preset
  const handleSelectPreset = useCallback(
    (presetId: string) => {
      const preset = DEFAULT_WORKFLOWS.find((p) => p.id === presetId);
      if (!preset) return;

      const clonedNodes = JSON.parse(JSON.stringify(preset.nodes));
      const clonedEdges = JSON.parse(JSON.stringify(preset.edges));

      setNodes(clonedNodes);
      setEdges(clonedEdges);
      setActivePresetId(presetId);
      setExecutionLogs([]);
      showNotification(`Loaded preset: "${preset.name}"`);
    },
    [setNodes, setEdges]
  );

  // Save to LocalStorage
  const handleSaveGraph = useCallback(() => {
    saveWorkflowToStorage(nodes, edges);
    showNotification('Workflow saved locally');
  }, [nodes, edges]);

  // Export JSON
  const handleExportJson = useCallback(() => {
    exportWorkflowToJson(nodes, edges, 'ai-decision-workflow');
    showNotification('Workflow exported as JSON');
  }, [nodes, edges]);

  // Import JSON
  const handleImportJson = useCallback(
    (jsonString: string) => {
      try {
        const { nodes: importedNodes, edges: importedEdges } = importWorkflowFromJson(jsonString);
        setNodes(importedNodes);
        setEdges(importedEdges);
        showNotification('Workflow successfully imported');
      } catch (err: any) {
        alert(`Invalid workflow JSON format: ${err.message}`);
      }
    },
    [setNodes, setEdges]
  );

  // Reset graph
  const handleResetGraph = useCallback(() => {
    if (confirm('Reset canvas back to the default Customer Triage workflow?')) {
      handleSelectPreset('preset-support-sales');
    }
  }, [handleSelectPreset]);

  // Execute Workflow via Inngest and stream UI playback
  const handleRunWorkflow = async (inputMessage: string) => {
    setIsRunning(true);
    setIsRunModalOpen(false);
    setIsLogsPanelOpen(true);
    setExecutionLogs([]);

    // Reset all nodes and edges to idle state
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          status: 'idle',
          decision: undefined,
          reasoning: undefined,
        },
      }))
    );

    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        animated: false,
        data: {
          ...e.data,
          isActive: false,
        },
      }))
    );

    try {
      const res = await fetch('/api/workflow/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nodes,
          edges,
          inputMessage,
        }),
      });

      if (!res.ok) {
        throw new Error(`Execution error: ${res.statusText}`);
      }

      const result: WorkflowExecutionResult = await res.json();

      // Playback simulation of the execution steps
      for (let i = 0; i < result.pathTraversed.length; i++) {
        const nodeId = result.pathTraversed[i];
        const decisionData = result.nodeDecisions[nodeId];

        // 1. Mark node as running
        setNodes((nds) =>
          nds.map((n) =>
            n.id === nodeId
              ? { ...n, data: { ...n.data, status: 'running' } }
              : n
          )
        );

        await new Promise((r) => setTimeout(r, 700));

        // 2. Mark node as completed with decision
        if (decisionData) {
          setNodes((nds) =>
            nds.map((n) =>
              n.id === nodeId
                ? {
                    ...n,
                    data: {
                      ...n.data,
                      status: 'completed',
                      decision: decisionData.decision,
                      reasoning: decisionData.reasoning,
                      confidence: decisionData.confidence,
                      durationMs: decisionData.durationMs,
                    },
                  }
                : n
            )
          );

          // 3. Highlight the active edge exiting this node
          setEdges((eds) =>
            eds.map((e) => {
              const isMatch =
                e.source === nodeId &&
                ((decisionData.decision === 'YES' && (e.sourceHandle === 'yes' || e.data?.decisionType === 'YES')) ||
                  (decisionData.decision === 'NO' && (e.sourceHandle === 'no' || e.data?.decisionType === 'NO')));
              if (isMatch) {
                return {
                  ...e,
                  animated: true,
                  data: { ...e.data, isActive: true },
                };
              }
              return e;
            })
          );
        } else {
          // Terminal node reached
          setNodes((nds) =>
            nds.map((n) =>
              n.id === nodeId
                ? { ...n, data: { ...n.data, status: 'completed' } }
                : n
            )
          );
        }

        await new Promise((r) => setTimeout(r, 500));
      }

      setExecutionLogs(result.logs || []);
      saveExecutionToHistory(result);
      showNotification('Workflow execution completed successfully!');
    } catch (err: any) {
      console.error(err);
      showNotification(`Execution failed: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 select-none">
      {/* Top Toolbar */}
      <WorkflowToolbar
        onAddDecisionNode={handleAddDecisionNode}
        onAddTerminalNode={handleAddTerminalNode}
        onOpenRunModal={() => setIsRunModalOpen(true)}
        onResetGraph={handleResetGraph}
        onSaveGraph={handleSaveGraph}
        onExportJson={handleExportJson}
        onImportJson={handleImportJson}
        onSelectPreset={handleSelectPreset}
        isRunning={isRunning}
      />

      {/* Main Workspace Body */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Flow Canvas */}
        <div className="flex-1 relative h-full">
          <FlowEditor
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
          />
        </div>

        {/* Side Execution Logs Drawer */}
        <div
          className={`transition-all duration-300 ease-in-out border-l border-slate-800 ${
            isLogsPanelOpen ? 'w-[420px]' : 'w-0'
          } overflow-hidden flex flex-col`}
        >
          <ExecutionLogs
            logs={executionLogs}
            onClear={() => setExecutionLogs([])}
            isRunning={isRunning}
          />
        </div>

        {/* Logs Drawer Toggle Button */}
        <button
          onClick={() => setIsLogsPanelOpen(!isLogsPanelOpen)}
          className="absolute bottom-5 right-5 z-20 rounded-lg bg-slate-900/90 border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-300 shadow-xl backdrop-blur-md hover:bg-slate-800 hover:text-white transition-all flex items-center gap-1.5"
        >
          <span>{isLogsPanelOpen ? 'Hide Logs' : 'Show Logs'}</span>
          <span className="flex h-2 w-2 rounded-full bg-blue-500" />
        </button>

        {/* Global Toast Notification */}
        {notification && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-slate-900/95 border border-indigo-500/50 text-indigo-200 px-4 py-2 rounded-xl shadow-2xl backdrop-blur-md text-xs font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
            {notification}
          </div>
        )}
      </div>

      {/* Run Input Modal */}
      <RunModal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
        onRun={handleRunWorkflow}
        isRunning={isRunning}
      />
    </div>
  );
}
