import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { palette } from '../theme/palette';
import { mulberry32, plantWorldPos, type FieldGeom } from './geometry';

export type Detail = 'high' | 'mid' | 'min';

/** Level of detail so a full 80 m block (1 000+ plants) stays fluid; compact views use the lightest. */
export function detailFor(plants: number, compact = false): Detail {
  if (compact) return 'min';
  return plants > 800 ? 'mid' : 'high';
}

const NOMINAL_HALF_WIDTH = 0.45;

/** One elliptical, pointed blueberry leaf, ~1 unit long along +Z, slightly cupped. */
function leafGeometry(): THREE.BufferGeometry {
  const segs = 3;
  const positions: number[] = [];
  const colors: number[] = [];
  const outline = (t: number) => Math.sin(Math.PI * Math.pow(t, 0.85)) * 0.24;
  const lift = (t: number) => 0.12 * t * t;
  const push = (x: number, y: number, z: number, shade: number) => {
    positions.push(x, y, z);
    colors.push(shade, shade, shade);
  };
  for (let s = 0; s < segs; s++) {
    const t0 = s / segs;
    const t1 = (s + 1) / segs;
    const w0 = outline(t0);
    const w1 = outline(t1);
    const sh0 = 0.72 + 0.28 * t0;
    const sh1 = 0.72 + 0.28 * t1;
    for (const side of [-1, 1]) {
      const cup = 0.05;
      push(0, lift(t0), t0, sh0);
      push(side * w0, lift(t0) + cup * w0, t0, sh0 * 0.92);
      push(side * w1, lift(t1) + cup * w1, t1, sh1 * 0.92);
      push(0, lift(t0), t0, sh0);
      push(side * w1, lift(t1) + cup * w1, t1, sh1 * 0.92);
      push(0, lift(t1), t1, sh1);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  g.computeVertexNormals();
  return g;
}

/** A clump of leaves radiating from a center — unit radius. */
export function leafClumpGeometry(leaves = 16, seed = 7): THREE.BufferGeometry {
  const rand = mulberry32(seed);
  const base = leafGeometry();
  const parts: THREE.BufferGeometry[] = [];
  const o = new THREE.Object3D();
  for (let i = 0; i < leaves; i++) {
    const u = rand() * 2 - 1;
    const phi = rand() * Math.PI * 2;
    const r = Math.sqrt(1 - u * u);
    const dir = new THREE.Vector3(r * Math.cos(phi), u * 0.75 + 0.2, r * Math.sin(phi)).normalize();
    const len = 0.55 + rand() * 0.35;
    o.position.copy(dir.clone().multiplyScalar(0.25 + rand() * 0.25));
    o.lookAt(o.position.clone().add(dir));
    o.rotateZ(rand() * Math.PI * 2);
    o.rotateX(-0.25 - rand() * 0.35);
    o.scale.setScalar(len);
    o.updateMatrix();
    parts.push(base.clone().applyMatrix4(o.matrix));
  }
  const merged = mergeGeometries(parts, false)!;
  merged.computeBoundingSphere();
  return merged;
}

/** Blueberry: slightly flattened sphere with the characteristic five-point crown. */
export function berryGeometry(detail: Detail = 'high'): THREE.BufferGeometry {
  const hi = detail === 'high';
  const body = new THREE.SphereGeometry(1, hi ? 10 : 6, hi ? 8 : 5);
  body.scale(1, 0.86, 1);
  const crown = new THREE.CylinderGeometry(0.42, 0.28, 0.22, 5, 1, true);
  crown.translate(0, 0.86, 0);
  const color = (geo: THREE.BufferGeometry, v: number) => {
    const n = geo.getAttribute('position').count;
    geo.setAttribute('color', new THREE.Float32BufferAttribute(new Array(n * 3).fill(v), 3));
    return geo.toNonIndexed();
  };
  const merged = mergeGeometries([color(body, 1), color(crown, 0.35)], false)!;
  merged.computeVertexNormals();
  return merged;
}

export function stemGeometry(): THREE.BufferGeometry {
  const g = new THREE.CylinderGeometry(0.6, 1, 1, 5, 1, false);
  g.translate(0, 0.5, 0);
  return g;
}

/** Plastic nursery pot, unit height. */
export function potGeometry(): THREE.BufferGeometry {
  const g = new THREE.CylinderGeometry(0.5, 0.4, 1, 16, 1, false);
  g.translate(0, 0.5, 0);
  return g;
}

export type InstanceSpec = {
  matrices: Float32Array;
  plant: Uint16Array;
  baseColor: Float32Array;
  count: number;
};

export type BushLayout = {
  stems: InstanceSpec;
  clumps: InstanceSpec;
  berries: InstanceSpec;
  crowns: Float32Array; // per-plant foliage center [x,y,z,radius]
};

class SpecBuilder {
  m: number[] = [];
  p: number[] = [];
  c: number[] = [];
  add(mat: THREE.Matrix4, plant: number, color: THREE.Color) {
    for (let k = 0; k < 16; k++) this.m.push(mat.elements[k]);
    this.p.push(plant);
    this.c.push(color.r, color.g, color.b);
  }
  build(): InstanceSpec {
    return {
      matrices: new Float32Array(this.m),
      plant: new Uint16Array(this.p),
      baseColor: new Float32Array(this.c),
      count: this.p.length,
    };
  }
}

const _o = new THREE.Object3D();
const _c = new THREE.Color();
const _up = new THREE.Vector3(0, 1, 0);
const _newGrowth = new THREE.Color(palette.leafNewGrowth);

const PRESET: Record<Detail, { stems: number; perStem: number; fill: number; clusters: number; perCluster: number }> = {
  high: { stems: 5, perStem: 3, fill: 4, clusters: 5, perCluster: 5 },
  mid: { stems: 4, perStem: 2, fill: 2, clusters: 3, perCluster: 4 },
  min: { stems: 3, perStem: 1, fill: 1, clusters: 0, perCluster: 0 },
};

/** Deterministic multi-stem bush layout; overflowing plants get an arching branch into the aisle. */
export function buildBushLayout(
  g: FieldGeom,
  heights: number[],
  spreadL: number[] | null,
  spreadR: number[] | null,
  detail: Detail,
): BushLayout {
  const stems = new SpecBuilder();
  const clumps = new SpecBuilder();
  const berries = new SpecBuilder();
  const n = g.nBeds * g.nPlants;
  const crowns = new Float32Array(n * 4);
  const pre = PRESET[detail];

  for (let i = 0; i < n; i++) {
    const rand = mulberry32(i * 7919 + 17);
    const bed = Math.floor(i / g.nPlants);
    const plant = i % g.nPlants;
    const [bx, by, bz] = plantWorldPos(g, bed, plant);
    const h = heights[i] ?? 1.5;
    const sl = spreadL?.[i] ?? NOMINAL_HALF_WIDTH;
    const sr = spreadR?.[i] ?? NOMINAL_HALF_WIDTH;
    const kx = (dx: number) => (dx < 0 ? sl : sr) / NOMINAL_HALF_WIDTH;
    const tips: { pos: THREE.Vector3; dir: THREE.Vector3; len: number; spill: boolean }[] = [];

    const nStems = pre.stems + (detail === 'high' ? Math.floor(rand() * 2) : 0);
    for (let s = 0; s < nStems; s++) {
      const az = (s / nStems) * Math.PI * 2 + rand() * 0.8;
      const tilt = 0.14 + rand() * 0.26;
      tips.push({
        pos: new THREE.Vector3(bx + (rand() - 0.5) * 0.08, by, bz + (rand() - 0.5) * 0.08),
        dir: new THREE.Vector3(Math.sin(tilt) * Math.cos(az), Math.cos(tilt), Math.sin(tilt) * Math.sin(az)),
        len: h * (0.7 + rand() * 0.25),
        spill: false,
      });
    }
    for (const [side, spread] of [
      [-1, sl],
      [1, sr],
    ] as const) {
      if (spread < NOMINAL_HALF_WIDTH + 0.15) continue;
      const tilt = 0.75 + rand() * 0.25;
      tips.push({
        pos: new THREE.Vector3(bx + side * 0.05, by, bz + (rand() - 0.5) * 0.1),
        dir: new THREE.Vector3(side * Math.sin(tilt), Math.cos(tilt), (rand() - 0.5) * 0.3).normalize(),
        len: Math.min(h * 0.95, spread / Math.sin(tilt) + 0.1),
        spill: true,
      });
    }

    const clumpPositions: { p: THREE.Vector3; s: number; f: number }[] = [];
    const sz = Math.sqrt(h / 1.5);
    for (const st of tips) {
      _o.position.copy(st.pos);
      _o.quaternion.setFromUnitVectors(_up, st.dir);
      const rad = 0.013 + rand() * 0.009;
      _o.scale.set(rad, st.len, rad);
      _o.updateMatrix();
      _c.set(palette.stem).offsetHSL(0, 0, (rand() - 0.5) * 0.08);
      stems.add(_o.matrix, i, _c);
      const per = st.spill ? Math.max(pre.perStem, 2) : pre.perStem;
      for (let k = 0; k < per; k++) {
        const f = st.spill ? 0.55 + (k / per) * 0.45 : 0.4 + (k / per) * 0.52 + rand() * 0.08;
        const p = st.pos.clone().addScaledVector(st.dir, st.len * f);
        if (!st.spill) p.x = bx + (p.x - bx) * kx(p.x - bx);
        p.x += (rand() - 0.5) * 0.08;
        p.z += (rand() - 0.5) * 0.08;
        clumpPositions.push({ p, s: (0.2 + rand() * 0.1) * sz * (1.1 - 0.25 * f), f });
      }
    }
    for (let k = 0; k < pre.fill; k++) {
      const a = rand() * Math.PI * 2;
      const r = 0.12 + rand() * 0.16;
      const p = new THREE.Vector3(bx + Math.cos(a) * r * kx(Math.cos(a)), by + h * (0.42 + rand() * 0.4), bz + Math.sin(a) * r);
      clumpPositions.push({ p, s: (0.24 + rand() * 0.06) * sz * (detail === 'min' ? 1.35 : 1), f: 0.6 });
    }

    let cy = 0;
    for (const c of clumpPositions) {
      _o.position.copy(c.p);
      _o.rotation.set(rand() * 0.6, rand() * Math.PI * 2, rand() * 0.6);
      _o.scale.setScalar(c.s);
      _o.updateMatrix();
      const pal = palette.leafHealthy;
      _c.set(pal[Math.floor(rand() * pal.length)]);
      if (c.f > 0.9) _c.lerp(_newGrowth, 0.35);
      _c.offsetHSL((rand() - 0.5) * 0.02, 0, (rand() - 0.5) * 0.05);
      clumps.add(_o.matrix, i, _c);
      cy += c.p.y;
    }
    crowns[i * 4] = bx;
    crowns[i * 4 + 1] = cy / Math.max(clumpPositions.length, 1);
    crowns[i * 4 + 2] = bz;
    crowns[i * 4 + 3] = Math.max(sl, sr);

    const mids = clumpPositions.filter((c) => c.f > 0.45 && c.f < 0.92);
    for (let k = 0; k < pre.clusters && mids.length; k++) {
      const host = mids[Math.floor(rand() * mids.length)];
      const out = new THREE.Vector3(host.p.x - bx, 0, host.p.z - bz);
      if (out.lengthSq() < 1e-4) out.set(rand() - 0.5, 0, rand() - 0.5);
      out.normalize();
      const center = host.p.clone().addScaledVector(out, host.s * 0.75);
      center.y -= host.s * 0.35;
      const ripe = rand() < 0.78;
      for (let b = 0; b < pre.perCluster; b++) {
        _o.position.set(center.x + (rand() - 0.5) * 0.07, center.y - rand() * 0.06, center.z + (rand() - 0.5) * 0.07);
        _o.rotation.set(rand() * Math.PI, rand() * Math.PI * 2, 0);
        _o.scale.setScalar(0.022 + rand() * 0.008);
        _o.updateMatrix();
        const pal = ripe || rand() < 0.4 ? palette.berryRipe : palette.berryUnripe;
        _c.set(pal[Math.floor(rand() * pal.length)]);
        berries.add(_o.matrix, i, _c);
      }
    }
  }
  return { stems: stems.build(), clumps: clumps.build(), berries: berries.build(), crowns };
}
