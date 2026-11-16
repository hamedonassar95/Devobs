#!/usr/bin/env node
/** The same verified public CI client is used by the browser and manual CLI. */
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { inspectPublicPortfolio } from '../assets/public-ci/portfolio-api.mjs';
export { PUBLIC_TARGETS, normalizePublicRun, inspectPublicPortfolio, PublicPortfolioError } from '../assets/public-ci/portfolio-api.mjs';

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv.length !== 2) {
    process.stderr.write('usage: node scripts/portfolio_public_ci.mjs\n');
    process.exitCode = 2;
  } else {
    const report = await inspectPublicPortfolio();
    process.stdout.write(JSON.stringify(report, null, 2) + '\n');
    process.exitCode = report.results.some(x => x.status === 'unverified') ? 1 : 0;
  }
}
