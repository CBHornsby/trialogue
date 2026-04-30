"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSettings, updateSettings, listProviderModels, clearApiKey } from "@/lib/api";

type Provider = "claude" | "openai" | "gemini";
type RoleKey = "proposer" | "critic" | "judge";

interface ModelOption {
  provider: Provider;
  model: string;
  label: string;
}

// Fallback list shown before the user fetches live models from the API.
// Use "Refresh available models" on each role to get the actual list from your account.
const FALLBACK_MODELS: ModelOption[] = [
  { provider: "claude", model: "claude-opus-4-7", label: "Claude Opus 4.7" },
  { provider: "claude", model: "claude-opus-4-6", label: "Claude Opus 4.6" },
  { provider: "claude", model: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
  { provider: "openai", model: "gpt-5.5", label: "GPT-5.5" },
  { provider: "openai", model: "gpt-5.4", label: "GPT-5.4" },
  { provider: "openai", model: "gpt-5.4-mini", label: "GPT-5.4 mini" },
  { provider: "gemini", model: "gemini-3.1-pro-preview", label: "Gemini 3.1 Pro Preview" },
  { provider: "gemini", model: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
];

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [googleKey, setGoogleKey] = useState("");

  const [keysSetStatus, setKeysSetStatus] = useState({
    anthropic: false,
    openai: false,
    google: false,
  });

  const [roleConfig, setRoleConfig] = useState<Record<RoleKey, { provider: Provider; model: string }>>({
    proposer: { provider: "claude", model: "claude-opus-4-7" },
    critic: { provider: "openai", model: "gpt-5.5" },
    judge: { provider: "gemini", model: "gemini-3.1-pro-preview" },
  });

  // Live models fetched per provider - empty until user clicks "refresh"
  const [liveModels, setLiveModels] = useState<Record<Provider, string[]>>({
    claude: [],
    openai: [],
    gemini: [],
  });
  const [refreshing, setRefreshing] = useState<Provider | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  async function refreshModels(provider: Provider) {
    setRefreshing(provider);
    setRefreshError(null);
    try {
      const models = await listProviderModels(provider);
      setLiveModels(prev => ({ ...prev, [provider]: models }));
    } catch (e: any) {
      setRefreshError(e.message || `Failed to fetch ${provider} models`);
    } finally {
      setRefreshing(null);
    }
  }

  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        setKeysSetStatus({
          anthropic: s.anthropic_api_key_set,
          openai: s.openai_api_key_set,
          google: s.google_api_key_set,
        });
        setRoleConfig({
          proposer: { provider: s.proposer_provider, model: s.proposer_model },
          critic: { provider: s.critic_provider, model: s.critic_model },
          judge: { provider: s.judge_provider, model: s.judge_model },
        });
      } catch (e: any) {
        setError(e.message || "Failed to load settings");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateSettings({
        anthropic_api_key: anthropicKey,
        openai_api_key: openaiKey,
        google_api_key: googleKey,
        proposer_provider: roleConfig.proposer.provider,
        proposer_model: roleConfig.proposer.model,
        critic_provider: roleConfig.critic.provider,
        critic_model: roleConfig.critic.model,
        judge_provider: roleConfig.judge.provider,
        judge_model: roleConfig.judge.model,
      });
      setSavedAt(Date.now());
      // Refresh status display
      if (anthropicKey) setKeysSetStatus(s => ({ ...s, anthropic: true }));
      if (openaiKey) setKeysSetStatus(s => ({ ...s, openai: true }));
      if (googleKey) setKeysSetStatus(s => ({ ...s, google: true }));
      // Clear the inputs (we don't want to display keys after saving)
      setAnthropicKey("");
      setOpenaiKey("");
      setGoogleKey("");
    } catch (e: any) {
      setError(e.message || "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleClearKey(provider: "anthropic" | "openai" | "google") {
    if (!confirm(`Remove the saved ${provider} API key?`)) return;
    try {
      await clearApiKey(provider);
      setKeysSetStatus(s => ({ ...s, [provider]: false }));
      // Also clear the input field for that provider
      if (provider === "anthropic") setAnthropicKey("");
      if (provider === "openai") setOpenaiKey("");
      if (provider === "google") setGoogleKey("");
    } catch (e: any) {
      setError(e.message || "Failed to clear key");
    }
  }

  function setRole(key: RoleKey, provider: Provider, model: string) {
    setRoleConfig(prev => ({ ...prev, [key]: { provider, model } }));
  }

  // Enforce one-model-per-role uniqueness with a soft check (visual warning, not blocked)
  const allModels = [
    `${roleConfig.proposer.provider}/${roleConfig.proposer.model}`,
    `${roleConfig.critic.provider}/${roleConfig.critic.model}`,
    `${roleConfig.judge.provider}/${roleConfig.judge.model}`,
  ];
  const hasDuplicate = new Set(allModels).size !== allModels.length;

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-ink-400 font-mono text-sm">loading...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen max-w-3xl mx-auto px-6 sm:px-8 py-12 sm:py-16">
      <header className="mb-12 flex items-baseline justify-between">
        <div>
          <h1 className="font-display text-4xl text-ink-100 tracking-tight">
            Settings
          </h1>
          <p className="text-ink-400 font-display italic text-sm mt-1">
            Configure providers and roles.
          </p>
        </div>
        <Link
          href="/"
          className="text-xs font-mono uppercase tracking-widest text-ink-400 hover:text-ink-100 transition-colors"
        >
          ← back
        </Link>
      </header>

      {/* API Keys Section */}
      <section className="mb-12">
        <h2 className="font-display text-2xl text-ink-100 mb-2">API Keys</h2>
        <p className="text-ink-400 text-sm mb-6 font-display italic">
          Stored locally in <code className="text-proposer not-italic">~/.debate-tool/config.json</code>. Never sent anywhere except the providers themselves.
        </p>

        <div className="space-y-5">
          <KeyInput
            label="Anthropic"
            sublabel="for Claude models"
            value={anthropicKey}
            onChange={setAnthropicKey}
            placeholder="sk-ant-..."
            isSet={keysSetStatus.anthropic}
            link="https://console.anthropic.com"
            onClear={() => handleClearKey("anthropic")}
          />
          <KeyInput
            label="OpenAI"
            sublabel="for GPT models"
            value={openaiKey}
            onChange={setOpenaiKey}
            placeholder="sk-..."
            isSet={keysSetStatus.openai}
            link="https://platform.openai.com/api-keys"
            onClear={() => handleClearKey("openai")}
          />
          <KeyInput
            label="Google"
            sublabel="for Gemini models"
            value={googleKey}
            onChange={setGoogleKey}
            placeholder="AIza..."
            isSet={keysSetStatus.google}
            link="https://aistudio.google.com/app/apikey"
            onClear={() => handleClearKey("google")}
          />
        </div>
      </section>

      {/* Roles Section */}
      <section className="mb-12">
        <h2 className="font-display text-2xl text-ink-100 mb-2">Roles</h2>
        <p className="text-ink-400 text-sm mb-6 font-display italic">
          Different models for different roles surface different blind spots.
        </p>

        <div className="space-y-5">
          <RoleConfig
            roleKey="proposer"
            label="I. Proposer"
            description="Drafts the initial answer."
            colorClass="text-proposer"
            value={roleConfig.proposer}
            onChange={(p, m) => setRole("proposer", p, m)}
            liveModels={liveModels}
            onRefresh={refreshModels}
            refreshing={refreshing}
          />
          <RoleConfig
            roleKey="critic"
            label="II. Critic"
            description="Adversarially reviews the proposer's answer."
            colorClass="text-critic"
            value={roleConfig.critic}
            onChange={(p, m) => setRole("critic", p, m)}
            liveModels={liveModels}
            onRefresh={refreshModels}
            refreshing={refreshing}
          />
          <RoleConfig
            roleKey="judge"
            label="III. Judge"
            description="Synthesizes final answer from both."
            colorClass="text-judge"
            value={roleConfig.judge}
            onChange={(p, m) => setRole("judge", p, m)}
            liveModels={liveModels}
            onRefresh={refreshModels}
            refreshing={refreshing}
          />
        </div>

        {refreshError && (
          <p className="mt-3 text-xs text-red-400 font-mono">{refreshError}</p>
        )}

        {hasDuplicate && (
          <p className="mt-4 text-xs text-proposer/80 font-mono">
            ⚠ Same model assigned to multiple roles — the debate works best with three different models.
          </p>
        )}
      </section>

      {/* Save bar */}
      <div className="sticky bottom-0 -mx-8 px-8 py-5 bg-ink-950/95 backdrop-blur-sm border-t border-ink-700 flex items-center justify-between">
        <div className="text-xs font-mono">
          {error && <span className="text-red-400">{error}</span>}
          {!error && savedAt && (
            <span className="text-judge animate-fade-in">saved · {new Date(savedAt).toLocaleTimeString()}</span>
          )}
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="
            px-6 py-2.5 bg-ink-100 text-ink-950
            font-mono text-xs uppercase tracking-widest rounded
            hover:bg-ink-50 transition-colors
            disabled:opacity-50
          "
        >
          {saving ? "saving..." : "Save settings"}
        </button>
      </div>
    </main>
  );
}

function KeyInput({
  label,
  sublabel,
  value,
  onChange,
  placeholder,
  isSet,
  link,
  onClear,
}: {
  label: string;
  sublabel: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  isSet: boolean;
  link: string;
  onClear?: () => void;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <label className="font-display text-base text-ink-100">
          {label}
          <span className="ml-2 text-ink-400 italic text-xs">{sublabel}</span>
        </label>
        <div className="flex items-center gap-3">
          {isSet && (
            <span className="text-[10px] font-mono uppercase tracking-widest text-judge">
              ● configured
            </span>
          )}
          {isSet && onClear && (
            <button
              onClick={onClear}
              className="text-[11px] font-mono text-ink-500 hover:text-red-400 transition-colors"
            >
              clear
            </button>
          )}
          <a
            href={link}
            target="_blank"
            rel="noreferrer"
            className="text-[11px] font-mono text-ink-400 hover:text-ink-200 transition-colors"
          >
            get key ↗
          </a>
        </div>
      </div>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={isSet ? "•••••••• (leave blank to keep current)" : placeholder}
        className="w-full bg-ink-900 border border-ink-700 focus:border-ink-500 rounded px-4 py-2.5 text-ink-100 placeholder:text-ink-500 font-mono text-sm focus:outline-none transition-colors"
      />
    </div>
  );
}

function RoleConfig({
  roleKey,
  label,
  description,
  colorClass,
  value,
  onChange,
  liveModels,
  onRefresh,
  refreshing,
}: {
  roleKey: RoleKey;
  label: string;
  description: string;
  colorClass: string;
  value: { provider: Provider; model: string };
  onChange: (provider: Provider, model: string) => void;
  liveModels: Record<Provider, string[]>;
  onRefresh: (provider: Provider) => void;
  refreshing: Provider | null;
}) {
  const [customModel, setCustomModel] = useState(false);

  // Models to show in dropdown: live if fetched, otherwise fallback
  const liveForProvider = liveModels[value.provider];
  const usingLive = liveForProvider && liveForProvider.length > 0;

  let dropdownOptions: ModelOption[];
  if (usingLive) {
    dropdownOptions = liveForProvider.map(m => ({
      provider: value.provider,
      model: m,
      label: m,
    }));
  } else {
    dropdownOptions = FALLBACK_MODELS.filter(o => o.provider === value.provider);
  }

  // If current model isn't in the dropdown, fall back to custom mode
  const matchedOption = dropdownOptions.find(o => o.model === value.model);
  const showCustom = customModel || !matchedOption;
  const isRefreshing = refreshing === value.provider;

  return (
    <div className="bg-ink-900/50 border border-ink-700 rounded-md px-5 py-4">
      <div className="flex items-baseline justify-between mb-2">
        <h3 className={`font-display text-lg ${colorClass}`}>{label}</h3>
        <div className="flex items-center gap-3">
          <button
            onClick={() => onRefresh(value.provider)}
            disabled={isRefreshing}
            className="text-[10px] font-mono uppercase tracking-widest text-ink-400 hover:text-ink-200 transition-colors disabled:opacity-40"
            title="Fetch the live list of models from this provider's API"
          >
            {isRefreshing ? "fetching..." : usingLive ? "↻ refresh" : "↻ fetch live"}
          </button>
          <button
            onClick={() => setCustomModel(!customModel)}
            className="text-[10px] font-mono uppercase tracking-widest text-ink-400 hover:text-ink-200 transition-colors"
          >
            {showCustom ? "use list" : "custom"}
          </button>
        </div>
      </div>
      <p className="text-ink-400 text-xs italic mb-3 font-display">{description}</p>

      {!showCustom ? (
        <div>
          <select
            value={`${value.provider}/${value.model}`}
            onChange={(e) => {
              const [provider, ...modelParts] = e.target.value.split("/");
              onChange(provider as Provider, modelParts.join("/"));
            }}
            className="w-full bg-ink-800 border border-ink-700 focus:border-ink-500 rounded px-4 py-2 text-ink-100 font-mono text-sm focus:outline-none"
          >
            {dropdownOptions.map(opt => (
              <option key={`${opt.provider}/${opt.model}`} value={`${opt.provider}/${opt.model}`}>
                {opt.label}
              </option>
            ))}
          </select>
          {!usingLive && (
            <p className="text-[10px] text-ink-500 mt-1.5 italic">
              Showing fallback list. Click &quot;fetch live&quot; for actual available models from your account.
            </p>
          )}
          {usingLive && (
            <p className="text-[10px] text-judge mt-1.5 font-mono">
              ● live ({liveForProvider.length} models)
            </p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-2">
          <select
            value={value.provider}
            onChange={(e) => onChange(e.target.value as Provider, value.model)}
            className="bg-ink-800 border border-ink-700 focus:border-ink-500 rounded px-3 py-2 text-ink-100 font-mono text-sm focus:outline-none"
          >
            <option value="claude">Anthropic</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Google</option>
          </select>
          <input
            type="text"
            value={value.model}
            onChange={(e) => onChange(value.provider, e.target.value)}
            placeholder="model-name"
            className="col-span-2 bg-ink-800 border border-ink-700 focus:border-ink-500 rounded px-3 py-2 text-ink-100 placeholder:text-ink-500 font-mono text-sm focus:outline-none"
          />
        </div>
      )}
    </div>
  );
}
