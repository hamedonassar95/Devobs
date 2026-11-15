#!/usr/bin/env node
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ingestText, readEventStore, readInputFile } from './ai_intelligence/event_ingest.mjs';
import { MAX_INPUT_BYTES, parseEventLines, parseJsonLine } from './ai_intelligence/event_schema.mjs';
import { buildDashboardSnapshot } from './ai_intelligence/dashboard_server.mjs';
import { ALLOWED_SOURCES } from './integrations/project_sources.mjs';
import { convertText as cloudevents } from './integrations/cloudevents_ci_adapter.mjs';
import { convertText as alertmanager } from './integrations/alertmanager_adapter.mjs';
import { convertText as grafana } from './integrations/grafana_webhook_adapter.mjs';

const FIXTURES = Object.freeze({ cloudevents: 'synthetic-ci-events.jsonl',
  alertmanager: 'synthetic-alertmanager.json', grafana: 'synthetic-grafana.json' });
const STAGES = ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7'];
const EXPECTED_COUNTS = [5, 0, 0, 0, 0, 0, 1];
const counts = () => ({ critical: 0, warning: 0, info: 0, error: 0, unknown: 0 });

export class IntegrationAcceptanceError extends Error {
  constructor(code) { super(code); this.name = 'IntegrationAcceptanceError'; this.code = code; }
}
function check(condition, code = 'acceptance_failed') {
  if (!condition) throw new IntegrationAcceptanceError(code);
}
async function fixedFixtures() {
  return Object.fromEntries(await Promise.all(Object.entries(FIXTURES).map(async ([key, file]) =>
    [key, await readInputFile(fileURLToPath(new URL('../examples/integrations/' + file, import.meta.url)))])));
}

// The optional library input is validated fixture text, never a filesystem path.
// CLI callers can only use the three fixed checked-in public synthetic fixtures.
export async function runAcceptance(suppliedFixtures) {
  let folder;
  let report;
  try {
    const fixtures = suppliedFixtures === undefined ? await fixedFixtures() : suppliedFixtures;
    check(fixtures !== null && typeof fixtures === 'object' && !Array.isArray(fixtures)
      && [Object.prototype, null].includes(Object.getPrototypeOf(fixtures))
      && Object.keys(fixtures).length === 3 && Object.keys(FIXTURES).every(key =>
        Object.hasOwn(fixtures, key) && typeof fixtures[key] === 'string'
        && Buffer.byteLength(fixtures[key], 'utf8') <= MAX_INPUT_BYTES), 'invalid_fixture');
    cloudevents(fixtures.cloudevents); // Validate the entire CI batch before selection.
    const ciRows = fixtures.cloudevents.trim().split(/\r?\n/).map(parseJsonLine);
    const rowsBySource = new Map();
    for (const row of ciRows) {
      check(!rowsBySource.has(row.source), 'invalid_fixture'); rowsBySource.set(row.source, row);
    }
    check(rowsBySource.size === 7 && Object.keys(ALLOWED_SOURCES).length === 7
      && Object.keys(ALLOWED_SOURCES).every(source => rowsBySource.has(source)), 'invalid_fixture');
    folder = await mkdtemp(path.join(os.tmpdir(), 'devobs-integrations-acceptance-'));
    const allIds = new Set();
    const results = [];
    const totals = { projects: 0, unique_events: 0, accepted: 0, duplicate_ignored_on_replay: 0, severity_counts: counts() };
    for (const [projectSource, project] of Object.entries(ALLOWED_SOURCES)) {
      const scope = { projectSource, serviceId: 'monitoring' };
      const texts = [cloudevents(JSON.stringify(rowsBySource.get(projectSource))),
        alertmanager(fixtures.alertmanager, scope), grafana(fixtures.grafana, scope)];
      const providerEvents = texts.map(text => parseEventLines(text).events);
      check(providerEvents.every((events, index) => events.length === [1, 2, 2][index]));
      const expected = providerEvents.flat();
      const projectIds = new Set();
      for (const event of expected) {
        check(!projectIds.has(event.event_id) && !allIds.has(event.event_id));
        projectIds.add(event.event_id); allIds.add(event.event_id);
      }
      const store = path.join(folder, results.length + '.jsonl');
      const first = await ingestText(texts.join(''), store);
      const replay = await ingestText([...texts].reverse().join(''), store);
      const stored = await readEventStore(store);
      check(first.accepted === 5 && first.duplicateIgnored === 0
        && replay.accepted === 0 && replay.duplicateIgnored === 5
        && stored.length === 5 && stored.every(event => projectIds.has(event.event_id))
        && new Set(stored.map(event => event.event_id)).size === 5);
      const snapshot = buildDashboardSnapshot(stored);
      check(snapshot.pipeline.mode === 'local_advisory_only' && snapshot.pipeline.stages.length === 7
        && snapshot.pipeline.stages.every((stage, index) => stage.id === STAGES[index] && stage.count === EXPECTED_COUNTS[index])
        && snapshot.summary.kind_counts.ci_result === 1 && snapshot.summary.kind_counts.incident === 4
        && snapshot.summary.metric_series_count === 0 && snapshot.summary.anomaly_candidate_count === 0
        && snapshot.summary.forecast_count === 0 && snapshot.incidents.length === 0 && snapshot.recommendations.length === 0);
      const severityCounts = counts();
      for (const event of stored) {
        check(Object.hasOwn(severityCounts, event.severity)); severityCounts[event.severity]++;
        totals.severity_counts[event.severity]++;
      }
      const incidents = stored.filter(event => event.kind === 'incident');
      const incidentCounts = { open: incidents.filter(event => event.data.status === 'open').length,
        resolved: incidents.filter(event => event.data.status === 'resolved').length };
      check(incidentCounts.open + incidentCounts.resolved === 4);
      results.push({ project, provider_counts: { cloudevents_ci: providerEvents[0].length,
        alertmanager_v4: providerEvents[1].length, grafana_v1: providerEvents[2].length },
      accepted: first.accepted, stored_events: stored.length, duplicate_ignored_on_replay: replay.duplicateIgnored,
      synthetic_ci_conclusion: stored.find(event => event.kind === 'ci_result').data.conclusion,
      incident_counts: incidentCounts, severity_counts: severityCounts,
      pipeline_stage_counts: snapshot.pipeline.stages.map(stage => stage.count),
      log_clusters: snapshot.incidents.length, recommendations: snapshot.recommendations.length });
      totals.projects++; totals.accepted += first.accepted;
      totals.duplicate_ignored_on_replay += replay.duplicateIgnored;
    }
    totals.unique_events = allIds.size;
    check(totals.unique_events === 35 && totals.projects === 7);
    report = { schema_version: 1, status: 'PASS', scope: 'offline_synthetic_namespaces_only',
      production_ready: false, live_integrations_verified: false, totals, results };
  } catch (error) {
    if (error instanceof IntegrationAcceptanceError) throw error;
    throw new IntegrationAcceptanceError('acceptance_failed');
  } finally {
    if (folder) {
      try { await rm(folder, { recursive: true, force: true }); }
      catch { throw new IntegrationAcceptanceError('cleanup_failed'); }
    }
  }
  return { ...report, cleanup: 'complete' };
}

export async function main(args = process.argv.slice(2)) {
  try {
    check(args.length === 0, 'invalid_arguments');
    const report = await runAcceptance();
    process.stdout.write(JSON.stringify(report, null, 2) + '\n');
    return 0;
  } catch (error) {
    const code = error instanceof IntegrationAcceptanceError
      && ['invalid_arguments', 'invalid_fixture', 'acceptance_failed', 'cleanup_failed'].includes(error.code)
      ? error.code : 'acceptance_failed';
    process.stderr.write(`integration-acceptance: ${code}\n`);
    return 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) process.exitCode = await main();
