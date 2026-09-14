#!/usr/bin/env python3
"""Blender background export. Open the source with --disable-autoexec; never save it.
Intermediate outputs go to /tmp/yui-3d; see docs/marimba-3d.md for the full build.
"""
import bpy, math, json, hashlib
from pathlib import Path
from collections import defaultdict

ROOT=Path(__file__).resolve().parent.parent
WORK=Path('/tmp/yui-3d'); WORK.mkdir(exist_ok=True)
SOURCE=Path(bpy.data.filepath)
source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
scene=bpy.context.scene
source_objects=[o for o in scene.objects if o.type in {'MESH','CURVE','FONT'} and not o.hide_render]
bars=[o for o in source_objects if o.name.startswith('Bar ')]
assert len(bars)==68, f'Expected 68 bars, got {len(bars)}'
report={'source':SOURCE.name,'source_sha256':source_hash,'blender':bpy.app.version_string,'bars':len(bars),'source_objects':len(source_objects)}
dg=bpy.context.evaluated_depsgraph_get()
source_triangles=0
for o in source_objects:
    e=o.evaluated_get(dg); mesh=e.to_mesh(); mesh.calc_loop_triangles(); source_triangles+=len(mesh.loop_triangles); e.to_mesh_clear()
report['source_triangles']=source_triangles
# Parent assemblies carry the plaque transforms. Preserve world-space placement
# before stripping empties, otherwise labels end up floating at the origin.
for o in source_objects:
    world=o.matrix_world.copy()
    o.parent=None
    o.matrix_world=world
for o in list(scene.objects):
    if o not in source_objects: bpy.data.objects.remove(o,do_unlink=True)

wood=[]
for o in source_objects:
    iswood=any(m and ('rosewood' in m.name or 'oak' in m.name) for m in o.data.materials)
    if iswood: wood.append(o)
    # Preserve profiles and mechanism parts; lower the edge tessellation first.
    for m in o.modifiers:
        if m.type=='BEVEL': m.segments=2 if iswood else 1
    if o.type=='CURVE': o.data.resolution_u=min(o.data.resolution_u,4); o.data.bevel_resolution=1
    if o.type=='FONT': o.data.resolution_u=2
bpy.ops.object.select_all(action='DESELECT')
for o in source_objects:o.select_set(True)
bpy.context.view_layer.objects.active=source_objects[0]
bpy.ops.object.convert(target='MESH')
source_objects=list(bpy.context.selected_objects)
wood=[o for o in source_objects if any(m and ('rosewood' in m.name or 'oak' in m.name) for m in o.data.materials)]
for i,o in enumerate(source_objects):
    if o in wood:continue
    o.data.calc_loop_triangles()
    if len(o.data.loop_triangles)>300:
        bpy.context.view_layer.objects.active=o
        dec=o.modifiers.new('Web detail reduction','DECIMATE');dec.ratio=.28
        bpy.ops.object.modifier_apply(modifier=dec.name)
print('GEOMETRY reduced; wood objects',len(wood),flush=True)

# Separate UV islands per original wood object preserve Generated coordinates and grain variation.
# Bake BEFORE joining: Object Info randomness and Generated bounds belong to the original part.
grid=math.ceil(math.sqrt(len(wood)))
for i,o in enumerate(sorted(wood,key=lambda o:o.name)):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(70),island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')
    for loop in o.data.uv_layers.active.data:
        loop.uv.x=(loop.uv.x*.94+.03+i%grid)/grid
        loop.uv.y=(loop.uv.y*.94+.03+i//grid)/grid

scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.render.bake.use_clear=False;scene.render.bake.margin=8
wood_materials=set(m for o in wood for m in o.data.materials if m)
# Emission-only bake copies the shader colour without studio illumination/shadows.
color=bpy.data.images.new('Wood grain atlas',width=4096,height=4096,alpha=False)
rough=bpy.data.images.new('Wood roughness atlas',width=1024,height=1024,alpha=False);rough.colorspace_settings.name='Non-Color'
original_links={}
for mat in wood_materials:
    nt=mat.node_tree;bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
    output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
    original_links[mat]=(bsdf,output)
    tex=nt.nodes.new('ShaderNodeTexImage');tex.name='Web bake target';tex.image=color;nt.nodes.active=tex
    emit=nt.nodes.new('ShaderNodeEmission');emit.name='Web colour bake'
    inp=bsdf.inputs['Base Color']
    if inp.is_linked:nt.links.new(inp.links[0].from_socket,emit.inputs['Color'])
    else:emit.inputs['Color'].default_value=inp.default_value
    nt.links.new(emit.outputs[0],output.inputs['Surface'])
bpy.ops.object.select_all(action='DESELECT')
for o in wood:o.select_set(True)
bpy.context.view_layer.objects.active=wood[0]
bpy.ops.object.bake(type='EMIT')
color.filepath_raw=str(WORK/'wood-color.png');color.file_format='PNG';color.save()
print('COLOR baked',flush=True)
for mat,(bsdf,output) in original_links.items():
    nt=mat.node_tree;nt.nodes['Web bake target'].image=rough
    emit=nt.nodes['Web colour bake'];inp=bsdf.inputs['Roughness']
    for link in list(emit.inputs['Color'].links):nt.links.remove(link)
    if inp.is_linked:nt.links.new(inp.links[0].from_socket,emit.inputs['Color'])
    else:emit.inputs['Color'].default_value=(*([inp.default_value]*3),1)
bpy.ops.object.bake(type='EMIT')
rough.filepath_raw=str(WORK/'wood-roughness.png');rough.file_format='PNG';rough.save()
print('ROUGHNESS baked',flush=True)
woodmat=bpy.data.materials.new('Baked original rosewood and oak');woodmat.use_nodes=True
nt=woodmat.node_tree;bsdf=nt.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.4
for img,socket in [(color,'Base Color'),(rough,'Roughness')]:
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=img;nt.links.new(tex.outputs['Color'],bsdf.inputs[socket])
for o in wood:o.data.materials.clear();o.data.materials.append(woodmat)
# Only the wood required procedural colour baking. Metal micro-bump is omitted at web scale.
for mat in bpy.data.materials:
    if mat==woodmat or not mat.use_nodes:continue
    for n in mat.node_tree.nodes:
        if n.type=='BSDF_PRINCIPLED':
            for link in list(n.inputs['Normal'].links):mat.node_tree.links.remove(link)

# Merge static components by material, retaining every bar as disconnected geometry.
groups=defaultdict(list)
for o in source_objects:
    groups[tuple(m.name if m else '' for m in o.data.materials)].append(o)
for materials,objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join();objects[0].name='Web '+(' + '.join(materials) or 'unpainted')
bpy.ops.object.select_all(action='SELECT')
objects=[o for o in scene.objects if o.type=='MESH']
triangles=0
for o in objects:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
report.update(web_objects=len(objects),web_triangles=triangles,wood_objects=len(wood),wood_atlas=[4096,4096],roughness_atlas=[1024,1024])
bpy.ops.export_scene.gltf(filepath=str(WORK/'marimba-raw.glb'),export_format='GLB',use_selection=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=False,export_yup=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
(WORK/'export-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('EXPORT_REPORT',json.dumps(report),flush=True)
