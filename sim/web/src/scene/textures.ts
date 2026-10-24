import * as THREE from 'three';
import { mulberry32 } from './geometry';

const cache = new Map<string, THREE.Texture>();

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return [c, c.getContext('2d')!];
}

/** Speckled tileable texture (grass, soil, mulch). */
export function speckleTexture(key: string, base: string, specks: string[], density: number, repeat: [number, number]): THREE.Texture {
  const id = `${key}-${repeat.join('x')}`;
  const hit = cache.get(id);
  if (hit) return hit;
  const [c, ctx] = canvas(256, 256);
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, 256, 256);
  const rand = mulberry32(key.length * 131 + 7);
  for (let i = 0; i < density; i++) {
    ctx.fillStyle = specks[Math.floor(rand() * specks.length)];
    ctx.globalAlpha = 0.35 + rand() * 0.5;
    const x = rand() * 256;
    const y = rand() * 256;
    const w = 1 + rand() * 2.5;
    const h = 2 + rand() * 6;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((rand() - 0.5) * 1.2);
    ctx.fillRect(-w / 2, -h / 2, w, h);
    ctx.restore();
  }
  ctx.globalAlpha = 1;
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(repeat[0], repeat[1]);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  cache.set(id, tex);
  return tex;
}

/** Virtual ArUco-style marker (6x6 cells, black border, id-derived bits). Not a real dictionary entry. */
export function markerTexture(id: number, bedsPerNave = 3): THREE.Texture {
  const key = `aruco-${id}-${bedsPerNave}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const [c, ctx] = canvas(120, 150);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, 120, 150);
  const cell = 16;
  const ox = 12;
  const oy = 8;
  ctx.fillStyle = '#111111';
  ctx.fillRect(ox, oy, cell * 6, cell * 6);
  const rand = mulberry32(id * 977 + 3);
  ctx.fillStyle = '#ffffff';
  for (let r = 0; r < 4; r++) {
    for (let k = 0; k < 4; k++) {
      if (rand() > 0.5) ctx.fillRect(ox + cell * (k + 1), oy + cell * (r + 1), cell, cell);
    }
  }
  ctx.fillStyle = '#1B1F4B';
  ctx.font = '700 26px "Bricolage Grotesque", sans-serif';
  ctx.textAlign = 'center';
  const nave = Math.floor((id - 1) / bedsPerNave) + 1;
  const cama = ((id - 1) % bedsPerNave) + 1;
  ctx.fillText(`N${nave} C${cama}`, 60, 138);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  cache.set(key, tex);
  return tex;
}

/** Wooden farm sign at the block entrance. */
export function signTexture(title: string, subtitle: string): THREE.Texture {
  const key = `sign-${title}-${subtitle}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const [c, ctx] = canvas(1024, 384);
  const grad = ctx.createLinearGradient(0, 0, 0, 384);
  grad.addColorStop(0, '#A86B3B');
  grad.addColorStop(1, '#8A532A');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 1024, 384);
  ctx.strokeStyle = 'rgba(70,35,15,0.35)';
  ctx.lineWidth = 3;
  for (let y = 40; y < 384; y += 64) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    for (let x = 0; x <= 1024; x += 64) ctx.lineTo(x, y + Math.sin(x * 0.02 + y) * 4);
    ctx.stroke();
  }
  const berry = (x: number, y: number, r: number, col: string) => {
    ctx.fillStyle = col;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.35)';
    ctx.beginPath();
    ctx.arc(x - r * 0.35, y - r * 0.35, r * 0.28, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#1B1F4B';
    ctx.beginPath();
    for (let k = 0; k < 5; k++) {
      const a = (k / 5) * Math.PI * 2 - Math.PI / 2;
      ctx.lineTo(x + Math.cos(a) * r * 0.32, y - r * 0.55 + Math.sin(a) * r * 0.2);
    }
    ctx.fill();
  };
  const leaf = (x: number, y: number, rot: number) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rot);
    ctx.fillStyle = '#6FCB45';
    ctx.beginPath();
    ctx.ellipse(0, 0, 38, 16, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  };
  leaf(120, 150, -0.5);
  leaf(150, 210, 0.4);
  berry(110, 205, 34, '#3A55D6');
  berry(160, 250, 30, '#4A62E8');
  berry(80, 265, 28, '#2F45B8');
  leaf(900, 150, 0.5);
  leaf(870, 215, -0.4);
  berry(915, 210, 34, '#3A55D6');
  berry(860, 258, 30, '#5A4BC9');
  berry(945, 268, 26, '#2F45B8');
  ctx.fillStyle = '#FFF4E0';
  ctx.textAlign = 'center';
  ctx.shadowColor = 'rgba(40,20,5,0.6)';
  ctx.shadowOffsetY = 5;
  ctx.font = '800 92px "Bricolage Grotesque", sans-serif';
  ctx.fillText(title, 512, 175);
  ctx.font = '600 54px "Figtree", sans-serif';
  ctx.fillText(subtitle, 512, 270);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  cache.set(key, tex);
  return tex;
}

export function clearTextureCache(prefix: string) {
  for (const k of [...cache.keys()]) if (k.startsWith(prefix)) cache.delete(k);
}
