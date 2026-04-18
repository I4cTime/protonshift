import { app, BrowserWindow, ipcMain } from "electron";
import { ChildProcess, spawn } from "child_process";
import * as path from "path";
import * as http from "http";

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;
let apiPort: number | null = null;
let staticServer: http.Server | null = null;
let staticRendererPort: number | null = null;

const isDev = !app.isPackaged;

import * as fs from "fs";

function findPythonCmd(projectRoot: string): string {
  // Prefer the project venv if it exists (dev workflow)
  const candidates = [
    path.join(projectRoot, ".venv", "bin", "python3"),
    path.join(projectRoot, ".venv", "bin", "python"),
    "python3",
    "python",
  ];
  for (const c of candidates) {
    if (c.startsWith("/") && fs.existsSync(c)) return c;
    if (!c.startsWith("/")) return c; // fall back to PATH
  }
  return "python3";
}

const EXTRA_PATH_DIRS = [
  "/usr/bin",
  "/usr/local/bin",
  "/var/usrlocal/bin",
  "/usr/lib/extensions/vulkan/MangoHud/bin",
  "/usr/lib64/extensions/vulkan/MangoHud/bin",
  "/run/current-system/sw/bin", // NixOS
].join(":");

function getPythonCommand(): { cmd: string; args: string[]; env: NodeJS.ProcessEnv } {
  const env = { ...process.env };
  // Immutable distros (Bazzite, SteamOS, Fedora Atomic) and AppImage
  // wrappers can strip PATH entries. Ensure common locations are present.
  if (env.PATH && !env.PATH.includes("/var/usrlocal/bin")) {
    env.PATH = `${env.PATH}:${EXTRA_PATH_DIRS}`;
  }

  if (isDev) {
    const projectRoot = path.resolve(__dirname, "..", "..");
    const srcDir = path.join(projectRoot, "src");
    env.PYTHONPATH = srcDir + (env.PYTHONPATH ? `:${env.PYTHONPATH}` : "");
    return {
      cmd: findPythonCmd(projectRoot),
      args: ["-m", "game_setup_hub.api", "--port", "0"],
      env,
    };
  }

  const resourcesPath = process.resourcesPath;
  const srcDir = path.join(resourcesPath, "python", "src");
  const vendorDir = path.join(resourcesPath, "python", "vendor");
  const pyPathParts: string[] = [];
  if (fs.existsSync(vendorDir)) {
    pyPathParts.push(vendorDir);
  }
  pyPathParts.push(srcDir);
  if (env.PYTHONPATH) {
    pyPathParts.push(env.PYTHONPATH);
  }
  env.PYTHONPATH = pyPathParts.join(":");
  // Ensure system site-packages are available as fallback for native
  // extensions (.so) that may not match the vendored Python version.
  env.PYTHONNOUSERSITE = "";
  return {
    cmd: "python3",
    args: ["-m", "game_setup_hub.api", "--port", "0"],
    env,
  };
}

function startPython(): Promise<number> {
  return new Promise((resolve, reject) => {
    const { cmd, args, env } = getPythonCommand();
    pythonProcess = spawn(cmd, args, { env, stdio: ["pipe", "pipe", "pipe"] });

    const timeout = setTimeout(() => {
      reject(new Error("Python backend did not start within 15 seconds"));
    }, 15000);

    pythonProcess.stdout?.on("data", (data: Buffer) => {
      const output = data.toString();
      const match = output.match(/PORT:(\d+)/);
      if (match) {
        clearTimeout(timeout);
        resolve(parseInt(match[1], 10));
      }
    });

    pythonProcess.stderr?.on("data", (data: Buffer) => {
      console.error("[python]", data.toString().trim());
    });

    pythonProcess.on("error", (err) => {
      clearTimeout(timeout);
      reject(err);
    });

    pythonProcess.on("exit", (code) => {
      if (code !== null && code !== 0) {
        clearTimeout(timeout);
        reject(new Error(`Python exited with code ${code}`));
      }
      pythonProcess = null;
    });
  });
}

function waitForHealth(port: number, retries = 30): Promise<void> {
  return new Promise((resolve, reject) => {
    let attempt = 0;
    const check = () => {
      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else if (++attempt < retries) {
          setTimeout(check, 500);
        } else {
          reject(new Error("Health check failed"));
        }
      });
      req.on("error", () => {
        if (++attempt < retries) {
          setTimeout(check, 500);
        } else {
          reject(new Error("Python backend not reachable"));
        }
      });
      req.end();
    };
    check();
  });
}

function getIconPath(): string {
  if (isDev) {
    return path.resolve(__dirname, "..", "..", "assets", "256x256.png");
  }
  return path.join(process.resourcesPath, "assets", "256x256.png");
}

function mimeFor(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  const map: Record<string, string> = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".map": "application/json; charset=utf-8",
  };
  return map[ext] ?? "application/octet-stream";
}

/** Serves Next static export over http://127.0.0.1 — root-relative /_next/... URLs do not work with file:// */
function startStaticRendererServer(rootDir: string): Promise<number> {
  const root = path.resolve(rootDir);
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      try {
        const rawPath = req.url?.split("?")[0] ?? "/";
        let pathname: string;
        try {
          pathname = decodeURIComponent(rawPath);
        } catch {
          res.writeHead(400).end();
          return;
        }
        if (pathname.includes("..")) {
          res.writeHead(403).end();
          return;
        }
        const rel = pathname.replace(/^\/+/, "");
        const rootResolved = path.resolve(root);

        const candidates: string[] = [];
        if (rel === "" || rel === "/") {
          candidates.push(path.join(rootResolved, "index.html"));
        } else {
          candidates.push(
            path.join(rootResolved, rel),
            path.join(rootResolved, `${rel}.html`),
            path.join(rootResolved, rel, "index.html"),
          );
        }

        let found: string | null = null;
        for (const candidate of candidates) {
          const normalized = path.resolve(candidate);
          if (!normalized.startsWith(rootResolved + path.sep) && normalized !== rootResolved) {
            continue;
          }
          if (fs.existsSync(normalized) && fs.statSync(normalized).isFile()) {
            found = normalized;
            break;
          }
        }

        if (!found) {
          res.writeHead(404).end("Not found");
          return;
        }

        const body = fs.readFileSync(found);
        res.writeHead(200, {
          "Content-Type": mimeFor(found),
          "Content-Length": String(body.length),
          "Cache-Control": "no-store",
        });
        res.end(body);
      } catch {
        res.writeHead(500).end();
      }
    });

    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      staticServer = server;
      if (addr && typeof addr === "object") {
        staticRendererPort = addr.port;
        resolve(addr.port);
      } else {
        reject(new Error("Static server failed to bind"));
      }
    });
  });
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "ProtonShift",
    icon: getIconPath(),
    frame: false,
    backgroundColor: "#0f0f14",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:3000");
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else if (staticRendererPort) {
    mainWindow.loadURL(`http://127.0.0.1:${staticRendererPort}/`);
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "renderer", "out", "index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

ipcMain.handle("get-api-port", () => apiPort);

ipcMain.handle("window-close", () => {
  mainWindow?.close();
});

ipcMain.handle("window-minimize", () => {
  mainWindow?.minimize();
});

ipcMain.handle("window-toggle-maximize", () => {
  if (!mainWindow) return;
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow.maximize();
  }
});

ipcMain.handle("api-fetch", async (_event, urlPath: string, init?: RequestInit) => {
  if (!apiPort) throw new Error("API not ready");
  const url = `http://127.0.0.1:${apiPort}${urlPath}`;
  try {
    const response = await fetch(url, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    const body = await response.text();
    return {
      ok: response.ok,
      status: response.status,
      body,
    };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      body: JSON.stringify({ detail: String(err) }),
    };
  }
});

app.on("ready", async () => {
  try {
    apiPort = await startPython();
    await waitForHealth(apiPort);
    if (!isDev) {
      const outDir = path.join(__dirname, "..", "renderer", "out");
      await startStaticRendererServer(outDir);
    }
  } catch (err) {
    console.error("Failed to start Python backend:", err);
    app.quit();
    return;
  }
  createWindow();
});

app.on("window-all-closed", () => {
  app.quit();
});

app.on("before-quit", () => {
  if (pythonProcess) {
    pythonProcess.kill("SIGTERM");
    pythonProcess = null;
  }
  if (staticServer) {
    staticServer.close();
    staticServer = null;
    staticRendererPort = null;
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});
