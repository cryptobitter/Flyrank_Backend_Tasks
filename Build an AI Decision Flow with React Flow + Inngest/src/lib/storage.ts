import { WorkflowExecutionResult } from "@/types/workflow";

const WORKFLOW_STORAGE_KEY = "ai_decision_flow_active_graph";
const EXECUTION_HISTORY_KEY = "ai_decision_flow_history";

export function saveWorkflowToStorage(nodes: any[], edges: any[]): void {
  if (typeof window === "undefined") return;
  try {
    const payload = JSON.stringify({ nodes, edges, updatedAt: new Date().toISOString() });
    localStorage.setItem(WORKFLOW_STORAGE_KEY, payload);
  } catch (err) {
    console.error("Failed to save workflow locally:", err);
  }
}

export function loadWorkflowFromStorage(): { nodes: any[]; edges: any[] } | null {
  if (typeof window === "undefined") return null;
  try {
    const data = localStorage.getItem(WORKFLOW_STORAGE_KEY);
    if (!data) return null;
    return JSON.parse(data);
  } catch (err) {
    console.error("Failed to load stored workflow:", err);
    return null;
  }
}

export function exportWorkflowToJson(nodes: any[], edges: any[], name: string = "decision-flow"): void {
  const exportData = {
    name,
    exportedAt: new Date().toISOString(),
    nodes,
    edges,
  };
  const jsonStr = JSON.stringify(exportData, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${name.toLowerCase().replace(/\s+/g, "-")}-workflow.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function importWorkflowFromJson(
  jsonString: string
): { nodes: any[]; edges: any[] } {
  const parsed = JSON.parse(jsonString);
  if (!parsed.nodes || !Array.isArray(parsed.nodes) || !parsed.edges || !Array.isArray(parsed.edges)) {
    throw new Error("Invalid workflow file: 'nodes' and 'edges' arrays are required.");
  }
  return { nodes: parsed.nodes, edges: parsed.edges };
}

export function saveExecutionToHistory(result: WorkflowExecutionResult): void {
  if (typeof window === "undefined") return;
  try {
    const existing = loadExecutionHistory();
    const updated = [result, ...existing].slice(0, 20); // Keep last 20 runs
    localStorage.setItem(EXECUTION_HISTORY_KEY, JSON.stringify(updated));
  } catch (err) {
    console.error("Failed to save execution to history:", err);
  }
}

export function loadExecutionHistory(): WorkflowExecutionResult[] {
  if (typeof window === "undefined") return [];
  try {
    const data = localStorage.getItem(EXECUTION_HISTORY_KEY);
    return data ? JSON.parse(data) : [];
  } catch (err) {
    return [];
  }
}

export function clearExecutionHistory(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(EXECUTION_HISTORY_KEY);
}
