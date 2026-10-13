import test from 'node:test';
import assert from 'node:assert/strict';
import {projectPublicInventory} from '../index.mjs';
const site = {id:'rasa',origin:'https://rasa.community',trailingSlash:'always'};
const document = (patch={}) => ({id:'casebook/a',kind:'article',path:'/library/casebook/a/',title:'Inspect one failed transfer',summary:'Trace the actual receipt boundary.',status:'published',access:'public',...patch});
const selection = {publishedAt:'2026-10-14T09:00:00Z'};
test('projection refuses an absent publication policy',()=>assert.throws(()=>projectPublicInventory(site,[document()])));
test('selector exclusion is authoritative even for declared published public metadata',()=>assert.deepEqual(projectPublicInventory(site,[document()],{selectPublication:()=>null}),[]));
test('selection retains exact UTC timestamp and refuses extra payload propagation',()=>{
  const result=projectPublicInventory(site,[document({body:'PRIVATE_INPUT'})],{selectPublication:()=>({...selection,body:'PRIVATE_SELECTION'})});
  assert.equal(result[0].publishedAt,selection.publishedAt);
  assert.ok(!JSON.stringify(result).includes('PRIVATE'));
});
test('member, paid and draft data do not reach a publication selector',()=>{
  let calls=0;
  const result=projectPublicInventory(site,[document({access:'paid'}),document({id:'member',access:'member'}),document({id:'draft',status:'draft'})],{selectPublication:()=>{calls++;return selection;}});
  assert.deepEqual(result,[]);assert.equal(calls,0);
});
test('malformed policy results and invalid UTC dates fail closed',()=>{
  for(const invalid of [undefined,true,[],{}, {publishedAt:'2026-02-30T09:00:00Z'},{publishedAt:'2026-10-14T09:00:00'},{publishedAt:'2026-10-14T09:00:00+00:00'}])assert.throws(()=>projectPublicInventory(site,[document()],{selectPublication:()=>invalid}));
});
test('date-only author metadata does not create an implicit scheduling gate',()=>{
  const result=projectPublicInventory(site,[document({id:'guides/a',path:'/library/guides/a/'})],{selectPublication:()=>({publishedAt:'2026-10-16'})});
  assert.equal(result.length,1); // Source-specific editorial/route policy owns eligibility.
});
