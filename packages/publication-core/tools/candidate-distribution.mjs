// Offline CANDIDATE tooling. This is not part of the pure runtime or an issuing authority.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {constants, closeSync, fstatSync, lstatSync, mkdirSync, mkdtempSync, openSync, readFileSync, realpathSync, rmSync, writeFileSync} from 'node:fs';
import {basename, dirname, isAbsolute, join, relative, resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';

const PACKAGE = 'packages/publication-core';
const LIMIT = 2 * 1024 * 1024;
const TAR_LIMIT = 8 * LIMIT;
const SCHEMA = 'zeocreator.publication-core-candidate/v1';
const utf8 = new TextDecoder('utf-8', {fatal: true});
const digest = (bytes, algorithm = 'sha256', encoding = 'hex') => createHash(algorithm).update(bytes).digest(encoding);
const refuse = (condition, code) => { if (!condition) throw new Error(code); };
const keys = (value, expected) => {
  refuse(value !== null && typeof value === 'object' && !Array.isArray(value), 'invalid_object');
  assert.deepEqual(Object.keys(value).sort(), [...expected].sort(), 'unexpected_fields');
};
const sha = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const commit = value => typeof value === 'string' && /^[0-9a-f]{40}$/.test(value);
const safePath = value => typeof value === 'string' && value.length > 0 && value.length <= 240 &&
  /^[A-Za-z0-9_.\-/]+$/.test(value) && !value.split('/').some(p => !p || p === '.' || p === '..') &&
  !value.startsWith('/') && !value.includes('\\');

// JSON.parse alone accepts duplicate keys. This bounded parser rejects them, including escaped aliases.
export function parseIndex(bytes) {
  refuse(Buffer.isBuffer(bytes) && bytes.length <= LIMIT, 'index_size');
  const text = utf8.decode(bytes);
  let at = 0;
  const space = () => { while (/[ \t\r\n]/.test(text[at] ?? '') && at < text.length) at++; };
  function string() {
    refuse(text[at] === '"', 'json_string');
    const start = at++;
    while (at < text.length) {
      const ch = text[at++];
      if (ch === '\\') { at++; continue; }
      if (ch === '"') return JSON.parse(text.slice(start, at));
    }
    throw new Error('json_truncated');
  }
  function value(depth = 0) {
    refuse(depth <= 16, 'json_depth'); space();
    if (text[at] === '"') return string();
    if (text[at] === '{') {
      at++; space(); const result = Object.create(null); const seen = new Set();
      if (text[at] === '}') { at++; return result; }
      while (at < text.length) {
        space(); const name = string(); refuse(!seen.has(name), 'duplicate_json_key'); seen.add(name);
        space(); refuse(text[at++] === ':', 'json_colon'); result[name] = value(depth + 1); space();
        const end = text[at++]; if (end === '}') return result;
        refuse(end === ',', 'json_comma');
      }
      throw new Error('json_truncated');
    }
    if (text[at] === '[') {
      at++; space(); const result = [];
      if (text[at] === ']') { at++; return result; }
      while (at < text.length) {
        refuse(result.length < 128, 'json_array_size'); result.push(value(depth + 1)); space();
        const end = text[at++]; if (end === ']') return result;
        refuse(end === ',', 'json_comma');
      }
      throw new Error('json_truncated');
    }
    const token = /^(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/.exec(text.slice(at));
    refuse(token, 'json_value'); at += token[0].length; return JSON.parse(token[0]);
  }
  const result = value(); space(); refuse(at === text.length, 'json_trailing'); return result;
}

function regular(path, limit = LIMIT) {
  const absolute = resolve(path);
  let parent = dirname(absolute);
  while (true) {
    refuse(!lstatSync(parent).isSymbolicLink(), 'symlink_ancestor');
    const next = dirname(parent); if (parent === next) break; parent = next;
  }
  // A FIFO must reach the descriptor type check without waiting for a writer.
  const fd = openSync(absolute, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const before = fstatSync(fd, {bigint: true});
    refuse(before.isFile() && before.size <= BigInt(limit), 'regular_file_size');
    const bytes = readFileSync(fd); const after = fstatSync(fd, {bigint: true});
    for (const name of ['dev', 'ino', 'size', 'mtimeNs', 'ctimeNs']) refuse(before[name] === after[name], 'file_changed');
    refuse(BigInt(bytes.length) === before.size, 'file_changed'); return bytes;
  } finally { closeSync(fd); }
}

const git = (repo, ...args) => execFileSync('/usr/bin/git', ['--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', repo, ...args], {
  maxBuffer: TAR_LIMIT, timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'],
  env: {PATH: '/usr/bin:/bin', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0', GIT_NO_REPLACE_OBJECTS: '1'},
});
function blob(repo, source, path) {
  refuse(commit(source) && safePath(path), 'source_provenance');
  const line = git(repo, 'ls-tree', source, '--', path).toString().trim();
  refuse(/^100644 blob [0-9a-f]{40}\t/.test(line) && line.split('\t')[1] === path, 'source_regular_blob');
  const bytes = git(repo, 'show', `${source}:${path}`); refuse(bytes.length <= LIMIT, 'source_size'); return bytes;
}

function requireCommit(repo, source) {
  refuse(commit(source), 'source_commit');
  let peeled;
  try { peeled = git(repo, 'rev-parse', '--verify', `${source}^{commit}`).toString().trim(); }
  catch { throw new Error('source_commit'); }
  refuse(peeled === source, 'source_commit');
}

// Compare the real index, then inspect worktree bytes with private metadata.
// No source repository configuration, filters or submodule process is imported
// into the status operation. Its index is freshly built from the pinned tree,
// so source assume-unchanged/skip-worktree bits cannot conceal modified files.
function cleanSource(repo, source) {
  requireCommit(repo, source);
  refuse(realpathSync(git(repo, 'rev-parse', '--show-toplevel').toString().trim()) === repo, 'source_root');
  const entries = utf8.decode(git(repo, 'ls-tree', '-r', '-z', '--full-tree', source)).split('\0').filter(Boolean);
  const expectedIndex = entries.map(entry => {
    const tab = entry.indexOf('\t');
    const header = /^([0-7]{6}) (blob|commit) ([0-9a-f]{40})$/.exec(entry.slice(0, tab));
    refuse(header && tab > 0, 'source_inventory');
    refuse(header[1] !== '160000' && header[2] === 'blob', 'source_submodule');
    return `${header[1]} ${header[3]} 0\t${entry.slice(tab + 1)}\0`;
  }).join('');
  refuse(git(repo, 'ls-files', '--stage', '-z').equals(Buffer.from(expectedIndex)), 'source_dirty');
  const objects = git(repo, 'rev-parse', '--path-format=absolute', '--git-path', 'objects').toString().trim();
  const metadata = mkdtempSync(join(realpathSync(tmpdir()), 'core-candidate-git-'));
  try {
    mkdirSync(join(metadata, 'objects')); mkdirSync(join(metadata, 'refs'));
    writeFileSync(join(metadata, 'HEAD'), `${source}\n`, {flag: 'wx'});
    writeFileSync(join(metadata, 'config'), '[core]\nrepositoryformatversion = 0\nbare = false\n', {flag: 'wx'});
    const inspect = (...args) => execFileSync('/usr/bin/git', ['--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-c', 'core.attributesFile=/dev/null', ...args], {
      maxBuffer: TAR_LIMIT, timeout: 10000, stdio: ['pipe', 'pipe', 'pipe'],
      env: {PATH: '/usr/bin:/bin', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0', GIT_NO_REPLACE_OBJECTS: '1',
        GIT_DIR: metadata, GIT_WORK_TREE: repo, GIT_OBJECT_DIRECTORY: objects},
    });
    inspect('read-tree', source);
    refuse(inspect('status', '--porcelain', '--untracked-files=normal', '--ignore-submodules=all').length === 0, 'source_dirty');
  } finally { rmSync(metadata, {recursive: true, force: true}); }
}

function packageInputs(repo, source) {
  requireCommit(repo, source);
  const metadata = blob(repo, source, `${PACKAGE}/package.json`);
  const manifest = parseIndex(metadata);
  refuse(typeof manifest.name === 'string' && /^@[a-z0-9-]+\/[a-z0-9-]+$/.test(manifest.name), 'package_name');
  refuse(typeof manifest.version === 'string' && /^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.-]+)?$/.test(manifest.version), 'package_version');
  refuse(manifest.private === true && manifest.dependencies === undefined && manifest.devDependencies === undefined && manifest.bundleDependencies === undefined && manifest.bundledDependencies === undefined, 'candidate_private_dependency_free');
  refuse(Array.isArray(manifest.files) && manifest.files.length > 0 && manifest.files.length <= 32, 'package_files');
  const names = ['package.json', ...manifest.files];
  refuse(new Set(names).size === names.length && names.every(safePath), 'package_files');
  // v1 deliberately supports literal regular-file selections only, not glob/directory expansion.
  const inputs = new Map(names.map(name => [name, blob(repo, source, `${PACKAGE}/${name}`)]));
  // npm forcibly includes root readme/copying/license files even when omitted from files.
  for (const name of git(repo, 'ls-tree', '--name-only', source, `${PACKAGE}/`).toString().trim().split('\n')) {
    const local = name.slice(PACKAGE.length + 1);
    if (/^(?:readme|copying|licen[cs]e)(?:\.[A-Za-z0-9_.-]+)?$/i.test(local) && !inputs.has(local))
      inputs.set(local, blob(repo, source, name));
  }
  return {manifest, inputs};
}

function licenseInput(repo, source, value) {
  if (value === null) return null;
  keys(value, ['sourcePath', 'sourceCommit', 'sha256']);
  refuse(value.sourceCommit === source && safePath(value.sourcePath) && !value.sourcePath.includes('/') && sha(value.sha256), 'license_provenance');
  refuse(/^licen[cs]e(?:\.[A-Za-z0-9_.-]+)?$/i.test(value.sourcePath), 'license_path');
  const bytes = blob(repo, source, value.sourcePath);
  refuse(digest(bytes) === value.sha256, 'license_provenance');
  return {bytes, provenance: {sourcePath: value.sourcePath, sourceCommit: source, sha256: value.sha256, memberPath: 'LICENSE'}};
}

function octal(buffer) {
  const text = buffer.toString('ascii').replace(/\0.*$/s, '').trim();
  refuse(/^[0-7]+$/.test(text), 'tar_number'); const result = Number.parseInt(text, 8);
  refuse(Number.isSafeInteger(result), 'tar_number'); return result;
}
function cstring(buffer) {
  const zero = buffer.indexOf(0);
  if (zero !== -1) refuse(buffer.subarray(zero).every(byte => byte === 0), 'tar_string_padding');
  return utf8.decode(zero === -1 ? buffer : buffer.subarray(0, zero));
}

export function archiveMembers(archive) {
  refuse(Buffer.isBuffer(archive) && archive.length > 0 && archive.length <= LIMIT, 'archive_size');
  const tar = gunzipSync(archive, {maxOutputLength: TAR_LIMIT});
  refuse(tar.length % 512 === 0, 'tar_length');
  const members = new Map(); let offset = 0;
  while (offset + 512 <= tar.length) {
    const header = tar.subarray(offset, offset + 512);
    if (header.every(byte => byte === 0)) {
      refuse(tar.length - offset >= 1024 && tar.subarray(offset).every(byte => byte === 0), 'tar_trailing');
      refuse(members.size > 0, 'tar_empty'); return members;
    }
    refuse(members.size < 64, 'tar_member_count');
    const checksum = [...header].reduce((sum, byte, i) => sum + (i >= 148 && i < 156 ? 32 : byte), 0);
    refuse(octal(header.subarray(148, 156)) === checksum, 'tar_checksum');
    refuse(header[156] === 0 || header[156] === 48, 'tar_regular_only');
    refuse(cstring(header.subarray(157, 257)) === '', 'tar_link');
    refuse(header.subarray(257, 263).toString('ascii') === 'ustar\0' && header.subarray(263, 265).toString('ascii') === '00', 'tar_format');
    const prefix = cstring(header.subarray(345, 500));
    const path = `${prefix ? `${prefix}/` : ''}${cstring(header.subarray(0, 100))}`;
    refuse(path.startsWith('package/') && safePath(path), 'tar_path');
    const name = path.slice(8); refuse(safePath(name) && !members.has(name), 'tar_duplicate_path');
    const mode = octal(header.subarray(100, 108)); refuse((mode & ~0o777) === 0 && !(mode & 0o111), 'tar_mode');
    const size = octal(header.subarray(124, 136)); refuse(size <= LIMIT, 'tar_member_size');
    const end = offset + 512 + size; const next = offset + 512 + Math.ceil(size / 512) * 512;
    refuse(next <= tar.length && tar.subarray(end, next).every(byte => byte === 0), 'tar_member_padding');
    members.set(name, Buffer.from(tar.subarray(offset + 512, end))); offset = next;
  }
  throw new Error('tar_terminator');
}

function inventory(members) {
  return [...members].sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([path, bytes]) => ({path, size: bytes.length, sha256: digest(bytes)}));
}
function expectedInputs(repo, source, license) {
  const {manifest, inputs} = packageInputs(repo, source);
  const extra = licenseInput(repo, source, license);
  if (extra) { refuse(!inputs.has('LICENSE'), 'license_collision'); inputs.set('LICENSE', extra.bytes); }
  return {manifest, inputs, license: extra?.provenance ?? null};
}

export function verifyCandidate({repo, source, archive, index}) {
  refuse(commit(source), 'source_commit');
  refuse(Buffer.isBuffer(archive) && archive.length > 0 && archive.length <= LIMIT, 'archive_size');
  const document = parseIndex(index);
  keys(document, ['schema', 'candidate', 'label', 'source', 'package', 'archive', 'members', 'license']);
  refuse(document.schema === SCHEMA && document.candidate === true && document.label === 'CANDIDATE', 'candidate_label');
  keys(document.source, ['commit', 'packagePath']);
  refuse(document.source.commit === source && document.source.packagePath === PACKAGE, 'source_provenance');
  let license = null;
  if (document.license !== null) {
    keys(document.license, ['sourcePath', 'sourceCommit', 'sha256', 'memberPath']);
    refuse(document.license.memberPath === 'LICENSE', 'license_path');
    license = {sourcePath: document.license.sourcePath, sourceCommit: document.license.sourceCommit, sha256: document.license.sha256};
  }
  const expected = expectedInputs(repo, source, license);
  keys(document.package, ['name', 'version', 'private']);
  refuse(document.package.name === expected.manifest.name && document.package.version === expected.manifest.version && document.package.private === true, 'package_identity');
  keys(document.archive, ['size', 'sha256', 'integrity']);
  refuse(document.archive.size === archive.length && document.archive.sha256 === digest(archive) && document.archive.integrity === `sha512-${digest(archive, 'sha512', 'base64')}`, 'archive_integrity');
  const members = archiveMembers(archive);
  refuse(Array.isArray(document.members) && document.members.length > 0 && document.members.length <= 64, 'member_inventory');
  for (const member of document.members) {
    keys(member, ['path', 'size', 'sha256']);
    refuse(safePath(member.path) && Number.isSafeInteger(member.size) && member.size >= 0 && sha(member.sha256), 'member_inventory');
  }
  // Convert to ordinary JSON objects after duplicate-key checking before deep comparisons.
  assert.deepEqual(JSON.parse(JSON.stringify(document.members)), inventory(members), 'archive_inventory');
  assert.deepEqual(inventory(members), inventory(expected.inputs), 'source_member_inventory');
  for (const [name, bytes] of members) refuse(bytes.equals(expected.inputs.get(name)), 'source_member_bytes');
  return {ok: true, schema: SCHEMA, candidate: true, label: 'CANDIDATE', sourceCommit: source, members: members.size, archiveSha256: digest(archive)};
}

// realpath may preserve supplied casing on a case-insensitive filesystem.
// Compare actual directory identity along the output's ancestor chain too.
function refusePhysicalSourceOutput(repo, output) {
  const source = lstatSync(repo, {bigint: true});
  let path = output;
  while (true) {
    let entry;
    try { entry = lstatSync(path, {bigint: true}); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    refuse(!entry || entry.dev !== source.dev || entry.ino !== source.ino, 'output_inside_source');
    const parent = dirname(path); if (parent === path) break; path = parent;
  }
}

export function buildCandidate({repo, source, out, npmCli, rootLicense = null}) {
  repo = realpathSync(repo); out = resolve(out); npmCli = resolve(npmCli);
  refuse(commit(source) && git(repo, 'rev-parse', 'HEAD').toString().trim() === source, 'source_head');
  cleanSource(repo, source);
  const parent = realpathSync(dirname(out));
  let physicalOutput = join(parent, basename(out));
  try { physicalOutput = realpathSync(out); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  refusePhysicalSourceOutput(repo, physicalOutput);
  const outputRelative = relative(repo, physicalOutput);
  refuse(isAbsolute(outputRelative) || outputRelative === '..' || outputRelative.startsWith('../'), 'output_inside_source');
  refuse(parent === dirname(out), 'output_symlink_ancestor');
  regular(npmCli);
  const expected = expectedInputs(repo, source, rootLicense);
  mkdirSync(out); // Refuse existing output, rather than overwrite someone else's candidate.
  const scratch = mkdtempSync(join(out, 'scratch-'));
  try {
    const stage = join(scratch, 'package'); mkdirSync(stage);
    for (const [path, bytes] of expected.inputs) { mkdirSync(dirname(join(stage, path)), {recursive: true}); writeFileSync(join(stage, path), bytes, {flag: 'wx', mode: 0o644}); }
    const home = join(scratch, 'home'); mkdirSync(home);
    const cache = join(scratch, 'cache'); mkdirSync(cache);
    const tmp = join(scratch, 'tmp'); mkdirSync(tmp);
    const env = {PATH: '/usr/bin:/bin', HOME: home, TMPDIR: tmp, XDG_CONFIG_HOME: home, XDG_CACHE_HOME: cache,
      npm_config_cache: cache, npm_config_userconfig: join(home, 'absent-npmrc'), npm_config_globalconfig: join(home, 'absent-global-npmrc'),
      npm_config_offline: 'true', npm_config_ignore_scripts: 'true', npm_config_audit: 'false', npm_config_fund: 'false',
      UV_THREADPOOL_SIZE: '1'};
    const raw = execFileSync(process.execPath, ['--max-old-space-size=128', '--v8-pool-size=1', npmCli, 'pack', '--offline', '--ignore-scripts', '--json', '--pack-destination', scratch], {cwd: stage, env, timeout: 30000, maxBuffer: LIMIT});
    const report = parseIndex(raw); refuse(Array.isArray(report) && report.length === 1, 'pack_report');
    const packed = report[0]; refuse(safePath(packed.filename) && !packed.filename.includes('/'), 'pack_filename');
    const archive = regular(join(scratch, packed.filename)); const members = archiveMembers(archive);
    refuse(Array.isArray(packed.files), 'pack_inventory');
    assert.deepEqual(packed.files.map(item => ({path: item.path, size: item.size})).sort((a, b) => a.path < b.path ? -1 : 1), inventory(members).map(({path, size}) => ({path, size})), 'pack_inventory');
    const document = {schema: SCHEMA, candidate: true, label: 'CANDIDATE', source: {commit: source, packagePath: PACKAGE},
      package: {name: expected.manifest.name, version: expected.manifest.version, private: true},
      archive: {size: archive.length, sha256: digest(archive), integrity: `sha512-${digest(archive, 'sha512', 'base64')}`},
      members: inventory(members), license: expected.license};
    const index = Buffer.from(`${JSON.stringify(document, null, 2)}\n`);
    const result = verifyCandidate({repo, source, archive, index});
    writeFileSync(join(out, 'candidate.tgz'), archive, {flag: 'wx', mode: 0o600});
    writeFileSync(join(out, 'candidate-index.json'), index, {flag: 'wx', mode: 0o600});
    return result;
  } finally { rmSync(scratch, {recursive: true, force: true}); }
}

function main(args) {
  const [command, ...options] = args; const flags = new Map();
  for (let i = 0; i < options.length; i += 2) {
    refuse(options[i]?.startsWith('--') && options[i + 1] && !flags.has(options[i]), 'arguments'); flags.set(options[i], options[i + 1]);
  }
  const allowed = command === 'build' ? ['--repo', '--source', '--out', '--npm-cli', '--root-license-provenance'] : ['--repo', '--source', '--archive', '--index'];
  refuse(command === 'build' || command === 'verify', 'command');
  refuse([...flags.keys()].every(key => allowed.includes(key)) && allowed.filter(key => key !== '--root-license-provenance').every(key => flags.has(key)), 'arguments');
  if (command === 'build') return buildCandidate({repo: flags.get('--repo'), source: flags.get('--source'), out: flags.get('--out'), npmCli: flags.get('--npm-cli'), rootLicense: flags.has('--root-license-provenance') ? parseIndex(regular(flags.get('--root-license-provenance'))) : null});
  return verifyCandidate({repo: flags.get('--repo'), source: flags.get('--source'), archive: regular(flags.get('--archive')), index: regular(flags.get('--index'))});
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { console.log(JSON.stringify(main(process.argv.slice(2)))); }
  catch { console.log(JSON.stringify({ok: false, schema: SCHEMA, candidate: true, label: 'CANDIDATE', reason: 'candidate_refused'})); process.exitCode = 20; }
}
