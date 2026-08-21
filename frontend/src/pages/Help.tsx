import React from 'react';
import { HelpCircle, BookOpen, ShieldCheck, Cpu } from 'lucide-react';
import { Card } from '../components/common/Card';

export const Help: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-200 max-w-4xl">
      <div>
        <h1 className="text-2xl font-display font-bold text-fintech-textPrimary tracking-tight">
          Help & Platform Documentation
        </h1>
        <p className="text-xs text-fintech-textMuted mt-1">
          Understanding RecoverAI architecture, Row-Level Security, and AI decision transparency.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="w-5 h-5 text-status-success" />
            <h3 className="text-sm font-semibold text-fintech-textPrimary">Multi-Tenant RLS Security</h3>
          </div>
          <p className="text-xs text-fintech-textMuted leading-relaxed">
            Every database table in Supabase is secured with PostgreSQL Row-Level Security. Data query isolation is guaranteed per merchant through authenticated sessions (`get_auth_merchant_id()`).
          </p>
        </Card>

        <Card>
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-5 h-5 text-brand-primary" />
            <h3 className="text-sm font-semibold text-fintech-textPrimary">Autonomous AI Engine</h3>
          </div>
          <p className="text-xs text-fintech-textMuted leading-relaxed">
            Powered by Gemini 1.5 Pro and custom fintech agents. All decision rationale, prompt outputs, and JSON payloads are saved to `ai_decisions` for complete audit compliance.
          </p>
        </Card>
      </div>
    </div>
  );
};
