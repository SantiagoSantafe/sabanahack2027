import { Line } from '@react-three/drei';
import { useMemo } from 'react';
import { useStore } from '../state/store';

/** The Ruta real polyline drawn on the ground: amber = simulation (dry-run), green = running, grey = paused. */
export function RutaReal() {
  const ruta = useStore((s) => s.realRobot?.ruta);
  const pts = useMemo(() => (ruta?.puntos ?? []).map(([x, z]) => [x, 0.08, z] as [number, number, number]), [ruta?.puntos]);
  if (!ruta || pts.length < 2) return null;
  const color = ruta.estado === 'simulacion' ? '#ffb020' : ruta.estado === 'pausa' ? '#9aa3b2' : '#35d07f';
  return (
    <group>
      <Line points={pts} color={color} lineWidth={4} depthTest={false} renderOrder={20} />
      <mesh position={pts[pts.length - 1]} renderOrder={21}>
        <sphereGeometry args={[0.12, 12, 12]} />
        <meshBasicMaterial color={color} depthTest={false} />
      </mesh>
    </group>
  );
}
