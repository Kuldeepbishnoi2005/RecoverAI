import React, { useState } from 'react';
import { Menu, Search, Bell, Sparkles, User, LogOut, CheckCircle2 } from 'lucide-react';
import { Badge } from '../common/Badge';

interface HeaderProps {
  onMenuToggle: () => void;
  userEmail?: string;
  onLogout?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onMenuToggle, userEmail = 'merchant@acme.com', onLogout }) => {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-fintech-border px-4 lg:px-8 flex items-center justify-between shadow-2xs">
      {/* Left section: Mobile menu + Search */}
      <div className="flex items-center gap-3 flex-1 max-w-xl">
        <button
          onClick={onMenuToggle}
          className="p-2 rounded-elem text-fintech-textMuted hover:text-fintech-textPrimary hover:bg-surface-muted lg:hidden"
          aria-label="Toggle navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="relative w-full max-w-md hidden sm:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-fintech-blueGray" />
          <input
            type="text"
            placeholder="Search transactions, risk events, AI decisions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-surface-muted border border-fintech-border rounded-elem text-xs text-fintech-textPrimary placeholder:text-fintech-blueGray focus:outline-none focus:border-brand-primary focus:bg-white transition-colors"
          />
        </div>
      </div>

      {/* Right section: Badges, Notifications, User */}
      <div className="flex items-center gap-3">
        {/* System Status Indicator */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-status-success/10 border border-status-success/20 text-xs text-status-success font-medium">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>System Operational</span>
        </div>

        {/* AI Engine Status */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-secondary/10 border border-brand-secondary/20 text-xs text-brand-secondary font-medium">
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span>AI Recovery Engine Active</span>
        </div>

        {/* Notifications */}
        <button
          className="relative p-2 rounded-elem text-fintech-textMuted hover:text-fintech-textPrimary hover:bg-surface-muted transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-brand-secondary" />
        </button>

        {/* User profile avatar & menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2.5 p-1 rounded-full hover:bg-surface-muted transition-colors focus:outline-none"
          >
            <div className="w-8 h-8 rounded-full bg-brand-primary text-white flex items-center justify-center font-semibold text-xs border border-white shadow-2xs">
              AM
            </div>
          </button>

          {/* User Dropdown */}
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-56 bg-white border border-fintech-border rounded-card shadow-medium p-1 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-2.5 border-b border-fintech-border">
                <span className="block text-xs font-semibold text-fintech-textPrimary">Acme Merchant Account</span>
                <span className="block text-[11px] text-fintech-textMuted truncate">{userEmail}</span>
              </div>
              <div className="py-1">
                <button
                  onClick={() => setShowUserMenu(false)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-fintech-textMuted hover:text-fintech-textPrimary hover:bg-surface-muted rounded-elem transition-colors"
                >
                  <User className="w-4 h-4" />
                  <span>Profile & Billing</span>
                </button>
              </div>
              <div className="pt-1 border-t border-fintech-border">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    if (onLogout) onLogout();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs text-status-danger hover:bg-status-danger/10 rounded-elem transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
