export {};

declare global {
  interface Window {
    /** Frameless window controls (only present in the Electron shell). */
    electron?: {
      closeWindow: () => Promise<void>;
      minimizeWindow: () => Promise<void>;
      toggleMaximize: () => Promise<void>;
      /** Read the packaged Electron app version (== electron/package.json#version). */
      getVersion: () => Promise<string>;
    };
  }
}
