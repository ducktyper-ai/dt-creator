// Pure publication fundamentals. Callers own classifications, schemas and policy.
const schemas = new WeakMap();
const text = (value, name) => {
  if (typeof value !== 'string' || !value.length || value.trim() !== value)
    throw new TypeError(`${name} must be a nonempty trimmed string`);
  return value;
};
const object = (value, name) => {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      ![Object.prototype, null].includes(Object.getPrototypeOf(value)))
    throw new TypeError(`${name} must be plain data`);
  return value;
};
function dataCopy(value, seen = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (!value || typeof value !== 'object' || seen.has(value)) throw new TypeError('Metadata must be finite acyclic plain data');
  if (!Array.isArray(value)) object(value, 'Metadata');
  else for (let index = 0; index < value.length; index++)
    if (!Object.hasOwn(value, index)) throw new TypeError('Sparse metadata arrays are forbidden');
  seen.add(value);
  const copy = Array.isArray(value) ? [] : Object.create(null);
  for (const key of Reflect.ownKeys(value)) {
    if (Array.isArray(value) && key === 'length') continue;
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (typeof key !== 'string' || !descriptor.enumerable || !Object.hasOwn(descriptor, 'value'))
      throw new TypeError('Metadata accessors and hidden properties are forbidden');
    Object.defineProperty(copy, key, {value: dataCopy(descriptor.value, seen), enumerable: true});
  }
  seen.delete(value);
  return Object.freeze(copy);
}
function registry(values, name) {
  if (!Array.isArray(values) || !values.length) throw new TypeError(`${name} must be a nonempty explicit registry`);
  const result = Array.from(values, value => text(value, name));
  if (new Set(result).size !== result.length) throw new TypeError(`${name} must be unique`);
  return Object.freeze(result);
}
export function utcInstant(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value))
    throw new TypeError('Expected an explicit UTC instant');
  const normalized = value.includes('.') ? value : value.replace('Z', '.000Z');
  const instant = new Date(value);
  if (!Number.isFinite(instant.getTime()) || instant.toISOString() !== normalized)
    throw new TypeError('Expected a real UTC instant');
  return value;
}
export function defineSite(input) {
  object(input, 'Site');
  const id = text(input.id, 'Site ID');
  if (!/^[a-z][a-z0-9-]*$/.test(id)) throw new TypeError('Invalid site ID');
  const url = new URL(input.origin);
  if (url.protocol !== 'https:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash)
    throw new TypeError('Expected a credential-free HTTPS origin');
  if (!['always', 'never'].includes(input.trailingSlash)) throw new TypeError('Explicit slash convention required');
  return Object.freeze({id, origin: url.origin, trailingSlash: input.trailingSlash});
}
export function canonicalPath(siteInput, path) {
  const site = defineSite(siteInput);
  text(path, 'Path');
  if (!/^\/[A-Za-z0-9._~/-]*$/.test(path) || path.includes('//') || path.split('/').some(part => part === '.' || part === '..'))
    throw new TypeError('Unsafe or ambiguous path');
  const bare = path === '/' ? '/' : path.replace(/\/$/, '');
  return bare === '/' ? bare : site.trailingSlash === 'always' ? `${bare}/` : bare;
}
/** Explicit caller-owned classifications and validation, with no public/default status. */
export function defineMetadataSchema(input) {
  object(input, 'Schema');
  const kinds = registry(input.kinds, 'Kinds');
  const statuses = registry(input.statuses, 'Statuses');
  const accessLevels = registry(input.accessLevels, 'Access levels');
  if (!statuses.includes(input.publishedStatus) || !accessLevels.includes(input.publicAccess))
    throw new TypeError('Explicit publication/access mapping must belong to declared registries');
  if (typeof input.validateSource !== 'function') throw new TypeError('Explicit source validator required');
  const config = Object.freeze({kinds, statuses, accessLevels,
    publishedStatus: input.publishedStatus, publicAccess: input.publicAccess,
    validateSource: input.validateSource});
  const schema = Object.freeze({kinds, statuses, accessLevels,
    publishedStatus: config.publishedStatus, publicAccess: config.publicAccess});
  schemas.set(schema, config);
  return schema;
}
export function projectPublicInventory(siteInput, documents, options) {
  const site = defineSite(siteInput);
  object(options, 'Options');
  const {schema, now, selectPublication} = options;
  const config = schemas.get(schema);
  if (!config) throw new TypeError('Factory-created metadata schema required');
  if (typeof now !== 'number' || !Number.isFinite(now) || !Number.isFinite(new Date(now).getTime()))
    throw new TypeError('Finite explicit evaluation clock required');
  if (typeof selectPublication !== 'function') throw new TypeError('Explicit publication selector required');
  if (!Array.isArray(documents)) throw new TypeError('Documents must be an array');
  const ids = new Set(), paths = new Set();
  // Complete registration precedes every source-policy/selection callback.
  const registered = Array.from(documents, raw => {
    const doc = dataCopy(object(raw, 'Document'));
    const id = text(doc.id, 'ID');
    if (ids.has(id)) throw new TypeError('Duplicate content ID');
    ids.add(id);
    if (!config.kinds.includes(doc.kind) || !config.statuses.includes(doc.status) || !config.accessLevels.includes(doc.access))
      throw new TypeError('Undeclared classification');
    const path = canonicalPath(site, doc.path);
    if (paths.has(path.toLowerCase())) throw new TypeError('Duplicate registered route');
    paths.add(path.toLowerCase());
    const canonicalUrl = new URL(path, site.origin).href;
    if (doc.canonicalUrl !== undefined && doc.canonicalUrl !== canonicalUrl) throw new TypeError('Canonical differs from site/path');
    const candidate = doc.status === config.publishedStatus && doc.access === config.publicAccess;
    const metadata = {id, kind: doc.kind, status: doc.status, access: doc.access, path,
      title: text(doc.title, 'Title'), summary: text(doc.summary, 'Summary'), canonicalUrl};
    if (candidate) metadata.availableAt = utcInstant(doc.availableAt);
    if (doc.sourceMetadata !== undefined) metadata.sourceMetadata = doc.sourceMetadata;
    return {metadata: Object.freeze(metadata), candidate};
  });
  // All documents receive caller schema validation; invalid hidden documents cannot silently vanish.
  for (const {metadata} of registered)
    if (config.validateSource(metadata) !== true) throw new TypeError('Source schema validation failed');
  const entries = [];
  for (const {metadata, candidate} of registered) {
    if (!candidate) continue;
    const selection = selectPublication(metadata, now);
    if (selection === null) continue;
    const selected = dataCopy(object(selection, 'Publication selection'));
    const available = Date.parse(metadata.availableAt);
    if (available > now) throw new TypeError('Selected publication is unavailable at evaluatedAt');
    // availableAt is the source-derived release instant, never a calendar display label.
    const entry = {id: metadata.id, kind: metadata.kind, path: metadata.path,
      title: metadata.title, summary: metadata.summary, canonicalUrl: metadata.canonicalUrl,
      availableAt: metadata.availableAt};
    if (selected.publishedAt !== undefined) {
      entry.publishedAt = utcInstant(selected.publishedAt);
      if (Date.parse(entry.publishedAt) > now) throw new TypeError('Future publication instant');
    }
    if (selected.updatedAt !== undefined) {
      entry.updatedAt = utcInstant(selected.updatedAt);
      const updated = Date.parse(entry.updatedAt);
      if (updated < available || updated > now || (entry.publishedAt && updated < Date.parse(entry.publishedAt)))
        throw new TypeError('Invalid substantive update bounds');
    }
    entries.push(Object.freeze(entry));
  }
  entries.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  return Object.freeze({evaluatedAt: now, entries: Object.freeze(entries)});
}
