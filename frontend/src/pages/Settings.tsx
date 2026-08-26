import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, Sliders, Shield, Save, Check, RefreshCw, Copy, AlertTriangle, Lock, HelpCircle } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { api } from '../lib/api';
import { MerchantSettings } from '../types';
import { WebhookDeliveryTable } from '../components/WebhookDeliveryTable';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<MerchantSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [autoMode, setAutoMode] = useState(true);
  const [minConfidence, setMinConfidence] = useState(85);
  const [gateway, setGateway] = useState('sandbox');

  // Secret rotation states
  const [rotating, setRotating] = useState(false);
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showRotateConfirm, setShowRotateConfirm] = useState(false);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getMerchantSettings();
      setSettings(data);
      setAutoMode(data.autonomous_mode ?? true);
      setMinConfidence(Math.round((data.min_ai_confidence_threshold ?? 0.85) * 100));
      setGateway(data.default_gateway ?? 'sandbox');
    } catch (err: any) {
      console.error('Failed to load merchant settings:', err);
      setError(err.message || 'Failed to load merchant settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      const updated = await api.updateMerchantSettings({
        autonomous_mode: autoMode,
        min_ai_confidence_threshold: minConfidence / 100,
        default_gateway: gateway
      });
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      console.error('Failed to save settings:', err);
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleRotateSecret = async () => {
    try {
      setRotating(true);
      setError(null);
      const res = await api.rotateWebhookSecret();
      setNewSecret(res.new_webhook_secret);
      setShowRotateConfirm(false);
      // Refresh masked secret view
      await fetchSettings();
    } catch (err: any) {
      console.error('Failed to rotate webhook secret:', err);
      setError(err.message || 'Failed to rotate secret');
    } finally {
      setRotating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-brand-primary" />
        <span className="ml-3 text-sm text-fintech-textMuted">Loading merchant configuration...</span>
      </div>
    );
  }

  const webhookEndpoint = `${window.location.origin.replace(':3000', ':8000')}/api/v1/webhooks/ingest`;

  return (
    <div className="space-y-6 animate-in fade-in duration-200 max-w-4xl">
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          Merchant Settings & AI Engine Configuration
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Configure automation policies, AI risk confidence thresholds, gateway selection, and Webhook secret rotation.
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-600 rounded-elem p-4 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>Dismiss</Button>
        </div>
      )}

      {/* Autonomous Mode Controls */}
      <Card>
        <div className="flex items-center justify-between mb-6 border-b border-fintech-border pb-4">
          <div>
            <h3 className="text-base font-semibold text-fintech-textPrimary">Autonomous Mode Controls</h3>
            <p className="text-xs text-fintech-textMuted">Enable or restrict AI engine autonomous execution</p>
          </div>
          <Badge variant={autoMode ? 'ai' : 'neutral'}>
            {autoMode ? 'AI Agent Active' : 'Manual Approval Only'}
          </Badge>
        </div>

        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <span className="block text-xs font-semibold text-fintech-textPrimary">
                Fully Autonomous Recovery Actions
              </span>
              <span className="block text-xs text-fintech-textMuted mt-0.5">
                Automatically execute retry schedules and dunning flows when AI confidence meets threshold
              </span>
            </div>
            <button
              onClick={() => setAutoMode(!autoMode)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${
                autoMode ? 'bg-brand-primary' : 'bg-slate-300 dark:bg-slate-700'
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
            <div className="flex justify-between items-center mb-1">
              <label className="block text-xs font-semibold text-fintech-textPrimary">
                Minimum AI Confidence Threshold for Autonomous Execution ({minConfidence}%)
              </label>
              <span className="text-xs font-mono font-bold text-brand-primary">{minConfidence}%</span>
            </div>
            <input
              type="range"
              min="50"
              max="99"
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-full h-2 bg-surface-muted rounded-lg appearance-none cursor-pointer accent-brand-primary"
            />
            <span className="text-[11px] text-fintech-textMuted mt-1 block">
              Decisions below {minConfidence}% confidence will be queued for manual human review in the dashboard.
            </span>
          </div>
        </div>
      </Card>

      {/* Payment Gateway Provider Integration */}
      <Card>
        <div className="mb-4 border-b border-fintech-border pb-3">
          <h3 className="text-base font-semibold text-fintech-textPrimary">Gateway Integration Adapter</h3>
          <p className="text-xs text-fintech-textMuted">Select default recovery execution provider adapter</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-fintech-textMuted mb-1">Default Payment Gateway Adapter</label>
            <select
              value={gateway}
              onChange={(e) => setGateway(e.target.value)}
              className="w-full px-3 py-2 bg-surface-muted border border-fintech-border rounded-elem text-xs font-medium text-fintech-textPrimary focus:outline-none focus:border-brand-primary"
            >
              <option value="sandbox">Sandbox Simulator Adapter (Zero Risk / Built-in)</option>
              <option value="stripe">Stripe Adapter (Production - Multi-region)</option>
              <option value="razorpay">Razorpay Adapter (Production - India/APAC)</option>
              <option value="payu">PayU Adapter (Production)</option>
            </select>
            <p className="text-[11px] text-fintech-textMuted mt-1">
              Currently running in safe Sandbox Simulator mode. External payment gateway API connections are validated before active dispatch.
            </p>
          </div>
        </div>
      </Card>

      {/* Webhook Secret & Security Management */}
      <Card>
        <div className="mb-4 border-b border-fintech-border pb-3 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-fintech-textPrimary">Webhook Security & Secret Management</h3>
            <p className="text-xs text-fintech-textMuted">HMAC-SHA256 signature verification credentials for tenant isolation</p>
          </div>
          <Badge variant="neutral">Strict Security</Badge>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-fintech-textMuted mb-1">Webhook Ingestion URL Endpoint</label>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={webhookEndpoint}
                className="w-full px-3 py-2 bg-surface-muted border border-fintech-border rounded-elem font-mono text-xs text-fintech-textPrimary"
              />
              <Button variant="ghost" size="sm" onClick={() => copyToClipboard(webhookEndpoint)}>
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-fintech-textMuted mb-1">Active HMAC Webhook Secret</label>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={settings?.webhook_secret_masked || '••••••••••••••••••••••••••••••••'}
                className="w-full px-3 py-2 bg-surface-muted border border-fintech-border rounded-elem font-mono text-xs text-fintech-textMuted"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRotateConfirm(true)}
                disabled={rotating}
                className="whitespace-nowrap text-xs gap-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${rotating ? 'animate-spin' : ''}`} />
                <span>Rotate Secret</span>
              </Button>
            </div>
            <p className="text-[11px] text-fintech-textMuted mt-1">
              Existing secret is masked for security. Rotating the secret invalidates previous credentials immediately.
            </p>
          </div>

          {/* Newly Rotated Secret Alert */}
          {newSecret && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-elem p-4 space-y-2">
              <div className="flex items-center gap-2 text-emerald-600 font-semibold text-xs">
                <Check className="w-4 h-4" />
                <span>Webhook Secret Rotated Successfully!</span>
              </div>
              <p className="text-xs text-fintech-textMuted">
                Save this new secret immediately. It will NOT be shown again in plain text!
              </p>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={newSecret}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-emerald-500/40 rounded-elem font-mono text-xs text-emerald-600 font-bold"
                />
                <Button variant="primary" size="sm" onClick={() => copyToClipboard(newSecret)}>
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </Button>
              </div>
            </div>
          )}

          {/* Rotate Confirmation Modal/Box */}
          {showRotateConfirm && !newSecret && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-elem p-4 space-y-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-amber-700 dark:text-amber-400">Confirm Webhook Secret Rotation</h4>
                  <p className="text-xs text-fintech-textMuted mt-1">
                    Are you sure you want to generate a new webhook secret? Webhooks using the previous signature will be rejected with 401 Unauthorized immediately.
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <Button variant="ghost" size="sm" onClick={() => setShowRotateConfirm(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleRotateSecret}
                  disabled={rotating}
                  className="bg-amber-600 hover:bg-amber-700 text-white border-none"
                >
                  {rotating ? 'Generating Secret...' : 'Yes, Rotate Secret Now'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Webhook Delivery Log Inspector (Sanitized) */}
      <WebhookDeliveryTable limit={10} showCardWrapper={true} />

      {/* Save Settings Bar */}
      <div className="flex justify-end pt-2">
        <Button variant="primary" size="md" onClick={handleSave} disabled={saving} className="gap-2 px-6">
          {saved ? (
            <>
              <Check className="w-4 h-4" />
              <span>Saved Successfully</span>
            </>
          ) : saving ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Saving Changes...</span>
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              <span>Save Merchant Configuration</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
};
