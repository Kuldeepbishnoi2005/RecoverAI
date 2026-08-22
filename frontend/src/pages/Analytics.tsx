import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, DollarSign, Zap, RefreshCw } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { LoadingSpinner, ErrorBanner, EmptyState } from '../components/common/Feedback';
import { api } from '../lib/api';
import { OverviewMetrics } from '../types';

export const Analytics: React.FC = () => {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getOverviewMetrics();
      setMetrics(data);
    } catch (err: any) {
      console.error('Failed to fetch analytics:', err);
      setError(err.message || 'Failed to load analytics data from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
            Revenue Recovery Analytics
          </h1>
          <p className="text-xs text-fintech-textMuted mt-1">
            Historical trends, gateway performance, and recovery conversion efficiency.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAnalytics} isLoading={loading} className="gap-2">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {loading ? (
        <LoadingSpinner label="Calculating recovery analytics & performance metrics..." />
      ) : error ? (
        <ErrorBanner message={error} onRetry={fetchAnalytics} />
      ) : !metrics ? (
        <EmptyState
          title="No Analytics Available"
          description="Unable to load analytics metrics at this time."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <span className="text-xs font-semibold text-fintech-textMuted">Average Recovery Rate</span>
              <div className="text-2xl font-bold font-display text-fintech-textPrimary mt-2">
                {metrics.recoveryRate.toFixed(1)}%
              </div>
              <p className="text-xs text-status-success mt-1">Active AI recovery engine performance</p>
            </Card>

            <Card>
              <span className="text-xs font-semibold text-fintech-textMuted">Active Risk Incidents</span>
              <div className="text-2xl font-bold font-display text-fintech-textPrimary mt-2">
                {metrics.activeRiskCount}
              </div>
              <p className="text-xs text-brand-primary mt-1">Events monitored by engine</p>
            </Card>

            <Card>
              <span className="text-xs font-semibold text-fintech-textMuted">Net Revenue Preserved</span>
              <div className="text-2xl font-bold font-display text-status-success mt-2">
                ${metrics.totalRecoveredAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
              <p className="text-xs text-fintech-blueGray mt-1">Total capital recovered</p>
            </Card>
          </div>

          {/* Visual Chart Card */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-fintech-textPrimary">
                Monthly Recovery Trajectory
              </h3>
              <Badge variant="info">30-Day Cohort</Badge>
            </div>
            <div className="h-64 bg-surface-muted/50 rounded-elem border border-fintech-border flex items-end p-6 gap-4">
              {[40, 55, 62, 48, 70, 85, 92, 78, 95, 110, 105, 124].map((val, idx) => (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                  <div
                    className="w-full bg-brand-primary group-hover:bg-brand-secondary rounded-t-sm transition-all"
                    style={{ height: `${(val / 130) * 100}%` }}
                  />
                  <span className="text-[9px] text-fintech-blueGray font-mono">W{idx + 1}</span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
};

