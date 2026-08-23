import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertTriangle,
  Wallet,
  ReceiptText,
  Brain,
  BarChart3,
  FileCheck2,
  Settings,
  HelpCircle,
  ShieldCheck,
  UserCheck,
  ChevronDown
} from 'lucide-react';
import { Badge } from '../common/Badge';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  badge?: string;
}

interface NavSection {
  sectionTitle: string;
  items: NavItem[];
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const sections: NavSection[] = [
    {
      sectionTitle: 'WORKSPACE',
      items: [
        { label: 'Overview', path: '/', icon: <LayoutDashboard className="w-4 h-4" /> },
        { label: 'Revenue Risk', path: '/revenue-risk', icon: <AlertTriangle className="w-4 h-4" /> },
        { label: 'Recovery Opportunities', path: '/recovery-opportunities', icon: <Wallet className="w-4 h-4" /> },
        { label: 'Transactions', path: '/transactions', icon: <ReceiptText className="w-4 h-4" /> },
      ],
    },
    {
      sectionTitle: 'INTELLIGENCE',
      items: [
        { label: 'AI Decisions', path: '/ai-decisions', icon: <Brain className="w-4 h-4" />, badge: 'AI' },
        { label: 'Manual Review', path: '/manual-review', icon: <UserCheck className="w-4 h-4" />, badge: 'Review' },
        { label: 'Analytics', path: '/analytics', icon: <BarChart3 className="w-4 h-4" /> },
        { label: 'Audit Logs', path: '/audit-logs', icon: <FileCheck2 className="w-4 h-4" /> },
      ],
    },
    {
      sectionTitle: 'SYSTEM',
      items: [
        { label: 'Settings', path: '/settings', icon: <Settings className="w-4 h-4" /> },
        { label: 'Help', path: '/help', icon: <HelpCircle className="w-4 h-4" /> },
      ],
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-white border-r border-fintech-border flex flex-col transition-transform duration-200 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-fintech-border flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-elem bg-brand-primary flex items-center justify-center text-white font-display font-bold text-lg tracking-wider">
              R
            </div>
            <div>
              <span className="font-display font-bold text-base text-fintech-textPrimary tracking-tight">
                Recover<span className="text-brand-secondary font-extrabold">AI</span>
              </span>
              <span className="block text-[10px] text-fintech-textMuted leading-none mt-0.5">
                Revenue Recovery
              </span>
            </div>
          </div>
          <Badge variant="ai" className="text-[10px] px-1.5 py-0">v1.0</Badge>
        </div>

        {/* Merchant Selector Pill */}
        <div className="p-4 border-b border-fintech-border/60 bg-surface-muted/30">
          <div className="flex items-center justify-between p-2.5 rounded-elem border border-fintech-border bg-white shadow-2xs hover:border-fintech-blueGray/40 cursor-pointer transition-colors">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-6 h-6 rounded bg-brand-secondary/10 text-brand-secondary flex items-center justify-center font-bold text-xs">
                A
              </div>
              <div className="truncate">
                <span className="block text-xs font-semibold text-fintech-textPrimary truncate">Acme Merchant</span>
                <span className="block text-[10px] text-fintech-textMuted truncate">Enterprise Plan</span>
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-fintech-blueGray" />
          </div>
        </div>

        {/* Navigation items */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {sections.map((sec) => (
            <div key={sec.sectionTitle}>
              <h4 className="px-3 text-[10px] font-semibold text-fintech-blueGray tracking-widest uppercase mb-2">
                {sec.sectionTitle}
              </h4>
              <nav className="space-y-1">
                {sec.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `flex items-center justify-between px-3 py-2 rounded-elem text-xs font-medium transition-colors ${
                        isActive
                          ? 'bg-brand-primary text-white shadow-2xs font-semibold'
                          : 'text-fintech-textMuted hover:text-fintech-textPrimary hover:bg-surface-muted'
                      }`
                    }
                  >
                    <div className="flex items-center gap-2.5">
                      {item.icon}
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <Badge variant="ai" className="px-1.5 py-0 text-[9px]">
                        {item.badge}
                      </Badge>
                    )}
                  </NavLink>
                ))}
              </nav>
            </div>
          ))}
        </div>

        {/* Audit & Compliance footer badge */}
        <div className="p-4 border-t border-fintech-border bg-white">
          <div className="flex items-center gap-2 p-2.5 rounded-elem bg-surface-muted text-xs text-fintech-textMuted">
            <ShieldCheck className="w-4 h-4 text-status-success flex-shrink-0" />
            <span className="text-[11px] leading-tight font-medium">
              Audit Trail Active · RLS Isolated
            </span>
          </div>
        </div>
      </aside>
    </>
  );
};
