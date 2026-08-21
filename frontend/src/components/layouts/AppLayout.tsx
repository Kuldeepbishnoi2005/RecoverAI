import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans text-fintech-textPrimary antialiased">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Area */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* Header */}
        <Header onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="py-4 px-8 border-t border-fintech-border bg-white text-center text-xs text-fintech-textMuted flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            © {new Date().getFullYear()} RecoverAI Platform. All rights reserved. Turn lost revenue into recovered revenue.
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <a href="#security" className="hover:underline text-fintech-blueGray">Security & RLS</a>
            <span>·</span>
            <a href="#api" className="hover:underline text-fintech-blueGray">API Docs</a>
            <span>·</span>
            <a href="#audit" className="hover:underline text-fintech-blueGray">Audit Compliance</a>
          </div>
        </footer>
      </div>
    </div>
  );
};
