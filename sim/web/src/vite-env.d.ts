/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WS_URL?: string;
  /** Base URL of the camera panel (panel_demo.py), default http://localhost:8092 */
  readonly VITE_PANEL_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'urdf-loader' {
  import type { LoadingManager, Object3D } from 'three';

  export default class URDFLoader {
    constructor(manager?: LoadingManager);
    workingPath: string;
    packages: string | Record<string, string> | ((targetPkg: string) => string);
    loadMeshCb: (
      path: string,
      manager: LoadingManager,
      material: unknown,
      done: (mesh: Object3D | null, err?: unknown) => void,
    ) => void;
    load(
      url: string,
      onLoad: (robot: Object3D) => void,
      onProgress?: (ev: ProgressEvent) => void,
      onError?: (err: unknown) => void,
    ): void;
  }
}
