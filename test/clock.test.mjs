import test from 'node:test';
import assert from 'node:assert/strict';
import {projectPublicInventory} from '../index.mjs';
import {utcAvailability,londonDateAvailability} from '../policies.mjs';
const site={id:'profrod',origin:'https://profrod.ai',trailingSlash:'never'};
const availableAt='2026-06-30T23:00:00.000Z',boundary=Date.parse(availableAt);
const doc=(patch={})=>({id:'note',kind:'note',path:'/notes/note',title:'London release',summary:'The label is not a UTC-day release instant.',status:'published',access:'public',availableAt,...patch});
test('finite explicit clock required, no global-clock fallback',()=>{
  for(const now of [undefined,null,'today',NaN,Infinity,1e100])assert.throws(()=>projectPublicInventory(site,[doc()],{now,selectPublication:()=>null}), /Finite evaluation clock required/);
});
test('core clock is passed to selector and retained as evaluatedAt',()=>{
  const result=projectPublicInventory(site,[doc()],{now:boundary,selectPublication:(copy,now)=>{assert.equal(now,boundary);return {publishedAt:'2026-07-01'};}});
  assert.equal(result.evaluatedAt,boundary);assert.equal(result.entries[0].availableAt,availableAt);
  assert.equal(result.entries[0].publishedAt,'2026-07-01');assert.ok(Object.isFrozen(result));
});
test('wrong earlier clock yields zero entries under source-selected eligibility',()=>{
  const result=projectPublicInventory(site,[doc()],{now:boundary-1,selectPublication:(copy,now)=>Date.parse(copy.availableAt)<=now?{publishedAt:'2026-07-01'}:null});
  assert.deepEqual(result.entries,[]);assert.equal(result.evaluatedAt,boundary-1);
});
test('rogue selector cannot expose a future availability instant',()=>assert.throws(()=>projectPublicInventory(site,[doc()],{now:boundary-1,selectPublication:()=>({publishedAt:'2026-07-01'})}), /Selected publication is not available at evaluatedAt/));
test('missing or invalid source-derived availability refuses even when hidden',()=>{
  for(const value of [undefined,'','2026-07-01','2026-02-30T00:00:00Z','2026-07-01T00:00:00+01:00'])assert.throws(()=>projectPublicInventory(site,[doc({availableAt:value})],{now:boundary,selectPublication:()=>null}), /Availability must be an explicit UTC timestamp|Availability must be a real UTC timestamp/);
});
test('updatedAt is bounded by availability and evaluation instants, equality allowed',()=>{
  for(const updatedAt of ['2026-06-30T22:59:59.999Z','2026-06-30T23:00:00.001Z'])assert.throws(()=>projectPublicInventory(site,[doc()],{now:boundary,selectPublication:()=>({publishedAt:'2026-07-01',updatedAt})}), /Invalid substantive update instant/);
  const result=projectPublicInventory(site,[doc()],{now:boundary,selectPublication:()=>({publishedAt:'2026-07-01',updatedAt:availableAt})});
  assert.equal(result.entries[0].updatedAt,availableAt);
});
test('a known accepted availability does not invent an unknown display date',()=>{
  const result=projectPublicInventory(site,[doc()],{now:boundary,selectPublication:()=>({})});
  assert.ok(!Object.hasOwn(result.entries[0],'publishedAt'));
});
test('pure London derivation preserves summer and23/25hour DST boundaries',()=>{
  assert.equal(londonDateAvailability('2026-07-01'),availableAt);
  for(const [day,next,hours] of [['2026-03-29','2026-03-30',23],['2026-10-25','2026-10-26',25]])assert.equal((Date.parse(londonDateAvailability(next))-Date.parse(londonDateAvailability(day)))/3600000,hours);
});
test('absolute London winter and transition dates match the source policy',()=>{
  for(const [label,instant] of [
    ['2026-01-01','2026-01-01T00:00:00.000Z'],
    ['2026-03-29','2026-03-29T00:00:00.000Z'],
    ['2026-03-30','2026-03-29T23:00:00.000Z'],
    ['2026-10-25','2026-10-24T23:00:00.000Z'],
    ['2026-10-26','2026-10-26T00:00:00.000Z'],
  ])assert.equal(londonDateAvailability(label),instant);
});
test('no derivable date or UTC instant produces a default',()=>{
  for(const value of [undefined,'not a date','2026-02-30'])assert.throws(()=>londonDateAvailability(value), /London publication label must be/);
  assert.throws(()=>utcAvailability('2026-07-01'), /Availability must be an explicit UTC timestamp/);
});
