"use client";

import { useState, useEffect } from "react";

type Role = "proposer" | "critic" | "judge";

interface RolePanelProps {
  role: Role;
  text: string;
  status: "pending" | "active" | "complete" | "error" | "stopped";
  modelLabel?: string;
  errorMessage?: string;
  inputTokens?: number;
  outputTokens?: number;
  canRetry?: boolean;
  onRetry?: () => void;
}

const ROLE_META: Record<Role, { label: string; subtitle: string; colorClass: string; borderClass: string; numeral: string }> = {
  proposer: {
    label: "Proposer",
    subtitle: "First take, given as a peer would",
    colorClass: "text-proposer",
    borderClass: "border-proposer/40",
    numeral: "I",
  },
  critic: {
    label: "Critic",
    subtitle: "Calibrated review against independent criteria",
    colorClass: "text-critic",
    borderClass: "border-critic/40",
    numeral: "II",
  },
  judge: {
    label: "Judge",
    subtitle: "Synthesis - final answer first",
    colorClass: "text-judge",
    borderClass: "border-judge/40",
    numeral: "III",
  },
};

export default function RolePanel({
  role, text, status, modelLabel, errorMessage,
  inputTokens, outputTokens, canRetry, onRetry,
}: RolePanelProps) {
  const meta = ROLE_META[role];
  const [collapsed, setCollapsed] = useState(false);

  const isPending = status === "pending";
  const isActive = status === "active";
  const isComplete = status === "complete";
  const isError = status === "error";
  const isStopped = status === "stopped";

  const hasUsage = (inputTokens !== undefined && inputTokens > 0) || (outputTokens !== undefined && outputTokens > 0);

  return (
    <article
      className={`
        relative border-l-2 ${meta.borderClass}
        pl-6 sm:pl-8 py-4 mb-2
        transition-all duration-500
        ${isPending ? "opacity-30" : "opacity-100"}
      `}
    >
      <div
        className={`
          absolute left-0 top-5 -translate-x-[calc(50%+1px)]
          w-7 h-7 rounded-full
          flex items-center justify-center
          bg-ink-950
          font-display text-xs ${meta.colorClass}
          border ${meta.borderClass}
          ${isActive ? "animate-pulse-slow" : ""}
        `}
      >
        {meta.numeral}
      </div>

      <header className="flex items-baseline justify-between gap-4 mb-3">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h2 className={`font-display text-xl ${meta.colorClass} tracking-tight`}>
            {meta.label}
          </h2>
          {modelLabel && (
            <span className="font-mono text-[11px] text-ink-400 tracking-wider uppercase">
              {modelLabel}
            </span>
          )}
          <StatusPill status={status} />
          {hasUsage && (
            <span className="font-mono text-[10px] text-ink-500 tracking-wider">
              {inputTokens?.toLocaleString() ?? 0} in · {outputTokens?.toLocaleString() ?? 0} out
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {(isError || isStopped) && canRetry && onRetry && (
            <button
              onClick={onRetry}
              className="text-ink-100 hover:text-ink-50 text-xs font-mono uppercase tracking-wider transition-colors border border-ink-500 hover:border-ink-300 rounded px-2 py-0.5"
            >
              ↻ retry
            </button>
          )}
          {(isComplete || isError || isStopped) && (
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="text-ink-400 hover:text-ink-200 text-xs font-mono uppercase tracking-wider transition-colors"
              aria-label={collapsed ? "Expand" : "Collapse"}
            >
              {collapsed ? "expand" : "collapse"}
            </button>
          )}
        </div>
      </header>

      <p className="text-ink-400 text-xs italic mb-4 -mt-1 font-display">
        {meta.subtitle}
      </p>

      {!collapsed && (
        <div className="animate-fade-in">
          {isError && errorMessage && (
            <div className="text-red-400/90 text-sm font-mono bg-red-950/20 border border-red-900/40 rounded px-4 py-3 mb-3">
              {errorMessage}
            </div>
          )}
          {isStopped && !text && (
            <div className="text-ink-400 text-sm font-mono italic">
              Stopped before output started.
            </div>
          )}
          {(text || (isActive && !text)) && (
            <div
              className={`
                prose-content text-ink-100 text-[15px] leading-relaxed
                ${isActive && text.length > 0 ? "stream-caret" : ""}
              `}
            >
              {text || (isActive ? <Thinking /> : null)}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function StatusPill({ status }: { status: string }) {
  if (status === "pending") {
    return (
      <span className="text-[10px] font-mono uppercase tracking-widest text-ink-500">
        waiting
      </span>
    );
  }
  if (status === "active") {
    return (
      <span className="text-[10px] font-mono uppercase tracking-widest text-ink-200 flex items-center gap-1.5">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-ink-100 animate-pulse" />
        live
      </span>
    );
  }
  if (status === "complete") {
    return (
      <span className="text-[10px] font-mono uppercase tracking-widest text-ink-400">
        done
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="text-[10px] font-mono uppercase tracking-widest text-red-400">
        error
      </span>
    );
  }
  if (status === "stopped") {
    return (
      <span className="text-[10px] font-mono uppercase tracking-widest text-ink-400">
        stopped
      </span>
    );
  }
  return null;
}

function Thinking() {
  const [dots, setDots] = useState(".");
  useEffect(() => {
    const id = setInterval(() => {
      setDots(d => (d.length >= 3 ? "." : d + "."));
    }, 400);
    return () => clearInterval(id);
  }, []);
  return <span className="text-ink-400 italic">thinking{dots}</span>;
}
