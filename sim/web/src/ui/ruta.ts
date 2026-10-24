import { create } from 'zustand';

/** Parameters of the Ruta real (sent with every dry-run / start). `largo` 0 = no length limit. */
type Rp = { escala: number; largo: number; deriva: number; escaneos: number };
export const useRutaParams = create<Rp & { set: (p: Partial<Rp>) => void }>(
  (set) => ({ escala: 0.01, largo: 0, deriva: 0.4, escaneos: 2, set: (p) => set(p) }),
);
