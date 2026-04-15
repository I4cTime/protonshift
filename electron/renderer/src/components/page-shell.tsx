"use client";

import { NavBar } from "./nav-bar";
import { AmbientBlobs } from "./ambient-blobs";
import { motion, AnimatePresence } from "motion/react";
import type { ReactNode } from "react";

const pageVariants = {
  initial: { opacity: 0, y: 16, filter: "blur(6px)" },
  animate: { opacity: 1, y: 0, filter: "blur(0px)" },
  exit: { opacity: 0, y: -10, filter: "blur(4px)" },
};

interface PageShellProps {
  children: ReactNode;
}

export function PageShell({ children }: PageShellProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <AmbientBlobs />
      <NavBar />
      <AnimatePresence mode="wait">
        <motion.main
          className="flex-1 min-h-0 overflow-y-auto p-6"
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={{
            duration: 0.35,
            ease: [0.25, 0.46, 0.45, 0.94],
          }}
        >
          {children}
        </motion.main>
      </AnimatePresence>
    </div>
  );
}
