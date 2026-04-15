"use client";

import { motion } from "motion/react";

const BLOB_CONFIG = [
  {
    className: "bg-blob-a",
    size: "h-[500px] w-[500px]",
    position: "-top-48 -left-48",
    animation: {
      scale: [1, 1.2, 0.95, 1] as number[],
      x: [0, 80, -40, 0] as number[],
      y: [0, -60, 40, 0] as number[],
    },
    duration: 22,
  },
  {
    className: "bg-blob-b",
    size: "h-[400px] w-[400px]",
    position: "top-1/3 -right-32",
    animation: {
      scale: [1, 0.9, 1.15, 1] as number[],
      x: [0, -70, 30, 0] as number[],
      y: [0, 50, -30, 0] as number[],
    },
    duration: 26,
  },
  {
    className: "bg-blob-c",
    size: "h-[350px] w-[350px]",
    position: "bottom-0 left-1/4",
    animation: {
      scale: [0.95, 1.1, 1, 0.95] as number[],
      x: [0, 60, -50, 0] as number[],
      y: [0, -40, 60, 0] as number[],
    },
    duration: 30,
  },
];

export function AmbientBlobs() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {BLOB_CONFIG.map((blob, i) => (
        <motion.div
          key={i}
          className={`absolute rounded-full blur-[120px] ${blob.size} ${blob.position} ${blob.className}`}
          animate={blob.animation}
          transition={{
            duration: blob.duration,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      ))}
    </div>
  );
}
