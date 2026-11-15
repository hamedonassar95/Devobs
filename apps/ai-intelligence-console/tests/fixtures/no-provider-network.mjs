// Child-process fixture only. Real provider traffic is forbidden in these tests.
import http from 'node:http';
import https from 'node:https';
import { syncBuiltinESMExports } from 'node:module';

function deny() {
  process.stderr.write('unexpected_provider_network\n');
  throw new Error('provider_network_forbidden');
}
globalThis.fetch = deny;
http.get = http.request = deny;
https.get = https.request = deny;
// https://nodejs.org/api/module.html#modulesyncbuiltinesmexports
syncBuiltinESMExports();
