import { useFrame } from '@react-three/fiber';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { isSick, palette, stateRing, stateTint } from '../theme/palette';
import type { FieldGeom } from './geometry';
import {
  berryGeometry,
  buildBushLayout,
  leafClumpGeometry,
  potGeometry,
  stemGeometry,
  type Detail,
  type InstanceSpec,
} from './plantModel';

type Props = {
  g: FieldGeom;
  heights: number[] | null;
  spreadL: number[] | null;
  spreadR: number[] | null;
  plantBytes: Uint8Array | null;
  godMode: boolean;
  detail: Detail;
  shadows?: boolean;
};

const _m = new THREE.Matrix4();
const _c = new THREE.Color();
const _tint = new THREE.Color();

function applyMatrices(mesh: THREE.InstancedMesh | null, spec: InstanceSpec) {
  if (!mesh) return;
  for (let k = 0; k < spec.count; k++) {
    _m.fromArray(spec.matrices, k * 16);
    mesh.setMatrixAt(k, _m);
  }
  mesh.count = spec.count;
  mesh.instanceMatrix.needsUpdate = true;
  mesh.computeBoundingSphere();
}

/** Optional: drop a CC-BY blueberry GLB at web/public/models/blueberry.glb to replace the procedural berry. */
function useBerryGeometry(detail: Detail): THREE.BufferGeometry {
  const procedural = useMemo(() => berryGeometry(detail), [detail]);
  const [glb, setGlb] = useState<THREE.BufferGeometry | null>(null);
  useEffect(() => {
    let alive = true;
    fetch('/models/blueberry.glb', { method: 'HEAD' })
      .then((r) => {
        if (!r.ok || !(r.headers.get('content-type') ?? '').includes('model')) return;
        new GLTFLoader().load('/models/blueberry.glb', (gltf) => {
          let found: THREE.BufferGeometry | null = null;
          gltf.scene.traverse((o) => {
            const mesh = o as THREE.Mesh;
            if (!found && mesh.isMesh) found = mesh.geometry.clone();
          });
          if (!found || !alive) return;
          const g = found as THREE.BufferGeometry;
          g.computeBoundingSphere();
          const s = g.boundingSphere!;
          g.translate(-s.center.x, -s.center.y, -s.center.z);
          g.scale(1 / s.radius, 1 / s.radius, 1 / s.radius);
          if (!g.getAttribute('color')) {
            const n = g.getAttribute('position').count;
            g.setAttribute('color', new THREE.Float32BufferAttribute(new Array(n * 3).fill(1), 3));
          }
          setGlb(g);
        });
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);
  return glb ?? procedural;
}

export function Crop({ g, heights, spreadL, spreadR, plantBytes, godMode, detail, shadows = true }: Props) {
  const stemRef = useRef<THREE.InstancedMesh>(null);
  const clumpRef = useRef<THREE.InstancedMesh>(null);
  const berryRef = useRef<THREE.InstancedMesh>(null);
  const ringRef = useRef<THREE.InstancedMesh>(null);
  const pinRef = useRef<THREE.InstancedMesh>(null);
  const alertIdx = useRef<{ k: number; x: number; y: number; z: number }[]>([]);

  const n = g.nBeds * g.nPlants;
  const leafGeo = useMemo(() => leafClumpGeometry(detail === 'high' ? 15 : 11), [detail]);
  const potGeo = useMemo(() => potGeometry(), []);
  const potRef = useRef<THREE.InstancedMesh>(null);
  const stemGeo = useMemo(() => stemGeometry(), []);
  const berryGeo = useBerryGeometry(detail);
  const ringGeo = useMemo(() => {
    const t = new THREE.TorusGeometry(0.42, 0.035, 6, 28);
    t.rotateX(-Math.PI / 2);
    return t;
  }, []);
  const pinGeo = useMemo(() => {
    const cone = new THREE.ConeGeometry(0.07, 0.22, 10);
    cone.rotateX(Math.PI);
    const head = new THREE.SphereGeometry(0.09, 12, 10);
    head.translate(0, 0.17, 0);
    return mergePin(cone, head);
  }, []);

  const layout = useMemo(
    () => (heights ? buildBushLayout(g, heights, spreadL, spreadR, detail) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [heights, spreadL, spreadR, detail, g.nBeds, g.nPlants, g.spacing, g.bedH, g.bed_x[0]],
  );

  useLayoutEffect(() => {
    if (!layout) return;
    applyMatrices(stemRef.current, layout.stems);
    applyMatrices(clumpRef.current, layout.clumps);
    applyMatrices(berryRef.current, layout.berries);
    const pots = potRef.current;
    if (pots) {
      const m = new THREE.Matrix4();
      const r = g.potD;
      for (let i = 0; i < n; i++) {
        m.makeScale(r, g.bedH, r).setPosition(layout.crowns[i * 4], 0.02, layout.crowns[i * 4 + 2]);
        pots.setMatrixAt(i, m);
      }
      pots.instanceMatrix.needsUpdate = true;
    }
  }, [layout, g.potD, g.bedH, n]);

  useEffect(() => {
    if (!layout || !plantBytes) return;
    const clump = clumpRef.current;
    const berry = berryRef.current;
    if (clump) {
      const spec = layout.clumps;
      for (let k = 0; k < spec.count; k++) {
        const st = plantBytes[spec.plant[k]] ?? 0;
        _c.fromArray(spec.baseColor, k * 3);
        const tint = stateTint(st, godMode);
        if (tint) {
          const spotty = (k * 2654435761) % 7 < 2;
          _c.lerp(_tint.set(tint.color), spotty ? tint.mix * 0.55 : tint.mix);
        }
        clump.setColorAt(k, _c);
      }
      if (clump.instanceColor) clump.instanceColor.needsUpdate = true;
    }
    if (berry) {
      const spec = layout.berries;
      for (let k = 0; k < spec.count; k++) {
        const st = plantBytes[spec.plant[k]] ?? 0;
        if (isSick(st)) _c.set(palette.berrySick);
        else _c.fromArray(spec.baseColor, k * 3);
        berry.setColorAt(k, _c);
      }
      if (berry.instanceColor) berry.instanceColor.needsUpdate = true;
    }
    const stem = stemRef.current;
    if (stem) {
      const spec = layout.stems;
      for (let k = 0; k < spec.count; k++) {
        _c.fromArray(spec.baseColor, k * 3);
        stem.setColorAt(k, _c);
      }
      if (stem.instanceColor) stem.instanceColor.needsUpdate = true;
    }

    const ring = ringRef.current;
    const pin = pinRef.current;
    if (ring && pin) {
      let ri = 0;
      let pi = 0;
      const alerts: { k: number; x: number; y: number; z: number }[] = [];
      for (let i = 0; i < n; i++) {
        const st = plantBytes[i] ?? 0;
        const color = stateRing(st);
        const cx = layout.crowns[i * 4];
        const cz = layout.crowns[i * 4 + 2];
        const top = (heights?.[i] ?? 1.4) + g.bedH;
        if (color) {
          _m.makeTranslation(cx, g.bedH + 0.04, cz);
          ring.setMatrixAt(ri, _m);
          ring.setColorAt(ri, _c.set(color));
          ri++;
        }
        if (st === 4 || st === 5) {
          _m.makeTranslation(cx, top + 0.25, cz);
          pin.setMatrixAt(pi, _m);
          pin.setColorAt(pi, _c.set(st === 4 ? palette.alertRing : palette.leafConfirmed));
          if (st === 4) alerts.push({ k: pi, x: cx, y: top + 0.25, z: cz });
          pi++;
        }
      }
      ring.count = ri;
      pin.count = pi;
      ring.instanceMatrix.needsUpdate = true;
      pin.instanceMatrix.needsUpdate = true;
      if (ring.instanceColor) ring.instanceColor.needsUpdate = true;
      if (pin.instanceColor) pin.instanceColor.needsUpdate = true;
      alertIdx.current = alerts;
    }
  }, [layout, plantBytes, godMode, heights, g.bedH, n]);

  useFrame(({ clock }) => {
    const pin = pinRef.current;
    if (!pin || alertIdx.current.length === 0) return;
    const t = clock.elapsedTime;
    const s = 1 + 0.18 * Math.sin(t * 6);
    for (const a of alertIdx.current) {
      _m.makeScale(s, s, s);
      _m.setPosition(a.x, a.y + Math.sin(t * 4) * 0.06, a.z);
      pin.setMatrixAt(a.k, _m);
    }
    pin.instanceMatrix.needsUpdate = true;
  });

  const counts = layout
    ? { s: layout.stems.count, c: layout.clumps.count, b: layout.berries.count }
    : { s: 1, c: 1, b: 1 };
  counts.b = Math.max(counts.b, 1);

  return (
    <group>
      <instancedMesh
        key={`s${counts.s}`}
        ref={stemRef}
        args={[stemGeo, undefined, counts.s]}
        castShadow={shadows}
        frustumCulled={false}
      >
        <meshStandardMaterial roughness={0.85} />
      </instancedMesh>
      <instancedMesh
        key={`c${counts.c}-${detail}`}
        ref={clumpRef}
        args={[leafGeo, undefined, counts.c]}
        castShadow={shadows}
        receiveShadow
        frustumCulled={false}
      >
        <meshStandardMaterial vertexColors side={THREE.DoubleSide} roughness={0.55} metalness={0.02} />
      </instancedMesh>
      <instancedMesh
        key={`b${counts.b}-${berryGeo.uuid}`}
        ref={berryRef}
        args={[berryGeo, undefined, counts.b]}
        frustumCulled={false}
      >
        <meshPhysicalMaterial vertexColors roughness={0.38} clearcoat={0.35} clearcoatRoughness={0.6} sheen={0.6} sheenColor="#C9D4FF" />
      </instancedMesh>
      <instancedMesh ref={potRef} args={[potGeo, undefined, n]} castShadow={shadows} receiveShadow frustumCulled={false}>
        <meshStandardMaterial color={palette.pot} roughness={0.75} />
      </instancedMesh>
      <instancedMesh ref={ringRef} args={[ringGeo, undefined, n]} frustumCulled={false}>
        <meshBasicMaterial toneMapped={false} />
      </instancedMesh>
      <instancedMesh ref={pinRef} args={[pinGeo, undefined, n]} frustumCulled={false}>
        <meshStandardMaterial emissive="#FF3B2E" emissiveIntensity={0.35} roughness={0.4} />
      </instancedMesh>
    </group>
  );
}

function mergePin(a: THREE.BufferGeometry, b: THREE.BufferGeometry): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry();
  const pa = a.toNonIndexed();
  const pb = b.toNonIndexed();
  const pos = new Float32Array([...pa.getAttribute('position').array, ...pb.getAttribute('position').array]);
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.computeVertexNormals();
  return g;
}
