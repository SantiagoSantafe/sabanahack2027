import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import * as THREE from 'three';
import { useStore, type SimState } from '../state/store';
import { palette } from '../theme/palette';
import { RobotView } from '../robot/RobotView';
import { Crop } from '../scene/Crop';
import { fieldGeom } from '../scene/geometry';
import { detailFor } from '../scene/plantModel';
import { SkyDome } from '../scene/SkyDome';
import { Dock, Ground } from '../scene/Terrain';
import { fmt } from './format';

function MiniScene({ state, bytes }: { state: SimState; bytes: Uint8Array }) {
  const heights = useStore((s) => s.heights);
  const spreadL = useStore((s) => s.spreadL);
  const spreadR = useStore((s) => s.spreadR);
  const g = fieldGeom(state);
  const w = g.x1 - g.x0;
  return (
    <>
      <color attach="background" args={[palette.sky]} />
      <SkyDome />
      <hemisphereLight args={['#D7ECFF', '#6B8F3A', 0.95]} />
      <directionalLight position={[30, 40, -25]} intensity={2.2} color="#FFF3DA" />
      <PerspectiveCamera makeDefault position={[g.x1 + w * 0.35, w * 1.1, g.bed_z0 - w * 0.9]} fov={42} />
      <OrbitControls target={[(g.x0 + g.x1) / 2, 0, g.bed_z0 + 18]} enablePan={false} maxPolarAngle={Math.PI / 2.2} />
      <Ground g={g} light />
      <Dock g={g} light />
      <Crop g={g} heights={heights} spreadL={spreadL} spreadR={spreadR} plantBytes={bytes} godMode={false} detail={detailFor(g.nBeds * g.nPlants, true)} shadows={false} />
      <RobotView g={g} heights={heights} compact robotOverride={state.robot} />
    </>
  );
}

export function CompareGrid() {
  const states = useStore((s) => s.compareStates);
  const bytes = useStore((s) => s.comparePlantBytes);
  const recordMode = useStore((s) => s.recordMode);
  if (states.length === 0) return null;

  return (
    <div className={`compare-grid ${recordMode ? 'is-record' : ''}`}>
      {states.map((st, i) => {
        const m = st.metrics;
        const det = m.first_detection_day as number | null;
        return (
          <div key={st.alternative} className="compare-cell">
            <div className="compare-caption">
              <b>{st.alternative}</b> {st.alternative_name}
            </div>
            <Canvas dpr={[1, 1.5]} gl={{ antialias: true, preserveDrawingBuffer: true, toneMapping: THREE.NeutralToneMapping }}>
              <MiniScene state={st} bytes={bytes[i] ?? new Uint8Array()} />
            </Canvas>
            <div className="compare-metrics">
              <span>
                Detección <b>{det != null ? `día ${fmt(det, 1)}` : 'pendiente'}</b>
              </span>
              <span>
                Camas infectadas al detectar <b>{m.beds_infected_at_detection ?? '–'}</b>
              </span>
              <span>
                Infectadas <b>{fmt(m.infected ?? 0)}</b>
              </span>
              <span>
                Sin revisar por espacio <b>{fmt(st.kpis?.plants_skipped ?? 0)}</b>
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
