import OpenAI from "openai";
import { DecisionOutcome } from "@/types/workflow";

export interface AIJudgeResult {
  decision: "YES" | "NO";
  reasoning: string;
  confidence: number;
  model: string;
  durationMs: number;
}

/**
 * Evaluates an AI decision node's question against the user input.
 * Guarantees that the decision returned is strictly "YES" or "NO".
 */
export async function evaluateAIDecision(
  question: string,
  userMessage: string,
  apiKey?: string
): Promise<AIJudgeResult> {
  const startTime = Date.now();
  const effectiveKey = apiKey || process.env.OPENAI_API_KEY;

  if (effectiveKey && !effectiveKey.startsWith("your_")) {
    try {
      const openai = new OpenAI({ apiKey: effectiveKey });
      const prompt = `You are an automated decision logic unit in an AI workflow.
Evaluate the following question strictly based on the provided user message.

QUESTION: "${question}"
USER MESSAGE: "${userMessage}"

You MUST answer strictly in JSON format with:
- "decision": strictly either "YES" or "NO"
- "reasoning": concise 1-2 sentence explanation
- "confidence": number between 0.0 and 1.0

Return ONLY valid JSON.`;

      const response = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: "You are a precise binary decision engine. Respond only with YES or NO judgments in JSON format." },
          { role: "user", content: prompt },
        ],
        response_format: { type: "json_object" },
        temperature: 0.1,
      });

      const content = response.choices[0]?.message?.content || "{}";
      const parsed = JSON.parse(content);
      const rawDecision = String(parsed.decision || "").trim().toUpperCase();
      const decision: "YES" | "NO" = rawDecision === "YES" ? "YES" : "NO";

      return {
        decision,
        reasoning: parsed.reasoning || `Model evaluated criteria and returned ${decision}.`,
        confidence: typeof parsed.confidence === "number" ? parsed.confidence : 0.95,
        model: "gpt-4o-mini",
        durationMs: Date.now() - startTime,
      };
    } catch (err) {
      console.warn("OpenAI API call failed or timed out. Falling back to local semantic evaluator:", err);
    }
  }

  // High-fidelity local semantic evaluator for offline, tests, and zero-key dev
  return localSemanticDecision(question, userMessage, startTime);
}

/**
 * Intelligent deterministic local evaluator for zero-configuration testing.
 */
function localSemanticDecision(
  question: string,
  userMessage: string,
  startTime: number
): AIJudgeResult {
  const q = question.toLowerCase();
  const msg = userMessage.toLowerCase();

  let decision: "YES" | "NO" = "NO";
  let reasoning = "";
  let confidence = 0.92;

  // 1. Support Request Check
  if (q.includes("support") || q.includes("issue") || q.includes("help") || q.includes("broken")) {
    const isSupport = /problem|issue|broken|help|error|fail|bug|stuck|cannot|can't|not working|crash|urgent/i.test(msg);
    decision = isSupport ? "YES" : "NO";
    reasoning = isSupport
      ? "Detected technical problem keywords ('error', 'not working', 'broken')."
      : "Message does not report an operational problem or technical bug.";
  }
  // 2. Billing / Refund / Money Check
  else if (q.includes("billing") || q.includes("refund") || q.includes("invoice") || q.includes("charge") || q.includes("payment")) {
    const isBilling = /refund|charged|money|invoice|bill|cost|price|subscription|payment|card|receipt|\$/i.test(msg);
    decision = isBilling ? "YES" : "NO";
    reasoning = isBilling
      ? "Detected financial transaction keywords indicating billing inquiry or refund request."
      : "No financial or billing entities detected in message.";
  }
  // 3. Enterprise / Sales / Pricing / Demo
  else if (q.includes("sales") || q.includes("enterprise") || q.includes("lead") || q.includes("quote") || q.includes("tier")) {
    const isSales = /enterprise|pricing|purchase|buy|quote|demo|team|license|sales|seats|contract/i.test(msg);
    decision = isSales ? "YES" : "NO";
    reasoning = isSales
      ? "Detected high-intent commercial or enterprise purchasing inquiry."
      : "Message is non-commercial or does not express enterprise purchasing intent.";
  }
  // 4. Urgent / High Priority
  else if (q.includes("urgent") || q.includes("critical") || q.includes("emergency") || q.includes("now")) {
    const isUrgent = /urgent|critical|immediately|asap|emergency|outage|down|now|blocker/i.test(msg);
    decision = isUrgent ? "YES" : "NO";
    reasoning = isUrgent
      ? "High-urgency markers (ASAP, critical, outage) identified."
      : "Standard inquiry without critical time-sensitive urgency markers.";
  }
  // 5. General question intent
  else {
    // If words from question appear in the message, evaluate YES
    const qWords = q.split(/\W+/).filter((w) => w.length > 3);
    const matches = qWords.filter((w) => msg.includes(w));
    if (matches.length > 0) {
      decision = "YES";
      reasoning = `Found semantic overlap with criteria terms: ${matches.join(", ")}.`;
      confidence = 0.85;
    } else {
      decision = "NO";
      reasoning = "Message did not satisfy the evaluation criteria.";
      confidence = 0.85;
    }
  }

  return {
    decision,
    reasoning,
    confidence,
    model: "local-semantic-evaluator",
    durationMs: Date.now() - startTime,
  };
}
