// Pure contracts: Astro/platform adapters consume this module; no filesystem or service access.
const statuses = new Set(['draft', 'review', 'published', 'retired']);
const accessLevels = new Set(['public', 'member', 'paid']);
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
  return Object.freeze({id: input.id, origin: url.origin, trailingSlash: input.trailingSlash});
}
export function canonicalPath(siteInput, path) {
  const site = defineSite(siteInput);
  nonempty(path, 'path');
  if (!path.startsWith('/') || path.includes('//') || /[\u0000-\u0020\\?#%]/.test(path) || path.split('/').some(x => x === '.' || x === '..')) throw new TypeError('Unsafe or ambiguous content path');
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
export function projectPublicInventory(siteInput, documents, {selectPublication} = {}) {
  const site = defineSite(siteInput);
  if (typeof selectPublication !== 'function') throw new TypeError('Explicit trusted publication selector required');
  if (!Array.isArray(documents)) throw new TypeError('documents must be an array');
  const ids = new Set(), paths = new Set();
  const entries = [];
  for (const doc of documents) {
    if (!doc || typeof doc !== 'object') throw new TypeError('Invalid document');
    nonempty(doc.id, 'id');
    if (ids.has(doc.id)) throw new TypeError(`Duplicate content ID: ${doc.id}`);
    ids.add(doc.id);
    if (!statuses.has(doc.status) || !accessLevels.has(doc.access)) throw new TypeError(`Invalid publication/access classification: ${doc.id}`);
    // Private/draft fields are not inspected or projected into a public manifest.
    if (doc.status !== 'published' || doc.access !== 'public') continue;
    const selection = selectPublication(doc);
    if (selection === null) continue;
    if (!selection || typeof selection !== 'object' || Array.isArray(selection)) throw new TypeError('Publication selector must return null or metadata');
    const publishedAt = publicationDate(selection.publishedAt, 'publishedAt');
    const path = canonicalPath(site, doc.path);
    if (paths.has(path)) throw new TypeError(`Duplicate public route: ${path}`);
    paths.add(path);
    const canonicalUrl = new URL(path, site.origin).href;
    if (doc.canonicalUrl !== undefined && doc.canonicalUrl !== canonicalUrl) throw new TypeError(`Canonical differs from site/path: ${doc.id}`);
    const entry = {id: doc.id, kind: nonempty(doc.kind, 'kind'), path, title: nonempty(doc.title, 'title'), summary: nonempty(doc.summary, 'summary'), canonicalUrl, publishedAt};
    if (selection.updatedAt !== undefined) entry.updatedAt = publicationDate(selection.updatedAt, 'updatedAt');
    entries.push(Object.freeze(entry));
  }
  // Code-unit ordering is locale-independent; do not reorder source documents in place.
  return Object.freeze(entries.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
}
/** Explicit date-only prototype policy retained; not the Rasa request-clock adapter. */
export function compilePublicInventory(siteInput, documents, {asOf} = {}) {
  dateOnly(asOf, 'asOf');
  return projectPublicInventory(siteInput, documents, {selectPublication(doc) {
    const publishedAt = dateOnly(doc.publishedAt, 'publishedAt');
    if (publishedAt > asOf) return null;
    const selection = {publishedAt};
    if (doc.updatedAt !== undefined) {
      selection.updatedAt = dateOnly(doc.updatedAt, 'updatedAt');
      if (selection.updatedAt < publishedAt || selection.updatedAt > asOf) throw new TypeError(`Invalid substantive update date: ${doc.id}`);
    }
    return selection;
  }});
}
