import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Save, Loader2, Info, CheckCircle } from 'lucide-react';
import { listAgentProfiles, saveAgentProfile } from '../api';

const DEFAULT_PROFILE = {
  name: 'Default',
  model: 'gemini-2.5-pro',
  temperature: 0.3,
  system_instructions: `You are an expert phishing threat analyst. Analyze the following content and evidence to produce:
1. A concise, plain-English explanation of why this content is or is not a phishing threat.
2. A recommended action for the user.
3. Highlight the most critical evidence items.

Be factual and cite specific evidence. Never fabricate indicators.`,
  score_weights: {
    layer1_weight: 40,
    layer2_weight: 25,
    base_score: 0,
    evidence_cap: 100,
  },
};

export default function AgentSettingsPage() {
  const [profiles, setProfiles] = useState([]);
  const [current, setCurrent] = useState(DEFAULT_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    listAgentProfiles()
      .then(data => {
        setProfiles(data || []);
        if (data?.length > 0) {
          setCurrent(data[0]);
        }
      })
      .catch(() => setProfiles([]))
      .finally(() => setLoading(false));
  }, []);

  function handleChange(field, value) {
    setCurrent(prev => ({ ...prev, [field]: value }));
    setSaved(false);
  }

  function handleWeightChange(field, value) {
    setCurrent(prev => ({
      ...prev,
      score_weights: { ...prev.score_weights, [field]: parseInt(value) || 0 },
    }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await saveAgentProfile(current);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
    setSaving(false);
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-1">
        <Settings size={22} style={{ color: 'var(--color-accent)' }} />
        <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>Agent Settings</h1>
      </div>
      <p className="text-sm mb-8" style={{ color: 'var(--color-text-secondary)' }}>
        Customize the LLM triage agent behavior and scoring weights
      </p>

      {/* ── Info banner ────────────────────────────────── */}
      <motion.div
        initial={{ y: 15, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex items-start gap-3 rounded-lg px-4 py-3 mb-8"
        style={{
          backgroundColor: 'rgba(96,165,250,0.08)',
          border: '1px solid rgba(96,165,250,0.2)',
        }}
      >
        <Info size={16} style={{ color: 'var(--color-info)', flexShrink: 0, marginTop: 2 }} />
        <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          <strong style={{ color: 'var(--color-info)' }}>Note:</strong> The LLM agent only explains and narrates.
          Risk scores are deterministically computed from Layer 1 + 2 evidence. Changing the model or temperature affects
          explanation quality only — not the score itself.
        </div>
      </motion.div>

      {/* ── Model Selection ────────────────────────────── */}
      <motion.div
        initial={{ y: 15, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.05 }}
        className="card mb-4"
        style={{ padding: '1.25rem' }}
      >
        <span className="section-label normal-case block mb-3">Model Configuration</span>
        <div className="flex flex-col gap-4">
          <div>
            <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--color-text-secondary)' }}>
              Profile Name
            </label>
            <input
              type="text"
              value={current.name}
              onChange={e => handleChange('name', e.target.value)}
              placeholder="My Custom Profile"
            />
          </div>
          <div>
            <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--color-text-secondary)' }}>
              LLM Model
            </label>
            <select value={current.model} onChange={e => handleChange('model', e.target.value)}>
              <option value="gemini-2.5-pro">Gemini 2.5 Pro (Recommended)</option>
              <option value="gemini-2.5-flash">Gemini 2.5 Flash (Faster)</option>
              <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--color-text-secondary)' }}>
              Temperature: {current.temperature}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={current.temperature}
              onChange={e => handleChange('temperature', parseFloat(e.target.value))}
              className="w-full"
              style={{
                accentColor: 'var(--color-accent)',
                height: 4,
                border: 'none',
                background: 'var(--color-surface-alt)',
                padding: 0,
              }}
            />
            <div className="flex justify-between text-[10px] font-mono mt-1" style={{ color: 'var(--color-text-muted)' }}>
              <span>Precise (0)</span>
              <span>Creative (1)</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── System Instructions ────────────────────────── */}
      <motion.div
        initial={{ y: 15, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="card mb-4"
        style={{ padding: '1.25rem' }}
      >
        <span className="section-label block mb-3">System Instructions</span>
        <textarea
          rows={8}
          value={current.system_instructions}
          onChange={e => handleChange('system_instructions', e.target.value)}
          className="font-mono text-xs overflow-y-auto"
          style={{ resize: 'vertical', minHeight: 120 }}
        />
      </motion.div>

      {/* ── Score Weights ──────────────────────────────── */}
      <motion.div
        initial={{ y: 15, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.15 }}
        className="card mb-6"
        style={{ padding: '1.25rem' }}
      >
        <span className="section-label block mb-3">Scoring Weights</span>
        <div className="grid grid-cols-2 gap-4">
          {[
            { key: 'layer1_weight', label: 'Layer 1 (Deterministic) Weight', max: 100 },
            { key: 'layer2_weight', label: 'Layer 2 (Behavioral) Weight', max: 100 },
            { key: 'base_score', label: 'Base Score', max: 50 },
            { key: 'evidence_cap', label: 'Evidence Cap', max: 200 },
          ].map(w => (
            <div key={w.key}>
              <label
                htmlFor={w.key}
                className="text-xs font-medium block mb-1.5"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                {w.label}
              </label>
              <input
                id={w.key}
                type="number"
                min="0"
                max={w.max}
                value={current.score_weights?.[w.key] ?? 0}
                onChange={e => handleWeightChange(w.key, e.target.value)}
                className="font-mono text-sm"
                aria-label={w.label}
                required
              />
            </div>
          ))}
        </div>
      </motion.div>

      {/* ── Save Button ───────────────────────────────── */}
      <div className="px-[21px]">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary w-full justify-center"
          style={{ padding: '12px' }}
        >
          {saving ? (
            <><Loader2 size={14} className="animate-spin" /> Saving...</>
          ) : saved ? (
            <><CheckCircle size={14} /> Saved!</>
          ) : (
            <><Save size={14} /> Save Profile</>
          )}
        </button>
      </div>
    </div>
  );
}
