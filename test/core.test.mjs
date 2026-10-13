import test from 'node:test';
import assert from 'node:assert/strict';
import {defineSite, canonicalPath, compilePublicInventory} from '../index.mjs';
const asOf = '2026-10-14';
const profrod = {id:'profrod',origin:'https://profrod.ai',trailingSlash:'never'};
const rasa = {id:'rasa',origin:'https://rasa.community',trailingSlash:'always'};
const article = (overrides = {}) => ({id:'a',kind:'article',path:'/articles/a',title:'Trace a failed request',summary:'Follow one request through the worker and inspect the failure.',status:'published',access:'public',publishedAt:'2026-10-12',...overrides});
const inventory = (docs, site=profrod) => compilePublicInventory(site, docs, {asOf});
test('two site policies share logic but retain origin and URL convention', () => {
  assert.equal(inventory([article()])[0].canonicalUrl,'https://profrod.ai/articles/a');
  assert.equal(inventory([article({path:'/library/guides/a'})],rasa)[0].canonicalUrl,'https://rasa.community/library/guides/a/');
});
test('public inventory never serializes full body or unknown metadata', () => {
  const result=inventory([article({body:'BODY_MUST_NOT_PROJECT',extension:{secret:'DO_NOT_PROJECT'},privateNotes:'DO_NOT_PROJECT'})]);
  assert.ok(!JSON.stringify(result).includes('PROJECT'));
  assert.ok(!Object.hasOwn(result[0],'body'));
});
test('draft, review, retired, member and paid material excluded from every projection', () => {
  const docs=[article(),...['draft','review','retired'].map(status=>article({id:status,status,body:'HIDDEN'})),...['member','paid'].map(access=>article({id:access,access,body:'HIDDEN'}))];
  assert.deepEqual(inventory(docs).map(x=>x.id),['a']);
});
test('scheduled future publication excluded using an explicit reproducible time', () => assert.deepEqual(inventory([article({publishedAt:'2026-10-15'})]),[]));
test('missing publication clock refuses rather than using wall clock', () => assert.throws(()=>compilePublicInventory(profrod,[article()])));
test('invalid publication/access classification fails closed', () => {
  assert.throws(()=>inventory([article({status:'Publish'})]));
  assert.throws(()=>inventory([article({access:undefined})]));
});
test('duplicate IDs refused even across a draft and public document', () => assert.throws(()=>inventory([article(),article({status:'draft'})])));
test('duplicate route alias with trailing slash refused', () => assert.throws(()=>inventory([article(),article({id:'b',path:'/articles/a/'})])));
test('wrong site canonical cannot pass by otherwise valid metadata', () => assert.throws(()=>inventory([article({canonicalUrl:'https://rasa.community/articles/a'})])));
test('real calendar date validation and substantive modification bounds', () => {
  for(const patch of [{publishedAt:'2026-02-30'},{updatedAt:'2026-10-11'},{updatedAt:'2026-10-15'}])assert.throws(()=>inventory([article(patch)]));
  assert.equal(inventory([article({updatedAt:'2026-10-13'})])[0].updatedAt,'2026-10-13');
});
test('external, traversal, encoded and query paths rejected', () => {
  for(const path of ['//evil.example/x','/a/../x','/a/%2e%2e/x','/a?token=x','/a#x','/a\\x','/a//b'])assert.throws(()=>canonicalPath(profrod,path));
});
test('origin rejects insecure schemes, credentials and base paths', () => {
  for(const origin of ['http://example.com','https://user:pass@example.com','https://example.com/base','https://example.com?x=1'])assert.throws(()=>defineSite({...profrod,origin}));
});
test('stable ordering, frozen output and input remains unchanged', () => {
  const docs=[article({id:'z',path:'/z'}),article()];
  const before=JSON.stringify(docs), output=inventory(docs);
  assert.deepEqual(output.map(x=>x.id),['a','z']);
  assert.equal(JSON.stringify(docs),before);
  assert.ok(Object.isFrozen(output)&&Object.isFrozen(output[0]));
});
