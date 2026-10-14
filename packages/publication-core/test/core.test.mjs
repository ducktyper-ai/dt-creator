import test from 'node:test';
import assert from 'node:assert/strict';
import {defineSite, canonicalPath, defineMetadataSchema, projectPublicInventory, utcInstant} from '../index.mjs';
import {verifyContract, verifyDeclarationExports} from '../tools/check-contract.mjs';
const site = {id:'example', origin:'https://example.org', trailingSlash:'never'};
const stamp = '2026-10-14T01:00:00Z', now = Date.parse(stamp);
const schemaInput = {kinds:['entry'],statuses:['pending','approved','withdrawn'],accessLevels:['open','restricted'],publishedStatus:'approved',publicAccess:'open',validateSource:()=>true};
const doc = (patch={}) => Object.fromEntries(Object.entries({id:'one',kind:'entry',path:'/one',title:'One entry',summary:'A synthetic example.',status:'approved',access:'open',availableAt:stamp,...patch}).filter(([,value])=>value!==undefined));
const schema = defineMetadataSchema(schemaInput);
const project = (documents, patch={}) => projectPublicInventory(site,documents,{schema,now,selectPublication:()=>({}),...patch});
test('caller-owned classifications and explicit clock yield immutable public metadata',()=>{
  const input=doc({body:'PRIVATE_BODY',privateNotes:'PRIVATE_NOTES',sourceMetadata:{label:'synthetic'}});
  const before=JSON.stringify(input); const result=project([input]);
  assert.equal(result.evaluatedAt,now); assert.equal(result.entries[0].availableAt,stamp);
  assert.ok(Object.isFrozen(result)&&Object.isFrozen(result.entries)&&Object.isFrozen(result.entries[0]));
  assert.ok(!JSON.stringify(result).includes('PRIVATE')); assert.equal(JSON.stringify(input),before);
});
test('two caller origins and slash conventions retain deterministic canonical routes',()=>{
  assert.equal(project([doc()]).entries[0].canonicalUrl,'https://example.org/one');
  const other=projectPublicInventory({...site,id:'second',origin:'https://second.example',trailingSlash:'always'},[doc()],{schema,now,selectPublication:()=>({})});
  assert.equal(other.entries[0].canonicalUrl,'https://second.example/one/');
});
test('there is no built-in kind, status or access default',()=>{
  for(const patch of [{kind:'article'},{kind:undefined},{status:undefined},{access:undefined},{access:'public'}]) assert.throws(()=>project([doc(patch)]),/Undeclared classification/);
});
test('schema factory requires registries, explicit mapping and source validation',()=>{
  for(const patch of [{kinds:[]},{statuses:undefined},{accessLevels:['open','open']},{publishedStatus:'unknown'},{publicAccess:undefined},{validateSource:undefined}])assert.throws(()=>defineMetadataSchema({...schemaInput,...patch}));
  assert.throws(()=>project([doc()],{schema:{...schema}}),/Factory-created/);
  assert.ok(Object.isFrozen(schema.kinds));
});
test('source validation applies to hidden data before any selector',()=>{
  let calls=0;
  const rejecting=defineMetadataSchema({...schemaInput,validateSource:metadata=>metadata.status!=='pending'});
  assert.throws(()=>project([doc(),doc({id:'two',path:'/two',status:'pending'})],{schema:rejecting,selectPublication:()=>{calls++;return {};}}),/Source schema validation failed/);
  assert.equal(calls,0);
});
test('all routes register before source validators and publication selectors',()=>{
  let validations=0,calls=0;
  const counted=defineMetadataSchema({...schemaInput,validateSource:()=>{validations++;return true;}});
  for(const patch of [{status:'pending'},{access:'restricted'},{availableAt:'2027-01-01T00:00:00Z'}]) {
    assert.throws(()=>project([doc(),doc({id:'two',path:'/ONE/',...patch})],{schema:counted,selectPublication:()=>{calls++;return null;}}),/Duplicate registered route/);
  }
  assert.equal(validations,0);assert.equal(calls,0);
});
test('duplicate IDs and malformed hidden routes fail registration',()=>{
  assert.throws(()=>project([doc(),doc({path:'/two',status:'pending'})]),/Duplicate content ID/);
  assert.throws(()=>project([doc({path:'/../two',status:'pending'})]),/Unsafe or ambiguous path/);
});
test('unapproved or restricted documents never reach selector',()=>{
  let calls=0;
  const result=project([doc({status:'pending'}),doc({id:'two',path:'/two',access:'restricted'})],{selectPublication:()=>{calls++;return {};}});
  assert.equal(calls,0);assert.deepEqual(result.entries,[]);
});
test('finite explicit time has no fallback',()=>{
  for(const value of [undefined,null,NaN,Infinity,1e100,'today'])assert.throws(()=>project([doc()],{now:value}),/Finite explicit evaluation clock/);
});
test('missing or invalid availability fails even if a selector would hide it',()=>{
  for(const value of [undefined,'2026-10-14','2026-02-30T01:00:00Z','2026-10-14T01:00:00+00:00'])assert.throws(()=>project([doc({availableAt:value})],{selectPublication:()=>null}),/UTC instant/);
});
test('selector exclusion and before/at/after boundary use the same clock',()=>{
  for(const offset of [-1,0,1]){
    const result=project([doc()],{now:now+offset,selectPublication:(metadata,clock)=>{
      assert.equal(clock,now+offset);return Date.parse(metadata.availableAt)<=clock?{}:null;
    }});
    assert.equal(result.entries.length,offset<0?0:1);
  }
  assert.throws(()=>project([doc()],{now:now-1}),/unavailable at evaluatedAt/);
});
test('publication/update instants enforce ordering and evaluation bounds',()=>{
  for(const selection of [{updatedAt:'2026-10-14T00:59:59.999Z'},{updatedAt:'2026-10-14T01:00:00.001Z'},{publishedAt:'2026-10-14T01:00:00.001Z'},{publishedAt:stamp,updatedAt:'2026-10-14T00:59:59.999Z'},{publishedAt:'2026-10-14'}])assert.throws(()=>project([doc()],{selectPublication:()=>selection}));
  const entry=project([doc()],{selectPublication:()=>({publishedAt:stamp,updatedAt:stamp})}).entries[0];
  assert.equal(entry.publishedAt,stamp);assert.equal(entry.updatedAt,stamp);
});
test('availability does not invent display labels or publication history',()=>{
  assert.ok(!Object.hasOwn(project([doc()]).entries[0],'publishedAt'));
  assert.ok(!Object.hasOwn(project([doc()]).entries[0],'updatedAt'));
});
test('source metadata copy is deeply immutable and strips bodies before callbacks',()=>{
  const input=doc({body:'PRIVATE',sourceMetadata:{nested:{value:1}}});
  project([input],{selectPublication:metadata=>{
    assert.ok(!Object.hasOwn(metadata,'body'));
    assert.ok(Object.isFrozen(metadata.sourceMetadata.nested));
    assert.throws(()=>{metadata.sourceMetadata.nested.value=2;});return {};
  }});
  assert.equal(input.sourceMetadata.nested.value,1);
});
test('accessors, functions, cycles and non-data prototypes are refused without invoking getters',()=>{
  let calls=0;const getter=doc();Object.defineProperty(getter,'secret',{enumerable:true,get(){calls++;return 'x';}});
  const cycle={};cycle.self=cycle;
  for(const value of [getter,doc({callback(){}}),doc({sourceMetadata:cycle}),doc({sourceMetadata:new Date()})])assert.throws(()=>project([value]));
  assert.equal(calls,0);
});
test('selector must return null or plain data',()=>{
  for(const value of [undefined,true,[],new Date()])assert.throws(()=>project([doc()],{selectPublication:()=>value}),/plain data/);
});
test('canonical mismatch and malformed origin/path fail',()=>{
  assert.throws(()=>project([doc({canonicalUrl:'https://other.example/one'})]),/Canonical differs/);
  for(const origin of ['http://example.org','https://user:pass@example.org','https://example.org/base'])assert.throws(()=>defineSite({...site,origin}));
  for(const path of ['relative','//bad','/a//b','/a?x=1','/a#x','/a/%2f','/a/../b','/caf\u00e9','/a\u202e'])assert.throws(()=>canonicalPath(site,path));
});
test('ordering is locale independent and input order remains unchanged',()=>{
  const inputs=[doc({id:'z',path:'/z'}),doc({id:'a',path:'/a'})];const before=JSON.stringify(inputs);
  assert.deepEqual(project(inputs).entries.map(entry=>entry.id),['a','z']);assert.equal(JSON.stringify(inputs),before);
});
test('UTC precision is retained and impossible instants fail',()=>{
  assert.equal(utcInstant('2026-10-14T01:00:00.123Z'),'2026-10-14T01:00:00.123Z');
  assert.throws(()=>utcInstant('2026-02-30T00:00:00Z'));
});
test('dependency-free declaration/export and package-content gate passes',()=>assert.equal(verifyContract().exports,5));
test('declaration gate rejects omitted and invented runtime exports',()=>{
  assert.throws(()=>verifyDeclarationExports(['one'],'export declare function two(): void;'));
  assert.throws(()=>verifyDeclarationExports(['one'],'export declare function one(): void;\nexport declare function extra(): void;'));
  assert.throws(()=>verifyDeclarationExports(['one'],'export declare function one(): void;\nexport declare function one(): void;'));
});
