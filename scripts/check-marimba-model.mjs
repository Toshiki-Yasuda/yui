// Usage: node scripts/check-marimba-model.mjs /tmp/yui-3d/tools
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(path.resolve(process.argv[2] || '/tmp/yui-3d/tools'), 'package.json'));
const { NodeIO } = await import(require.resolve('@gltf-transform/core'));
const { ALL_EXTENSIONS } = await import(require.resolve('@gltf-transform/extensions'));
const draco = require('draco3dgltf');
const validator = require('gltf-validator');
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
    'draco3d.decoder': await draco.createDecoderModule()
});
const modelPath = path.join(root, 'models/marimba.glb');
const bytes = fs.readFileSync(modelPath);
const document = await io.read(modelPath);
const primitives = document.getRoot().listMeshes().flatMap(m => m.listPrimitives());
const triangles = primitives.reduce((n, p) => n + p.getIndices().getCount() / 3, 0);
if (triangles > 200000 || primitives.length > 6 || bytes.length > 2000000) throw new Error('Web model exceeds the agreed geometry/transfer budget');
for (const p of primitives) {
    const positions = p.getAttribute('POSITION').getArray();
    if (!positions.every(Number.isFinite)) throw new Error('Invalid decoded vertex');
    if (Math.max(...p.getAttribute('POSITION').getMax([])) > 5) throw new Error('Unexpected model scale');
}
// Validate the DECODED geometry too, as glTF Validator does not inspect Draco bitstreams.
for (const ext of document.getRoot().listExtensionsUsed()) {
    if (ext.extensionName === 'KHR_draco_mesh_compression') ext.dispose();
}
const decoded = await io.writeBinary(document);
const result = await validator.validateBytes(decoded, { uri: 'marimba-decoded.glb' });
if (result.issues.numErrors || result.issues.numWarnings) throw new Error(JSON.stringify(result.issues));
const report = {
    bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
    triangles, primitives: primitives.length,
    textures: document.getRoot().listTextures().map(t => ({name: t.getName(), dimensions: t.getSize(), bytes: t.getImage().byteLength})),
    validation: {errors: result.issues.numErrors, warnings: result.issues.numWarnings}
};
fs.mkdirSync(path.join(root, 'models'), {recursive:true});
fs.writeFileSync(path.join(root, 'models/marimba-report.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
