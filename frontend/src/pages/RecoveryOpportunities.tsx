import React, { useState, useEffect } from 'react';
import { Wallet, Sparkles, ArrowRight, CheckCircle2, Zap, RefreshCw } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { LoadingSpinner, ErrorBanner, EmptyState } from '../components/common/Feedback';
import { api } from '../lib/api';
import { RecoveryOpportunity } from '../types';

export const RecoveryOpportunities: React.FC = () => {
  const [opportunities, setOpportunities] = useState<RecoveryOpportunity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOpportunities = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRecoveryOpportunities();
      setOpportunities(data);
    } catch (err: any) {
      console.error('Failed to fetch recovery opportunities:', err);
      setError(err.message || 'Failed to load recovery opportunities from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOpportunities();
  }, []);

  const totalValue = opportunities.reduce((acc, curr) => acc + (curr.potential_revenue || 0), 0);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
            Recovery Opportunities & Interventions
          </h1>
          <p className="text-xs text-fintech-textMuted mt-1">
            High-yield recovery strategies generated autonomously by the RecoverAI engine.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchOpportunities} isLoading={loading} className="gap-2">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Hero Banner Card */}
      <div className="p-6 rounded-card bg-gradient-to-r from-brand-primary via-fintech-darkBg to-brand-primary text-white shadow-medium flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="ai" className="bg-brand-secondary text-white text-[10px]">
              AI Recommender Active
            </Badge>
            <span className="text-xs text-slate-300">Live Backend Stream</span>
          </div>
          <h2 className="text-xl font-display font-bold">
            ${totalValue.toLocaleString()} Total Recoverable Opportunity Identified
          </h2>
          <p className="text-xs text-slate-300 max-w-xl">
            Autonomous retry schedules, personalized dunning workflows, and pre-dispute resolution rules ready for deployment.
          </p>
        </div>
        <Button
          variant="secondary"
          size="md"
          onClick={() => alert('All active autonomous recovery workflows deployed successfully!')}
          className="whitespace-nowrap shadow-subtle gap-2"
        >
          <Zap className="w-4 h-4 fill-white" />
          <span>Execute All Workflows</span>
        </Button>
      </div>

      {loading ? (
        <LoadingSpinner label="Fetching recovery opportunities..." />
      ) : error ? (
        <ErrorBanner message={error} onRetry={fetchOpportunities} />
      ) : opportunities.length === 0 ? (
        <EmptyState
          title="No Recovery Opportunities Found"
          description="There are currently no active recovery strategies recommended by the engine."
        />
      ) : (
        /* Opportunities List */
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {opportunities.map((opp) => (
            <Card key={opp.id} className="flex flex-col justify-between hover:border-brand-primary/40 transition-colors">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <Badge variant="info" className="text-[10px] capitalize">
                    {(opp.risk_type || 'failed_payment').replace(/_/g, ' ')}
                  </Badge>
                  <span className="text-xs font-semibold text-status-success">
                    {opp.success_rate}% Success Rate
                  </span>
                </div>
                <h3 className="text-base font-semibold text-fintech-textPrimary mb-1">
                  {opp.title}
                </h3>
                <p className="text-xs text-fintech-textMuted mb-4 leading-relaxed">
                  {opp.description}
                </p>
              </div>

              <div className="pt-4 border-t border-fintech-border space-y-4">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-fintech-blueGray">Potential Value:</span>
                  <span className="text-lg font-display font-bold text-brand-primary">
                    ${opp.potential_revenue.toLocaleString()}
                  </span>
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  className="w-full justify-center text-xs"
                  onClick={() => alert(`Deployed strategy: ${opp.title}`)}
                >
                  {opp.recommended_action || 'Execute Strategy'} <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

