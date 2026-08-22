import React, { useState, useEffect } from 'react';
import { FileCheck2, ShieldCheck, Lock, Database, RefreshCw } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { LoadingSpinner, ErrorBanner, EmptyState } from '../components/common/Feedback';
import { api } from '../lib/api';
import { AuditLog } from '../types';

export const AuditLogs: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAuditLogs();
      setLogs(data);
    } catch (err: any) {
      console.error('Failed to fetch audit logs:', err);
      setError(err.message || 'Failed to load system audit logs from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
            System Audit & Security Logs
          </h1>
          <p className="text-xs text-fintech-textMuted mt-1">
            Immutable system log records enforcing tenant isolation and security compliance.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchLogs} isLoading={loading} className="gap-2">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      <Card padding="none">
        <div className="p-6 border-b border-fintech-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-status-success" />
            <h3 className="text-sm font-semibold text-fintech-textPrimary">Security Audit Trail</h3>
          </div>
          <Badge variant="success">RLS Enforced</Badge>
        </div>

        {loading ? (
          <LoadingSpinner label="Loading system audit logs..." />
        ) : error ? (
          <ErrorBanner message={error} onRetry={fetchLogs} />
        ) : logs.length === 0 ? (
          <EmptyState
            title="No Audit Logs Found"
            description="No system audit logs recorded for this environment."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-fintech-textPrimary">
              <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-6 py-3">Log ID</th>
                  <th className="px-6 py-3">Action Event</th>
                  <th className="px-6 py-3">Initiator / Actor</th>
                  <th className="px-6 py-3">IP Address</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-fintech-border">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-surface-muted/50 transition-colors">
                    <td className="px-6 py-4 font-mono font-medium text-brand-primary">
                      {log.id}
                    </td>
                    <td className="px-6 py-4 font-mono font-semibold text-fintech-textPrimary">
                      {log.action}
                    </td>
                    <td className="px-6 py-4 text-fintech-textMuted">
                      {log.user}
                    </td>
                    <td className="px-6 py-4 font-mono text-fintech-blueGray">
                      {log.ip}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="success" className="text-[10px]">
                        {log.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 font-mono text-fintech-textMuted text-[11px]">
                      {log.timestamp || log.created_at ? new Date(log.timestamp || log.created_at || '').toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};

