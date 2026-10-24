import type { ReactNode } from 'react';

type Tab<T extends string> = { id: T; label: string; badge?: ReactNode };

export function Tabs<T extends string>({ tabs, value, onChange, label }: { tabs: Tab<T>[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((t) => (
        <button key={t.id} type="button" role="tab" aria-selected={value === t.id} className={value === t.id ? 'is-on' : ''} onClick={() => onChange(t.id)}>
          {t.label}
          {t.badge}
        </button>
      ))}
    </div>
  );
}

export function LevelChip({ label, tone }: { label: string; tone: 'ok' | 'warn' | 'danger' }) {
  return <span className={`chip chip-${tone}`}>{label}</span>;
}
