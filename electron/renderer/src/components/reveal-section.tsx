"use client";

import { useRef, type ReactNode } from "react";
import { motion, useInView } from "motion/react";

interface RevealSectionProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  /** Anchor id for in-page navigation (e.g. FloatingToc). */
  sectionId?: string;
}

export function RevealSection({ children, className = "", delay = 0, sectionId }: RevealSectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <motion.div
      ref={ref}
      id={sectionId}
      className={className}
      initial={{ opacity: 0, y: 24, filter: "blur(4px)" }}
      animate={
        isInView
          ? { opacity: 1, y: 0, filter: "blur(0px)" }
          : { opacity: 0, y: 24, filter: "blur(4px)" }
      }
      transition={{
        duration: 0.5,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
    >
      {children}
    </motion.div>
  );
}
