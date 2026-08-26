import React, { useState, useEffect } from 'react';
import { RefreshCw, ShieldCheck, Eye, Search, Filter, CheckCircle2, AlertTriangle, Code2 } from 'lucide-react';
import { Card } from './common/Card';
import { Badge } from './common/Badge';
import { Button } from './common/Button';
import { Modal } from './common/Modal';
import { LoadingSpinner, EmptyState } from './common/Feedback';
import { api } from '../lib/api';
import { WebhookDeliveryItem } from '../types';

interface WebhookDeliveryTableProps {
  limit?: number;
  showCardWrapper?: boolean;
}

export const WebhookDeliveryTable: React.FC<WebhookDeliveryTableProps> = ({
  limit = 20,
  showCardWrapper = true
}) => {
  const [deliveries, setDeliveries] = useState<WebhookDeliveryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedDelivery, setSelectedDelivery] = useState<WebhookDeliveryItem | null>(null);

  const fetchDeliveries = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWebhookDeliveries(limit);
      setDeliveries(data.items || []);
    } catch (err: any) {
      console.error('Failed to fetch webhook deliveries:', err);
      setError(err.message || 'Failed to load webhook delivery log history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeliveries();
  }, [limit]);

  const filteredDeliveries = deliveries.filter(d => {
    const matchesSearch =
      d.event_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      JSON.stringify(d.payload || {}).toLowerCase().includes(searchTerm.toLowerCase());

    if (filterStatus === 'success') {
      return matchesSearch && d.status_code >= 200 && d.status_code < 300;
    }
    if (filterStatus === 'error') {
      return matchesSearch && d.status_code >= 400;
    }
    return matchesSearch;
  });

  const content = (
    <div className="space-y-4">
      {/* Table Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-fintech-border pb-3">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-fintech-textMuted" />
            <input
              type="text"
              placeholder="Search event type or payload..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-surface-muted border border-fintech-border rounded-elem text-xs text-fintech-textPrimary focus:outline-none focus:border-brand-primary w-56"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-2.5 py-1.5 bg-surface-muted border border-fintech-border rounded-elem text-xs text-fintech-textPrimary focus:outline-none focus:border-brand-primary"
          >
            <option value="all">All Statuses</option>
            <option value="success">2xx Success</option>
            <option value="error">4xx / 5xx Errors</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="success" className="gap-1 text-[11px] font-mono">
            <ShieldCheck className="w-3 h-3" />
            PII & Credentials Sanitized
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchDeliveries}
            disabled={loading}
            className="text-xs gap-1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner label="Loading sanitized webhook delivery history..." />
      ) : error ? (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-600 rounded-elem text-xs flex items-center justify-between">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={fetchDeliveries}>Retry</Button>
        </div>
      ) : filteredDeliveries.length === 0 ? (
        <EmptyState
          title="No Webhook Deliveries Recorded"
          description="Webhook events ingested via the public endpoint will appear here with fully sanitized payloads."
          onAction={fetchDeliveries}
          actionLabel="Refresh Logs"
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-fintech-textPrimary">
            <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
              <tr>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5">Event Type</th>
                <th className="px-4 py-2.5">Delivery ID</th>
                <th className="px-4 py-2.5">Ingested At</th>
                <th className="px-4 py-2.5 text-right">Sanitized Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fintech-border">
              {filteredDeliveries.map((item) => {
                const isSuccess = item.status_code >= 200 && item.status_code < 300;
                return (
                  <tr key={item.id} className="hover:bg-surface-muted/50 transition-colors">
                    <td className="px-4 py-3">
                      <Badge
                        variant={isSuccess ? 'success' : 'danger'}
                        className="font-mono text-[10px]"
                      >
                        {item.status_code} {isSuccess ? 'OK' : 'ERR'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-mono text-fintech-textPrimary font-medium">
                      {item.event_type}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-fintech-textMuted">
                      {item.id.slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3 text-fintech-textMuted font-mono text-[11px]">
                      {new Date(item.delivered_at || item.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedDelivery(item)}
                        className="gap-1 text-xs py-1 px-2.5"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Payload Inspection Modal */}
      {selectedDelivery && (
        <Modal
          isOpen={!!selectedDelivery}
          onClose={() => setSelectedDelivery(null)}
          title={`Webhook Delivery Inspection: ${selectedDelivery.id}`}
          subtitle={`Event: ${selectedDelivery.event_type} | HTTP Status: ${selectedDelivery.status_code}`}
          maxWidth="lg"
          footer={
            <div className="flex justify-end w-full">
              <Button variant="outline" size="sm" onClick={() => setSelectedDelivery(null)}>
                Close Inspector
              </Button>
            </div>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-elem flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-semibold">
              <ShieldCheck className="w-4 h-4 flex-shrink-0" />
              <span>Sanitization Active: Authorization headers, webhook secrets, and payment credentials redacted.</span>
            </div>

            <div>
              <label className="block font-semibold text-fintech-textPrimary mb-1 flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-brand-primary" />
                Sanitized Request Headers
              </label>
              <pre className="p-3 bg-slate-900 text-slate-200 rounded-elem font-mono text-[11px] overflow-x-auto max-h-36">
                {JSON.stringify(selectedDelivery.headers || {}, null, 2)}
              </pre>
            </div>

            <div>
              <label className="block font-semibold text-fintech-textPrimary mb-1 flex items-center gap-1.5">
                <Code2 className="w-3.5 h-3.5 text-brand-secondary" />
                Sanitized Ingested Payload
              </label>
              <pre className="p-3 bg-slate-900 text-emerald-400 rounded-elem font-mono text-[11px] overflow-x-auto max-h-64">
                {JSON.stringify(selectedDelivery.payload || {}, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );

  if (!showCardWrapper) {
    return content;
  }

  return (
    <Card>
      <div className="mb-4 border-b border-fintech-border pb-3">
        <h3 className="text-base font-semibold text-fintech-textPrimary">Webhook Delivery Log Inspector</h3>
        <p className="text-xs text-fintech-textMuted">Sanitized, tenant-isolated record of ingested merchant webhooks.</p>
      </div>
      {content}
    </Card>
  );
};
