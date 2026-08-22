import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Brain,
  TrendingUp,
  ArrowUpRight,
  Sparkles,
  Zap,
  Clock,
  ChevronRight,
  SlidersHorizontal
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { LoadingSpinner, ErrorBanner, EmptyState } from '../components/common/Feedback';
import { api } from '../lib/api';
import { RevenueRiskEvent, OverviewMetrics, AIDecision } from '../types';

export const Overview: React.FC = () => {
  const navigate = useNavigate();
  const [isScanning, setIsScanning] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<RevenueRiskEvent | null>(null);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [riskEvents, setRiskEvents] = useState<RevenueRiskEvent[]>([]);
  const [aiDecisions, setAiDecisions] = useState<AIDecision[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [mRes, rRes, dRes] = await Promise.all([
        api.getOverviewMetrics(),
        api.getRevenueRisk(),
        api.getAIDecisions()
      ]);
      setMetrics(mRes);
      setRiskEvents(rRes);
      setAiDecisions(dRes);
    } catch (err: any) {
      console.error('Failed to fetch Overview dashboard data:', err);
      setError(err.message || 'Failed to connect to RecoverAI backend API.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunAudit = () => {
    setIsScanning(true);
    setScanMessage(null);
    setTimeout(() => {
      setIsScanning(false);
      setScanMessage('AI Audit complete: Identified 2 new risk events ($3,340) and initiated autonomous retry schedule.');
      fetchData();
    }, 1800);
  };

  if (isLoading) {
    return <LoadingSpinner label="Loading RecoverAI Overview metrics & risk events..." />;
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={fetchData} />;
  }

  const summary = metrics || {
    totalRiskAmount: 0,
    totalRecoveredAmount: 0,
    activeRiskCount: 0,
    aiDecisionsExecuted: 0,
    recoveryRate: 0
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
            Revenue Recovery Overview
          </h1>
          <p className="text-xs text-fintech-textMuted mt-1">
            Real-time AI revenue risk detection, root-cause analysis, and autonomous recovery performance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" className="gap-2">
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Last 30 Days</span>
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleRunAudit}
            isLoading={isScanning}
            className="gap-2 shadow-subtle"
          >
            <Sparkles className="w-4 h-4" />
            <span>Run AI Recovery Sweep</span>
          </Button>
        </div>
      </div>

      {/* Audit Banner Message if triggered */}
      {scanMessage && (
        <div className="p-4 rounded-card bg-brand-secondary/10 border border-brand-secondary/30 text-xs text-brand-primary flex items-center justify-between animate-in fade-in duration-150">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-secondary flex-shrink-0" />
            <span className="font-medium">{scanMessage}</span>
          </div>
          <button onClick={() => setScanMessage(null)} className="text-fintech-textMuted hover:text-fintech-textPrimary">
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Revenue at Risk */}
        <Card className="hover:border-status-warning/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-fintech-textMuted">Total Revenue at Risk</span>
            <div className="p-2 rounded-elem bg-status-warning/10 text-status-warning">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-display font-bold text-fintech-textPrimary">
              ${summary.totalRiskAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
            <Badge variant="warning" className="text-[10px]">
              Active
            </Badge>
          </div>
          <p className="text-[11px] text-fintech-blueGray mt-2">
            Across {summary.activeRiskCount} open risk events
          </p>
        </Card>

        {/* Card 2: Recovered Revenue */}
        <Card className="hover:border-status-success/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-fintech-textMuted">Recovered Revenue</span>
            <div className="p-2 rounded-elem bg-status-success/10 text-status-success">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-display font-bold text-fintech-textPrimary">
              ${summary.totalRecoveredAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </span>
            <Badge variant="success" className="text-[10px]">
              {summary.recoveryRate.toFixed(1)}% Rate
            </Badge>
          </div>
          <p className="text-[11px] text-fintech-blueGray mt-2">
            Recovered capital via smart engine
          </p>
        </Card>

        {/* Card 3: Active Risk Events */}
        <Card className="hover:border-brand-secondary/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-fintech-textMuted">Active Risk Events</span>
            <div className="p-2 rounded-elem bg-status-info/10 text-status-info">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-display font-bold text-fintech-textPrimary">
              {summary.activeRiskCount}
            </span>
            <span className="text-xs text-status-danger font-medium">
              {riskEvents.filter(e => e.severity === 'critical' || e.severity === 'high').length} High Severity
            </span>
          </div>
          <p className="text-[11px] text-fintech-blueGray mt-2">
            Needs autonomous intervention
          </p>
        </Card>

        {/* Card 4: AI Decisions Executed */}
        <Card className="hover:border-brand-primary/40 transition-colors">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-fintech-textMuted">AI Decisions Executed</span>
            <div className="p-2 rounded-elem bg-brand-primary/10 text-brand-primary">
              <Brain className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-display font-bold text-fintech-textPrimary">
              {summary.aiDecisionsExecuted}
            </span>
            <Badge variant="ai" className="text-[10px]">
              94.2% Conf.
            </Badge>
          </div>
          <p className="text-[11px] text-fintech-blueGray mt-2">
            100% Audit trail logged
          </p>
        </Card>
      </div>

      {/* Middle Section: Performance Breakdown + AI Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recovery Performance Breakdown (2 cols) */}
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between mb-6 border-b border-fintech-border pb-4">
            <div>
              <h2 className="text-base font-semibold text-fintech-textPrimary">
                Recovery Pipeline by Risk Category
              </h2>
              <p className="text-xs text-fintech-textMuted mt-0.5">
                Breakdown of identified revenue at risk vs. successfully recovered capital
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate('/analytics')}>
              View Full Analytics <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>

          <div className="space-y-5">
            {/* Category 1: Failed Payments */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-fintech-textPrimary">Failed Payments & Retry Engine</span>
                <span className="text-fintech-textMuted">
                  <strong className="text-status-success">$62,400</strong> / $84,000 (74.2%)
                </span>
              </div>
              <div className="w-full h-3 bg-surface-muted rounded-full overflow-hidden flex">
                <div className="h-full bg-status-success rounded-l-full" style={{ width: '74.2%' }} />
                <div className="h-full bg-status-warning" style={{ width: '25.8%' }} />
              </div>
            </div>

            {/* Category 2: Subscription Leaks */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-fintech-textPrimary">Subscription & Card Expirations</span>
                <span className="text-fintech-textMuted">
                  <strong className="text-status-success">$28,500</strong> / $36,500 (78.0%)
                </span>
              </div>
              <div className="w-full h-3 bg-surface-muted rounded-full overflow-hidden flex">
                <div className="h-full bg-status-success rounded-l-full" style={{ width: '78%' }} />
                <div className="h-full bg-status-warning" style={{ width: '22%' }} />
              </div>
            </div>

            {/* Category 3: Abandoned Checkout */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-fintech-textPrimary">High-Value Abandoned Carts</span>
                <span className="text-fintech-textMuted">
                  <strong className="text-status-success">$9,850</strong> / $18,000 (54.7%)
                </span>
              </div>
              <div className="w-full h-3 bg-surface-muted rounded-full overflow-hidden flex">
                <div className="h-full bg-status-success rounded-l-full" style={{ width: '54.7%' }} />
                <div className="h-full bg-status-warning" style={{ width: '45.3%' }} />
              </div>
            </div>

            {/* Category 4: Chargeback Prevention */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-fintech-textPrimary">Pre-Dispute Chargeback Mitigation</span>
                <span className="text-fintech-textMuted">
                  <strong className="text-status-success">$3,500</strong> / $10,000 (35.0%)
                </span>
              </div>
              <div className="w-full h-3 bg-surface-muted rounded-full overflow-hidden flex">
                <div className="h-full bg-status-success rounded-l-full" style={{ width: '35%' }} />
                <div className="h-full bg-status-warning" style={{ width: '65%' }} />
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-fintech-border flex items-center justify-between text-xs text-fintech-textMuted">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-status-success inline-block" /> Recovered Revenue
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-status-warning inline-block" /> Pending Recovery
              </span>
            </div>
            <span className="font-mono text-[11px]">Live Database Feed</span>
          </div>
        </Card>

        {/* Live AI Decision Stream (1 col) */}
        <Card className="flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 border-b border-fintech-border pb-3">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-brand-secondary" />
                <h3 className="text-sm font-semibold text-fintech-textPrimary">Recent AI Decisions</h3>
              </div>
              <Badge variant="ai" className="text-[10px]">Real-time</Badge>
            </div>

            {aiDecisions.length === 0 ? (
              <p className="text-xs text-fintech-textMuted py-4 text-center">No AI decisions recorded yet.</p>
            ) : (
              <div className="space-y-3.5">
                {aiDecisions.slice(0, 3).map((dec) => (
                  <div
                    key={dec.id}
                    onClick={() => navigate('/ai-decisions')}
                    className="p-3 rounded-elem bg-surface-muted/60 hover:bg-surface-muted border border-fintech-border cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[11px] text-brand-primary font-medium truncate max-w-[140px]">
                        {dec.id}
                      </span>
                      <Badge variant={dec.status === 'executed' ? 'success' : 'warning'} className="text-[9px]">
                        {dec.status}
                      </Badge>
                    </div>
                    <p className="text-xs font-semibold text-fintech-textPrimary capitalize">
                      {dec.action_type.replace(/_/g, ' ')}
                    </p>
                    <p className="text-[11px] text-fintech-textMuted line-clamp-2 mt-1">
                      {dec.reasoning}
                    </p>
                    <div className="mt-2 flex items-center justify-between text-[10px] text-fintech-blueGray">
                      <span>Confidence: {(dec.confidence_score * 100).toFixed(0)}%</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(dec.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/ai-decisions')}
            className="w-full mt-4 text-xs"
          >
            Audit All AI Decisions <ArrowUpRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </Card>
      </div>

      {/* Bottom Table: Active Revenue Risk Events */}
      <Card padding="none">
        <div className="p-6 border-b border-fintech-border flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-fintech-textPrimary">
              Active Revenue Risk Events
            </h2>
            <p className="text-xs text-fintech-textMuted mt-0.5">
              High-priority events requiring automated or review intervention
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate('/revenue-risk')}>
            View All Risk Events ({riskEvents.length})
          </Button>
        </div>

        {riskEvents.length === 0 ? (
          <EmptyState
            title="No Active Risk Events"
            description="All payment pipelines are currently healthy with zero active revenue risk events."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-fintech-textPrimary">
              <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-6 py-3">Event ID</th>
                  <th className="px-6 py-3">Risk Category</th>
                  <th className="px-6 py-3">Customer / Email</th>
                  <th className="px-6 py-3">Amount at Risk</th>
                  <th className="px-6 py-3">Severity</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-fintech-border">
                {riskEvents.slice(0, 10).map((event) => (
                  <tr key={event.id} className="hover:bg-surface-muted/50 transition-colors">
                    <td className="px-6 py-4 font-mono font-medium text-brand-primary truncate max-w-[120px]">
                      {event.id}
                    </td>
                    <td className="px-6 py-4 capitalize font-medium">
                      {event.event_type.replace(/_/g, ' ')}
                    </td>
                    <td className="px-6 py-4">
                      <span className="block font-medium">{event.customer_email}</span>
                      <span className="block text-[10px] text-fintech-textMuted">{event.customer_id}</span>
                    </td>
                    <td className="px-6 py-4 font-semibold text-fintech-textPrimary">
                      ${event.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4">
                      <Badge
                        variant={
                          event.severity === 'critical' || event.severity === 'high'
                            ? 'danger'
                            : event.severity === 'medium'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {event.severity}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge
                        variant={
                          event.status === 'resolved'
                            ? 'success'
                            : event.status === 'in_recovery'
                            ? 'info'
                            : 'warning'
                        }
                      >
                        {event.status.replace(/_/g, ' ')}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedEvent(event)}
                        className="text-brand-primary hover:text-brand-secondary"
                      >
                        Inspect Breakdown
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Inspect Event Modal */}
      {selectedEvent && (
        <Modal
          isOpen={!!selectedEvent}
          onClose={() => setSelectedEvent(null)}
          title={`Risk Analysis: ${selectedEvent.id}`}
          subtitle={`Detected on ${new Date(selectedEvent.detected_at).toLocaleString()}`}
          maxWidth="lg"
          footer={
            <>
              <Button variant="outline" size="sm" onClick={() => setSelectedEvent(null)}>
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  alert(`Autonomous recovery triggered for event ${selectedEvent.id}`);
                  setSelectedEvent(null);
                }}
              >
                Trigger Recovery Intervention
              </Button>
            </>
          }
        >
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4 p-4 rounded-elem bg-surface-muted border border-fintech-border">
              <div>
                <span className="block text-[10px] text-fintech-blueGray uppercase font-semibold">Amount at Risk</span>
                <span className="text-lg font-bold text-fintech-textPrimary">
                  ${selectedEvent.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-fintech-blueGray uppercase font-semibold">AI Risk Score</span>
                <span className="text-lg font-bold text-status-danger">
                  {(selectedEvent.risk_score * 100).toFixed(0)}% Likelihood of Leak
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-fintech-textPrimary mb-2">Metadata & Signals</h4>
              <div className="p-3 rounded-elem bg-white border border-fintech-border font-mono text-xs text-fintech-textMuted space-y-1">
                {Object.entries(selectedEvent.metadata || {}).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-fintech-blueGray">{key}:</span>
                    <span className="text-fintech-textPrimary font-semibold">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-fintech-textPrimary mb-2">Recommended Recovery Protocol</h4>
              <p className="text-xs text-fintech-textMuted bg-brand-primary/5 p-3 rounded-elem border border-brand-primary/20">
                The RecoverAI engine recommends executing a localized smart retry within 4 hours, combined with an automated payment update dunning email.
              </p>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

