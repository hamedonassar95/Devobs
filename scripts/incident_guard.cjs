// Read-only gate shared by pre-activation and the final comment writer.
// Keep this function dependency-free: its source is embedded in the compiled workflow.
async function incidentGuard({ github, context, core }, requireEligible = false) {
  core.setOutput('eligible', 'false');
  const stop = (reason) => {
    core.info(reason);
    if (requireEligible) core.setFailed(reason);
    return false;
  };
  const raw = context.payload.issue?.number ?? context.payload.inputs?.issue_number;
  if (!/^[1-9][0-9]*$/.test(String(raw)) || !Number.isSafeInteger(Number(raw))) {
    return stop('Invalid incident number; no investigation or comment permitted.');
  }
  const issue_number = Number(raw);
  const params = { ...context.repo, issue_number };
  const { data: issue } = await github.rest.issues.get(params);
  if (issue.pull_request || issue.state !== 'open' ||
      issue.user?.login !== 'github-actions[bot]' ||
      !issue.title?.startsWith('incident:') ||
      !/<!-- incident-run-id:(?:simulation-)?[0-9]+ -->/.test(issue.body ?? '')) {
    return stop('Incident failed the trust gate; no investigation or comment permitted.');
  }
  // Paginate: an existing investigation may be beyond the first 100 comments.
  const comments = await github.paginate(github.rest.issues.listComments, {
    ...params, per_page: 100,
  });
  const existing = comments.some(comment =>
    comment.user?.login === 'github-actions[bot]' &&
    (comment.body?.includes('## AI Incident Investigation') ||
     comment.body?.includes('<!-- devobs-investigation:v1 -->')));
  if (existing) return stop('Investigation already exists; duplicate skipped.');
  core.setOutput('eligible', 'true');
  return true;
}

module.exports = { incidentGuard };
