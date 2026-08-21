import React, { useState } from 'react';
import { Settings as SettingsIcon, Key, Sliders, Shield, Save, Check } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';

export const Settings: React.FC = () => {
  const [autoMode, setAutoMode] = useState(true);
  const [minConfidence, setMinConfidence] = useState(85);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200 max-w-4xl">
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          Merchant Settings & AI Engine Configuration
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Configure automation policies, risk confidence thresholds, gateway credentials, and Webhooks.
        </p>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-6 border-b border-fintech-border pb-4">
          <div>
            <h3 className="text-base font-semibold text-fintech-textPrimary">Autonomous Mode Controls</h3>
            <p className="text-xs text-fintech-textMuted">Enable or restrict AI engine autonomous execution</p>
          </div>
          <Badge variant="ai">AI Agent Active</Badge>
        </div>

        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <span className="block text-xs font-semibold text-fintech-textPrimary">
                Fully Autonomous Recovery Actions
              </span>
              <span className="block text-xs text-fintech-textMuted mt-0.5">
                Automatically execute retry schedules and dunning flows without manual approval
              </span>
            </div>
            <button
              onClick={() => setAutoMode(!autoMode)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${
                autoMode ? 'bg-brand-primary' : 'bg-slate-300'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transition-transform ${
                  autoMode ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="border-t border-fintech-border pt-4">
            <label className="block text-xs font-semibold text-fintech-textPrimary mb-1">
              Minimum AI Confidence Threshold for Autonomous Execution ({minConfidence}%)
            </label>
            <input
              type="range"
              min="50"
              max="99"
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-full h-2 bg-surface-muted rounded-lg appearance-none cursor-pointer accent-brand-primary"
            />
            <span className="text-[11px] text-fintech-textMuted mt-1 block">
              Decisions below {minConfidence}% confidence will require manual human approval in the dashboard.
            </span>
          </div>
        </div>
      </Card>

      <Card>
        <div className="mb-4 border-b border-fintech-border pb-3">
          <h3 className="text-base font-semibold text-fintech-textPrimary">API Keys & Ingestion Webhook</h3>
          <p className="text-xs text-fintech-textMuted">Connect payment gateways (Razorpay, Stripe, PayU)</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-fintech-textMuted mb-1">Webhook Ingestion Endpoint</label>
            <input
              type="text"
              readOnly
              value="https://api.recoverai.io/v1/webhooks/ingest/merchant_acme_01"
              className="w-full px-3 py-2 bg-surface-muted border border-fintech-border rounded-elem font-mono text-xs text-fintech-textPrimary"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-fintech-textMuted mb-1">RecoverAI Secret API Key</label>
            <input
              type="password"
              readOnly
              value="sk_live_rcvr_991823190238120391"
              className="w-full px-3 py-2 bg-surface-muted border border-fintech-border rounded-elem font-mono text-xs text-fintech-textPrimary"
            />
          </div>
        </div>
      </Card>

      <div className="flex justify-end">
        <Button variant="primary" size="md" onClick={handleSave} className="gap-2">
          {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          <span>{saved ? 'Saved Successfully' : 'Save Settings'}</span>
        </Button>
      </div>
    </div>
  );
};
