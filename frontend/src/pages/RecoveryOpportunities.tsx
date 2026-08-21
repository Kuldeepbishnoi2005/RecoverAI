import React from 'react';
import { Wallet, Sparkles, ArrowRight, CheckCircle2, Zap } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { MOCK_RECOVERY_OPPORTUNITIES } from '../lib/mockData';

export const RecoveryOpportunities: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          Recovery Opportunities & Interventions
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          High-yield recovery strategies generated autonomously by the RecoverAI engine.
        </p>
      </div>

      {/* Hero Banner Card */}
      <div className="p-6 rounded-card bg-gradient-to-r from-brand-primary via-fintech-darkBg to-brand-primary text-white shadow-medium flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="ai" className="bg-brand-secondary text-white text-[10px]">
              AI Recommender Active
            </Badge>
            <span className="text-xs text-slate-300">Updated 5 minutes ago</span>
          </div>
          <h2 className="text-xl font-display font-bold">
            $106,400 Total Recoverable Opportunity Identified
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

      {/* Opportunities List */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {MOCK_RECOVERY_OPPORTUNITIES.map((opp) => (
          <Card key={opp.id} className="flex flex-col justify-between hover:border-brand-primary/40 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-3">
                <Badge variant="info" className="text-[10px] capitalize">
                  {opp.risk_type.replace(/_/g, ' ')}
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
                {opp.recommended_action} <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
