// hook_payload.mjs — one payload shape for hooks that run on either host.
//
// Copy this file into `<project root>/.agents/hooks/` next to the hook scripts
// that import it, then:
//
//     import { loadEvent, projectRoot } from "./hook_payload.mjs";
//
//     const event = await loadEvent();
//     if (event.name === null) process.exit(0);   // untrusted payload, see below
//
// It normalises the two dialects a hook payload arrives in. One host sends
// `tool_input.file_path` for an edit; the other sends `tool_name: "apply_patch"`
// with the patch text in `tool_input.command`. Both end up in `event.files` as
// absolute paths.
//
// Detect the host from the payload, never from environment variables: a
// project variable that looks host-specific can be inherited from whatever
// process started the session.
//
// Written against a strict lint baseline (explicit `node:` imports, every
// payload field narrowed from `unknown`); a project with its own conventions
// may still want to adjust it before its gates pass.
//
// Node >= 18, no dependencies.

import { execFileSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const SHELL_TOOLS = new Set(["bash", "shell"]);
const READ_TOOLS = new Set(["read"]);
const EDIT_TOOLS = new Set([
  "edit",
  "write",
  "multiedit",
  "notebookedit",
  "apply_patch",
]);
// `*** Add File: path`, `*** Update File: path`, `*** Delete File: path`,
// `*** Move to: path` — the four lines in a patch that name a file.
const PATCH_PATH_RE =
  /^\*\*\*\s+(?:Add File|Update File|Delete File|Move to):\s*(\S.*?)\s*$/gm;

/**
 * @typedef {object} Event
 * @property {string | null} name  `hook_event_name`. `null` means "do not trust
 *   this payload" — it was unreadable, not an object, or carried no event
 *   name; callers exit 0 on it. Both hosts always send the name.
 * @property {"shell" | "read" | "edit" | "other" | null} tool  Coarse kind.
 *   A `Read` call is `"read"`, not `"edit"`, even though it also carries
 *   `file_path`; a check that must tell reads from writes branches on this
 *   or on `toolName`.
 * @property {string | null} toolName  The host's own name for the tool.
 * @property {string | null} command  Shell command, only when tool is `"shell"`.
 * @property {string[]} files  Absolute paths the call reads or edits.
 * @property {string} cwd
 * @property {boolean} stopHookActive  This Stop hook already ran once.
 * @property {Record<string, unknown>} raw  The parsed payload.
 */

/** @param {unknown} value @returns {Record<string, unknown>} */
function asRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? /** @type {Record<string, unknown>} */ (value)
    : {};
}

/** @param {unknown} value @returns {string | null} */
function asString(value) {
  return typeof value === "string" && value !== "" ? value : null;
}

/** @param {string} value @param {string} base */
function absolute(value, base) {
  return path.normalize(path.isAbsolute(value) ? value : path.join(base, value));
}

/**
 * Absolute paths touched by a patch, in the order the patch names them.
 * @param {string} patch @param {string} base @returns {string[]}
 */
export function patchFiles(patch, base) {
  /** @type {string[]} */
  const out = [];
  for (const match of patch.matchAll(PATCH_PATH_RE)) out.push(absolute(match[1], base));
  return out;
}

/**
 * Build an event from an already-parsed payload.
 * @param {unknown} payload @returns {Event}
 */
export function fromPayload(payload) {
  const raw = asRecord(payload);
  const toolInput = asRecord(raw.tool_input);
  const toolName = asString(raw.tool_name);
  const key = (toolName ?? "").toLowerCase();
  const filePath = asString(toolInput.file_path);
  const inputCommand = asString(toolInput.command);

  /** @type {Event["tool"]} */
  let tool = null;
  if (SHELL_TOOLS.has(key)) tool = "shell";
  else if (READ_TOOLS.has(key)) tool = "read";
  else if (EDIT_TOOLS.has(key) || filePath !== null) tool = "edit";
  else if (toolName !== null) tool = "other";

  const cwd = asString(raw.cwd) ?? process.cwd();
  const command = tool === "shell" ? inputCommand : null;

  /** @type {string[]} */
  const files = [];
  if (filePath !== null) files.push(absolute(filePath, cwd));
  if (tool === "edit" && inputCommand?.includes("*** ")) {
    files.push(...patchFiles(inputCommand, cwd));
  }

  return {
    name: asString(raw.hook_event_name),
    tool,
    toolName,
    command,
    files: [...new Set(files)],
    cwd,
    stopHookActive: Boolean(raw.stop_hook_active),
    raw,
  };
}

/** @returns {Event} */
function emptyEvent() {
  return {
    name: null,
    tool: null,
    toolName: null,
    command: null,
    files: [],
    cwd: process.cwd(),
    stopHookActive: false,
    raw: {},
  };
}

/**
 * Read one JSON payload (default: stdin). Unreadable input -> name is null.
 * @param {NodeJS.ReadableStream} [stream] @returns {Promise<Event>}
 */
export async function loadEvent(stream = process.stdin) {
  let text = "";
  try {
    stream.setEncoding("utf8");
    for await (const chunk of stream) text += String(chunk);
    return fromPayload(JSON.parse(text));
  } catch {
    return emptyEvent();
  }
}

/**
 * The project root, resolved from the calling script's own location.
 * Pass `import.meta.url`. Walks up to the directory holding `.agents/hooks`,
 * then falls back to the git top level, then to the working directory.
 * @param {string} [importMetaUrl] @returns {string}
 */
export function projectRoot(importMetaUrl) {
  let dir = importMetaUrl ? path.dirname(fileURLToPath(importMetaUrl)) : process.cwd();
  for (;;) {
    const candidate = path.join(dir, ".agents", "hooks");
    if (existsSync(candidate) && statSync(candidate).isDirectory()) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  try {
    const top = execFileSync("git", ["rev-parse", "--show-toplevel"], {
      encoding: "utf8",
    }).trim();
    if (top) return top;
  } catch {
    // no git, or not a repository
  }
  return process.cwd();
}

/**
 * `filePath` relative to the root, slash-separated, for matching.
 * @param {string} filePath @param {Event} event @param {string} [root]
 * @returns {string}
 */
export function relativeToRoot(filePath, event, root) {
  for (const base of [root, event.cwd]) {
    if (!base) continue;
    const rel = path.relative(base, filePath);
    if (rel && !rel.startsWith("..") && !path.isAbsolute(rel))
      return rel.split(path.sep).join("/");
  }
  return path.basename(filePath);
}
