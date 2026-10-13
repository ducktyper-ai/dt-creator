// Explicit read-only source probe; not part of the dependency-free standalone suite.
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {projectPublicInventory} from '../index.mjs';
const repo = process.argv[2];
if (!repo || process.argv.length !== 3) throw Error('Pass the existing Rasa repository containing the accepted object');
const baseline = 'f6acbd6c822ddb9273bf5decd58b4e647d2c8cfd';
const source = execFileSync('git',['-C',repo,'show',`${baseline}:src/lib/casebook-publication.mjs`],{encoding:'utf8',timeout:2500,maxBuffer:128*1024});
const upstream = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const timestamp = '2026-10-14T09:00:00Z', boundary=Date.parse(timestamp);
const cases = [
  {id:'due',data:{draft:false,publishAt:timestamp}},
  {id:'draft',data:{draft:true,publishAt:'2026-10-13T09:00:00Z'}},
  {id:'missing',data:{draft:false}},
  {id:'timezone-free',data:{draft:false,publishAt:'2026-10-13T09:00:00'}},
];
const site={id:'rasa',origin:'https://rasa.community',trailingSlash:'always'};
const documents=cases.map(entry=>({id:entry.id,kind:'article',path:`/library/casebook/${entry.id}/`,title:entry.id,summary:'Source-owned casebook publication probe.',status:entry.data.draft===false?'published':'draft',access:'public',sourceMetadata:entry.data,body:'NEVER_PUBLIC_METADATA'}));
for(const offset of [-1,0,1]){
  const now=boundary+offset;
  const projected=projectPublicInventory(site,documents,{selectPublication(doc){return upstream.isCasebookPublished(doc.sourceMetadata,now)?{publishedAt:doc.sourceMetadata.publishAt}:null;}});
  assert.deepEqual(projected.map(x=>x.id),cases.filter(x=>upstream.isCasebookPublished(x.data,now)).map(x=>x.id));
  if(offset>=0)assert.equal(projected[0].publishedAt,timestamp);
  assert.ok(!JSON.stringify(projected).includes('NEVER_PUBLIC_METADATA'));
  console.log(`PASS exact source publication selection at ${offset}ms relative to release`);
}
assert.equal(upstream.unpublishedResponse().status,404);
assert.equal(upstream.unpublishedResponse().headers.get('Cache-Control'),'no-store');
assert.equal(upstream.publicationCacheHeaders([{data:{draft:false,publishAt:timestamp}}],boundary-1)['Netlify-CDN-Cache-Control'],'no-store');
assert.ok(upstream.publicationProblem({draft:false}));
console.log(`PASS source oracle ${baseline}:src/lib/casebook-publication.mjs; no packaged Astro/Netlify or browser parity claim`);
