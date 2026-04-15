export {};

declare global {
  interface Window {
    /** Frameless window controls (only present in the Electron shell). */
    electron?: {
      closeWindow: () => Promise<void>;
      minimizeWindow: () => Promise<void>;
      toggleMaximize: () => Promise<void>;
    };
  }
}
