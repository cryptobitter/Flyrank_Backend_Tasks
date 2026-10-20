import { NextRequest, NextResponse } from "next/server";
import { inngest } from "@/inngest/client";
import { evaluateAIDecision } from "@/lib/ai-judge";
import { ExecutionLog, WorkflowExecutionResult } from "@/types/workflow";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { nodes, edges, inputMessage, startNodeId } = body;

    if (!nodes || !edges || !inputMessage) {
      return NextResponse.json(
        { error: "Missing required parameters: nodes, edges, or inputMessage" },
        { status: 400 }
      );
    }

    const runId = `run-${Date.now()}`;

    // 1. Dispatch event to Inngest for durable background tracking
    try {
      await inngest.send({
        name: "app/workflow.execute",
        data: {
          runId,
          nodes,
          edges,
          inputMessage,
          startNodeId,
        },
      });
    } catch (inngestErr) {
      console.warn("Inngest send skipped (dev server might not be running yet):", inngestErr);
    }

    // 2. Perform end-to-end traversal with step-by-step logging for real-time frontend visualization
    const startTime = Date.now();
    const logs: ExecutionLog[] = [];
    const pathTraversed: string[] = [];
    const nodeDecisions: Record<string, any> = {};

    let currentNode = nodes.find((n: any) => n.id === (startNodeId || "node-1")) || nodes[0];
    let stepCount = 0;
    const maxSteps = 25;

    logs.push({
      id: `log-${Date.now()}-init`,
      timestamp: new Date().toLocaleTimeString(),
      nodeId: currentNode?.id || "start",
      nodeLabel: currentNode?.data?.label || "Workflow Start",
      level: "info",
      message: `Triggered execution for input: "${inputMessage}"`,
    });

    while (currentNode && stepCount < maxSteps) {
      stepCount++;
      const nodeId = currentNode.id;
      const nodeLabel = currentNode.data.label;
      pathTraversed.push(nodeId);

      // Terminal node
      if (currentNode.type === "terminalNode" || !currentNode.data.question) {
        logs.push({
          id: `log-${Date.now()}-${nodeId}`,
          timestamp: new Date().toLocaleTimeString(),
          nodeId,
          nodeLabel,
          level: "success",
          message: `Arrived at terminal action node: [${currentNode.data.action || nodeLabel}]`,
        });
        break;
      }

      // Decision node -> Ask LLM
      const question = currentNode.data.question;
      const aiResult = await evaluateAIDecision(question, inputMessage);

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
        },
      });

      // Find matching edge for YES or NO
      const matchingEdge = edges.find((edge: any) => {
        if (edge.source !== nodeId) return false;
        const edgeDecision = edge.data?.decisionType || (edge.sourceHandle === "yes" ? "YES" : "NO");
        return edgeDecision === aiResult.decision;
      });

      if (!matchingEdge) {
        logs.push({
          id: `log-${Date.now()}-edge-missing`,
          timestamp: new Date().toLocaleTimeString(),
          nodeId,
          nodeLabel,
          level: "warn",
          message: `Branch complete: No outgoing [${aiResult.decision}] edge defined from [${nodeLabel}].`,
        });
        break;
      }

      const nextNode = nodes.find((n: any) => n.id === matchingEdge.target);
      if (!nextNode) {
        logs.push({
          id: `log-${Date.now()}-target-missing`,
          timestamp: new Date().toLocaleTimeString(),
          nodeId,
          nodeLabel,
          level: "error",
          message: `Target node '${matchingEdge.target}' is missing from workflow graph.`,
        });
        break;
      }

      currentNode = nextNode;
    }

    const finalNode = nodes.find((n: any) => n.id === pathTraversed[pathTraversed.length - 1]);

    const result: WorkflowExecutionResult = {
      runId,
      status: "completed",
      inputMessage,
      pathTraversed,
      nodeDecisions,
      finalOutcomeNodeId: finalNode?.id,
      finalAction: finalNode?.data?.action || finalNode?.data?.label,
      totalDurationMs: Date.now() - startTime,
      logs,
    };

    return NextResponse.json(result);
  } catch (err: any) {
    console.error("Workflow run endpoint error:", err);
    return NextResponse.json(
      { error: err.message || "Failed to execute decision workflow" },
      { status: 500 }
    );
  }
}
