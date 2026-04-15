"use client";

import { useRef, type ReactNode, type MouseEvent } from "react";
import { motion, useMotionValue, useTransform } from "motion/react";

interface GlowCardProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export function GlowCard({ children, className = "", delay = 0 }: GlowCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.5);

  const gradientX = useTransform(mouseX, [0, 1], [0, 100]);
  const gradientY = useTransform(mouseY, [0, 1], [0, 100]);

  const glowBackground = useTransform(
    [gradientX, gradientY],
    ([x, y]) =>
      `radial-gradient(circle at ${x}% ${y}%, var(--theme-glow-primary) 0%, transparent 60%)`,
  );
  const glowOpacity = useTransform(mouseX, (v) => (v === 0.5 ? 0 : 0.4));

  function handleMouseMove(e: MouseEvent) {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    mouseX.set((e.clientX - rect.left) / rect.width);
    mouseY.set((e.clientY - rect.top) / rect.height);
  }

  function handleMouseLeave() {
    mouseX.set(0.5);
    mouseY.set(0.5);
  }

  return (
    <motion.div
      ref={ref}
      className="relative overflow-hidden bg-surface-elevated border border-neon-cyan/25 rounded-2xl shadow-card transition-colors hover:border-neon-cyan/40 hover:shadow-glow-md"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.35,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <motion.div
        className="pointer-events-none absolute inset-0 rounded-2xl"
        style={{
          background: glowBackground,
          opacity: glowOpacity,
          marginBottom: 0,
        }}
      />
      <div className={`relative z-10 ${className}`}>{children}</div>
    </motion.div>
  );
}
