import React from 'react';
import { clsx } from 'clsx';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'ai'
  | 'neutral';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  children,
  className,
  dot = false,
}) => {
  const styles: Record<BadgeVariant, string> = {
    success: 'bg-status-successBg text-status-success border-status-success/20',
    warning: 'bg-status-warningBg text-status-warning border-status-warning/20',
    danger: 'bg-status-dangerBg text-status-danger border-status-danger/20',
    info: 'bg-status-infoBg text-status-info border-status-info/20',
    ai: 'bg-brand-lavenderLight text-brand-secondary border-brand-lavender/40',
    neutral: 'bg-surface-muted text-fintech-textMuted border-fintech-border',
  };

  const dotColors: Record<BadgeVariant, string> = {
    success: 'bg-status-success',
    warning: 'bg-status-warning',
    danger: 'bg-status-danger',
    info: 'bg-status-info',
    ai: 'bg-brand-secondary',
    neutral: 'bg-fintech-blueGray',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border tracking-wide uppercase',
        styles[variant],
        className
      )}
    >
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
      {children}
    </span>
  );
};
