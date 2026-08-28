import React from 'react';
import { Loader2 } from 'lucide-react';

export const PageLoadingFallback: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[350px] w-full p-8 rounded-card border border-fintech-border/60 bg-white/60 backdrop-blur-xs shadow-subtle animate-fade-in">
      <div className="relative flex items-center justify-center mb-4">
        <div className="w-10 h-10 rounded-full border-2 border-brand-purple/20 border-t-brand-purple animate-spin" />
        <Loader2 className="w-5 h-5 text-brand-purple animate-pulse absolute" />
      </div>
      <p className="text-xs font-medium text-fintech-textSecondary tracking-wide animate-pulse">
        Loading module...
      </p>
    </div>
  );
};

export default PageLoadingFallback;
