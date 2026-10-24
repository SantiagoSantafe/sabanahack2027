type P = { size?: number };

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
});

export const IconPlay = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <path d="M7 5l12 7-12 7z" fill="currentColor" stroke="none" />
  </svg>
);
export const IconPause = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none" />
    <rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor" stroke="none" />
  </svg>
);
export const IconReset = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <path d="M4 4v6h6" />
    <path d="M20 12a8 8 0 1 1-2.3-5.7L20 8" />
  </svg>
);
export const IconCamera = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
    <circle cx="12" cy="13" r="3.5" />
  </svg>
);
export const IconLayers = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <path d="M12 3l9 5-9 5-9-5z" />
    <path d="M3 13l9 5 9-5" />
  </svg>
);
export const IconMore = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <circle cx="5" cy="12" r="1.6" fill="currentColor" />
    <circle cx="12" cy="12" r="1.6" fill="currentColor" />
    <circle cx="19" cy="12" r="1.6" fill="currentColor" />
  </svg>
);
export const IconChevron = ({ size = 14, open = false }: P & { open?: boolean }) => (
  <svg {...base(size)} style={{ transform: open ? 'rotate(180deg)' : undefined, transition: 'transform .15s' }}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);
export const IconJoystick = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <rect x="3" y="14" width="18" height="6" rx="2" />
    <path d="M12 14V8" />
    <circle cx="12" cy="6" r="2.5" />
  </svg>
);
export const IconRobot = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <rect x="4" y="8" width="16" height="7" rx="2" />
    <path d="M7 15l-1 5M17 15l1 5M10 15v5M14 15v5" />
    <circle cx="17" cy="11.5" r="1" fill="currentColor" />
  </svg>
);
export const IconClose = ({ size = 14 }: P) => (
  <svg {...base(size)}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);
export const IconGrid = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <rect x="4" y="4" width="7" height="7" rx="1" />
    <rect x="13" y="4" width="7" height="7" rx="1" />
    <rect x="4" y="13" width="7" height="7" rx="1" />
    <rect x="13" y="13" width="7" height="7" rx="1" />
  </svg>
);
export const IconSkip = ({ size = 14 }: P) => (
  <svg {...base(size)}>
    <path d="M5 5l9 7-9 7z" fill="currentColor" stroke="none" />
    <path d="M18 5v14" />
  </svg>
);
export const IconRecord = ({ size = 16 }: P) => (
  <svg {...base(size)}>
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none" />
  </svg>
);
