#!/usr/bin/env node
'use strict';

/**
 * guard-paths — denies any tool call whose target resolves outside the project.
 *
 * Allow-list by construction: anything that does not resolve under the project
 * root is refused, so no list of forbidden directories has to be kept up to
 * date. Written in Node rather than as a .ps1/.sh pair because the tools that
 * run it are Node applications: one committed file behaves identically on
 * Windows, macOS and Linux, and a repository cloned on another OS needs no
 * per-machine setup to stay protected.
 *
 * Reads the hook payload on stdin, writes a deny decision on stdout, exits 0.
 */

const fs = require('fs');
const path = require('path');

// .agent/hooks/guard-paths.js -> project root is two levels up.
const PROJECT_ROOT = realpath(path.resolve(__dirname, '..', '..'));

// Windows and macOS compare paths case-insensitively; Linux does not. Applying
// the wrong rule either blocks legitimate paths or lets a differently-cased
// one through.
const CASE_INSENSITIVE = process.platform === 'win32' || process.platform === 'darwin';

function realpath(target) {
  try {
    return fs.realpathSync.native ? fs.realpathSync.native(target) : fs.realpathSync(target);
  } catch (err) {
    return path.resolve(target);
  }
}

/**
 * Resolves a target through symlinks, junctions and shared-folder mounts even
 * when it does not exist yet: walk up to the nearest existing ancestor, resolve
 * that, then re-append the missing tail. Without this, a write to a new file
 * inside a symlinked tree compares two spellings of the same place.
 */
function resolveTarget(target) {
  const absolute = path.isAbsolute(target)
    ? path.resolve(target)
    : path.resolve(PROJECT_ROOT, target);

  let probe = absolute;
  let tail = '';
  while (!fs.existsSync(probe)) {
    const parent = path.dirname(probe);
    if (parent === probe) return absolute;
    tail = tail ? path.join(path.basename(probe), tail) : path.basename(probe);
    probe = parent;
  }
  return tail ? path.join(realpath(probe), tail) : realpath(probe);
}

function isInsideProject(target) {
  if (!target || typeof target !== 'string') return true;

  let root = PROJECT_ROOT;
  let candidate = resolveTarget(target);
  if (CASE_INSENSITIVE) {
    root = root.toLowerCase();
    candidate = candidate.toLowerCase();
  }
  // The trailing separator matters: without it a sibling directory whose name
  // merely starts with the project name would pass.
  const rootWithSep = root.endsWith(path.sep) ? root : root + path.sep;
  return candidate === root || candidate.startsWith(rootWithSep);
}

function deny(target) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason:
        `Outside the project perimeter: ${target}\n` +
        `Project root: ${PROJECT_ROOT}\n` +
        `Declared in .agent/profile.json. Ask the user before working outside it.`
    },
    systemMessage: `PERIMETER: blocked access to ${target}`
  }));
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(raw || '{}');
  } catch (err) {
    // Never block on a payload we failed to parse: a guard that fails closed on
    // malformed input would make the tool unusable for reasons nobody can see.
    process.exit(0);
  }

  const input = (payload && payload.tool_input) || {};
  for (const target of [input.file_path, input.notebook_path, input.path]) {
    if (!isInsideProject(target)) {
      deny(target);
      break;
    }
  }
  process.exit(0);
});
