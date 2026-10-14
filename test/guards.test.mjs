import test from 'node:test';
import assert from 'node:assert/strict';
import {defineSite,canonicalPath,projectPublicInventory,compilePublicInventory} from '../index.mjs';
const site={id:'rasa',origin:'https://rasa.community',trailingSlash:'always'};
const doc=(patch={})=>({id:'a',kind:'article',path:'/a/',status:'published',access:'public',title:'A real article',summary:'A concrete summary.',publishedAt:'2026-10-14',availableAt:'2026-10-14T00:00:00Z',...patch});
const now=Date.parse('2026-10-14T12:00:00Z');
const selectPublication=()=>({publishedAt:'2026-10-14'});
const project=(docs,selector=selectPublication)=>projectPublicInventory(site,docs,{now,selectPublication:selector}).entries;
test('future collision fails before the first publication callback',()=>{
  let calls=0;
  assert.throws(()=>project([doc(),doc({id:'future',publishedAt:'2026-10-15'})],()=>{calls++;return null;}), /Duplicate registered route: \/a\//);
  assert.equal(calls,0);
});
test('draft/member routes are registered, even when never selected',()=>{
  for(const patch of [{status:'draft'},{access:'member'},{access:'paid'}])assert.throws(()=>project([doc(),doc({id:'reserved',...patch})]), /Duplicate registered route/);
});
test('invalid future route refuses even when selector would hide it',()=>assert.throws(()=>project([doc({path:'/../future'})],()=>null), /Unsafe or ambiguous content path/));
test('case-only aliases cannot reserve two routes',()=>assert.throws(()=>project([doc(),doc({id:'b',path:'/A/'})]), /Duplicate registered route/));
test('unknown and missing kind fail registration',()=>{
  for(const kind of [undefined,'invented'])assert.throws(()=>project([doc({kind})]), /Unknown content kind/);
});
test('required explicit access has no public default',()=>{
  for(const access of [undefined,null,'',false,'Public'])assert.throws(()=>project([doc({access})]), /Invalid publication\/access classification/);
});
test('site identity and slash policy guards are specific',()=>{
  assert.throws(()=>defineSite({...site,id:'bad ID'}), /Invalid site ID/);
  assert.throws(()=>defineSite({...site,id:''}), /site.id must be a nonempty/);
  assert.throws(()=>defineSite({...site,trailingSlash:'guess'}), /Choose explicit trailingSlash/);
});
test('non-array collection and null documents fail before selector',()=>{
  assert.throws(()=>project({}), /documents must be an array/);
  assert.throws(()=>project([null]), /Invalid document/);
});
test('published text fields are required rather than replaced with a default',()=>{
  assert.throws(()=>project([doc({title:''})]), /title must be a nonempty/);
  assert.throws(()=>project([doc({summary:undefined})]), /summary must be a nonempty/);
});
test('relative, dot, control, bidi and non-ASCII paths refused',()=>{
  for(const path of ['relative','/./a','/a/..','/a\u0000','/a\u007f','/a\u202e','/caf\u00e9'])assert.throws(()=>canonicalPath(site,path), /Unsafe or ambiguous content path/);
});
test('millisecond timestamp precision is retained',()=>{
  const stamp='2026-10-14T09:00:00.001Z';
  assert.equal(project([doc()],()=>({publishedAt:stamp}))[0].publishedAt,stamp);
});
test('array selector result with otherwise valid fields is specifically refused',()=>{
  const array=[];array.publishedAt='2026-10-14';
  assert.throws(()=>project([doc()],()=>array), /Publication selector must return null or metadata/);
});
test('invalid substantive update syntax refused in projection',()=>assert.throws(()=>project([doc()],()=>({publishedAt:'2026-10-14',updatedAt:'2026-02-30T00:00:00Z'})), /Availability must be a real UTC timestamp/));
test('date-only wrapper permits equality at publication and evaluation bounds',()=>{
  const result=compilePublicInventory(site,[doc({updatedAt:'2026-10-14'})],{asOf:'2026-10-14'});
  assert.equal(result[0].updatedAt,'2026-10-14');
});
test('selector receives a deep-frozen independent copy',()=>{
  const input=doc({sourceMetadata:{draft:false}});
  project([input],copy=>{
    assert.notEqual(copy,input);assert.notEqual(copy.sourceMetadata,input.sourceMetadata);
    assert.ok(Object.isFrozen(copy)&&Object.isFrozen(copy.sourceMetadata));
    assert.throws(()=>{copy.access='paid';}, /read only|not extensible/);
    assert.throws(()=>{copy.sourceMetadata.draft=true;}, /read only|not extensible/);
    return {publishedAt:input.publishedAt};
  });
  assert.equal(input.access,'public');assert.equal(input.sourceMetadata.draft,false);
});
test('non-data metadata cannot be sent into the selector',()=>assert.throws(()=>project([doc({callback(){}})]), /Document metadata must be cloneable/));
