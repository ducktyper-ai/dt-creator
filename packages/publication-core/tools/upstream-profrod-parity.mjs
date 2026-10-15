// Explicit source-packet probe, not an installed/site-runtime qualification.
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {projectPublicInventory} from '../index.mjs';
import {londonDateAvailability} from '../policies.mjs';
import {probeContext} from './probe-context.mjs';
const packet=process.argv[2];
if(!packet || process.argv.length!==3)throw Error('Pass the owner-provided SOW311 source archive');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
assert.equal(hash(readFileSync(packet)),'621e8bba92aaaf6f81707c09170c9f39efa6dddfe215127a1dbf414915889c7e');
const listing=execFileSync('tar',['-tf',packet],{encoding:'utf8',timeout:2500}).trim().split('\n');
assert.equal(new Set(listing).size,listing.length,'Duplicate archive paths');
for(const file of listing)assert.ok(file && !file.startsWith('/') && !file.split('/').includes('..') && !file.includes('\\'),'Unsafe archive name');
// No extraction. Require every header to be a regular file before reading payloads.
const headers=execFileSync('tar',['-tvf',packet],{encoding:'utf8',timeout:2500}).trim().split('\n');
assert.ok(headers.every(line=>line.startsWith('-')),'Non-regular payload entry');
const read=entry=>execFileSync('tar',['-xOf',packet,entry],{timeout:2500,maxBuffer:2*1024*1024});
const manifest=JSON.parse(read('payload-manifest-v1.json'));
assert.equal(manifest.files.length,listing.length-1,'All payloads except manifest must be listed');
assert.equal(new Set(manifest.files.map(x=>x.path)).size,manifest.files.length);
for(const entry of manifest.files){
  assert.ok(listing.includes(entry.path));
  const bytes=read(entry.path);assert.equal(bytes.length,entry.bytes);assert.equal(hash(bytes),entry.sha256);
}
assert.equal(hash(read('profrod-shared-astro-extraction-contract-v1.md')),'bb7c7b08fdc55b9cc1e55c9ca6e35ef8d20c0683a0a2421b17859b45440eda3e');
const source=read('gold-source/src/lib/notePublication.mjs');
const upstream=await import(`data:text/javascript;base64,${source.toString('base64')}`);
const site={id:'profrod',origin:'https://profrod.ai',trailingSlash:'never'};
for(const [release,date] of [
  ['2026-07-01T00:00:00+01:00','2026-07-01'],
  ['2026-03-30T00:00:00+01:00','2026-03-30'],
  ['2026-10-26T00:00:00Z','2026-10-26'],
]){
  const records=[{id:'due',publishedAt:date},{id:'draft',publishedAt:date,draft:true},{id:'invalid',publishedAt:'2026-02-30'}];
  assert.equal(upstream.validDate('2026-02-30'),false);
  const docs=records.filter(x=>upstream.validDate(x.publishedAt)).map(x=>({...x,kind:'note',path:`/notes/${x.id}`,title:x.id,summary:'Source-owned London clock probe.',status:x.draft===true?'draft':'published',access:'public',availableAt:londonDateAvailability(x.publishedAt),body:'NEVER_DISCOVERY_BODY'}));
  for(const offset of [-1,0,1]){
    const now=new Date(Date.parse(release)+offset);
    console.log(JSON.stringify(probeContext(now.getTime())));
    const selected=new Set(upstream.publishedNotes(records,now).map(x=>x.id));
    const result=projectPublicInventory(site,docs,{now:now.getTime(),selectPublication:(doc,evaluatedAt)=>{assert.equal(evaluatedAt,now.getTime());return selected.has(doc.id)?{publishedAt:doc.publishedAt}:null;}});
    assert.deepEqual(result.entries.map(x=>x.id),[...selected]);
    assert.equal(result.entries.length,offset<0?0:1);
    assert.ok(!JSON.stringify(result).includes('NEVER_DISCOVERY_BODY'));
  }
  console.log(`PASS source-owned London midnight ${date}, before/at/after; no generic UTC-day selection`);
}
for(const [start,hours] of [['2026-03-29T00:00:00Z',23],['2026-10-24T23:00:00Z',25]]){
  const value=upstream.publicationHeaders(new Date(start))['Cloudflare-CDN-Cache-Control'];
  assert.ok(value.includes(`max-age=${hours*3600-1},`),`Preserve ${hours}-hour DST day freshness`);
}
assert.equal(upstream.unpublishedResponse().headers.get('Cache-Control'),'no-store');
console.log(`PASS owner archive SHA and ${manifest.files.length} payload hashes; source DST/cache/privacy observations only, not compiled Astro/host parity`);
