import { inngest } from "./client";
import { evaluateAIDecision } from "@/lib/ai-judge";
import { ExecutionLog, WorkflowExecutionResult } from "@/types/workflow";

/**
 * Inngest Function: Traverses an AI Decision Flow.
 * Maps each visual node to an isolated, durable Inngest step (step.run).
 * Guarantees that the LLM produces strictly YES or NO, and branches along the matching edge.
 */
export const executeDecisionWorkflow = inngest.createFunction(
  {
    id: "execute-ai-decision-workflow",
    name: "Execute AI Decision Workflow",
    retries: 2,
  },
  { event: "app/workflow.execute" },
  async ({ event, step }) => {
    const { nodes, edges, inputMessage, startNodeId } = event.data;
    const startTime = Date.now();
    const logs: ExecutionLog[] = [];
    const pathTraversed: string[] = [];
    const nodeDecisions: Record<string, any> = {};

    let currentNode = nodes.find((n: any) => n.id === (startNodeId || "node-1")) || nodes[0];
    let stepCount = 0;
    const maxSteps = 20; // Guardrail against infinite loops

    logs.push({
      id: `log-${Date.now()}-start`,
      timestamp: new Date().toLocaleTimeString(),
      nodeId: currentNode?.id || "start",
      nodeLabel: currentNode?.data?.label || "Workflow Start",
      level: "info",
      message: `Workflow execution started with input: "${inputMessage}"`,
    });

    while (currentNode && stepCount < maxSteps) {
      stepCount++;
      const nodeId = currentNode.id;
      const nodeLabel = currentNode.data.label;
      pathTraversed.push(nodeId);

      // 1. If it's a Terminal / Action node, complete workflow
      if (currentNode.type === "terminalNode" || !currentNode.data.question) {
        await step.run(`finalize-outcome-${nodeId}`, async () => {
          return {
            outcome: "COMPLETED",
            action: currentNode.data.action || nodeLabel,
            nodeId,
          };
        });

        logs.push({
          id: `log-${Date.now()}-${nodeId}`,
          timestamp: new Date().toLocaleTimeString(),
          nodeId,
          nodeLabel,
          level: "success",
          message: `Reached terminal action: [${currentNode.data.action || nodeLabel}]`,
        });
        break;
      }

      // 2. It's a Decision node -> Run Inngest Step with LLM
      const question = currentNode.data.question;
      const stepName = `decision-${nodeId}-${nodeLabel.replace(/\s+/g, "_")}`;

      const aiResult = await step.run(stepName, async () => {
        return await evaluateAIDecision(question, inputMessage);
      });

      nodeDecisions[nodeId] = {
        decision: aiResult.decision,
        reasoning: aiResult.reasoning,
        confidence: aiResult.confidence,
        durationMs: aiResult.durationMs,
      };

      logs.push({
        id: `log-${Date.now()}-${nodeId}`,
        timestamp: new Date().toLocaleTimeString(),
        nodeId,
        nodeLabel,
        level: "decision",
        message: `Decision: ${aiResult.decision} (${(aiResult.confidence * 100).toFixed(0)}% confidence) - ${aiResult.reasoning}`,
        details: {
          question,
          decision: aiResult.decision,
          reasoning: aiResult.reasoning,
          confidence: aiResult.confidence,
          durationMs: aiResult.durationMs,
          stepName,
        },
      });

      // 3. Find the matching edge based on decision: YES or NO
      const matchingEdge = edges.find((edge: any) => {
        if (edge.source !== nodeId) return false;
        const edgeType = edge.data?.decisionType || (edge.sourceHandle === "yes" ? "YES" : "NO");
        return edgeType === aiResult.decision;
      });

      if (!matchingEdge) {
        logs.push({
          id: `log-${Date.now()}-no-edge`,
          timestamp: new Date().toLocaleTimeString(),
          nodeId,
          nodeLabel,
          level: "warn",
          message: `No matching ${aiResult.decision} branch edge found from [${nodeLabel}]. Halting flow.`,
        });
        break;
      }

      // 4. Move to next target node
      const nextNode = nodes.find((n: any) => n.id === matchingEdge.target);
      if (!nextNode) {
        logs.push({
          id: `log-${Date.now()}-broken-target`,
          timestamp: new Date().toLocaleTimeString(),
          nodeId,
          nodeLabel,
          level: "error",
          message: `Target node ${matchingEdge.target} could not be found in graph.`,
        });
        break;
      }

      currentNode = nextNode;
    }

    const totalDurationMs = Date.now() - startTime;
    const finalOutcomeNode = nodes.find((n: any) => n.id === pathTraversed[pathTraversed.length - 1]);

    const result: WorkflowExecutionResult = {
      runId: event.data.runId || `run-${Date.now()}`,
      status: "completed",
      inputMessage,
      pathTraversed,
      nodeDecisions,
      finalOutcomeNodeId: finalOutcomeNode?.id,
      finalAction: finalOutcomeNode?.data?.action || finalOutcomeNode?.data?.label,
      totalDurationMs,
      logs,
    };

    return result;
  }
);
