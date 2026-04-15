import { app, BrowserWindow, ipcMain, session } from "electron";
import { ChildProcess, spawn } from "child_process";
import * as path from "path";
import * as http from "http";

let mainWindow: BrowserWindow | null = null;
let pythonProcess: ChildProcess | null = null;
let apiPort: number | null = null;

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

function getPythonCommand(): { cmd: string; args: string[]; env: NodeJS.ProcessEnv } {
  const env = { ...process.env };

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
  env.PYTHONPATH = srcDir + (env.PYTHONPATH ? `:${env.PYTHONPATH}` : "");
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
      if (isDev) {
        console.error("[python]", data.toString().trim());
      }
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
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});
