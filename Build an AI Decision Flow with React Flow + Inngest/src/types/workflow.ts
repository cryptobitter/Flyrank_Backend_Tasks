export type NodeExecutionStatus = 'idle' | 'running' | 'completed' | 'skipped' | 'failed';

export type DecisionOutcome = 'YES' | 'NO' | null;

export interface DecisionNodeData {
  label: string;
  question: string;
  status: NodeExecutionStatus;
  decision?: DecisionOutcome;
  reasoning?: string;
  confidence?: number;
  tokensUsed?: number;
  durationMs?: number;
}

export interface TerminalNodeData {
  label: string;
  action: string;
  status: NodeExecutionStatus;
  resultPayload?: Record<string, any>;
}

export type EdgeDecisionType = 'YES' | 'NO' | 'DEFAULT';

export interface WorkflowEdgeData {
  decisionType: EdgeDecisionType;
  isActive?: boolean;
}

export interface ExecutionLog {
  id: string;
  timestamp: string;
  nodeId: string;
  nodeLabel: string;
  level: 'info' | 'decision' | 'success' | 'warn' | 'error';
  message: string;
  details?: {
    question?: string;
    decision?: DecisionOutcome;
    reasoning?: string;
    confidence?: number;
    durationMs?: number;
    stepName?: string;
  };
}

export interface WorkflowExecutionResult {
  runId: string;
  status: 'completed' | 'failed';
  inputMessage: string;
  pathTraversed: string[];
  nodeDecisions: Record<string, {
    decision: 'YES' | 'NO';
    reasoning: string;
    confidence: number;
    durationMs: number;
  }>;
  finalOutcomeNodeId?: string;
  finalAction?: string;
  totalDurationMs: number;
  logs: ExecutionLog[];
}

export interface WorkflowPreset {
  id: string;
  name: string;
  description: string;
  sampleInput: string;
  nodes: any[];
  edges: any[];
}
