# AI Decision Flow Engine (React Flow + Inngest)

An enterprise-grade, visual AI workflow system where every node represents an intelligent decision step that returns strictly **`YES`** or **`NO`**. Workflow execution is orchestrated via **Inngest** durable step functions, and the graph is rendered with **React Flow** with interactive visual execution states, custom branching edges, and streaming logs.

---

## 🚀 Key Features by Phase

### Phase 1: Setup & Environment
- **Framework**: Next.js 14 App Router with React 18, TypeScript, and Tailwind CSS.
- **Visual Graph**: `@xyflow/react` (React Flow v12) with custom nodes, handles, edges, minimap, and pan/zoom controls.
- **Workflow Orchestration**: Inngest SDK (`inngest@3.x`) configured with a native Next.js API route handler (`/api/inngest`).
- **AI Judgement Engine**: OpenAI SDK (`gpt-4o-mini`) structured prompt pipeline enforcing strict binary outputs (`YES` or `NO`) with a deterministic semantic heuristic fallback when an API key is not supplied.

### Phase 2: Visual Flow Editor & Graph Foundations
- **Interactive Canvas**: Drag, drop, pan, zoom, and select nodes with dark-mode canvas styling.
- **Custom Decision Nodes**:
  - Live editable prompt textarea directly on the node.
  - Editable node titles and badges.
  - Dedicated **YES** output port (emerald right handle) and **NO** output port (rose bottom handle).
  - Visual status badges (`IDLE`, `RUNNING`, `DECIDED: YES`, `DECIDED: NO`).
- **Outcome Terminal Nodes**: Distinct endpoint nodes signaling resolution.
- **Custom Branching Edges**:
  - **Green YES Edge**: Routed from right handle with arrow markers.
  - **Red NO Edge**: Routed from bottom handle with arrow markers.
- **Local Persistence**: Graph state, custom nodes, and connections are preserved in browser `localStorage`.

### Phase 3: Durable Inngest Execution & Core Flow Engine
- **Inngest Step Mapping**: Each decision node maps to an isolated `step.run(node.id, ...)` ensuring fault isolation and retry capability.
- **Strict Binary Evaluation**: The model receives a system prompt demanding strictly `{"decision": "YES" | "NO", "rationale": "..."}`.
- **Dynamic Branch Traversal**: Follows the selected edge (`YES` or `NO`) to the next node in the graph until reaching a terminal node or leaf.
- **Execution Order Tracking**: Logs step number, node ID, timestamp, duration in ms, and decision tokens used.

### Phase 4: Visual Polish, Presets & Developer Tools
- **Live Execution Feedback**: Active node pulses with an amber glow; active edges animate with high-speed dashing.
- **Streaming Execution Terminal**: Collapsible drawer with log filtering (All, Info, Success, Warnings, Errors), token counts, and JSON step inspection.
- **Workflow Presets**:
  1. *Customer Support vs. Sales Triage* (Support ticket → Technical issue → Tier 2 vs. Sales Lead).
  2. *Security & Threat Triage* (Malicious IP → Data exfiltration → Firewall block vs. Routine audit).
- **Import / Export**: Save, load, download JSON workflow schemas, or upload custom JSON flows.

---

## 🛠️ Project Structure

```
Build an AI Decision Flow with React Flow + Inngest/
├── package.json                   # Next.js, React Flow, Inngest, Tailwind dependencies
├── tsconfig.json                  # TypeScript bundler configuration
├── tailwind.config.ts             # Custom animations, keyframes & decision colors
├── .env.example                   # Environment variable template
├── .env.local                     # Local dev environment
├── src/
│   ├── types/
│   │   └── workflow.ts            # Type definitions for Nodes, Edges, Logs & Inngest Steps
│   ├── lib/
│   │   ├── ai-judge.ts            # OpenAI binary decision evaluator & semantic fallback
│   │   ├── default-workflows.ts   # Built-in Customer Support & Security workflow presets
│   │   └── storage.ts             # LocalStorage manager, JSON export/import & history
│   ├── inngest/
│   │   ├── client.ts              # Inngest client initialization
│   │   └── functions.ts           # Durable workflow execution function (`step.run`)
│   ├── app/
│   │   ├── layout.tsx             # Root dark layout
│   │   ├── page.tsx               # Main Flow canvas & control orchestrator
│   │   ├── globals.css            # Tailwind directives & animated edge styles
│   │   └── api/
│   │       ├── inngest/route.ts   # Inngest API serve handler (GET, POST, PUT)
│   │       └── workflow/run/route.ts # Dual-engine workflow execution endpoint
│   └── components/
│       ├── flow/
│       │   ├── FlowEditor.tsx     # React Flow canvas setup with minimap & controls
│       │   ├── DecisionNode.tsx   # Custom AI Decision Node with inline prompt editor
│       │   ├── TerminalNode.tsx   # Outcome leaf node
│       │   ├── YesEdge.tsx        # Green YES branch edge with animated dash
│       │   └── NoEdge.tsx         # Red NO branch edge with animated dash
│       └── panel/
│           ├── WorkflowToolbar.tsx# Action bar (Add nodes, Presets, Save, Export, Run)
│           ├── ExecutionLogs.tsx  # Terminal logs drawer with filters & step metrics
│           └── RunModal.tsx       # Prompt submission dialog with sample test inputs
└── README.md                      # Comprehensive documentation
```

---

## ⚡ Quickstart

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment (Optional)
If you have an OpenAI API key, configure it in `.env.local`:
```env
OPENAI_API_KEY="sk-..."
INNGEST_EVENT_KEY="your-inngest-event-key"
INNGEST_SIGNING_KEY="your-inngest-signing-key"
```
> **Note**: If `OPENAI_API_KEY` is not provided, the engine automatically uses an intelligent local heuristic evaluator, so you can test end-to-end without spending credits.

### 3. Start Next.js Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. (Optional) Start Inngest Dev Server
In a separate terminal, run the Inngest local dashboard:
```bash
npx inngest-cli@latest dev -u http://localhost:3000/api/inngest
```
Visit [http://localhost:8288](http://localhost:8288) to inspect Inngest event payloads, step replays, and step retries.

---

## 🧪 Testing the Workflow

1. Click **"Run Workflow"** on the top navigation bar.
2. Choose one of the quick test inputs:
   - *"My account is locked and payment failed when upgrading to Pro plan."* (Routes to Technical Support)
   - *"We are an enterprise company with 500 users looking for custom contract pricing."* (Routes to Sales Executive)
3. Click **"Execute AI Flow"**.
4. Watch the flow in action:
   - Evaluated nodes light up amber (`RUNNING`) and then green or red (`YES` / `NO`).
   - The traversed edge animates with a glowing dash.
   - The bottom **Execution Logs** drawer streams step-by-step rationale, token metrics, and execution time.
