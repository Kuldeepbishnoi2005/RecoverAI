import React from 'react';
import { clsx } from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  loading?: boolean;
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  icon,
  loading = false,
  isLoading,
  children,
  className,
  disabled,
  ...props
}) => {
  const isSpinning = loading || isLoading;
  const base = 'inline-flex items-center justify-center font-medium rounded-elem transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 disabled:opacity-50 disabled:cursor-not-allowed';

  const variants = {
    primary: 'bg-brand-primary text-white hover:bg-black active:scale-[0.98]',
    secondary: 'bg-brand-secondary text-white hover:bg-opacity-90 active:scale-[0.98]',
    outline: 'bg-white text-fintech-textPrimary border border-fintech-border hover:bg-surface-muted active:scale-[0.98]',
    ghost: 'bg-transparent text-fintech-textMuted hover:text-fintech-textPrimary hover:bg-surface-muted',
    danger: 'bg-status-danger text-white hover:bg-red-600 active:scale-[0.98]',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-5 py-2.5 text-base gap-2.5',
  };

  return (
    <button
      className={clsx(base, variants[variant], sizes[size], className)}
      disabled={disabled || isSpinning}
      {...props}
    >
      {isSpinning ? (
        <svg className="animate-spin h-4 w-4 text-current" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : (
        icon
      )}
      {children}
    </button>
  );
};
