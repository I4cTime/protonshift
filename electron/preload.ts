import { contextBridge, ipcRenderer } from "electron";

export interface ApiResponse {
  ok: boolean;
  status: number;
  body: string;
}

contextBridge.exposeInMainWorld("api", {
  getApiPort: (): Promise<number | null> => ipcRenderer.invoke("get-api-port"),

  fetch: (path: string, init?: RequestInit): Promise<ApiResponse> =>
    ipcRenderer.invoke("api-fetch", path, init),
});

contextBridge.exposeInMainWorld("electron", {
  closeWindow: (): Promise<void> => ipcRenderer.invoke("window-close"),
  minimizeWindow: (): Promise<void> => ipcRenderer.invoke("window-minimize"),
  toggleMaximize: (): Promise<void> => ipcRenderer.invoke("window-toggle-maximize"),
});
