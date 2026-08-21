import React from 'react';
import { clsx } from 'clsx';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'ai' | 'flat';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'md',
  children,
  className,
  ...props
}) => {
  const paddingClasses = {
    none: 'p-0',
    sm: 'p-3',
    md: 'p-5',
    lg: 'p-6',
  };

  return (
    <div
      className={clsx(
        'rounded-card border transition-all duration-200',
        paddingClasses[padding],
        variant === 'default' && 'bg-white border-fintech-border shadow-subtle',
        variant === 'ai' && 'bg-gradient-to-br from-white via-white to-brand-lavenderLight border-brand-lavender/40 shadow-subtle',
        variant === 'flat' && 'bg-surface-muted border-fintech-border shadow-none',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
