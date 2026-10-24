import { Html, RoundedBox } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { useStore } from '../state/store';
import { palette } from '../theme/palette';
import { DEFAULT_LEVELS, fmt } from '../ui/format';
import type { FieldGeom } from './geometry';
import { clearTextureCache, markerTexture, signTexture, speckleTexture } from './textures';

type Props = { g: FieldGeom; light?: boolean };

export function Ground({ g }: Props) {
  const grass = useMemo(
    () => speckleTexture('grass', palette.grass, ['#5FAE3A', '#8ED65A', '#4E9A2F', '#A5DE6A'], 2600, [g.groundW / 3, g.groundD / 3]),
    [g.groundW, g.groundD],
  );
  const dirt = useMemo(() => speckleTexture('path', palette.path, ['#B88A55', '#D8B27E', '#A77A48'], 1600, [(g.x1 - g.x0 + 12) / 3, 2]), [g.x0, g.x1]);
  const floor = useMemo(
    () => speckleTexture('floor', palette.tunnelFloor, ['#B7794A', '#D69A66', '#A86C40'], 2200, [(g.x1 - g.x0) / 3, (g.bed_z1 - g.bed_z0) / 3]),
    [g.x0, g.x1, g.bed_z0, g.bed_z1],
  );
  const cover = useMemo(() => speckleTexture('cover', palette.groundCover, ['#2A2C33', '#3E414A', '#454852'], 1800, [1, 40]), []);
  const cx = (g.x0 + g.x1) / 2;
  const tunnelLen = g.bed_z1 - g.bed_z0 + g.north_w + 0.3;
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[cx, 0, (g.bed_z0 + g.bed_z1) / 2]} receiveShadow>
        <planeGeometry args={[g.groundW + 40, g.groundD + 40]} />
        <meshStandardMaterial map={grass} roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[cx, 0.004, g.bed_z0 - g.main_path_w / 2]} receiveShadow>
        <planeGeometry args={[g.x1 - g.x0 + 12, g.main_path_w]} />
        <meshStandardMaterial map={dirt} roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[cx, 0.005, g.bed_z0 - 0.3 + tunnelLen / 2]} receiveShadow>
        <planeGeometry args={[g.x1 - g.x0, tunnelLen]} />
        <meshStandardMaterial map={floor} roughness={1} />
      </mesh>
      {g.central && (
        /* camino central entre el Bloque 1 y el Bloque 2, a lo largo de las camas */
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[(g.central[0] + g.central[1]) / 2, 0.007, g.bed_z0 - 0.3 + tunnelLen / 2]} receiveShadow>
          <planeGeometry args={[g.central[1] - g.central[0], tunnelLen]} />
          <meshStandardMaterial map={dirt} roughness={1} />
        </mesh>
      )}
      {g.bed_x.map((x, i) => (
        <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[x, 0.008, (g.bed_z0 + g.bed_z1) / 2]} receiveShadow>
          <planeGeometry args={[g.bed_w + 0.25, g.bed_z1 - g.bed_z0]} />
          <meshStandardMaterial map={cover} roughness={0.9} />
        </mesh>
      ))}
    </group>
  );
}

/** Drip line along every pot row, with one stake per pot. */
export function DripLines({ g, light }: Props) {
  if (light) return null;
  const len = g.bed_z1 - g.bed_z0;
  return (
    <group>
      {g.bed_x.map((x, i) => (
        <mesh key={i} position={[x + 0.12, g.bedH + 0.03, (g.bed_z0 + g.bed_z1) / 2]} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.012, 0.012, len, 5]} />
          <meshStandardMaterial color={palette.drip} roughness={0.4} />
        </mesh>
      ))}
      <mesh position={[(g.x0 + g.x1) / 2, 0.04, g.bed_z0 - 0.15]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.03, 0.03, g.x1 - g.x0, 8]} />
        <meshStandardMaterial color={palette.drip} roughness={0.4} />
      </mesh>
    </group>
  );
}

export function ArucoMarkers({ g }: Props) {
  const beds = useStore((s) => s.state?.robot.sensors?.last_aruco?.beds);
  return (
    <group>
      {g.bed_x.map((x, i) => {
        const hot = beds?.includes(i) ?? false;
        return (
          <group key={i} position={[x, 0, g.bed_z0 - 0.22]}>
            <mesh position={[0, 0.45, 0]} castShadow>
              <boxGeometry args={[0.04, 0.9, 0.04]} />
              <meshStandardMaterial color={palette.woodDark} />
            </mesh>
            <mesh position={[0, 0.92, -0.025]} rotation={[0, Math.PI, 0]}>
              <planeGeometry args={[0.3, 0.38]} />
              <meshStandardMaterial
                map={markerTexture(i + 1, g.beds_per_nave)}
                emissive={hot ? palette.sensorBeam : '#000000'}
                emissiveIntensity={hot ? 0.3 : 0}
                side={THREE.DoubleSide}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

export function FarmSign({ g }: Props) {
  const [fontsReady, setFontsReady] = useState(0);
  useEffect(() => {
    document.fonts?.ready.then(() => {
      clearTextureCache('sign-');
      setFontsReady((v) => v + 1);
    });
  }, []);
  const tex = useMemo(
    () => signTexture('Arándanos de la Sabana', g.blocks && g.blocks.length > 1 ? `Bloque 1 · camino central · Bloque 2` : `Bloque 1, ${g.naves} naves en macrotúnel`),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [fontsReady, g.naves, g.blocks?.length],
  );
  return (
    <group position={[g.central ? (g.central[0] + g.central[1]) / 2 + 4 : (g.x0 + g.x1) / 2 + 4, 0, g.bed_z0 - g.main_path_w - 1.2]}>
      {[-1.25, 1.25].map((px) => (
        <mesh key={px} position={[px, 0.9, 0]} castShadow>
          <cylinderGeometry args={[0.07, 0.08, 1.8, 8]} />
          <meshStandardMaterial color={palette.woodDark} roughness={0.9} />
        </mesh>
      ))}
      <RoundedBox args={[3.0, 1.12, 0.1]} radius={0.04} position={[0, 1.42, 0]} castShadow>
        <meshStandardMaterial color={palette.woodDark} />
      </RoundedBox>
      <mesh position={[0, 1.42, -0.056]} rotation={[0, Math.PI, 0]}>
        <planeGeometry args={[2.86, 1.0]} />
        <meshStandardMaterial map={tex} roughness={0.8} />
      </mesh>
    </group>
  );
}

export function Dock({ g }: Props) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ring.current) return;
    const charging = useStore.getState().state?.robot.state === 'charging';
    const m = ring.current.material as THREE.MeshStandardMaterial;
    m.emissiveIntensity = charging ? 0.6 + 0.4 * Math.sin(clock.elapsedTime * 3) : 0.35;
  });
  return (
    <group position={[g.base[0], 0, g.base[1]]}>
      <mesh position={[0, 0.03, 0]} receiveShadow>
        <cylinderGeometry args={[0.75, 0.8, 0.06, 32]} />
        <meshStandardMaterial color={palette.ink} roughness={0.6} />
      </mesh>
      <mesh ref={ring} position={[0, 0.065, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.55, 0.65, 40]} />
        <meshStandardMaterial color={palette.robotAccent} emissive={palette.robotAccent} emissiveIntensity={0.35} />
      </mesh>
      <RoundedBox args={[0.32, 1.0, 0.22]} radius={0.04} position={[-0.95, 0.5, 0]} castShadow>
        <meshStandardMaterial color={palette.robotShell} />
      </RoundedBox>
      <mesh position={[-0.95, 0.85, 0.115]}>
        <planeGeometry args={[0.18, 0.08]} />
        <meshBasicMaterial color={palette.robotAccent} toneMapped={false} />
      </mesh>
    </group>
  );
}

/** Datalogger box on each nave wall; with a fixed network (B, F) it also reports live. */
export function SensorStations({ g }: Props) {
  const show = useStore((s) => s.showStations);
  const live = useStore((s) => s.state?.sensor_network ?? false);
  const w = useStore((s) => s.state?.weather);
  const risk = useStore((s) => s.state?.risk.per_bed);
  const lv = useStore((s) => s.state?.risk_levels) ?? DEFAULT_LEVELS;
  return (
    <group>
      {Array.from({ length: g.naves }, (_, k) => {
        const beds = Array.from({ length: g.beds_per_nave }, (_, j) => k * g.beds_per_nave + j);
        const r = Math.max(...beds.map((b) => risk?.[b] ?? 0));
        const rh = beds.reduce((acc, b) => acc + (w?.RH_bed?.[b] ?? 0), 0) / beds.length;
        const x = g.nave_x0[k] + (k === 0 ? 0.15 : 0);
        return (
          <group key={k} position={[x, 0, 0]}>
            <mesh position={[0, 0.8, 0]} castShadow>
              <cylinderGeometry args={[0.03, 0.035, 1.6, 8]} />
              <meshStandardMaterial color={palette.steel} metalness={0.5} roughness={0.35} />
            </mesh>
            <RoundedBox args={[0.2, 0.26, 0.12]} radius={0.03} position={[0, 1.35, 0]} castShadow>
              <meshStandardMaterial color={palette.robotShell} />
            </RoundedBox>
            <mesh position={[0, 1.3, 0.07]}>
              <sphereGeometry args={[0.025, 10, 8]} />
              <meshBasicMaterial color={r >= lv.high ? palette.danger : r >= lv.medium ? palette.warn : palette.leafUi} toneMapped={false} />
            </mesh>
            {show && w && (
              <Html position={[0, 1.85, 0]} center zIndexRange={[12, 0]}>
                <div className={`station-tag ${live ? 'is-live' : ''}`}>
                  <strong>
                    {live ? 'Estación' : 'Datalogger'} nave {k + 1}
                  </strong>
                  <span>
                    {fmt(w.T_in, 1)} °C, {fmt(rh, 0)} % HR
                  </span>
                </div>
              </Html>
            )}
          </group>
        );
      })}
    </group>
  );
}

export function RiskHeatmap({ g }: Props) {
  const show = useStore((s) => s.showHeatmap);
  const risks = useStore((s) => s.state?.risk.per_bed);
  const high = useStore((s) => s.state?.risk_levels?.high) ?? DEFAULT_LEVELS.high;
  const mats = useMemo(
    () => g.bed_x.map(() => new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, toneMapped: false })),
    [g.bed_x],
  );
  useEffect(() => {
    mats.forEach((m, i) => {
      const k = Math.min((risks?.[i] ?? 0) / high, 1);
      m.color.setHSL((1 - k) * 0.3, 0.9, 0.55);
      m.opacity = 0.25 + k * 0.5;
    });
  }, [mats, risks, high]);
  if (!show) return null;
  return (
    <group>
      {g.bed_x.map((x, i) => (
        <mesh key={i} position={[x, 0.014, (g.bed_z0 + g.bed_z1) / 2]} rotation={[-Math.PI / 2, 0, 0]} material={mats[i]}>
          <planeGeometry args={[g.bed_w + 1.1, g.bed_z1 - g.bed_z0]} />
        </mesh>
      ))}
    </group>
  );
}
