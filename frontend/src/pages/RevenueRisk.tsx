import React, { useState } from 'react';
import { Search, Filter, AlertTriangle, Play, CheckCircle, RefreshCw } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { MOCK_RISK_EVENTS } from '../lib/mockData';
import { RevenueRiskEvent } from '../types';

export const RevenueRisk: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [selectedEvent, setSelectedEvent] = useState<RevenueRiskEvent | null>(null);

  const filteredEvents = MOCK_RISK_EVENTS.filter((e) => {
    const matchesSearch =
      e.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.customer_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.event_type.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || e.status === statusFilter;
    const matchesSeverity = severityFilter === 'all' || e.severity === severityFilter;
    return matchesSearch && matchesStatus && matchesSeverity;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          Revenue Risk Analysis
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Identified payment declines, checkout drop-offs, expired cards, and dispute threats.
        </p>
      </div>

      {/* Filter Bar */}
      <Card padding="sm">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-fintech-blueGray" />
            <input
              type="text"
              placeholder="Filter by ID, email, risk type..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 bg-surface-muted border border-fintech-border rounded-elem text-xs text-fintech-textPrimary placeholder:text-fintech-blueGray focus:outline-none focus:border-brand-primary"
            />
          </div>

          {/* Dropdown Filters */}
          <div className="flex items-center gap-3 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            <div className="flex items-center gap-1.5 text-xs text-fintech-textMuted">
              <Filter className="w-3.5 h-3.5" />
              <span>Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-surface-muted border border-fintech-border rounded-elem px-2 py-1 text-xs text-fintech-textPrimary focus:outline-none"
              >
                <option value="all">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_recovery">In Recovery</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-fintech-textMuted">
              <span>Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-surface-muted border border-fintech-border rounded-elem px-2 py-1 text-xs text-fintech-textPrimary focus:outline-none"
              >
                <option value="all">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Table */}
      <Card padding="none">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-fintech-textPrimary">
            <thead className="bg-surface-muted border-b border-fintech-border font-semibold text-fintech-blueGray uppercase text-[10px] tracking-wider">
              <tr>
                <th className="px-6 py-3">Event ID</th>
                <th className="px-6 py-3">Risk Category</th>
                <th className="px-6 py-3">Customer Email</th>
                <th className="px-6 py-3">Amount at Risk</th>
                <th className="px-6 py-3">Risk Score</th>
                <th className="px-6 py-3">Severity</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-fintech-border">
              {filteredEvents.map((event) => (
                <tr key={event.id} className="hover:bg-surface-muted/50 transition-colors">
                  <td className="px-6 py-4 font-mono font-medium text-brand-primary">
                    {event.id}
                  </td>
                  <td className="px-6 py-4 capitalize font-semibold">
                    {event.event_type.replace(/_/g, ' ')}
                  </td>
                  <td className="px-6 py-4 text-fintech-textMuted">
                    {event.customer_email}
                  </td>
                  <td className="px-6 py-4 font-semibold text-fintech-textPrimary">
                    ${event.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-mono text-xs font-bold text-status-warning">
                      {(event.risk_score * 100).toFixed(0)}%
                    </span>
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
                  <td className="px-6 py-4 text-right space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedEvent(event)}
                      className="text-brand-primary"
                    >
                      Details
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => alert(`Initiated autonomous intervention for ${event.id}`)}
                    >
                      <Play className="w-3 h-3 mr-1 text-brand-secondary" />
                      Recover
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Event Details Modal */}
      {selectedEvent && (
        <Modal
          isOpen={!!selectedEvent}
          onClose={() => setSelectedEvent(null)}
          title={`Revenue Risk Detail: ${selectedEvent.id}`}
          subtitle={`Detected on ${new Date(selectedEvent.detected_at).toLocaleString()}`}
          maxWidth="lg"
          footer={
            <Button variant="primary" size="sm" onClick={() => setSelectedEvent(null)}>
              Done
            </Button>
          }
        >
          <div className="space-y-4">
            <div className="p-4 rounded-elem bg-surface-muted border border-fintech-border grid grid-cols-3 gap-4 text-center">
              <div>
                <span className="block text-[10px] text-fintech-blueGray uppercase font-semibold">Risk Amount</span>
                <span className="text-lg font-bold text-fintech-textPrimary">
                  ${selectedEvent.amount.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-fintech-blueGray uppercase font-semibold">Severity</span>
                <span className="text-sm font-bold uppercase text-status-danger mt-1 block">
                  {selectedEvent.severity}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-fintech-blueGray uppercase font-semibold">Confidence Score</span>
                <span className="text-lg font-bold text-brand-primary">
                  {(selectedEvent.risk_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-fintech-textPrimary mb-1">Customer Identifier</h4>
              <p className="text-xs font-mono text-fintech-textMuted">{selectedEvent.customer_email} ({selectedEvent.customer_id})</p>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-fintech-textPrimary mb-1">Raw Event Metadata</h4>
              <pre className="p-3 bg-fintech-darkBg text-emerald-400 rounded-elem font-mono text-xs overflow-x-auto">
                {JSON.stringify(selectedEvent.metadata, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
