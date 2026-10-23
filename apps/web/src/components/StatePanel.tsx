import type { ReactNode } from "react";

interface StatePanelProps {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  action?: { label: string; onClick: () => void };
}

/** One shape for empty, offline and error states: what happened, what to do. */
export function StatePanel({ icon, title, children, action }: StatePanelProps) {
  return (
    <section className="state" aria-live="polite">
      <span aria-hidden="true">{icon}</span>
      <h2>{title}</h2>
      <p>{children}</p>
      {action && (
        <button type="button" className="btn" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </section>
  );
}

/** Same footprint as the loaded screen (models, search, rows), so nothing jumps when the catalog arrives. */
export function BootSkeleton() {
  return (
    <div role="status" aria-label="Loading the songbook">
      <div className="boot__models" />
      <div className="boot__search" />
      <div className="songs boot__rows">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="skeleton" />
        ))}
      </div>
    </div>
  );
}

export function SongSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="songs" role="status" aria-label="Loading songs">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton" />
      ))}
    </div>
  );
}
