import React from 'react';
import { Database, AlertCircle } from 'lucide-react';
import { Button } from './Button';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Data Available',
  description = 'There are currently no records to display. Data will populate automatically when transactions or risk events occur.',
  icon,
  actionLabel,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center rounded-card border border-dashed border-fintech-border bg-white/50">
      <div className="w-12 h-12 rounded-full bg-surface-muted flex items-center justify-center text-fintech-blueGray mb-4">
        {icon || <Database className="w-6 h-6" />}
      </div>
      <h3 className="text-base font-semibold text-fintech-textPrimary mb-1">{title}</h3>
      <p className="text-xs text-fintech-textMuted max-w-sm mb-6">{description}</p>
      {actionLabel && onAction && (
        <Button variant="outline" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};

export const LoadingSpinner: React.FC<{ label?: string }> = ({ label = 'Loading records...' }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="w-8 h-8 border-2 border-brand-primary/20 border-t-brand-primary rounded-full animate-spin mb-3" />
      <span className="text-xs text-fintech-textMuted font-medium">{label}</span>
    </div>
  );
};

export const ErrorBanner: React.FC<{ message: string; onRetry?: () => void }> = ({
  message,
  onRetry,
}) => {
  return (
    <div className="flex items-center justify-between p-4 rounded-elem bg-status-dangerBg border border-status-danger/20 text-status-danger text-sm">
      <div className="flex items-center gap-2.5">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <span>{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs font-semibold underline hover:no-underline ml-4"
        >
          Retry
        </button>
      )}
    </div>
  );
};
