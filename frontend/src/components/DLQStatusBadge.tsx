import React, { useState, useEffect } from 'react';
import { AlertOctagon, CheckCircle2, RefreshCw } from 'lucide-react';
import { Badge } from './common/Badge';
import { api } from '../lib/api';
import { DLQSummaryResponse } from '../types';

interface DLQStatusBadgeProps {
  onClick?: () => void;
  onSelectDlqTab?: () => void;
}

export const DLQStatusBadge: React.FC<DLQStatusBadgeProps> = ({ onClick, onSelectDlqTab }) => {
  const [summary, setSummary] = useState<DLQSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const handleClick = onClick || onSelectDlqTab;

  const fetchSummary = async () => {
    try {
      const data = await api.getDLQSummary();
      setSummary(data);
    } catch (err) {
      console.warn('Failed to load DLQ summary badge status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
    // Poll DLQ health status every 30 seconds
    const interval = setInterval(fetchSummary, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Badge variant="neutral" className="gap-1.5 text-xs font-mono">
        <RefreshCw className="w-3 h-3 animate-spin text-fintech-textMuted" />
        <span>Checking DLQ...</span>
      </Badge>
    );
  }

  const count = summary?.total_dlq_count || 0;

  if (count === 0) {
    return (
      <button type="button" onClick={handleClick} className="focus:outline-none">
        <Badge variant="success" className="gap-1.5 text-xs font-semibold cursor-pointer">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>DLQ Healthy (0 Failed)</span>
        </Badge>
      </button>
    );
  }

  return (
    <button type="button" onClick={handleClick} className="focus:outline-none">
      <Badge
        variant="danger"
        className="gap-1.5 text-xs font-semibold cursor-pointer animate-pulse"
      >
        <AlertOctagon className="w-3.5 h-3.5" />
        <span>DLQ Alert: {count} Action{count === 1 ? '' : 's'} Pending Replay</span>
      </Badge>
    </button>
  );
};
