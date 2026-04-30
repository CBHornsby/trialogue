"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import RolePanel from "@/components/RolePanel";
import {
  streamDebate, resumeDebate, getSettings, checkBackendHealth,
  type DebateEvent,
} from "@/lib/api";

type RoleKey = "proposer" | "critic" | "judge";
type Status = "pending" | "active" | "complete" | "error" | "stopped";
type DebateStatus = "idle" | "running" | "complete" | "error" | "stopped";

interface RoleState {
  text: string;
  status: Status;
  modelLabel?: string;
  errorMessage?: string;
  inputTokens?: number;
  outputTokens?: number;
}

const initialRoleState: Record<RoleKey, RoleState> = {
  proposer: { text: "", status: "pending" },
  critic: { text: "", status: "pending" },
  judge: { text: "", status: "pending" },
};

export default function MainPage() {
  const [question, setQuestion] = useState("");
  const [debateStatus, setDebateStatus] = useState<DebateStatus>("idle");
  const [roles, setRoles] = useState<Record<RoleKey, RoleState>>(initialRoleState);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [keysConfigured, setKeysConfigured] = useState<boolean | null>(null);
  const [debateId, setDebateId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const debating = debateStatus === "running";

  useEffect(() => {
    (async () => {
      const ok = await checkBackendHealth();
      setBackendOk(ok);
      if (ok) {
        try {
          const s = await getSettings();
          const needed = new Set([s.proposer_provider, s.critic_provider, s.judge_provider]);
          const map: Record<string, boolean> = {
            claude: s.anthropic_api_key_set,
            openai: s.openai_api_key_set,
            gemini: s.google_api_key_set,
          };
          const allSet = Array.from(needed).every(p => map[p]);
          setKeysConfigured(allSet);
        } catch {
          setKeysConfigured(false);
        }
      }
    })();
  }, []);

  async function handleSubmit() {
    if (!question.trim() || debating) return;
    setDebateStatus("running");
    setHasStarted(true);
    setGlobalError(null);
    setRoles(initialRoleState);
    setDebateId(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamDebate(question, handleEvent, controller.signal);
    } catch (err: any) {
      if (err.name === "AbortError") {
        setDebateStatus(prev => prev === "running" ? "stopped" : prev);
      } else {
        setGlobalError(err.message || "Something went wrong");
        setDebateStatus("error");
      }
    } finally {
      abortRef.current = null;
    }
  }

  async function handleRetry(fromRole: RoleKey) {
    if (!debateId || debating) return;

    setDebateStatus("running");
    setGlobalError(null);

    // Reset just the role being retried + any later roles
    const roleOrder: RoleKey[] = ["proposer", "critic", "judge"];
    const fromIdx = roleOrder.indexOf(fromRole);
    setRoles(prev => {
      const next = { ...prev };
      for (let i = fromIdx; i < roleOrder.length; i++) {
        next[roleOrder[i]] = { text: "", status: "pending" };
      }
      return next;
    });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await resumeDebate(debateId, fromRole, handleEvent, controller.signal);
    } catch (err: any) {
      if (err.name === "AbortError") {
        setDebateStatus(prev => prev === "running" ? "stopped" : prev);
      } else {
        setGlobalError(err.message || "Retry failed");
        setDebateStatus("error");
      }
    } finally {
      abortRef.current = null;
    }
  }

  function handleEvent(event: DebateEvent) {
    if (event.type === "debate_started") {
      setDebateId(event.debate_id);
      return;
    }
    if (event.type === "done") {
      setDebateStatus("complete");
      return;
    }

    setRoles(prev => {
      const next = { ...prev };
      switch (event.type) {
        case "role_start": {
          const key = event.role as RoleKey;
          next[key] = {
            ...next[key],
            status: "active",
            modelLabel: `${event.provider} · ${event.model}`,
            text: "",
            errorMessage: undefined,
          };
          break;
        }
        case "token": {
          const key = event.role as RoleKey;
          next[key] = { ...next[key], text: next[key].text + event.content };
          break;
        }
        case "usage": {
          const key = event.role as RoleKey;
          next[key] = {
            ...next[key],
            inputTokens: event.input,
            outputTokens: event.output,
          };
          break;
        }
        case "role_complete": {
          const key = event.role as RoleKey;
          next[key] = { ...next[key], status: "complete" };
          break;
        }
        case "error": {
          if (event.role) {
            const key = event.role as RoleKey;
            next[key] = { ...next[key], status: "error", errorMessage: event.message };
          } else {
            setGlobalError(event.message);
          }
          setDebateStatus("error");
          break;
        }
        case "stopped": {
          if (event.role) {
            const key = event.role as RoleKey;
            next[key] = { ...next[key], status: "stopped" };
          }
          setDebateStatus("stopped");
          break;
        }
      }
      return next;
    });
  }

  function handleStop() {
    abortRef.current?.abort();
  }

  function handleNew() {
    setQuestion("");
    setRoles(initialRoleState);
    setHasStarted(false);
    setGlobalError(null);
    setDebateStatus("idle");
    setDebateId(null);
  }

  // Compute totals across all roles with usage data
  const totalInput = Object.values(roles).reduce((sum, r) => sum + (r.inputTokens || 0), 0);
  const totalOutput = Object.values(roles).reduce((sum, r) => sum + (r.outputTokens || 0), 0);
  const hasAnyTokens = totalInput > 0 || totalOutput > 0;

  // Backend not running
  if (backendOk === false) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md text-center">
          <h1 className="font-display text-3xl text-ink-100 mb-4">Backend offline</h1>
          <p className="text-ink-300 mb-6">
            The Python backend isn&apos;t responding at <code className="text-proposer">localhost:8000</code>.
            If you launched via the script, give it a few seconds and refresh.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm font-mono text-proposer hover:text-proposer/80 uppercase tracking-wider"
          >
            retry
          </button>
        </div>
      </main>
    );
  }

  if (backendOk === null) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-ink-400 font-mono text-sm">connecting...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen max-w-3xl mx-auto px-6 sm:px-8 py-12 sm:py-16">
      <header className="mb-12 flex items-baseline justify-between">
        <div>
          <h1 className="font-display text-4xl sm:text-5xl text-ink-100 tracking-tight leading-none">
            Trialogue
          </h1>
          <p className="text-ink-400 font-display italic text-sm mt-2">
            Three models, one answer.
          </p>
        </div>
        <Link
          href="/settings"
          className="text-xs font-mono uppercase tracking-widest text-ink-400 hover:text-ink-100 transition-colors"
        >
          settings
        </Link>
      </header>

      {keysConfigured === false && (
        <div className="mb-8 px-5 py-4 border border-proposer/40 bg-proposer/5 rounded">
          <p className="text-sm text-ink-100">
            <span className="font-display text-proposer">Setup needed.</span>{" "}
            One or more API keys aren&apos;t configured for your selected models.{" "}
            <Link href="/settings" className="text-proposer underline underline-offset-2 hover:text-proposer/80">
              Configure keys
            </Link>
          </p>
        </div>
      )}

      {!hasStarted && (
        <section className="animate-slide-up">
          <label className="block font-display italic text-ink-300 text-sm mb-3">
            Pose a question worth deliberating.
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What's the best architecture for...&#10;&#10;Is X actually true that...&#10;&#10;Should I approach Y by..."
            rows={5}
            className="w-full bg-ink-900 border border-ink-700 focus:border-ink-500 rounded-md px-5 py-4 text-ink-100 placeholder:text-ink-500 font-body text-[15px] leading-relaxed resize-none focus:outline-none transition-colors"
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
          <div className="mt-4 flex items-center justify-between">
            <p className="text-ink-500 text-xs font-mono">
              ⌘+Enter to submit · ~30-90 seconds per debate
            </p>
            <button
              onClick={handleSubmit}
              disabled={!question.trim() || keysConfigured === false}
              className="
                px-6 py-2.5 bg-ink-100 text-ink-950
                font-mono text-xs uppercase tracking-widest
                rounded hover:bg-ink-50 transition-colors
                disabled:opacity-30 disabled:cursor-not-allowed
              "
            >
              Begin
            </button>
          </div>
        </section>
      )}

      {hasStarted && (
        <section className="animate-fade-in">
          <div className="mb-10 pb-6 border-b border-ink-700">
            <p className="text-ink-400 font-display italic text-xs uppercase tracking-widest mb-2">
              Question
            </p>
            <p className="text-ink-100 text-base leading-relaxed">
              {question}
            </p>
          </div>

          <div className="ml-3 sm:ml-4">
            {(["proposer", "critic", "judge"] as RoleKey[]).map(roleKey => {
              const roleState = roles[roleKey];
              // Retry is only enabled when not currently running and we have a debate ID
              const canRetry = !debating && debateId !== null
                && (roleState.status === "error" || roleState.status === "stopped");

              return (
                <RolePanel
                  key={roleKey}
                  role={roleKey}
                  text={roleState.text}
                  status={roleState.status}
                  modelLabel={roleState.modelLabel}
                  errorMessage={roleState.errorMessage}
                  inputTokens={roleState.inputTokens}
                  outputTokens={roleState.outputTokens}
                  canRetry={canRetry}
                  onRetry={() => handleRetry(roleKey)}
                />
              );
            })}
          </div>

          {globalError && (
            <div className="mt-6 px-5 py-4 border border-red-900/40 bg-red-950/20 rounded text-red-300 text-sm font-mono">
              {globalError}
            </div>
          )}

          <div className="mt-10 pt-6 border-t border-ink-700 flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <DebateStatusPill status={debateStatus} />
              {hasAnyTokens && (
                <span className="text-xs font-mono text-ink-400 tracking-wider">
                  total: {totalInput.toLocaleString()} in · {totalOutput.toLocaleString()} out
                </span>
              )}
            </div>
            <div className="flex items-center gap-4">
              {debating && (
                <button
                  onClick={handleStop}
                  className="text-xs font-mono uppercase tracking-widest text-ink-300 hover:text-ink-100 transition-colors"
                >
                  stop
                </button>
              )}
              <button
                onClick={handleNew}
                disabled={debating}
                className="
                  px-5 py-2 border border-ink-600 text-ink-200
                  font-mono text-xs uppercase tracking-widest
                  rounded hover:border-ink-400 hover:text-ink-100 transition-colors
                  disabled:opacity-30 disabled:cursor-not-allowed
                "
              >
                New question
              </button>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}

function DebateStatusPill({ status }: { status: DebateStatus }) {
  if (status === "running") {
    return (
      <span className="text-xs font-mono uppercase tracking-widest text-ink-200 flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-ink-100 animate-pulse" />
        running
      </span>
    );
  }
  if (status === "complete") {
    return (
      <span className="text-xs font-mono uppercase tracking-widest text-judge">
        ● debate complete
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="text-xs font-mono uppercase tracking-widest text-red-400">
        ● debate failed
      </span>
    );
  }
  if (status === "stopped") {
    return (
      <span className="text-xs font-mono uppercase tracking-widest text-ink-400">
        ● debate stopped
      </span>
    );
  }
  return null;
}
