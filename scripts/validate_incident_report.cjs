#!/usr/bin/env node
"use strict";

const fs = require("node:fs");

const MARKER = "<!-- devobs-investigation:v1 -->";
const HEADING = "## AI Incident Investigation";

function validateIncidentReportFile(outputPath) {
  if (typeof outputPath !== "string" || outputPath.length === 0) {
    throw new Error("Agent output path is required.");
  }

  const metadata = fs.lstatSync(outputPath);
  if (!metadata.isFile() || metadata.isSymbolicLink()) {
    throw new Error("Agent output must be a regular file.");
  }

  const output = JSON.parse(fs.readFileSync(outputPath, "utf8"));
  if (!output || !Array.isArray(output.items) || output.items.length !== 1) {
    throw new Error("Agent output must contain exactly one safe incident report.");
  }

  const [item] = output.items;
  if (!item || item.type !== "add_comment" || typeof item.body !== "string") {
    throw new Error("The single safe output must be an incident report comment.");
  }

  const body = item.body;
  if (
    body.split(MARKER).length - 1 !== 1 ||
    !body.trimStart().startsWith(MARKER) ||
    !body.includes(HEADING)
  ) {
    throw new Error("The incident report is missing its unique marker or required heading.");
  }

  return true;
}

if (require.main === module) {
  try {
    validateIncidentReportFile(process.argv[2]);
    process.stdout.write("Incident report output passed validation.\n");
  } catch (error) {
    process.stderr.write(`::error::${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = { validateIncidentReportFile };
