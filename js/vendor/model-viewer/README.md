# Vendored model-viewer

- `model-viewer-4.3.1.min.js`: official `@google/model-viewer@4.3.1` npm distribution; Apache-2.0 (`LICENSE`).
- Three.js bundled dependency: `three@0.183.2`, MIT (`THREE-LICENSE`).
- Lit bundled dependency: BSD-3-Clause (`LIT-LICENSE`); inline notices retained.
- `draco/`: decoder files from `three@0.183.2/examples/jsm/libs/draco/gltf/`, Apache-2.0 (`draco/LICENSE`).

Standalone ES module and local decoder; no runtime CDN is required. Loaded only after the visitor activates 3D. See `docs/marimba-3d.md` for integration and rebuild instructions.
