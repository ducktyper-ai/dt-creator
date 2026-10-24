import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync, spawnSync} from 'node:child_process';
import {chmodSync, cpSync, existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, symlinkSync, utimesSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {gzipSync, gunzipSync} from 'node:zlib';
import {archiveMembers, buildCandidate, parseIndex, verifyCandidate} from '../tools/candidate-distribution.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
// Use npm bundled with the currently admitted Node, never PATH or a downloaded package.
const npmCli = join(dirname(process.execPath), '../lib/node_modules/npm/bin/npm-cli.js');
const sha = data => createHash('sha256').update(data).digest('hex');
function command(program, args, cwd, home) {
  if (program === process.execPath) args = ['--max-old-space-size=128', '--v8-pool-size=1', ...args];
  return execFileSync(program, args, {cwd, timeout: 30000, maxBuffer: 2 * 1024 * 1024,
    env: {PATH: '/usr/bin:/bin', HOME: home, TMPDIR: home, XDG_CONFIG_HOME: home, XDG_CACHE_HOME: home,
      npm_config_cache: join(home, 'cache'), npm_config_offline: 'true', npm_config_ignore_scripts: 'true',
      npm_config_userconfig: join(home, 'absent-npmrc'), npm_config_globalconfig: join(home, 'absent-global-npmrc'),
      npm_config_audit: 'false', npm_config_fund: 'false', GIT_CONFIG_NOSYSTEM: '1', UV_THREADPOOL_SIZE: '1'}});
}
function fixture(t, {lifecycle = false, tempRoot = tmpdir()} = {}) {
  const created = mkdtempSync(join(tempRoot, 'core-candidate-test-'));
  t.after(() => rmSync(created, {recursive: true, force: true}));
  const work = realpathSync(created);
  const repo = join(work, 'source'); mkdirSync(repo);
  const pkg = join(repo, 'packages/publication-core'); mkdirSync(pkg, {recursive: true});
  const manifest = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  for (const file of ['package.json', ...manifest.files]) {
    mkdirSync(dirname(join(pkg, file)), {recursive: true}); cpSync(join(root, file), join(pkg, file));
  }
  if (lifecycle) {
    const script = `${process.execPath} -e 'require("node:fs").writeFileSync(${JSON.stringify(join(work, 'LIFECYCLE_RAN'))}, "unexpected")'`;
    manifest.scripts = {prepack: script, prepare: script, postpack: script, preinstall: script, install: script, postinstall: script};
    writeFileSync(join(pkg, 'package.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  }
  // A root license exists to prove it does not leak into a default npm pack.
  writeFileSync(join(repo, 'LICENSE'), 'SYNTHETIC LICENSE INPUT\n');
  command('/usr/bin/git', ['init', '-q', repo], work, work);
  command('/usr/bin/git', ['add', '.'], repo, work);
  command('/usr/bin/git', ['-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic package input\n\nsow: zeroemployee-SOW-180'], repo, work);
  const source = command('/usr/bin/git', ['rev-parse', 'HEAD'], repo, work).toString().trim();
  return {work, repo, source, out: join(work, 'candidate'), npmCli};
}
function built(t, options = {}) {
  const f = fixture(t); const result = buildCandidate({...f, ...options});
  const archive = readFileSync(join(f.out, 'candidate.tgz'));
  const index = readFileSync(join(f.out, 'candidate-index.json'));
  return {...f, result, archive, index};
}
const encoded = value => Buffer.from(JSON.stringify(value));
function reindex(index, archive) {
  const document = JSON.parse(index);
  document.archive = {size: archive.length, sha256: sha(archive), integrity: `sha512-${createHash('sha512').update(archive).digest('base64')}`};
  return encoded(document);
}
function checksum(tar, offset = 0) {
  tar.fill(32, offset + 148, offset + 156);
  const sum = [...tar.subarray(offset, offset + 512)].reduce((total, byte) => total + byte, 0);
  tar.write(`${sum.toString(8).padStart(6, '0')}\0 `, offset + 148, 8, 'ascii');
}
function rewrite(f, modify) {
  const tar = Buffer.from(gunzipSync(f.archive)); modify(tar); return gzipSync(tar);
}

test('CANDIDATE pack/index verifies exact Git members and installs/imports offline', t => {
  const f = built(t);
  assert.equal(f.result.label, 'CANDIDATE'); assert.equal(f.result.candidate, true);
  const document = JSON.parse(f.index);
  const manifest = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
  assert.deepEqual(document.members.map(item => item.path).sort(), ['package.json', ...manifest.files].sort());
  assert.equal(document.license, null); assert.ok(!archiveMembers(f.archive).has('LICENSE'));
  assert.equal(document.source.commit, f.source);
  assert.equal(verifyCandidate(f).archiveSha256, sha(f.archive));
  const consumer = join(f.work, 'consumer'); mkdirSync(consumer);
  const home = join(f.work, 'consumer-home'); mkdirSync(home);
  writeFileSync(join(consumer, 'package.json'), '{"private":true,"type":"module"}\n');
  command(process.execPath, [npmCli, 'install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund', '--no-save', '--package-lock=false', join(f.out, 'candidate.tgz')], consumer, home);
  const smoke = command(process.execPath, ['--input-type=module', '-e', "import assert from 'node:assert/strict'; import {canonicalPath,defineSite} from '@zeroemployeeorg/publication-core'; const site=defineSite({id:'synthetic',origin:'https://example.invalid',trailingSlash:'never'}); assert.equal(canonicalPath(site,'/entry'),'/entry'); assert.equal(site.origin,'https://example.invalid'); console.log('OFFLINE_CANDIDATE_IMPORT_OK')"], consumer, home).toString();
  assert.match(smoke, /OFFLINE_CANDIDATE_IMPORT_OK/);
  const installed = join(consumer, 'node_modules', ...manifest.name.split('/'));
  for (const member of document.members) assert.equal(sha(readFileSync(join(installed, member.path))), member.sha256);
});

test('default-off root LICENSE capability requires exact recorded source provenance', t => {
  const f = fixture(t); const license = readFileSync(join(f.repo, 'LICENSE'));
  buildCandidate({...f, rootLicense: {sourcePath: 'LICENSE', sourceCommit: f.source, sha256: sha(license)}});
  const archive = readFileSync(join(f.out, 'candidate.tgz')); const index = readFileSync(join(f.out, 'candidate-index.json'));
  assert.equal(archiveMembers(archive).get('LICENSE').toString(), 'SYNTHETIC LICENSE INPUT\n');
  assert.equal(verifyCandidate({...f, archive, index}).candidate, true);
  const wrong = {...f, out: join(f.work, 'wrong'), rootLicense: {sourcePath: 'LICENSE', sourceCommit: f.source, sha256: '0'.repeat(64)}};
  assert.throws(() => buildCandidate(wrong), /license_provenance/);
});

test('pack and offline consumer installation never execute package lifecycle hooks', t => {
  const f = fixture(t, {lifecycle: true}); buildCandidate(f);
  const consumer = join(f.work, 'consumer'); mkdirSync(consumer);
  const home = join(f.work, 'consumer-home'); mkdirSync(home);
  writeFileSync(join(consumer, 'package.json'), '{"private":true}\n');
  command(process.execPath, [npmCli, 'install', '--offline', '--ignore-scripts', '--no-audit', '--no-fund', '--no-save', '--package-lock=false', join(f.out, 'candidate.tgz')], consumer, home);
  assert.equal(existsSync(join(f.work, 'LIFECYCLE_RAN')), false, 'lifecycle hooks must remain disabled');
});

test('package npmrc inputs refuse before npm execution', t => {
  for (const name of ['.npmrc', 'config/.npmrc', '.NPMRC']) {
    const f = fixture(t);
    const pkg = join(f.repo, 'packages/publication-core');
    const manifest = JSON.parse(readFileSync(join(pkg, 'package.json'), 'utf8'));
    manifest.files.push(name);
    writeFileSync(join(pkg, 'package.json'), JSON.stringify(manifest));
    mkdirSync(dirname(join(pkg, name)), {recursive: true});
    writeFileSync(join(pkg, name), 'workspaces=true\n');
    command('/usr/bin/git', ['add', '.'], f.repo, f.work);
    command('/usr/bin/git', ['-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid',
      '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic npmrc input\n\nsow: zeroemployee-SOW-180'], f.repo, f.work);
    f.source = command('/usr/bin/git', ['rev-parse', 'HEAD'], f.repo, f.work).toString().trim();
    const marker = join(f.work, 'NPM_INVOKED');
    const recorder = join(f.work, 'recorder.mjs');
    writeFileSync(recorder, `import {writeFileSync} from 'node:fs'; writeFileSync(${JSON.stringify(marker)}, 'invoked');`);
    assert.throws(() => buildCandidate({...f, npmCli: recorder}), /package_npmrc/, 'NPMRC_INPUT_GUARD');
    assert.equal(existsSync(marker), false, 'NPMRC_REFUSED_BEFORE_EXECUTION');
  }
});

test('npm failures keep child diagnostics out of public CLI output', t => {
  const f = fixture(t);
  const recorder = join(f.work, 'failing-npm.mjs');
  writeFileSync(recorder, "process.stdout.write('PRIVATE_NPM_STDOUT'); process.stderr.write('PRIVATE_NPM_STDERR'); process.exit(23);\n");
  const result = spawnSync(process.execPath, ['--max-old-space-size=128', '--v8-pool-size=1',
    join(root, 'tools/candidate-distribution.mjs'), 'build', '--repo', f.repo, '--source', f.source,
    '--out', f.out, '--npm-cli', recorder], {
    cwd: f.work, timeout: 10000, killSignal: 'SIGKILL', maxBuffer: 2 * 1024 * 1024, encoding: 'utf8',
    env: {PATH: '/usr/bin:/bin', HOME: f.work, TMPDIR: f.work, GIT_CONFIG_NOSYSTEM: '1', UV_THREADPOOL_SIZE: '1'},
  });
  assert.equal(result.error, undefined);
  assert.equal(result.status, 20);
  assert.deepEqual(JSON.parse(result.stdout), {ok: false, schema: 'zeocreator.publication-core-candidate/v1',
    candidate: true, label: 'CANDIDATE', reason: 'candidate_refused'});
  assert.equal(result.stderr, '', 'NPM_DIAGNOSTICS_NOT_PUBLIC');
});

test('CLI verification returns CANDIDATE JSON and refuses duplicate arguments without echoing input', t => {
  const f = built(t); const tool = join(root, 'tools/candidate-distribution.mjs');
  const raw = command(process.execPath, [tool, 'verify', '--repo', f.repo, '--source', f.source, '--archive', join(f.out, 'candidate.tgz'), '--index', join(f.out, 'candidate-index.json')], f.work, f.work);
  assert.equal(JSON.parse(raw).label, 'CANDIDATE');
  try {
    command(process.execPath, [tool, 'verify', '--repo', 'SYNTHETIC_PRIVATE_SENTINEL', '--repo', f.repo], f.work, f.work);
    assert.fail('duplicate argument must refuse');
  } catch (error) {
    assert.equal(error.status, 20);
    const text = error.stdout.toString(); assert.ok(!text.includes('SYNTHETIC_PRIVATE_SENTINEL'));
    assert.deepEqual(JSON.parse(text), {ok: false, schema: 'zeocreator.publication-core-candidate/v1', candidate: true, label: 'CANDIDATE', reason: 'candidate_refused'});
  }
});

test('FIFO inputs refuse before reads and preserve the regular-file CLI positive', t => {
  const f = built(t);
  const tool = join(root, 'tools/candidate-distribution.mjs');
  const fifo = join(f.work, 'PRIVATE_FIFO_INPUT');
  command('/usr/bin/mkfifo', [fifo], f.work, f.work);
  assert.equal(lstatSync(fifo).isFIFO(), true);
  const run = args => spawnSync(process.execPath, ['--max-old-space-size=128', '--v8-pool-size=1', ...args], {
    cwd: f.work, timeout: 5000, killSignal: 'SIGKILL', maxBuffer: 2 * 1024 * 1024, encoding: 'utf8',
    env: {PATH: '/usr/bin:/bin', HOME: f.work, TMPDIR: f.work, XDG_CONFIG_HOME: f.work,
      XDG_CACHE_HOME: f.work, GIT_CONFIG_NOSYSTEM: '1', UV_THREADPOOL_SIZE: '1'},
  });
  // Instrument only the isolated child: a removed type guard fails a named
  // assertion before a FIFO read, rather than earning a timeout as a mutant kill.
  const guard = run(['--input-type=module', '-e', `
    import assert from 'node:assert/strict';
    import fs from 'node:fs';
    import {syncBuiltinESMExports} from 'node:module';
    const read = fs.readFileSync, close = fs.closeSync;
    let fifoReads = 0, fifoCloses = 0;
    fs.readFileSync = function(fd, ...args) {
      if (typeof fd === 'number' && fs.fstatSync(fd).isFIFO()) {
        fifoReads++; throw new Error('CREATOR42_FIFO_READ_REACHED');
      }
      return read.call(this, fd, ...args);
    };
    fs.closeSync = function(fd) {
      if (fs.fstatSync(fd).isFIFO()) fifoCloses++;
      return close.call(this, fd);
    };
    syncBuiltinESMExports();
    const {buildCandidate} = await import(${JSON.stringify(tool)});
    assert.throws(() => buildCandidate(${JSON.stringify({repo: f.repo, source: f.source, out: join(f.work, 'guard-out'), npmCli: fifo})}),
      error => error.message === 'regular_file_size', 'CREATOR42_FIFO_TYPE_GUARD');
    assert.equal(fifoReads, 0, 'CREATOR42_FIFO_NO_READ');
    assert.equal(fifoCloses, 1, 'CREATOR42_FIFO_DESCRIPTOR_CLOSED');
  `]);
  assert.equal(guard.error, undefined, 'CREATOR42_FIFO_NONBLOCK: child must finish before its deadline');
  assert.equal(guard.status, 0, `CREATOR42_FIFO_TYPE_GUARD: ${guard.stderr}`);
  const verify = [tool, 'verify', '--repo', f.repo, '--source', f.source,
    '--archive', join(f.out, 'candidate.tgz'), '--index', join(f.out, 'candidate-index.json')];
  const positive = run(verify);
  assert.equal(positive.error, undefined);
  assert.equal(positive.status, 0, positive.stderr);
  assert.equal(JSON.parse(positive.stdout).candidate, true);
  const cases = [
    verify.map(value => value === join(f.out, 'candidate.tgz') ? fifo : value),
    verify.map(value => value === join(f.out, 'candidate-index.json') ? fifo : value),
    [tool, 'build', '--repo', f.repo, '--source', f.source, '--out', join(f.work, 'npm-out'), '--npm-cli', fifo],
    [tool, 'build', '--repo', f.repo, '--source', f.source, '--out', join(f.work, 'license-out'),
      '--npm-cli', npmCli, '--root-license-provenance', fifo],
  ];
  for (const args of cases) {
    const result = run(args);
    assert.equal(result.error, undefined, 'CREATOR42_FIFO_NONBLOCK: CLI must finish before its deadline');
    assert.equal(result.status, 20, result.stderr);
    assert.deepEqual(JSON.parse(result.stdout), {ok: false, schema: 'zeocreator.publication-core-candidate/v1',
      candidate: true, label: 'CANDIDATE', reason: 'candidate_refused'});
    assert.equal(result.stdout.includes(fifo), false);
  }
});

test('Git replacement refs cannot alter source provenance and configured fsmonitor does not run', t => {
  const f = fixture(t);
  const original = readFileSync(join(f.repo, 'packages/publication-core/README.md'));
  const originalObject = command('/usr/bin/git', ['rev-parse', `${f.source}:packages/publication-core/README.md`], f.repo, f.work).toString().trim();
  const replacement = join(f.work, 'replacement.txt'); writeFileSync(replacement, 'SYNTHETIC REPLACEMENT PAYLOAD\n');
  const replacementObject = command('/usr/bin/git', ['hash-object', '-w', replacement], f.repo, f.work).toString().trim();
  command('/usr/bin/git', ['replace', originalObject, replacementObject], f.repo, f.work);
  assert.equal(command('/usr/bin/git', ['show', `${f.source}:packages/publication-core/README.md`], f.repo, f.work).toString(), 'SYNTHETIC REPLACEMENT PAYLOAD\n');
  const marker = join(f.work, 'FSMONITOR_RAN'); const monitor = join(f.work, 'fsmonitor');
  writeFileSync(monitor, `#!/bin/sh\n/usr/bin/touch '${marker}'\nprintf 'token\\000'\n`); chmodSync(monitor, 0o700);
  command('/usr/bin/git', ['config', 'core.fsmonitor', monitor], f.repo, f.work);
  command('/usr/bin/git', ['status', '--porcelain'], f.repo, f.work);
  assert.equal(existsSync(marker), true, 'positive control: configured monitor is executable'); rmSync(marker);
  buildCandidate(f);
  assert.equal(existsSync(marker), false, 'candidate reader must disable configured fsmonitor');
  const members = archiveMembers(readFileSync(join(f.out, 'candidate.tgz')));
  assert.ok(members.get('README.md').equals(original), 'candidate uses actual committed blob, not a replacement ref');
});

test('index rejects duplicate keys including escaped aliases, truncation and trailing data', () => {
  for (const text of ['{"x":1,"x":2}', '{"x":1,"\\u0078":2}', '{"a":{"x":1,"x":2}}']) assert.throws(() => parseIndex(Buffer.from(text)), /duplicate_json_key/);
  for (const text of ['{', '[1,', '{"x":1,}', '{"x":01}', '{"x":"unterminated}', '{}{}']) assert.throws(() => parseIndex(Buffer.from(text)));
  assert.throws(() => parseIndex(Buffer.from([0xff])), /encoded data/);
});

test('wrong source/version/identity/label, missing/extra fields and invalid member data refuse', t => {
  const f = built(t);
  const changes = [
    doc => { doc.candidate = false; }, doc => { doc.label = 'RELEASE'; },
    doc => { doc.source.commit = '0'.repeat(40); }, doc => { doc.source.packagePath = '../escape'; },
    doc => { doc.package.name = '@wrong/core'; }, doc => { doc.package.version = '99.0.0'; }, doc => { doc.package.private = false; },
    doc => { doc.extra = true; }, doc => { delete doc.archive.integrity; },
    doc => { doc.members[0].path = '../escape'; }, doc => { doc.members[0].size = -1; }, doc => { doc.members[0].sha256 = 'bad'; },
    doc => { doc.members.push(doc.members[0]); }, doc => { doc.members.pop(); },
    doc => { doc.license = {sourcePath: 'LICENSE', sourceCommit: f.source, sha256: '0'.repeat(64), memberPath: 'LICENSE'}; },
  ];
  for (const change of changes) { const document = JSON.parse(f.index); change(document); assert.throws(() => verifyCandidate({...f, index: encoded(document)})); }
  assert.throws(() => verifyCandidate({...f, source: 'f'.repeat(40)}), /source_provenance/);
});

test('archive hash and integrity are independently required', t => {
  const f = built(t);
  for (const field of ['sha256', 'integrity', 'size']) {
    const doc = JSON.parse(f.index); doc.archive[field] = field === 'size' ? f.archive.length + 1 : 'wrong';
    assert.throws(() => verifyCandidate({...f, index: encoded(doc)}), /archive_integrity/);
  }
  assert.throws(() => verifyCandidate({...f, archive: f.archive.subarray(0, -5)}), /archive_integrity/);
});

test('self-consistent index cannot bless altered source payload bytes', t => {
  const f = built(t);
  const archive = rewrite(f, tar => { tar[512] ^= 1; });
  const doc = JSON.parse(reindex(f.index, archive));
  doc.members = [...archiveMembers(archive)].sort(([a], [b]) => a < b ? -1 : 1).map(([path, bytes]) => ({path, size: bytes.length, sha256: sha(bytes)}));
  assert.throws(() => verifyCandidate({...f, archive, index: encoded(doc)}), /source_member_inventory|source_member_bytes/);
});

test('strict tgz parser refuses traversal, links, duplicates, invalid headers and trailing members', t => {
  const f = built(t);
  const mutations = [
    tar => { tar.fill(0, 0, 100); tar.write('package/../escape', 0); checksum(tar); },
    tar => { tar[156] = 50; tar.write('elsewhere', 157); checksum(tar); },
    tar => { tar[156] = 49; checksum(tar); },
    tar => { tar[156] = 120; checksum(tar); },
    tar => { tar[257] = 0; checksum(tar); },
    tar => { tar[0] ^= 1; },
    tar => { tar.write('0000755\0', 100, 8, 'ascii'); checksum(tar); },
    tar => { tar[tar.length - 1] = 1; },
  ];
  for (const mutate of mutations) assert.throws(() => archiveMembers(rewrite(f, mutate)));
  const tar = gunzipSync(f.archive); const size = Number.parseInt(tar.subarray(124, 136).toString().replace(/\0.*$/s, '').trim(), 8);
  const first = tar.subarray(0, 512 + Math.ceil(size / 512) * 512);
  assert.throws(() => archiveMembers(gzipSync(Buffer.concat([first, tar]))), /tar_duplicate_path/);
  assert.throws(() => archiveMembers(gzipSync(tar.subarray(0, -1024))));
});

test('missing or extra valid tar member refuses against source inventory', t => {
  const f = built(t); const tar = gunzipSync(f.archive);
  const size = Number.parseInt(tar.subarray(124, 136).toString().replace(/\0.*$/s, '').trim(), 8);
  const offset = 512 + Math.ceil(size / 512) * 512;
  const missing = gzipSync(tar.subarray(offset));
  const first = Buffer.from(tar.subarray(0, offset)); first.fill(0, 0, 100); first.write('package/EXTRA.txt'); checksum(first);
  const extra = gzipSync(Buffer.concat([first, tar]));
  for (const archive of [missing, extra]) {
    const doc = JSON.parse(reindex(f.index, archive));
    doc.members = [...archiveMembers(archive)].sort(([a], [b]) => a < b ? -1 : 1).map(([path, bytes]) => ({path, size: bytes.length, sha256: sha(bytes)}));
    assert.throws(() => verifyCandidate({...f, archive, index: encoded(doc)}), /source_member_inventory/);
  }
});

test('dirty source, existing output, output in source, symlink input and invalid license refuse', t => {
  const f = fixture(t);
  assert.throws(() => buildCandidate({...f, source: '0'.repeat(40)}), /source_head/);
  assert.throws(() => buildCandidate({...f, out: join(f.repo, 'candidate')}), /output_inside_source/);
  mkdirSync(f.out); assert.throws(() => buildCandidate(f), /EEXIST/);
  const link = join(f.work, 'npm-link.js'); symlinkSync(npmCli, link);
  assert.throws(() => buildCandidate({...f, out: join(f.work, 'other'), npmCli: link}), error => error.code === 'ELOOP');
  writeFileSync(join(f.repo, 'untracked'), 'untracked');
  assert.throws(() => buildCandidate({...f, out: join(f.work, 'dirty')}), /source_dirty/);
});


test('aliased temp roots become canonical fixtures without weakening output refusal', t => {
  const created = mkdtempSync(join(tmpdir(), 'core-candidate-alias-'));
  t.after(() => rmSync(created, {recursive: true, force: true}));
  const physical = realpathSync(created);
  const target = join(physical, 'physical-tmp'); mkdirSync(target);
  const alias = join(physical, 'aliased-tmp'); symlinkSync(target, alias);
  const f = fixture(t, {tempRoot: alias});
  assert.equal(f.work, realpathSync(f.work), 'fixture path must be canonical');
  assert.equal(buildCandidate(f).ok, true);
  assert.throws(() => buildCandidate({...f, out: join(alias, 'refused-output')}), /output_symlink_ancestor/);
});


test('tree and annotated tag object identities cannot stand in for a commit', t => {
  const f = built(t);
  command('/usr/bin/git', ['-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'tag.gpgSign=false', 'tag', '-a', 'fixture-tag', '-m', 'Synthetic tag'], f.repo, f.work);
  const identities = [
    command('/usr/bin/git', ['rev-parse', `${f.source}^{tree}`], f.repo, f.work).toString().trim(),
    command('/usr/bin/git', ['rev-parse', 'refs/tags/fixture-tag'], f.repo, f.work).toString().trim(),
  ];
  for (const source of identities) {
    const document = JSON.parse(f.index); document.source.commit = source;
    assert.throws(() => verifyCandidate({...f, source, index: encoded(document)}), /source_commit/);
  }
});

test('source inspection never executes a configured clean filter', t => {
  const f = fixture(t);
  const file = join(f.repo, 'FILTERED.txt'); writeFileSync(file, 'original\n');
  writeFileSync(join(f.repo, '.gitattributes'), 'FILTERED.txt filter=candidate-fixture\n');
  command('/usr/bin/git', ['add', '.'], f.repo, f.work);
  command('/usr/bin/git', ['-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic filter input\n\nsow: zeroemployee-SOW-180'], f.repo, f.work);
  f.source = command('/usr/bin/git', ['rev-parse', 'HEAD'], f.repo, f.work).toString().trim();
  const marker = join(f.work, 'CLEAN_FILTER_RAN'); const driver = join(f.work, 'filter.cjs');
  writeFileSync(driver, `const fs = require('node:fs'); fs.writeFileSync(${JSON.stringify(marker)}, 'ran'); process.stdout.write(fs.readFileSync(0));\n`);
  const quote = value => "'" + value.replaceAll("'", "'\\''") + "'";
  command('/usr/bin/git', ['config', 'filter.candidate-fixture.clean', `${quote(process.execPath)} ${quote(driver)}`], f.repo, f.work);
  writeFileSync(file, 'changed!\n');
  utimesSync(file, new Date(1), new Date(1));
  command('/usr/bin/git', ['status', '--porcelain'], f.repo, f.work);
  assert.equal(existsSync(marker), true, 'positive control: ordinary Git status ran the clean filter');
  writeFileSync(file, 'original\n'); utimesSync(file, new Date(2), new Date(2)); rmSync(marker);
  assert.equal(buildCandidate(f).ok, true);
  assert.equal(existsSync(marker), false, 'candidate source inspection must not execute clean filters');
});

test('submodule trees refuse before any submodule worktree inspection', t => {
  const f = fixture(t);
  command('/usr/bin/git', ['update-index', '--add', '--cacheinfo', '160000', f.source, 'nested'], f.repo, f.work);
  command('/usr/bin/git', ['-c', 'user.name=Synthetic Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic gitlink\n\nsow: zeroemployee-SOW-180'], f.repo, f.work);
  f.source = command('/usr/bin/git', ['rev-parse', 'HEAD'], f.repo, f.work).toString().trim();
  assert.throws(() => buildCandidate(f), /source_submodule/);
});

test('source index changes and assume-unchanged flags cannot hide dirty bytes', t => {
  const hidden = fixture(t); const hiddenPath = join(hidden.repo, 'packages/publication-core/README.md');
  command('/usr/bin/git', ['update-index', '--assume-unchanged', 'packages/publication-core/README.md'], hidden.repo, hidden.work);
  writeFileSync(hiddenPath, 'hidden worktree change\n');
  assert.equal(command('/usr/bin/git', ['status', '--porcelain'], hidden.repo, hidden.work).length, 0, 'positive control: original index hides the change');
  assert.throws(() => buildCandidate(hidden), /source_dirty/);
  const staged = fixture(t); const path = join(staged.repo, 'packages/publication-core/README.md');
  const original = readFileSync(path); writeFileSync(path, 'staged change\n');
  command('/usr/bin/git', ['add', 'packages/publication-core/README.md'], staged.repo, staged.work);
  writeFileSync(path, original);
  assert.throws(() => buildCandidate(staged), /source_dirty/);
});

test('physical containment covers source aliases and actual filesystem case behavior', t => {
  const f = fixture(t); const alias = join(f.work, 'source-alias'); symlinkSync(f.repo, alias);
  assert.throws(() => buildCandidate({...f, out: join(alias, 'candidate')}), /output_inside_source/);
  const casePath = join(f.work, 'SOURCE');
  if (existsSync(casePath)) {
    const original = lstatSync(f.repo, {bigint: true}); const alias = lstatSync(casePath, {bigint: true});
    assert.equal(alias.dev, original.dev); assert.equal(alias.ino, original.ino);
    assert.throws(() => buildCandidate({...f, out: join(casePath, 'candidate')}), /output_inside_source/);
    assert.throws(() => buildCandidate({...f, out: casePath}), /output_inside_source/);
  } else {
    assert.equal(buildCandidate({...f, out: casePath}).ok, true, 'a distinct case-sensitive sibling is outside the source');
  }
});

test('index field order and whitespace are not a canonical serialization requirement', t => {
  const f = built(t); const reordered = Object.fromEntries(Object.entries(JSON.parse(f.index)).reverse());
  assert.equal(verifyCandidate({...f, index: Buffer.from(JSON.stringify(reordered))}).ok, true);
});
