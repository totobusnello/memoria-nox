/**
 * T12 — CLI: `nox-mem viewer`
 *
 * Opens the user's default browser at the local viewer URL. If no GUI
 * available (CI / headless ssh), prints the URL instead.
 *
 * Resolves URL from env:
 *   NOX_API_PORT (default 18802)
 *   NOX_VIEWER_BIND (default 127.0.0.1)
 *
 * The actual browser launch is delegated to a `launcher` injected for
 * testability — default is `node:child_process.spawn`.
 */

import { spawn } from "node:child_process";

export interface ViewerCliEnv {
  NOX_API_PORT?: string;
  NOX_VIEWER_BIND?: string;
  /** Override the default URL output stream. */
  CI?: string;
}

export interface ViewerCliLauncher {
  open(url: string): Promise<{ launched: boolean; reason: string }>;
}

export interface ViewerCliOutput {
  write(line: string): void;
}

export function buildViewerUrl(env: ViewerCliEnv = process.env): string {
  const port = env.NOX_API_PORT ?? "18802";
  const bind = env.NOX_VIEWER_BIND ?? "127.0.0.1";
  // 0.0.0.0 is unreachable as a URL host — use localhost in that case.
  const host = bind === "0.0.0.0" || bind === "::" ? "127.0.0.1" : bind;
  return `http://${host}:${port}/viewer/`;
}

export const defaultLauncher: ViewerCliLauncher = {
  async open(url: string) {
    const platform = process.platform;
    let cmd: string;
    let args: string[];
    if (platform === "darwin") {
      cmd = "open";
      args = [url];
    } else if (platform === "win32") {
      cmd = "cmd";
      args = ["/c", "start", "", url];
    } else {
      cmd = "xdg-open";
      args = [url];
    }
    return await new Promise((resolve) => {
      try {
        const proc = spawn(cmd, args, { stdio: "ignore", detached: true });
        proc.on("error", () =>
          resolve({ launched: false, reason: `spawn-error:${cmd}` })
        );
        proc.unref();
        resolve({ launched: true, reason: cmd });
      } catch (err) {
        resolve({
          launched: false,
          reason: `exception:${(err as Error).message}`,
        });
      }
    });
  },
};

export async function runViewerCli(
  args: string[] = [],
  opts: {
    env?: ViewerCliEnv;
    launcher?: ViewerCliLauncher;
    stdout?: ViewerCliOutput;
  } = {}
): Promise<number> {
  const env = opts.env ?? process.env;
  const launcher = opts.launcher ?? defaultLauncher;
  const stdout = opts.stdout ?? { write: (l: string) => process.stdout.write(l + "\n") };
  const url = buildViewerUrl(env);
  if (args.includes("--print") || args.includes("-p") || env.CI === "true") {
    stdout.write(url);
    return 0;
  }
  const result = await launcher.open(url);
  if (result.launched) {
    stdout.write(`Opening viewer at ${url}`);
    return 0;
  }
  stdout.write(`Failed to launch browser (${result.reason}). Open manually: ${url}`);
  return 1;
}
