import React, { useState } from 'react';
import { Search, ReceiptText, ShieldAlert, CheckCircle2, Clock } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { MOCK_TRANSACTIONS } from '../lib/mockData';

export const Transactions: React.FC = () => {
  const [search, setSearch] = useState('');

  const filtered = MOCK_TRANSACTIONS.filter(
    (t) =>
      t.id.toLowerCase().includes(search.toLowerCase()) ||
      t.gateway.toLowerCase().includes(search.toLowerCase()) ||
      (t.customer_id && t.customer_id.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          Transactions & Payment Stream
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Real-time transaction stream ingested across Razorpay, Stripe, and PayU payment gateways.
        </p>
      </div>

      <Card padding="sm">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-fintech-blueGray" />
          <input
            type="text"
            placeholder="Search by transaction ID, gateway, or customer..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-surface-muted border border-fintech-border rounded-elem text-xs text-fintech-textPrimary placeholder:text-fintech-blueGray focus:outline-none focus:border-brand-primary"
          />
        </div>
      </Card>

      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-fintech-textPrimary">
            <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
              <tr>
                <th className="px-6 py-3">Transaction ID</th>
                <th className="px-6 py-3">Gateway</th>
                <th className="px-6 py-3">Gateway Ref</th>
                <th className="px-6 py-3">Customer ID</th>
                <th className="px-6 py-3">Amount</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Risk Flag</th>
                <th className="px-6 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fintech-border">
              {filtered.map((txn) => (
                <tr key={txn.id} className="hover:bg-surface-muted/50 transition-colors">
                  <td className="px-6 py-4 font-mono font-medium text-brand-primary">
                    {txn.id}
                  </td>
                  <td className="px-6 py-4 font-medium">
                    {txn.gateway}
                  </td>
                  <td className="px-6 py-4 font-mono text-fintech-textMuted">
                    {txn.gateway_transaction_id || 'N/A'}
                  </td>
                  <td className="px-6 py-4 font-mono text-fintech-textMuted">
                    {txn.customer_id}
                  </td>
                  <td className="px-6 py-4 font-semibold text-fintech-textPrimary">
                    ${txn.amount.toFixed(2)} {txn.currency}
                  </td>
                  <td className="px-6 py-4">
                    <Badge
                      variant={
                        txn.status === 'succeeded'
                          ? 'success'
                          : txn.status === 'failed'
                          ? 'danger'
                          : 'warning'
                      }
                    >
                      {txn.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    {txn.risk_flag ? (
                      <span className="flex items-center gap-1 text-status-warning font-semibold text-[11px]">
                        <ShieldAlert className="w-3.5 h-3.5" /> Flagged
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-status-success text-[11px]">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Clean
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 font-mono text-fintech-textMuted text-[11px]">
                    {new Date(txn.created_at).toLocaleString()}
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
