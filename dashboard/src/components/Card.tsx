import type { ReactNode } from 'react'

/** Etiqueta de sección estilo panel técnico: "ALERTAS". Sin numeración: los números no seguían el orden de la página. */
export function Tag({ children }: { n?: string; children: ReactNode }) {
  return <p className="tag">{children}</p>
}

/** Botón circular con flecha ↗ para abrir el detalle de una tarjeta. */
export function ArrowBtn({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label} className="icon-btn shrink-0">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M7 17 17 7M8 7h9v9" /></svg>
    </button>
  )
}

export function Card({ n, tag, onOpen, openLabel, title, sub, className = '', children, label, id }: {
  id?: string; n?: string; tag: string; onOpen?: () => void; openLabel?: string; title?: string; sub?: string; className?: string; children: ReactNode; label: string
}) {
  return (
    <section id={id} className={`card p-5 md:p-6 ${className}`} aria-label={label}>
      <div className="flex items-start justify-between gap-3">
        <Tag n={n}>{tag}</Tag>
        {onOpen && <ArrowBtn label={openLabel ?? 'Abrir detalle'} onClick={onOpen} />}
      </div>
      {title && <h2 className="mt-2 text-title font-semibold text-fg">{title}</h2>}
      {sub && <p className="mb-3 text-label text-fg-muted">{sub}</p>}
      {children}
    </section>
  )
}

/** Número grande con decimales y unidad más pequeños y grises: 9<small>,3</small> °C. */
export function Big({ valor, unidad, size = 'text-[3.25rem]' }: { valor: string; unidad?: string; size?: string }) {
  const [ent, dec] = valor.split(',')
  return (
    <p className={`num ${size} text-fg`}>
      {ent}{dec != null && <span className="text-[.5em] font-semibold text-fg-subtle">,{dec}</span>}
      {unidad && <span className="ml-1.5 text-[.4em] font-medium text-fg-subtle">{unidad}</span>}
    </p>
  )
}
