/** @type {import('tailwindcss').Config} */
// Los valores viven en src/index.css (:root) como variables CSS: única fuente de tokens.
const c = (n) => `rgb(var(--c-${n}) / <alpha-value>)`
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: c('brand'), 700: c('brand-700'), 300: c('brand-300') },
        gold: { DEFAULT: c('gold'), 300: c('gold-300') },
        ink: { 950: c('ink-950'), 900: c('ink-900'), 800: c('ink-800'), 700: c('ink-700'), 600: c('ink-600') },
        fg: { DEFAULT: c('fg'), muted: c('fg-muted'), subtle: c('fg-subtle') },
        pos: { DEFAULT: c('pos'), 300: c('pos-300') },
        danger: { DEFAULT: c('danger'), 300: c('danger-300') },
        warn: { DEFAULT: c('warn'), 300: c('warn-300') },
      },
      fontFamily: { sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'] },
      borderRadius: { card: 'var(--r-card)', ctl: 'var(--r-ctl)' },
      boxShadow: { card: 'var(--sh-card)', pop: 'var(--sh-pop)' },
      fontSize: {
        // Escala tipográfica (rem: crece con el modo presentación)
        label: ['0.75rem', { lineHeight: '1rem' }],
        body: ['0.875rem', { lineHeight: '1.35rem' }],
        title: ['1rem', { lineHeight: '1.5rem' }],
        kpi: ['2.25rem', { lineHeight: '2.5rem' }],
      },
      spacing: { gutter: 'var(--gutter)', gap: 'var(--gap)' },
    },
  },
  plugins: [],
}
