import { WorkflowPreset } from "@/types/workflow";

export const DEFAULT_WORKFLOWS: WorkflowPreset[] = [
  {
    id: "preset-support-sales",
    name: "Customer Triage (Support vs. Sales)",
    description: "Evaluates inbound customer messages and routes them through nested support or sales branches.",
    sampleInput: "We have an urgent issue: our payment gateway keeps failing with 500 errors and our users cannot pay. Please refund the double charge on invoice #904.",
    nodes: [
      {
        id: "node-1",
        type: "decisionNode",
        position: { x: 380, y: 50 },
        data: {
          label: "01 · Triage Filter",
          question: "Is this a customer support request or technical issue?",
          status: "idle",
        },
      },
      {
        id: "node-2",
        type: "decisionNode",
        position: { x: 180, y: 260 },
        data: {
          label: "02 · Support Domain",
          question: "Does this involve billing, payments, invoices, or refund requests?",
          status: "idle",
        },
      },
      {
        id: "node-3",
        type: "decisionNode",
        position: { x: 580, y: 260 },
        data: {
          label: "03 · Commercial Intent",
          question: "Is this an enterprise purchasing inquiry, contract quote, or sales demo request?",
          status: "idle",
        },
      },
      {
        id: "node-4",
        type: "terminalNode",
        position: { x: 80, y: 470 },
        data: {
          label: "Billing & Refund Desk",
          action: "Route to Tier-2 Finance Specialist & Auto-Draft Refund Ticket",
          status: "idle",
        },
      },
      {
        id: "node-5",
        type: "terminalNode",
        position: { x: 300, y: 470 },
        data: {
          label: "Technical Engineering Queue",
          action: "Open P1 Engineering Defect in Linear / Sentry Alert",
          status: "idle",
        },
      },
      {
        id: "node-6",
        type: "terminalNode",
        position: { x: 500, y: 470 },
        data: {
          label: "Enterprise Sales Routing",
          action: "Notify Account Executive via Slack & Schedule Calendly Demo",
          status: "idle",
        },
      },
      {
        id: "node-7",
        type: "terminalNode",
        position: { x: 720, y: 470 },
        data: {
          label: "General Community Inbox",
          action: "Send Automated FAQ & Knowledge Base Help Docs",
          status: "idle",
        },
      },
    ],
    edges: [
      {
        id: "e1-2",
        source: "node-1",
        target: "node-2",
        sourceHandle: "yes",
        type: "yesEdge",
        data: { decisionType: "YES" },
      },
      {
        id: "e1-3",
        source: "node-1",
        target: "node-3",
        sourceHandle: "no",
        type: "noEdge",
        data: { decisionType: "NO" },
      },
      {
        id: "e2-4",
        source: "node-2",
        target: "node-4",
        sourceHandle: "yes",
        type: "yesEdge",
        data: { decisionType: "YES" },
      },
      {
        id: "e2-5",
        source: "node-2",
        target: "node-5",
        sourceHandle: "no",
        type: "noEdge",
        data: { decisionType: "NO" },
      },
      {
        id: "e3-6",
        source: "node-3",
        target: "node-6",
        sourceHandle: "yes",
        type: "yesEdge",
        data: { decisionType: "YES" },
      },
      {
        id: "e3-7",
        source: "node-3",
        target: "node-7",
        sourceHandle: "no",
        type: "noEdge",
        data: { decisionType: "NO" },
      },
    ],
  },
  {
    id: "preset-security-audit",
    name: "Security & Threat Triage",
    description: "Evaluates incident severity, credentials leaks, and automated defensive containment.",
    sampleInput: "Unauthorized root SSH access attempt detected on production bastion host at 04:12 UTC from unlisted IP address.",
    nodes: [
      {
        id: "node-sec-1",
        type: "decisionNode",
        position: { x: 380, y: 60 },
        data: {
          label: "01 · Threat Assessment",
          question: "Does this incident indicate an active security breach, unauthorized root access, or credential compromise?",
          status: "idle",
        },
      },
      {
        id: "node-sec-2",
        type: "terminalNode",
        position: { x: 200, y: 300 },
        data: {
          label: "P0 Security Lockdown",
          action: "Trigger PagerDuty Incident, Invalidate Tokens, & Alert CISO",
          status: "idle",
        },
      },
      {
        id: "node-sec-3",
        type: "terminalNode",
        position: { x: 560, y: 300 },
        data: {
          label: "Standard SIEM Log",
          action: "Record in Audit Log for Weekly SecOps Review",
          status: "idle",
        },
      },
    ],
    edges: [
      {
        id: "e-sec-1-2",
        source: "node-sec-1",
        target: "node-sec-2",
        sourceHandle: "yes",
        type: "yesEdge",
        data: { decisionType: "YES" },
      },
      {
        id: "e-sec-1-3",
        source: "node-sec-1",
        target: "node-sec-3",
        sourceHandle: "no",
        type: "noEdge",
        data: { decisionType: "NO" },
      },
    ],
  },
];
