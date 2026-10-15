// Pure contracts: Astro/platform adapters consume this module; no filesystem or service access.
import {utcAvailability} from './policies.mjs';
const statuses = new Set(['draft', 'review', 'published', 'retired']);
const accessLevels = new Set(['public', 'member', 'paid']);
const kinds = new Set(['article', 'note', 'tutorial', 'course', 'module', 'lesson', 'resource']);
const nonempty = (value, name) => {
  if (typeof value !== 'string' || value.trim() !== value || !value.length) throw new TypeError(`${name} must be a nonempty trimmed string`);
  return value;
};
function dateOnly(value, name) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new TypeError(`${name} must be YYYY-MM-DD`);
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) throw new TypeError(`${name} must be a real calendar date`);
  return value;
}
export function defineSite(input) {
  nonempty(input?.id, 'site.id');
  if (!/^[a-z][a-z0-9-]*$/.test(input.id)) throw new TypeError('Invalid site ID');
  const url = new URL(input.origin);
  if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new TypeError('Site origin must be an HTTPS origin without credentials, path or query');
  if (!['always', 'never'].includes(input.trailingSlash)) throw new TypeError('Choose explicit trailingSlash always or never');
  const extensionKinds=input.extensionKinds===undefined?[]:input.extensionKinds;
  if(!Array.isArray(extensionKinds))throw new TypeError('extensionKinds must be an explicit array');
  const seen=new Set(kinds);
  for(const kind of extensionKinds){
    if(typeof kind!=='string'||!/^[a-z][a-z0-9-]*$/.test(kind)||seen.has(kind))throw new TypeError('Extension kinds must be unique declared lowercase names');
    seen.add(kind);
  }
  return Object.freeze({id: input.id, origin: url.origin, trailingSlash: input.trailingSlash,extensionKinds:Object.freeze([...extensionKinds])});
}
export function canonicalPath(siteInput, path) {
  const site = defineSite(siteInput);
  nonempty(path, 'path');
  if (!/^\/[A-Za-z0-9._~/-]*$/.test(path) || path.includes('//') || path.split('/').some(x => x === '.' || x === '..')) throw new TypeError('Unsafe or ambiguous content path');
  const bare = path === '/' ? '/' : path.replace(/\/$/, '');
  return bare === '/' ? bare : site.trailingSlash === 'always' ? `${bare}/` : bare;
}
function publicationDate(value, name) {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) return dateOnly(value, name);
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)) throw new TypeError(`${name} must be a real date or UTC timestamp`);
  const parsed = new Date(value);
  const normalized = value.includes('.') ? value : value.replace('Z', '.000Z');
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString() !== normalized) throw new TypeError(`${name} must be a real UTC timestamp`);
  return value; // Retain source precision and spelling; never silently reduce to a day.
}
/** Site-owned trusted code selects publication. Projection never supplies a universal clock. */
export function projectPublicInventory(siteInput, documents, {now, selectPublication} = {}) {
  const site = defineSite(siteInput);
  if(typeof now!=='number'||!Number.isFinite(now)||!Number.isFinite(new Date(now).getTime()))throw new TypeError('Finite evaluation clock required');
  if (typeof selectPublication !== 'function') throw new TypeError('Explicit trusted publication selector required');
  if (!Array.isArray(documents)) throw new TypeError('documents must be an array');
  const ids = new Set(), paths = new Set();
  // Register all routable content before evaluating any publication callback.
  // A future/draft/private collision must fail now, not at its first release request.
  const registered = documents.map(doc => {
    if (!doc || typeof doc !== 'object') throw new TypeError('Invalid document');
    nonempty(doc.id, 'id');
    if (ids.has(doc.id)) throw new TypeError(`Duplicate content ID: ${doc.id}`);
    ids.add(doc.id);
    if (!statuses.has(doc.status) || !accessLevels.has(doc.access)) throw new TypeError(`Invalid publication/access classification: ${doc.id}`);
    if (!kinds.has(doc.kind)&&!site.extensionKinds.includes(doc.kind)) throw new TypeError(`Unknown content kind: ${doc.id}`);
    const path = canonicalPath(site, doc.path);
    const collisionKey = path.toLowerCase();
    if (paths.has(collisionKey)) throw new TypeError(`Duplicate registered route: ${path}`);
    paths.add(collisionKey);
    return {doc, path};
  });
  const entries = [];
  for (const {doc, path} of registered) {
    // Registered private/draft data never reaches the selector or public projection.
    if (doc.status !== 'published' || doc.access !== 'public') continue;
    const availableAt=utcAvailability(doc.availableAt);
    const availableInstant=Date.parse(availableAt);
    const selection = selectPublication(frozenMetadataCopy(doc),now);
    if (selection === null) continue;
    if (!selection || typeof selection !== 'object' || Array.isArray(selection)) throw new TypeError('Publication selector must return null or metadata');
    if(availableInstant>now)throw new TypeError(`Selected publication is not available at evaluatedAt: ${doc.id}`);
    const canonicalUrl = new URL(path, site.origin).href;
    if (doc.canonicalUrl !== undefined && doc.canonicalUrl !== canonicalUrl) throw new TypeError(`Canonical differs from site/path: ${doc.id}`);
    const entry = {id: doc.id, kind: nonempty(doc.kind, 'kind'), path, title: nonempty(doc.title, 'title'), summary: nonempty(doc.summary, 'summary'), canonicalUrl, availableAt};
    if(selection.publishedAt!==undefined)entry.publishedAt=publicationDate(selection.publishedAt,'publishedAt');
    if (selection.updatedAt !== undefined) {
      entry.updatedAt=utcAvailability(selection.updatedAt);
      const updated=Date.parse(entry.updatedAt);
      if(updated<availableInstant||updated>now)throw new TypeError(`Invalid substantive update instant: ${doc.id}`);
    }
    entries.push(Object.freeze(entry));
  }
  // Code-unit ordering is locale-independent; do not reorder source documents in place.
  return Object.freeze({evaluatedAt:now,entries:Object.freeze(entries.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0))});
}
function frozenMetadataCopy(doc) {
  let copy;
  try { copy = structuredClone(doc); } catch { throw new TypeError('Document metadata must be cloneable'); }
  const seen = new WeakSet();
  function freeze(value) {
    if (!value || typeof value !== 'object' || seen.has(value)) return value;
    seen.add(value);
    for (const key of Object.keys(value)) freeze(value[key]);
    return Object.freeze(value);
  }
  return freeze(copy);
}
/** Explicit date-only prototype policy retained; not the Rasa request-clock adapter. */
export function compilePublicInventory(siteInput, documents, {asOf} = {}) {
  dateOnly(asOf, 'asOf');
  if(!Array.isArray(documents))throw new TypeError('documents must be an array');
  const normalized=documents.map(doc=>{
    if(!doc||typeof doc!=='object')throw new TypeError('Invalid document');
    if(doc.status!=='published'||doc.access!=='public')return doc;
    return {...doc,availableAt:`${dateOnly(doc.publishedAt,'publishedAt')}T00:00:00Z`};
  });
  const result=projectPublicInventory(siteInput, normalized, {now:Date.parse(`${asOf}T00:00:00Z`),selectPublication(doc) {
    const publishedAt = dateOnly(doc.publishedAt, 'publishedAt');
    if (publishedAt > asOf) return null;
    const selection = {publishedAt};
    if (doc.updatedAt !== undefined) {
      const label=dateOnly(doc.updatedAt, 'updatedAt');
      if (label < publishedAt || label > asOf) throw new TypeError(`Invalid substantive update date: ${doc.id}`);
      selection.updatedAt=`${label}T00:00:00Z`;
    }
    return selection;
  }});
  // Keep the explicitly dated legacy spike wrapper's output shape for its fixtures.
  return Object.freeze(result.entries.map(entry=>Object.freeze({...entry,...(entry.updatedAt?{updatedAt:entry.updatedAt.slice(0,10)}:{})})));
}
