import React, { useState } from 'react';
import { Brain, Sparkles, FileText, CheckCircle2, AlertCircle, Eye, Shield } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { MOCK_AI_DECISIONS } from '../lib/mockData';
import { AIDecision } from '../types';

export const AIDecisions: React.FC = () => {
  const [selectedDecision, setSelectedDecision] = useState<AIDecision | null>(null);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div>
        <div className="flex items-center gap-2">
          <Badge variant="ai" className="px-2 py-0.5 text-xs">
            100% Deterministic & Auditable
          </Badge>
        </div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight mt-1">
          AI Decisions Audit Trail
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Complete transparent audit log of all autonomous recovery decisions, LLM rationales, confidence ratings, and JSON payloads.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Card className="bg-brand-primary/5 border-brand-primary/20">
          <div className="flex items-center gap-3 mb-2">
            <Brain className="w-5 h-5 text-brand-primary" />
            <h3 className="text-xs font-semibold text-fintech-textPrimary">LLM Model Runtime</h3>
          </div>
          <span className="text-lg font-bold font-mono text-brand-primary">Gemini 1.5 Pro / Resemble Engine</span>
          <p className="text-[11px] text-fintech-textMuted mt-1">Strict financial safety & compliance guardrails</p>
        </Card>

        <Card className="bg-status-success/5 border-status-success/20">
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-5 h-5 text-status-success" />
            <h3 className="text-xs font-semibold text-fintech-textPrimary">Avg Confidence Rating</h3>
          </div>
          <span className="text-lg font-bold text-status-success">93.8%</span>
          <p className="text-[11px] text-fintech-textMuted mt-1">Zero unauthorized financial mutations</p>
        </Card>

        <Card className="bg-status-info/5 border-status-info/20">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle2 className="w-5 h-5 text-status-info" />
            <h3 className="text-xs font-semibold text-fintech-textPrimary">Audit Ledger Integrity</h3>
          </div>
          <span className="text-lg font-bold text-status-info">Immutable RLS</span>
          <p className="text-[11px] text-fintech-textMuted mt-1">Directly queryable via API & Supabase</p>
        </Card>
      </div>

      <Card padding="none">
        <div className="p-6 border-b border-fintech-border flex items-center justify-between">
          <h3 className="text-base font-semibold text-fintech-textPrimary">Autonomous Decisions Log</h3>
          <span className="text-xs font-mono text-fintech-blueGray">Showing {MOCK_AI_DECISIONS.length} decisions</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-fintech-textPrimary">
            <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
              <tr>
                <th className="px-6 py-3">Decision ID</th>
                <th className="px-6 py-3">Event ID</th>
                <th className="px-6 py-3">Action Type</th>
                <th className="px-6 py-3">Confidence</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Reasoning / Rationale</th>
                <th className="px-6 py-3 text-right">Audit Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fintech-border">
              {MOCK_AI_DECISIONS.map((dec) => (
                <tr key={dec.id} className="hover:bg-surface-muted/50 transition-colors">
                  <td className="px-6 py-4 font-mono font-bold text-brand-primary">
                    {dec.id}
                  </td>
                  <td className="px-6 py-4 font-mono text-fintech-textMuted">
                    {dec.risk_event_id}
                  </td>
                  <td className="px-6 py-4 capitalize font-semibold">
                    {dec.action_type.replace(/_/g, ' ')}
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-bold text-brand-secondary font-mono">
                      {(dec.confidence_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant={dec.status === 'executed' ? 'success' : 'warning'}>
                      {dec.status.replace(/_/g, ' ')}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 max-w-xs text-fintech-textMuted truncate">
                    {dec.reasoning}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedDecision(dec)}
                      className="gap-1 text-xs"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Inspect JSON</span>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Decision JSON Modal */}
      {selectedDecision && (
        <Modal
          isOpen={!!selectedDecision}
          onClose={() => setSelectedDecision(null)}
          title={`AI Decision Audit: ${selectedDecision.id}`}
          subtitle={`Risk Reference: ${selectedDecision.risk_event_id}`}
          maxWidth="lg"
          footer={
            <Button variant="primary" size="sm" onClick={() => setSelectedDecision(null)}>
              Close Audit Record
            </Button>
          }
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-fintech-textPrimary mb-1">Reasoning Chain</h4>
              <p className="p-3 bg-surface-muted border border-fintech-border rounded-elem text-xs text-fintech-textPrimary leading-relaxed">
                {selectedDecision.reasoning}
              </p>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-fintech-textPrimary mb-1">Execution Payload</h4>
              <pre className="p-4 bg-fintech-darkBg text-emerald-400 rounded-elem font-mono text-xs overflow-x-auto">
                {JSON.stringify(selectedDecision.payload, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
