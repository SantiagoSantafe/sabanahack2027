import { useMemo } from 'react';
import * as THREE from 'three';

/** Saturated gradient sky (the physical Sky shader washes out to white at the horizon). */
export function SkyDome({ top = '#2F7FDB', horizon = '#93D0F7', bottom = '#C9E9FB' }: { top?: string; horizon?: string; bottom?: string }) {
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        fog: false,
        uniforms: {
          top: { value: new THREE.Color(top) },
          horizon: { value: new THREE.Color(horizon) },
          bottom: { value: new THREE.Color(bottom) },
        },
        vertexShader: /* glsl */ `
          varying vec3 vDir;
          void main() {
            vDir = normalize(position);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }`,
        fragmentShader: /* glsl */ `
          uniform vec3 top; uniform vec3 horizon; uniform vec3 bottom;
          varying vec3 vDir;
          void main() {
            float h = vDir.y;
            vec3 c = h > 0.0 ? mix(horizon, top, pow(smoothstep(0.0, 0.6, h), 0.55)) : mix(horizon, bottom, smoothstep(0.0, -0.2, h));
            gl_FragColor = vec4(c, 1.0);
            #include <colorspace_fragment>
          }`,
      }),
    [top, horizon, bottom],
  );
  return (
    <mesh material={mat} renderOrder={-10} frustumCulled={false} raycast={() => null}>
      <sphereGeometry args={[300, 32, 16]} />
    </mesh>
  );
}
