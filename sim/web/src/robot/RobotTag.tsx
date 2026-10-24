import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import * as THREE from 'three';
import { useStore } from '../state/store';
import { fmt } from '../ui/format';
import { PLATFORM_NAME, STATE_LABEL } from './labels';

/** Screen position of the robot label, written every frame by the anchor inside the canvas. */
const tagScreen = { x: 0, y: 0, visible: false };

const _v = new THREE.Vector3();

/** Lives inside the robot group; projects its world position to screen space each frame. */
export function RobotTagAnchor({ height }: { height: number }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(({ camera, size }) => {
    const o = ref.current;
    if (!o) return;
    o.getWorldPosition(_v);
    _v.project(camera);
    tagScreen.visible = _v.z < 1 && Math.abs(_v.x) < 1.2 && Math.abs(_v.y) < 1.2;
    tagScreen.x = ((_v.x + 1) / 2) * size.width;
    tagScreen.y = ((1 - _v.y) / 2) * size.height;
    const el = document.getElementById('robot-tag');
    if (el) {
      el.style.transform = `translate3d(${tagScreen.x}px, ${tagScreen.y}px, 0) translate(-50%, -100%)`;
      el.style.opacity = tagScreen.visible ? '1' : '0';
    }
    // Camera thumbnail: same anchor, stacked above the tag (CSS adds the vertical offset).
    const cam = document.getElementById('robot-cam');
    if (cam) {
      cam.style.transform = `translate3d(${tagScreen.x}px, ${tagScreen.y}px, 0) translate(-50%, -100%)`;
      cam.style.opacity = tagScreen.visible ? '1' : '0';
      cam.style.pointerEvents = tagScreen.visible ? 'auto' : 'none';
    }
  });
  return <group ref={ref} position={[0, height, 0]} />;
}

/** DOM label outside the canvas (drei Html roots were dropping this frequently updated label). */
export function RobotTag() {
  const robot = useStore((s) => s.state?.robot);
  const mode = useStore((s) => s.mode);
  const recordMode = useStore((s) => s.recordMode);
  const probe = robot?.sensors?.probe;
  if (!robot?.active || mode === 'compare' || recordMode) return null;
  const warn = robot.state === 'failed' || robot.state === 'stuck';
  return (
    <div id="robot-tag" className={`robot-tag ${warn ? 'is-warn' : ''}`} aria-hidden>
      <strong>{PLATFORM_NAME[robot.platform] ?? robot.platform}</strong>
      <span>{STATE_LABEL[robot.state] ?? robot.state}</span>
      {probe && ['walking', 'inspecting', 'manual'].includes(robot.state) && (
        <small>
          {fmt(probe.temp_c, 1)} °C, {fmt(probe.rh_pct, 0)} % HR
        </small>
      )}
      <i style={{ width: `${Math.round(robot.battery * 100)}%` }} />
    </div>
  );
}
