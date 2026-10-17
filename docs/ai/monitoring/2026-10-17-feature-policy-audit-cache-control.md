---
phase: monitoring
title: Reliable Repository Policy API Reads
description: Evidence and operational monitoring for the hosted policy-audit regression
---

# Reliable Repository Policy API Reads — Monitoring

## Observed Failure

The first hosted run after PR #164, run [39041619309](https://github.com/hamedonassar95/Devobs/actions/runs/39041619309), failed twice because the ruleset response did not contain a usable `bypass_actors` list. The API advertised a 60-second cache lifetime, and the ruleset detail also requires read-only authentication. A later hosted run [39051828800](https://github.com/hamedonassar95/Devobs/actions/runs/39051828800) passed after `POLICY_AUDIT_TOKEN` was configured. This follow-up adds `Cache-Control: no-cache`; re-run the hosted audit after merge to verify the combined setup.

## Operational Check

- Run the policy audit after merging the fix and confirm its Actions summary says **passed** with the existing read-only token configured.
- Keep the weekly schedule and manual dispatch unchanged.
- Treat missing or malformed ruleset fields as an unsuccessful audit; do not infer that a missing bypass list is empty.
- The audit is read-only and the existing Incident Response workflow can collect evidence for workflow failures.

## Limitations

This workflow checks repository policy integrity. It does not monitor the website's availability, provide service-level metrics, or alert outside GitHub Actions.
