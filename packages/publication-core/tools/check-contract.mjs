import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import * as runtime from '../index.mjs';
export function verifyDeclarationExports(names, declaration) {
  const declared = [...declaration.matchAll(/^export declare (?:function|const|class) ([A-Za-z_$][\w$]*)/gm)].map(match => match[1]);
  assert.equal(new Set(declared).size, declared.length, 'Duplicate runtime declarations');
  assert.deepEqual([...names].sort(), declared.sort(), 'Runtime and declaration exports differ');
}
export function verifyContract() {
  const root = new URL('../', import.meta.url);
  const manifest = JSON.parse(readFileSync(new URL('package.json', root), 'utf8'));
  assert.equal(manifest.private, true, 'Unreleased package must remain private');
  assert.equal(manifest.type, 'module');
  assert.deepEqual(Object.keys(manifest.exports), ['.']);
  assert.deepEqual(manifest.exports['.'], {types: './index.d.ts', import: './index.mjs'});
  assert.equal(manifest.dependencies, undefined);
  assert.equal(manifest.devDependencies, undefined);
  const declaration = readFileSync(new URL('index.d.ts', root), 'utf8');
  verifyDeclarationExports(Object.keys(runtime), declaration);
  const source = readFileSync(new URL('index.mjs', root), 'utf8');
  assert.ok(!/\b(?:import|require|fetch|process|Date\.now|Intl)\b/.test(source), 'Pure entry point must not import effects or global clock/policy');
  assert.deepEqual(manifest.files, ['index.mjs', 'index.d.ts', 'README.md', 'CHANGELOG.md']);
  for (const file of manifest.files) readFileSync(new URL(file, root));
  return {exports: Object.keys(runtime).length, declarationCheck: 'Names only; no compiler/type soundness claim'};
}
if (process.argv[1] === fileURLToPath(import.meta.url)) console.log(JSON.stringify(verifyContract()));
