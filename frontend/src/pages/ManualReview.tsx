import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  Clock,
  RefreshCw,
  Lock,
  DollarSign,
  UserCheck,
  Brain,
  Zap,
  Info,
  RotateCcw,
  AlertOctagon,
  ListFilter
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { LoadingSpinner, ErrorBanner, EmptyState } from '../components/common/Feedback';
import { api } from '../lib/api';
import { ManualReviewQueueItem, ManualReviewActionDetail, DLQActionItem } from '../types';

export const ManualReview: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'pending' | 'dlq'>('pending');

  // Queue state for pending approvals
  const [pendingQueue, setPendingQueue] = useState<ManualReviewQueueItem[]>([]);
  const [loadingPending, setLoadingPending] = useState<boolean>(true);

  // DLQ state
  const [dlqItems, setDlqItems] = useState<DLQActionItem[]>([]);
  const [loadingDlq, setLoadingDlq] = useState<boolean>(true);

  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Selected action for detailed inspection / modal (Pending Approval)
  const [selectedQueueItem, setSelectedQueueItem] = useState<ManualReviewQueueItem | null>(null);
  const [detailedAction, setDetailedAction] = useState<ManualReviewActionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Replay modal state (DLQ)
  const [selectedDlqItem, setSelectedDlqItem] = useState<DLQActionItem | null>(null);
  const [replayNotes, setReplayNotes] = useState<string>('');
  const [replaying, setReplaying] = useState<boolean>(false);

  // Approval/Rejection input state
  const [merchantNotes, setMerchantNotes] = useState<string>('');
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);
  const [showRejectForm, setShowRejectForm] = useState<boolean>(false);

  const fetchPendingQueue = async () => {
    setLoadingPending(true);
    try {
      const data = await api.manualReview.getQueue();
      setPendingQueue(data);
    } catch (err: any) {
      console.error('Failed to fetch manual review queue:', err);
      setError(err.message || 'Failed to load manual review queue from backend.');
    } finally {
      setLoadingPending(false);
    }
  };

  const fetchDlqItems = async () => {
    setLoadingDlq(true);
    try {
      const data = await api.getDLQActions();
      setDlqItems(data.items || []);
    } catch (err: any) {
      console.error('Failed to fetch DLQ items:', err);
      setError(err.message || 'Failed to load Dead-Letter Queue items.');
    } finally {
      setLoadingDlq(false);
    }
  };

  const refreshAll = async () => {
    setError(null);
    if (activeTab === 'pending') {
      await fetchPendingQueue();
    } else {
      await fetchDlqItems();
    }
  };

  useEffect(() => {
    fetchPendingQueue();
    fetchDlqItems();
  }, []);

  const openInspectModal = async (item: ManualReviewQueueItem) => {
    setSelectedQueueItem(item);
    setMerchantNotes('');
    setRejectionReason('');
    setShowRejectForm(false);
    setLoadingDetail(true);
    try {
      const detail = await api.manualReview.getActionDetails(item.id);
      setDetailedAction(detail);
    } catch (err: any) {
      console.error('Failed to fetch action details:', err);
      setDetailedAction(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const closeModal = () => {
    setSelectedQueueItem(null);
    setDetailedAction(null);
    setShowRejectForm(false);
    setMerchantNotes('');
    setRejectionReason('');
  };

  const handleApprove = async () => {
    if (!selectedQueueItem) return;
    setSubmittingAction(true);
    setError(null);
    try {
      const idempotencyKey = `manual_approve_${selectedQueueItem.id}_${Date.now()}`;
      const res = await api.manualReview.approveAction(
        selectedQueueItem.id,
        {
          approver_id: 'merchant_admin_1',
          approver_role: 'admin',
          notes: merchantNotes || 'Approved via RecoverAI Governance Portal'
        },
        idempotencyKey
      );

      setActionSuccess(
        `Action ${selectedQueueItem.id} approved successfully! Simulation result: ${res.simulation_result?.status || res.action?.status}`
      );
      closeModal();
      await fetchPendingQueue();
    } catch (err: any) {
      console.error('Approval failed:', err);
      setError(err.message || 'Failed to approve recovery action.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleReject = async () => {
    if (!selectedQueueItem) return;
    if (!rejectionReason.trim()) {
      alert('Please provide a rejection reason for governance tracking.');
      return;
    }
    setSubmittingAction(true);
    setError(null);
    try {
      const res = await api.manualReview.rejectAction(selectedQueueItem.id, {
        rejected_by: 'merchant_admin_1',
        approver_role: 'admin',
        rejection_reason: rejectionReason
      });

      setActionSuccess(`Action ${selectedQueueItem.id} rejected. Status: ${res.action?.status}`);
      closeModal();
      await fetchPendingQueue();
    } catch (err: any) {
      console.error('Rejection failed:', err);
      setError(err.message || 'Failed to reject recovery action.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleReplayAction = async () => {
    if (!selectedDlqItem) return;
    setReplaying(true);
    setError(null);
    try {
      const res = await api.replayAction(selectedDlqItem.id, replayNotes);
      setActionSuccess(
        `DLQ Action ${selectedDlqItem.id} replayed via ${res.replay_details?.gateway_provider || 'gateway'}! Result status: ${res.action?.status || 'EXECUTED'}`
      );
      setSelectedDlqItem(null);
      setReplayNotes('');
      await fetchDlqItems();
      await fetchPendingQueue();
    } catch (err: any) {
      console.error('Replay failed:', err);
      setError(err.message || 'Failed to replay failed recovery action.');
    } finally {
      setReplaying(false);
    }
  };

  // Metrics computation
  const pendingCount = pendingQueue.filter(q => q.status === 'pending_approval').length;
  const totalPendingAmount = pendingQueue
    .filter(q => q.status === 'pending_approval')
    .reduce((acc, curr) => acc + (curr.amount || 0), 0);

  const dlqCount = dlqItems.length;
  const totalDlqAmount = dlqItems.reduce((acc, curr) => acc + (curr.amount || 0), 0);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="warning" className="px-2 py-0.5 text-xs font-semibold">
              Human-In-The-Loop Governance & Operational Resilience
            </Badge>
            <span className="text-xs text-fintech-blueGray">Phase 8A Gateway Framework</span>
          </div>
          <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight mt-1">
            Manual Review & Dead-Letter Queue (DLQ)
          </h1>
          <p className="text-xs text-fintech-textMuted mt-1">
            Authorize high-risk recovery interventions and manually replay failed executions with gateway resilience.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={refreshAll}
          disabled={loadingPending || loadingDlq}
          className="gap-1.5 text-xs self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${(loadingPending || loadingDlq) ? 'animate-spin' : ''}`} />
          Refresh Workspace
        </Button>
      </div>

      {/* Tabs bar */}
      <div className="flex items-center gap-2 border-b border-fintech-border pb-1">
        <button
          onClick={() => setActiveTab('pending')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-elem transition-colors border-b-2 ${
            activeTab === 'pending'
              ? 'border-brand-primary text-brand-primary bg-brand-primary/5'
              : 'border-transparent text-fintech-textMuted hover:text-fintech-textPrimary'
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Pending Approvals ({pendingCount})</span>
        </button>

        <button
          onClick={() => setActiveTab('dlq')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-t-elem transition-colors border-b-2 ${
            activeTab === 'dlq'
              ? 'border-amber-500 text-amber-600 bg-amber-500/10'
              : 'border-transparent text-fintech-textMuted hover:text-fintech-textPrimary'
          }`}
        >
          <AlertOctagon className="w-4 h-4" />
          <span>Dead-Letter Queue (DLQ) ({dlqCount})</span>
        </button>
      </div>

      {/* Success Notification Banner */}
      {actionSuccess && (
        <div className="p-4 rounded-elem bg-status-success/10 border border-status-success/30 text-status-success text-xs font-medium flex items-center justify-between animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-status-success flex-shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-status-success hover:underline text-[11px] font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {error && <ErrorBanner message={error} onRetry={refreshAll} />}

      {/* TAB 1: PENDING APPROVAL QUEUE */}
      {activeTab === 'pending' && (
        <div className="space-y-6">
          {/* Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
            <Card className="bg-surface-card border-fintech-border shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-fintech-textMuted uppercase tracking-wider">Pending Review</span>
                <UserCheck className="w-4 h-4 text-brand-secondary" />
              </div>
              <div className="text-2xl font-display font-bold text-fintech-textPrimary">
                {pendingCount}
              </div>
              <p className="text-[11px] text-fintech-blueGray mt-1">Actions awaiting manual decision</p>
            </Card>

            <Card className="bg-surface-card border-fintech-border shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-fintech-textMuted uppercase tracking-wider">Total Value at Risk</span>
                <DollarSign className="w-4 h-4 text-status-success" />
              </div>
              <div className="text-2xl font-display font-bold text-brand-primary">
                ${totalPendingAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <p className="text-[11px] text-fintech-blueGray mt-1">Pending recovery revenue</p>
            </Card>

            <Card className="bg-surface-card border-fintech-border shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-fintech-textMuted uppercase tracking-wider">Policy Guardrails</span>
                <Lock className="w-4 h-4 text-status-warning" />
              </div>
              <div className="text-base font-display font-bold text-fintech-textPrimary font-mono">
                Threshold: Dynamic AI
              </div>
              <p className="text-[11px] text-fintech-blueGray mt-1">Configured in Merchant Settings</p>
            </Card>

            <Card className="bg-brand-primary/5 border-brand-primary/20 shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-brand-primary uppercase tracking-wider">Gateway Provider</span>
                <Zap className="w-4 h-4 text-brand-primary" />
              </div>
              <div className="text-base font-bold text-brand-primary font-mono">
                Sandbox Simulator
              </div>
              <p className="text-[11px] text-fintech-textMuted mt-1">Safe execution adapter</p>
            </Card>
          </div>

          {/* Pending Queue Table */}
          {loadingPending ? (
            <Card padding="lg">
              <LoadingSpinner label="Loading pending recovery queue items..." />
            </Card>
          ) : pendingQueue.length === 0 ? (
            <Card padding="lg">
              <EmptyState
                title="Manual Review Queue Empty"
                description="All flagged recovery actions have been reviewed or processed. No pending interventions require approval."
                onAction={fetchPendingQueue}
                actionLabel="Refresh Queue"
              />
            </Card>
          ) : (
            <Card padding="none">
              <div className="p-6 border-b border-fintech-border flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-fintech-textPrimary">Pending Approval Items</h3>
                  <p className="text-xs text-fintech-textMuted mt-0.5">
                    Review policy reasoning and decision confidence before confirming automated simulation.
                  </p>
                </div>
                <span className="text-xs font-mono text-fintech-blueGray">
                  {pendingQueue.length} Record{pendingQueue.length === 1 ? '' : 's'}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-fintech-textPrimary">
                  <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="px-6 py-3">Action ID</th>
                      <th className="px-6 py-3">Strategy / Action</th>
                      <th className="px-6 py-3">Amount</th>
                      <th className="px-6 py-3">Policy Trigger Rationale</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3">Created</th>
                      <th className="px-6 py-3 text-right">Governance Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-fintech-border">
                    {pendingQueue.map((item) => (
                      <tr key={item.id} className="hover:bg-surface-muted/50 transition-colors">
                        <td className="px-6 py-4 font-mono font-bold text-brand-primary">
                          {item.id.slice(0, 8)}...
                        </td>
                        <td className="px-6 py-4 capitalize">
                          <div className="font-semibold text-fintech-textPrimary">
                            {(item.action_type || item.strategy || 'recovery_action').replace(/_/g, ' ')}
                          </div>
                          {item.execution_strategy && (
                            <div className="text-[11px] text-fintech-textMuted font-mono mt-0.5">
                              Strategy: {item.execution_strategy}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 font-bold text-fintech-textPrimary font-mono">
                          ${(item.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {item.currency}
                        </td>
                        <td className="px-6 py-4 max-w-xs text-fintech-textMuted">
                          <div className="line-clamp-2 text-[11px] leading-relaxed">
                            {item.policy_check_results?.reason || item.reason || 'Flagged for merchant oversight'}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <Badge
                            variant={
                              item.status === 'pending_approval'
                                ? 'warning'
                                : item.status === 'approved'
                                ? 'success'
                                : item.status === 'rejected'
                                ? 'danger'
                                : 'neutral'
                            }
                            className="capitalize text-[10px]"
                          >
                            {(item.status || 'pending_approval').replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-fintech-textMuted font-mono text-[11px]">
                          {new Date(item.created_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => openInspectModal(item)}
                            className="gap-1 text-xs"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Inspect & Review</span>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* TAB 2: DEAD-LETTER QUEUE (DLQ) & REPLAY */}
      {activeTab === 'dlq' && (
        <div className="space-y-6">
          {/* DLQ Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <Card className="bg-amber-500/5 border-amber-500/20 shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-amber-700 dark:text-amber-400 uppercase tracking-wider">Failed Executions (DLQ)</span>
                <AlertOctagon className="w-4 h-4 text-amber-600" />
              </div>
              <div className="text-2xl font-display font-bold text-amber-700 dark:text-amber-300">
                {dlqCount}
              </div>
              <p className="text-[11px] text-fintech-textMuted mt-1">Actions flagged for manual replay</p>
            </Card>

            <Card className="bg-surface-card border-fintech-border shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-fintech-textMuted uppercase tracking-wider">DLQ Value at Risk</span>
                <DollarSign className="w-4 h-4 text-amber-600" />
              </div>
              <div className="text-2xl font-display font-bold text-fintech-textPrimary font-mono">
                ${totalDlqAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <p className="text-[11px] text-fintech-blueGray mt-1">Unresolved recovery attempts</p>
            </Card>

            <Card className="bg-surface-card border-fintech-border shadow-2xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-fintech-textMuted uppercase tracking-wider">Replay Policy</span>
                <RotateCcw className="w-4 h-4 text-brand-primary" />
              </div>
              <div className="text-base font-display font-bold text-fintech-textPrimary font-mono">
                Manual Trigger Only
              </div>
              <p className="text-[11px] text-fintech-blueGray mt-1">Persistent error tracking</p>
            </Card>
          </div>

          {/* DLQ Table */}
          {loadingDlq ? (
            <Card padding="lg">
              <LoadingSpinner label="Loading Dead-Letter Queue items..." />
            </Card>
          ) : dlqItems.length === 0 ? (
            <Card padding="lg">
              <EmptyState
                title="Dead-Letter Queue Clean"
                description="No failed recovery actions or unhandled gateway errors detected. All recovery workflows are operating normally."
                onAction={fetchDlqItems}
                actionLabel="Check DLQ"
              />
            </Card>
          ) : (
            <Card padding="none">
              <div className="p-6 border-b border-fintech-border flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-fintech-textPrimary">Dead-Letter Queue (DLQ) Items</h3>
                  <p className="text-xs text-fintech-textMuted mt-0.5">
                    Actions that failed during initial gateway dispatch or hit maximum automated retries.
                  </p>
                </div>
                <span className="text-xs font-mono text-amber-600 font-bold">
                  {dlqItems.length} Failed Item{dlqItems.length === 1 ? '' : 's'}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-fintech-textPrimary">
                  <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="px-6 py-3">Action ID</th>
                      <th className="px-6 py-3">Strategy / Type</th>
                      <th className="px-6 py-3">Amount</th>
                      <th className="px-6 py-3">Last Gateway Error</th>
                      <th className="px-6 py-3">Retries</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3 text-right">Replay Intervention</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-fintech-border">
                    {dlqItems.map((item) => (
                      <tr key={item.id} className="hover:bg-amber-500/5 transition-colors">
                        <td className="px-6 py-4 font-mono font-bold text-amber-600">
                          {item.id.slice(0, 8)}...
                        </td>
                        <td className="px-6 py-4 capitalize font-semibold">
                          {(item.action_type || item.strategy || 'recovery_action').replace(/_/g, ' ')}
                        </td>
                        <td className="px-6 py-4 font-bold font-mono text-fintech-textPrimary">
                          ${(item.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })} {item.currency}
                        </td>
                        <td className="px-6 py-4 max-w-xs text-red-600 font-mono text-[11px]">
                          <div className="line-clamp-2">
                            {item.last_error || item.reason || 'Execution failure / Max retries reached'}
                          </div>
                        </td>
                        <td className="px-6 py-4 font-mono font-bold text-fintech-textMuted">
                          {item.retry_count || 0}
                        </td>
                        <td className="px-6 py-4">
                          <Badge variant="danger" className="text-[10px] uppercase">
                            {item.status || 'EXECUTED_FAILED'}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedDlqItem(item)}
                            className="gap-1.5 text-xs text-amber-600 border-amber-500/30 hover:bg-amber-500/10"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>Replay Action</span>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* DLQ Replay Confirmation Modal */}
      {selectedDlqItem && (
        <Modal
          isOpen={!!selectedDlqItem}
          onClose={() => setSelectedDlqItem(null)}
          title={`Replay Failed Action: ${selectedDlqItem.id}`}
          subtitle={`Strategy: ${selectedDlqItem.action_type || selectedDlqItem.strategy} | Amount: $${selectedDlqItem.amount}`}
          maxWidth="md"
          footer={
            <div className="flex items-center justify-between w-full">
              <Button variant="outline" size="sm" onClick={() => setSelectedDlqItem(null)} disabled={replaying}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleReplayAction}
                isLoading={replaying}
                className="gap-1.5 bg-amber-600 hover:bg-amber-700 text-white border-none"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Execute Gateway Replay</span>
              </Button>
            </div>
          }
        >
          <div className="space-y-4 text-xs text-fintech-textPrimary">
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-elem space-y-1">
              <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-bold">
                <AlertOctagon className="w-4 h-4" />
                <span>Gateway Adapter Re-Execution</span>
              </div>
              <p className="text-fintech-textMuted">
                This will trigger the active Gateway Adapter (Sandbox Simulator) to re-process this recovery action and log audit events.
              </p>
            </div>

            <div>
              <label className="block font-semibold text-fintech-textMuted mb-1">Previous Error Context</label>
              <div className="p-3 bg-surface-muted font-mono text-[11px] text-red-600 rounded-elem border border-fintech-border">
                {selectedDlqItem.last_error || 'Execution failure / Max retries reached'}
              </div>
            </div>

            <div>
              <label className="block font-semibold text-fintech-textPrimary mb-1">Replay Audit Notes (Optional)</label>
              <input
                type="text"
                placeholder="Reason for manual replay, e.g. Customer card updated."
                value={replayNotes}
                onChange={(e) => setReplayNotes(e.target.value)}
                className="w-full px-3 py-2 rounded-elem border border-fintech-border text-xs focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            </div>
          </div>
        </Modal>
      )}

      {/* Detailed Action Modal for Pending Approvals */}
      {selectedQueueItem && (
        <Modal
          isOpen={!!selectedQueueItem}
          onClose={closeModal}
          title={`Review Action: ${selectedQueueItem.id}`}
          subtitle={`Type: ${selectedQueueItem.action_type || selectedQueueItem.strategy || 'recovery_action'} | Transaction Ref: ${selectedQueueItem.transaction_id || 'N/A'}`}
          maxWidth="lg"
          footer={
            <div className="flex items-center justify-between w-full">
              <Button variant="outline" size="sm" onClick={closeModal} disabled={submittingAction}>
                Cancel
              </Button>
              {selectedQueueItem.status === 'pending_approval' && (
                <div className="flex items-center gap-3">
                  {!showRejectForm ? (
                    <>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => setShowRejectForm(true)}
                        disabled={submittingAction}
                        className="gap-1"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject</span>
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleApprove}
                        isLoading={submittingAction}
                        className="gap-1 bg-status-success hover:bg-emerald-600 text-white"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approve Action (Simulate)</span>
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={handleReject}
                      isLoading={submittingAction}
                      className="gap-1"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Confirm Rejection</span>
                    </Button>
                  )}
                </div>
              )}
            </div>
          }
        >
          {loadingDetail ? (
            <div className="py-8">
              <LoadingSpinner label="Fetching detailed transaction context & policy logs..." />
            </div>
          ) : (
            <div className="space-y-5 text-xs text-fintech-textPrimary">
              <div className="p-4 rounded-elem bg-surface-muted border border-fintech-border flex items-center justify-between">
                <div>
                  <span className="text-[11px] text-fintech-blueGray uppercase tracking-wider block">Recovery Amount</span>
                  <span className="text-xl font-bold font-display text-brand-primary">
                    ${(selectedQueueItem.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })} {selectedQueueItem.currency}
                  </span>
                </div>
                <Badge variant={selectedQueueItem.status === 'pending_approval' ? 'warning' : 'info'} className="text-xs">
                  {(selectedQueueItem.status || '').replace(/_/g, ' ')}
                </Badge>
              </div>

              {detailedAction?.transaction ? (
                <div>
                  <h4 className="text-xs font-semibold text-fintech-textPrimary mb-2 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-brand-primary" />
                    Transaction & Customer Context
                  </h4>
                  <div className="grid grid-cols-2 gap-3 p-3 bg-white dark:bg-slate-900 rounded-elem border border-fintech-border font-mono text-[11px]">
                    <div>
                      <span className="text-fintech-blueGray">Transaction ID:</span> {detailedAction.transaction.id}
                    </div>
                    <div>
                      <span className="text-fintech-blueGray">Status:</span> {detailedAction.transaction.status}
                    </div>
                    <div>
                      <span className="text-fintech-blueGray">Customer Ref:</span> {detailedAction.transaction.customer_id || 'N/A'}
                    </div>
                    <div>
                      <span className="text-fintech-blueGray">Gateway:</span> {detailedAction.transaction.payment_gateway || 'Stripe'}
                    </div>
                    {detailedAction.transaction.error_code && (
                      <div className="col-span-2 text-status-danger">
                        <span className="text-fintech-blueGray">Gateway Error:</span> [{detailedAction.transaction.error_code}] {detailedAction.transaction.error_message}
                      </div>
                    )}
                  </div>
                </div>
              ) : null}

              <div>
                <h4 className="text-xs font-semibold text-fintech-textPrimary mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-status-warning" />
                  Policy Controller Rationale
                </h4>
                <div className="p-3 bg-status-warning/5 border border-status-warning/20 rounded-elem text-fintech-textPrimary leading-relaxed">
                  {selectedQueueItem.policy_check_results?.reason || selectedQueueItem.reason || 'This intervention exceeded autonomous execution thresholds and requires explicit merchant confirmation.'}
                </div>
              </div>

              {detailedAction?.ai_decision && (
                <div>
                  <h4 className="text-xs font-semibold text-fintech-textPrimary mb-2 flex items-center gap-1.5">
                    <Brain className="w-3.5 h-3.5 text-brand-secondary" />
                    AI Recommender Score & Rationale
                  </h4>
                  <div className="p-3 bg-surface-muted border border-fintech-border rounded-elem space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span>Model Confidence Rating:</span>
                      <span className="font-bold text-brand-secondary font-mono">
                        {((detailedAction.ai_decision.confidence_score || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-fintech-textMuted text-[11px] leading-relaxed">
                      {detailedAction.ai_decision.reasoning}
                    </p>
                  </div>
                </div>
              )}

              {selectedQueueItem.status === 'pending_approval' && (
                <div className="pt-3 border-t border-fintech-border space-y-3">
                  {!showRejectForm ? (
                    <div>
                      <label className="block text-xs font-semibold text-fintech-textPrimary mb-1">
                        Merchant Approval Notes (Optional)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Verified customer status, proceeding with automated retry."
                        value={merchantNotes}
                        onChange={(e) => setMerchantNotes(e.target.value)}
                        className="w-full px-3 py-2 rounded-elem border border-fintech-border text-xs focus:outline-none focus:ring-1 focus:ring-brand-primary"
                      />
                    </div>
                  ) : (
                    <div className="p-3 bg-status-danger/5 border border-status-danger/20 rounded-elem space-y-2">
                      <label className="block text-xs font-semibold text-status-danger">
                        Reason for Rejection (Required for Audit Log)
                      </label>
                      <textarea
                        rows={2}
                        placeholder="State why this recovery action is being cancelled..."
                        value={rejectionReason}
                        onChange={(e) => setRejectionReason(e.target.value)}
                        className="w-full px-3 py-2 rounded-elem border border-status-danger/30 text-xs focus:outline-none focus:ring-1 focus:ring-status-danger"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Modal>
      )}
    </div>
  );
};

export default ManualReview;
