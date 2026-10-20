"use client";

import React, { useState } from "react";
import { Play, Sparkles, X, MessageSquare } from "lucide-react";

interface RunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRun: (inputMessage: string) => void;
  isRunning: boolean;
  defaultMessage?: string;
}

const SAMPLE_PROMPTS = [
  {
    title: "Billing & Refund Issue",
    text: "We were charged $99.00 twice on invoice #INV-2041 this morning. Please process a refund for the duplicate transaction immediately.",
  },
  {
    title: "Technical Outage",
    text: "Our production cluster in us-east-1 is throwing 500 internal server errors and our team cannot save records. Urgent assistance required!",
  },
  {
    title: "Enterprise Sales Lead",
    text: "Hi! We are evaluating your software for a 120-person engineering team. Can we schedule an enterprise demo and request custom pricing?",
  },
  {
    title: "General FAQ",
    text: "Hello! Where can I find documentation on setting up automated webhook notifications in Slack?",
  },
];

export function RunModal({
  isOpen,
  onClose,
  onRun,
  isRunning,
  defaultMessage = "",
}: RunModalProps) {
  const [message, setMessage] = useState(defaultMessage || SAMPLE_PROMPTS[0].text);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isRunning) return;
    onRun(message.trim());
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl text-slate-100">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Run Decision Flow</h3>
              <p className="text-[11px] text-slate-400">
                Execute AI decision branching powered by Inngest steps.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors p-1"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5 text-blue-400" />
              Inbound Test Message
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              required
              placeholder="Enter customer message or incident description..."
              className="w-full rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs text-slate-200 outline-none focus:border-blue-500 transition-colors resize-none leading-relaxed"
            />
          </div>

          {/* Sample Prompts */}
          <div className="mb-6">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2 block">
              Quick Test Presets
            </span>
            <div className="grid grid-cols-2 gap-2">
              {SAMPLE_PROMPTS.map((p, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setMessage(p.text)}
                  className="rounded-lg border border-slate-800 bg-slate-950/70 p-2 text-left hover:border-slate-700 hover:bg-slate-950 transition-all text-[11px]"
                >
                  <span className="font-semibold text-slate-200 block truncate">{p.title}</span>
                  <span className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">{p.text}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isRunning || !message.trim()}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-blue-500/25 hover:bg-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>{isRunning ? "Executing Inngest Flow..." : "Start Workflow"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
