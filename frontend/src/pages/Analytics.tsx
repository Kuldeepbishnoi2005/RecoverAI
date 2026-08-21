import React from 'react';
import { BarChart3, TrendingUp, DollarSign, Zap } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

export const Analytics: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          Revenue Recovery Analytics
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Historical trends, gateway performance, and recovery conversion efficiency.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <span className="text-xs font-semibold text-fintech-textMuted">Average Recovery Time</span>
          <div className="text-2xl font-bold font-display text-fintech-textPrimary mt-2">
            3.4 Hours
          </div>
          <p className="text-xs text-status-success mt-1">42% faster than industry benchmark</p>
        </Card>

        <Card>
          <span className="text-xs font-semibold text-fintech-textMuted">Gateway Approval Rate Impact</span>
          <div className="text-2xl font-bold font-display text-fintech-textPrimary mt-2">
            +14.8%
          </div>
          <p className="text-xs text-status-success mt-1">Using smart routing & retry windows</p>
        </Card>

        <Card>
          <span className="text-xs font-semibold text-fintech-textMuted">Net Revenue Preserved</span>
          <div className="text-2xl font-bold font-display text-status-success mt-2">
            $104,250.00
          </div>
          <p className="text-xs text-fintech-blueGray mt-1">Last 30 rolling days</p>
        </Card>
      </div>

      {/* Visual Chart Placeholder Card */}
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
    </div>
  );
};
