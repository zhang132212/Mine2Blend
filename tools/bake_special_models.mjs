// Build-time deepslate 0.27.1 special models. Blender runtime needs no Node binary.
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {BlockState,SpecialRenderers,Cull,Identifier} from '../resources/converter/win-x64/node_modules/deepslate/lib/index.js';
import {initEntityModels,listEntityModelIds,createEntityModelMesh} from '../resources/converter/win-x64/src/entity-model.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const registry=JSON.parse(fs.readFileSync(path.join(root,'editor/data/blocks.json'),'utf8'));
const ids=[];
const atlas={getTextureUV(id){const name=id.toString().replace(/^minecraft:/,'');let index=ids.indexOf(name);if(index<0){index=ids.length;ids.push(name);}return [index*2,0,index*2+1,1];},getPixelSize(){return 0;},getTextureAtlas(){return null;}};
const relevant=new Set(['facing','rotation','attached','part','copper_golem_pose']);
function mesh(name,props){
  if(name==='shulker_box')name='purple_shulker_box';
  return SpecialRenderers.getBlockMesh(new BlockState('minecraft:'+name,{...props,waterlogged:'false'}),undefined,atlas,Cull.none());
}
const models={};
for(const [name,[allowed,defaults]] of Object.entries(registry)){
  if(['water','lava','bubble_column'].includes(name))continue;
  if(!mesh(name,defaults).quads.length)continue;
  const keys=Object.keys(allowed).filter(k=>relevant.has(k)).sort();
  let states=[{}];
  for(const key of keys)states=states.flatMap(p=>allowed[key].map(v=>({...p,[key]:v})));
  const variants={};
  for(const props of states){
    variants[keys.map(k=>k+'='+props[k]).join(',')]=mesh(name,{...defaults,...props}).quads.map(q=>{
      const v=q.vertices();const index=Math.floor(v.reduce((s,p)=>s+p.texture[0],0)/v.length/2);
      const texture=name==='shulker_box'?ids[index].replace('shulker_purple','shulker'):ids[index];
      return [v.map(p=>[p.pos.x,p.pos.y,p.pos.z].map(x=>Math.round(x*1e6)/1e6)),v.map(p=>[(p.texture[0]-index*2)*16,p.texture[1]*16]),texture,null,v[0].color??[1,1,1],false];
    });
  }
  models[name]={keys,variants};
}
fs.writeFileSync(path.join(root,'editor/data/resources/special-models.json'),JSON.stringify({deepslate:'0.27.1',models}));
console.log('SPECIAL_MODELS_OK',Object.keys(models).length,Object.values(models).reduce((n,m)=>n+Object.keys(m.variants).length,0));
initEntityModels(path.join(root,'resources/converter/win-x64/assets/entity-models'));
const available=JSON.parse(fs.readFileSync(path.join(root,'editor/data/resources/atlas-uv.json'),'utf8'));
const entityModels={};const missing=[];
for(const name of listEntityModelIds()){
  const result=createEntityModelMesh(name,atlas);if(!result)continue;
  let valid=true;
  const quads=result.mesh.quads.map(q=>{
    const v=q.vertices();const index=Math.floor(v.reduce((s,p)=>s+p.texture[0],0)/v.length/2);
    const texture=ids[index];if(!available[texture])valid=false;
    return [v.map(p=>[p.pos.x,p.pos.y,p.pos.z]),v.map(p=>[(p.texture[0]-index*2)*16,p.texture[1]*16]),texture,null,v[0].color??[1,1,1],false];
  });
  if(valid)entityModels[name]=quads;else missing.push(name);
}
fs.writeFileSync(path.join(root,'editor/data/resources/entity-models.json'),JSON.stringify({geometry_source:'EntityModelJson 1.19.x, upstream Mine2Blend catalog; only 26.2-resolving textures enabled',models:entityModels,placeholders:missing}));
console.log('ENTITY_MODELS_OK',Object.keys(entityModels).length,'texture-fallbacks',missing.length);
