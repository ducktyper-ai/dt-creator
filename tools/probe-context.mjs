// Read-only provenance for opt-in source probes; not a signed or sandboxed CI receipt.
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../../',import.meta.url));
export function probeContext(now) {
  const sourceHead=execFileSync('git',['-c','core.fsmonitor=','-C',root,'rev-parse','HEAD'],{encoding:'utf8',timeout:2500,env:{PATH:process.env.PATH,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_CONFIG_COUNT:'0'}}).trim();
  const inputs=Object.fromEntries(['index.mjs','policies.mjs'].map(name=>[name,createHash('sha256').update(readFileSync(new URL('../'+name,import.meta.url))).digest('hex')]));
  return {sourceHead,now,inputs,scope:'Local source observation, not signed CI or packaged site parity'};
}
