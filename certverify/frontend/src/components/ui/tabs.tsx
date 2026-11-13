import * as React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface TabsContextValue {
  value: string;
  onValueChange: (val: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

export const Tabs: React.FC<{
  value: string;
  onValueChange: (val: string) => void;
  className?: string;
  children: React.ReactNode;
}> = ({ value, onValueChange, className, children }) => {
  return (
    <TabsContext.Provider value={{ value, onValueChange }}>
      <div className={twMerge(clsx('w-full', className))}>{children}</div>
    </TabsContext.Provider>
  );
};

export const TabsList: React.FC<{ className?: string; children: React.ReactNode }> = ({
  className,
  children,
}) => (
  <div
    className={twMerge(
      clsx(
        'inline-flex h-9 items-center justify-center rounded-lg bg-slate-100 p-1 text-slate-500',
        className
      )
    )}
  >
    {children}
  </div>
);

export const TabsTrigger: React.FC<{
  value: string;
  className?: string;
  children: React.ReactNode;
}> = ({ value, className, children }) => {
  const ctx = React.useContext(TabsContext);
  const isSelected = ctx?.value === value;
  return (
    <button
      type="button"
      onClick={() => ctx?.onValueChange(value)}
      className={twMerge(
        clsx(
          'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50',
          isSelected ? 'bg-white text-slate-950 shadow-sm' : 'hover:text-slate-900',
          className
        )
      )}
    >
      {children}
    </button>
  );
};

export const TabsContent: React.FC<{
  value: string;
  className?: string;
  children: React.ReactNode;
}> = ({ value, className, children }) => {
  const ctx = React.useContext(TabsContext);
  if (ctx?.value !== value) return null;
  return <div className={twMerge(clsx('mt-2 focus-visible:outline-none', className))}>{children}</div>;
};

