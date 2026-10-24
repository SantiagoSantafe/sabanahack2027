import { Stats } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import type { CSSProperties } from 'react';
import * as THREE from 'three';
import { useStore } from '../state/store';
import { palette } from '../theme/palette';
import { RobotView } from '../robot/RobotView';
import { RutaReal } from './RutaReal';
import { Cameras } from './Cameras';
import { Crop } from './Crop';
import { fieldGeom } from './geometry';
import { detailFor } from './plantModel';
import { SkyDome } from './SkyDome';
import { ArucoMarkers, Dock, DripLines, FarmSign, Ground, RiskHeatmap, SensorStations } from './Terrain';
import { Tunnel } from './Tunnel';
import { FogController, Rain } from './WeatherFX';

function SceneBody() {
  const state = useStore((s) => s.state);
  const heights = useStore((s) => s.heights);
  const spreadL = useStore((s) => s.spreadL);
  const spreadR = useStore((s) => s.spreadR);
  const plantBytes = useStore((s) => s.plantBytes);
  const godMode = useStore((s) => s.godMode);
  const g = fieldGeom(state);
  const showStats = new URLSearchParams(window.location.search).has('fps');
  const cx = (g.x0 + g.x1) / 2;

  return (
    <>
      <color attach="background" args={[palette.sky]} />
      <SkyDome />
      <hemisphereLight args={['#D7ECFF', '#6B8F3A', 0.95]} />
      <ambientLight intensity={0.25} />
      <directionalLight
        castShadow
        position={[cx + 30, 40, -25]}
        intensity={2.2}
        color="#FFF3DA"
        shadow-mapSize={[2048, 2048]}
        shadow-bias={-0.0004}
        shadow-normalBias={0.03}
        shadow-camera-far={140}
        shadow-camera-left={-50}
        shadow-camera-right={50}
        shadow-camera-top={50}
        shadow-camera-bottom={-50}
      />
      <FogController />
      <Cameras g={g} />
      <Ground g={g} />
      <DripLines g={g} />
      <RiskHeatmap g={g} />
      <Crop g={g} heights={heights} spreadL={spreadL} spreadR={spreadR} plantBytes={plantBytes} godMode={godMode} detail={detailFor(g.nBeds * g.nPlants)} />
      <ArucoMarkers g={g} />
      <FarmSign g={g} />
      <Dock g={g} />
      <SensorStations g={g} />
      <Tunnel g={g} />
      <Rain />
      <RobotView g={g} heights={heights} />
      <RutaReal />
      {showStats && <Stats />}
    </>
  );
}

export function FieldCanvas() {
  const recordMode = useStore((s) => s.recordMode);
  const style: CSSProperties = recordMode
    ? { width: 1920, height: 1080, maxWidth: '100vw', maxHeight: '100vh', aspectRatio: '16/9', margin: '0 auto' }
    : { width: '100%', height: '100%' };
  return (
    <div style={style} className="canvas-wrap">
      <Canvas
        shadows="soft"
        dpr={[1, 1.75]}
        gl={{ antialias: true, preserveDrawingBuffer: true, toneMapping: THREE.NeutralToneMapping, toneMappingExposure: 1.05 }}
      >
        <SceneBody />
      </Canvas>
    </div>
  );
}
