import React from "react";
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  badge?: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  badge = "Awaiting Phase 2 Integration",
  actionText,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center rounded-xl border border-dashed border-border bg-card/50 shadow-sm max-w-2xl mx-auto my-12">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-4 ring-8 ring-primary/5">
        <Icon className="h-8 w-8" />
      </div>
      {badge && (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-secondary-foreground mb-3 border border-border">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          {badge}
        </span>
      )}
      <h3 className="text-xl font-semibold text-foreground tracking-tight mb-2">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground max-w-md mb-6 leading-relaxed">
        {description}
      </p>
      {actionText && (
        <button
          onClick={onAction}
          className="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
