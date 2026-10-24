import { D1 } from './gait';

export const STATE_LABEL: Record<string, string> = {
  walking: 'Recorriendo',
  inspecting: 'Inspeccionando planta',
  returning: 'Volviendo a la base',
  charging: 'Cargando',
  docked: 'En la base',
  failed: 'Detenido, requiere rescate',
  stuck: 'Atascado en barro',
  manual: 'Control manual',
};

export const PLATFORM_NAME: Record<string, string> = {
  quadruped: 'AgiBot D1',
  humanoid: 'Humanoide',
  wheeled: 'Plataforma con ruedas',
  sprayer: 'Aspersora con cámara',
  human: 'Monitor humano',
};

/** Camera height and forward offset per platform (matches the alternative YAMLs). */
export function cameraSpec(platform: string, mast: boolean): { h: number; fwd: number } {
  switch (platform) {
    case 'quadruped':
      return { h: mast ? D1.mastHeight : D1.cameraHeight, fwd: D1.cameraForward };
    case 'humanoid':
      return { h: 1.2, fwd: 0.12 };
    case 'wheeled':
      return { h: 1.45, fwd: 0.0 };
    case 'sprayer':
      return { h: 1.0, fwd: 0.7 };
    default:
      return { h: 1.6, fwd: 0.12 };
  }
}
