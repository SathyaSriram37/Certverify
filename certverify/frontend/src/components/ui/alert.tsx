import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export const Alert = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { variant?: 'default' | 'destructive' | 'success' | 'warning' }
>(({ className, variant = 'default', ...props }, ref) => {
  const variants: Record<string, string> = {
    default: 'bg-white text-slate-900 border-slate-200',
    destructive: 'border-red-500/50 text-red-700 bg-red-50/50 dark:border-red-500 [&>svg]:text-red-600',
    success: 'border-emerald-500/50 text-emerald-800 bg-emerald-50/50 [&>svg]:text-emerald-600',
    warning: 'border-amber-500/50 text-amber-800 bg-amber-50/50 [&>svg]:text-amber-600',
  };
  return (
    <div
      ref={ref}
      role="alert"
      className={twMerge(
        clsx(
          'relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground',
          variants[variant],
          className
        )
      )}
      {...props}
    />
  );
});
Alert.displayName = 'Alert';

export const AlertTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h5 ref={ref} className={twMerge(clsx('mb-1 font-medium leading-none tracking-tight', className))} {...props} />
  )
);
AlertTitle.displayName = 'AlertTitle';

export const AlertDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={twMerge(clsx('text-sm [&_p]:leading-relaxed', className))} {...props} />
  )
);
AlertDescription.displayName = 'AlertDescription';

