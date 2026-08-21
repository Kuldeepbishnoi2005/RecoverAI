import React from 'react';
import { FileCheck2, ShieldCheck, Lock, Database } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

export const AuditLogs: React.FC = () => {
  const logs = [
    { id: 'log_101', action: 'MERCHANT_LOGIN', user: 'admin@acme.com', ip: '192.168.1.45', status: 'SUCCESS', timestamp: '2026-08-21T18:30:10Z' },
    { id: 'log_102', action: 'RLS_POLICY_EVAL', user: 'system_rls', ip: 'internal', status: 'ISOLATED_PASS', timestamp: '2026-08-21T18:25:00Z' },
    { id: 'log_103', action: 'AUTONOMOUS_ACTION_TRIGGER', user: 'recover_ai_agent', ip: '10.0.4.12', status: 'EXECUTED', timestamp: '2026-08-21T15:10:00Z' },
    { id: 'log_104', action: 'WEBHOOK_PAYLOAD_RECEIVED', user: 'razorpay_gateway', ip: '52.74.12.9', status: 'INGESTED', timestamp: '2026-08-21T14:32:00Z' },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          System Audit & Security Logs
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Immutable system log records enforcing tenant isolation and security compliance.
        </p>
      </div>

      <Card padding="none">
        <div className="p-6 border-b border-fintech-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-status-success" />
            <h3 className="text-sm font-semibold text-fintech-textPrimary">Security Audit Trail</h3>
          </div>
          <Badge variant="success">RLS Enforced</Badge>
        </div>

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
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
