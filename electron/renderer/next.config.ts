import type { NextConfig } from "next";
import path from "path";

const workspaceRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");

const nextConfig: NextConfig = {
  output: "export",
  distDir: "out",
  images: {
    unoptimized: true,
  },
  outputFileTracingRoot: workspaceRoot,
  turbopack: {
    root: workspaceRoot,
  },
};

export default nextConfig;
