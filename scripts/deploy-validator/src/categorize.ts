/**
 * categorize.ts — T2: Command categorizer for bash code blocks
 *
 * Identifies primary command type(s) in each bash block so the
 * appropriate validator can be dispatched.
 */

import type { CodeBlock } from "./parser.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CommandType =
  | "rsync"
  | "file-op"        // cp, mv
  | "ssh-remote"     // ssh root@vps '...'
  | "sqlite3"        // sqlite3 db.db < migration.sql
  | "systemctl"      // systemctl restart ...
  | "curl"           // curl http(s)://...
  | "perm-op"        // chmod, chown, chattr
  | "archive"        // tar, gzip, gunzip
  | "env-setup"      // set -a; source ...; set +a or export VAR=
  | "destructive"    // rm -rf, dd, truncate
  | "node-exec"      // node -e '...' or node script.js
  | "build"          // npm run build, tsc
  | "other";

export interface CategorizedCommand {
  /** Original code block metadata */
  block: CodeBlock;
  /** Detected command type(s) in order of first appearance */
  types: CommandType[];
  /** Individual command lines detected */
  commands: DetectedCommand[];
  /** True if block contains at least one destructive command */
  hasDestructive: boolean;
  /** True if this block is SSH-only (all real work happens on remote) */
  isRemoteOnly: boolean;
}

export interface DetectedCommand {
  /** Trimmed line text */
  line: string;
  /** 1-based line number within block (1 = first content line) */
  lineOffset: number;
  /** Detected type */
  type: CommandType;
  /** Additional structured data extracted from the command */
  meta: CommandMeta;
}

export interface CommandMeta {
  /** For rsync: source and destination paths */
  rsyncSrc?: string;
  rsyncDest?: string;
  /** For sqlite3: db path and sql file/inline */
  sqliteDb?: string;
  sqliteInput?: string;
  /** For curl: URL */
  curlUrl?: string;
  /** For systemctl: action and unit */
  systemctlAction?: string;
  systemctlUnit?: string;
  /** For ssh: remote host and inner command */
  sshHost?: string;
  sshCommand?: string;
}

// ---------------------------------------------------------------------------
// Categorizer
// ---------------------------------------------------------------------------

/**
 * Categorize all bash code blocks from the parser output.
 * Non-bash blocks are skipped (returns empty array for them).
 */
export function categorizeBlocks(blocks: CodeBlock[]): CategorizedCommand[] {
  return blocks
    .filter((b) => b.language === "bash" || b.language === "sh" || b.language === "")
    .map(categorizeBlock);
}

export function categorizeBlock(block: CodeBlock): CategorizedCommand {
  // Join line continuations (\ at end of line) before splitting into logical commands
  const joinedContent = block.content.replace(/\\\n\s*/g, " ");
  const lines = joinedContent.split("\n");
  const commands: DetectedCommand[] = [];
  const typeSet = new Set<CommandType>();
  let hasDestructive = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line || line.startsWith("#")) continue;

    const detected = detectLine(line, i + 1);
    if (detected) {
      commands.push(detected);
      typeSet.add(detected.type);
      if (detected.type === "destructive") hasDestructive = true;
    }
  }

  // Determine if block is primarily remote (all work inside ssh "...")
  const isRemoteOnly = commands.every(
    (c) => c.type === "ssh-remote" || c.type === "env-setup" || c.type === "other"
  );

  return {
    block,
    types: [...typeSet],
    commands,
    hasDestructive,
    isRemoteOnly,
  };
}

// ---------------------------------------------------------------------------
// Line detection
// ---------------------------------------------------------------------------

function detectLine(line: string, lineOffset: number): DetectedCommand | null {
  // Skip comment-only lines
  if (/^#/.test(line)) return null;

  // Destructive — checked first
  if (/\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|rm\s+-[a-zA-Z]*f[a-zA-Z]*r|\bdd\b|\btruncate\b/.test(line)) {
    return { line, lineOffset, type: "destructive", meta: {} };
  }

  // rsync
  const rsyncMatch = line.match(/\brsync\b/);
  if (rsyncMatch) {
    const meta = extractRsyncMeta(line);
    return { line, lineOffset, type: "rsync", meta };
  }

  // sqlite3
  const sqlite3Match = line.match(/\bsqlite3\b/);
  if (sqlite3Match) {
    const meta = extractSqliteMeta(line);
    return { line, lineOffset, type: "sqlite3", meta };
  }

  // ssh remote (ssh user@host or ssh $VAR_HOST)
  const sshMatch = line.match(/\bssh\b\s+(\S+)\s*/);
  if (sshMatch && !line.match(/^#/)) {
    const host = sshMatch[1];
    // Extract command inside quotes if present
    const cmdMatch = line.match(/ssh\s+\S+\s+"([\s\S]*)"|ssh\s+\S+\s+'([\s\S]*)'/);
    const sshCommand = cmdMatch ? (cmdMatch[1] ?? cmdMatch[2]) : undefined;
    return {
      line,
      lineOffset,
      type: "ssh-remote",
      meta: { sshHost: host, sshCommand },
    };
  }

  // systemctl
  const systemctlMatch = line.match(/\bsystemctl\b\s+(\w+)\s+(\S+)/);
  if (systemctlMatch) {
    return {
      line,
      lineOffset,
      type: "systemctl",
      meta: {
        systemctlAction: systemctlMatch[1],
        systemctlUnit: systemctlMatch[2],
      },
    };
  }

  // curl
  const curlMatch = line.match(/\bcurl\b.*?(https?:\/\/[^\s'"]+)/);
  if (curlMatch) {
    return {
      line,
      lineOffset,
      type: "curl",
      meta: { curlUrl: curlMatch[1] },
    };
  }

  // chmod / chown / chattr
  if (/\b(chmod|chown|chattr)\b/.test(line)) {
    return { line, lineOffset, type: "perm-op", meta: {} };
  }

  // tar / gzip / gunzip
  if (/\b(tar|gzip|gunzip)\b/.test(line)) {
    return { line, lineOffset, type: "archive", meta: {} };
  }

  // cp / mv (file ops)
  if (/\b(cp|mv)\b/.test(line)) {
    return { line, lineOffset, type: "file-op", meta: {} };
  }

  // npm run build / tsc
  if (/\b(npm\s+run\s+build|tsc)\b/.test(line)) {
    return { line, lineOffset, type: "build", meta: {} };
  }

  // node -e or node script
  if (/\bnode\b/.test(line)) {
    return { line, lineOffset, type: "node-exec", meta: {} };
  }

  // env setup: set -a; source / export
  if (/\bsource\b|\bexport\b\s+\w+=|set\s+-a/.test(line)) {
    return { line, lineOffset, type: "env-setup", meta: {} };
  }

  return { line, lineOffset, type: "other", meta: {} };
}

// ---------------------------------------------------------------------------
// Metadata extractors
// ---------------------------------------------------------------------------

function extractRsyncMeta(line: string): CommandMeta {
  // rsync [flags] SRC DEST
  // Remove known flags: -avz --dry-run --verbose --delete
  const stripped = line
    .replace(/\brsync\b/, "")
    .replace(/--[\w-]+=?\S*/g, "")
    // Only remove flags: token starting with - followed by letters (not path chars like - in staged-A3)
    // A flag is: preceded by space/start, starts with -, followed by letters only (no digits/slash/dot)
    .replace(/(^|\s)-[a-zA-Z]+(?=\s|$)/g, " ")
    .trim();

  const parts = stripped.split(/\s+/).filter(Boolean);
  const src = parts[0] ?? "";
  const dest = parts[1] ?? "";
  return { rsyncSrc: src, rsyncDest: dest };
}

function extractSqliteMeta(line: string): CommandMeta {
  // sqlite3 <db> < <file>  OR  sqlite3 <db> '<inline sql>'
  const pipeMatch = line.match(/sqlite3\s+(\S+)\s+<\s+(\S+)/);
  if (pipeMatch) {
    return { sqliteDb: pipeMatch[1], sqliteInput: pipeMatch[2] };
  }

  const inlineMatch = line.match(/sqlite3\s+(\S+)\s+["'](.+?)["']/);
  if (inlineMatch) {
    return { sqliteDb: inlineMatch[1], sqliteInput: inlineMatch[2] };
  }

  const dbOnly = line.match(/sqlite3\s+(\S+)/);
  return { sqliteDb: dbOnly?.[1] };
}
