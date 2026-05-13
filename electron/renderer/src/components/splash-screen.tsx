"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import Image from "next/image";

type SplashPhase = "shown" | "fading" | "gone";

const EASE_OUT_CUBIC = [0.25, 0.46, 0.45, 0.94] as const;

export function SplashScreen() {
  const [phase, setPhase] = useState<SplashPhase>("shown");
  const reduceMotion = useReducedMotion() ?? false;

  useEffect(() => {
    const timer = setTimeout(() => setPhase("fading"), 2000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (phase !== "fading") return;
    const hide = setTimeout(() => setPhase("gone"), 650);
    return () => clearTimeout(hide);
  }, [phase]);

  if (phase === "gone") return null;

  return (
    <motion.div
      role="status"
      aria-label="Starting ProtonShift"
      className="fixed inset-0 z-[9999] overflow-hidden bg-background"
      style={{ pointerEvents: phase === "fading" ? "none" : "auto" }}
      initial={{ opacity: 1 }}
      animate={{
        opacity: phase === "shown" ? 1 : 0,
        filter: phase === "shown" ? "blur(0px)" : "blur(12px)",
      }}
      transition={{ duration: 0.6, ease: EASE_OUT_CUBIC }}
    >
      <AmbientBlobs />
      <ScanGrid />
      <HudCorners />
      <ShimmerEdges />

      <div className="relative z-10 flex h-full w-full flex-col items-center justify-center px-8">
        <div className="relative">
          {!reduceMotion && (
            <motion.div
              className="pointer-events-none absolute -inset-16 rounded-full opacity-50 blur-3xl"
              style={{
                background:
                  "conic-gradient(from 0deg, var(--theme-accent), var(--theme-secondary), var(--theme-tertiary), var(--theme-accent))",
              }}
              animate={{ rotate: 360 }}
              transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
              aria-hidden
            />
          )}

          <motion.div
            className="pointer-events-none absolute -inset-10 rounded-full border border-neon-cyan/25"
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: EASE_OUT_CUBIC, delay: 0.15 }}
            aria-hidden
          />
          <motion.div
            className="pointer-events-none absolute -inset-5 rounded-full border border-neon-cyan/15"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: EASE_OUT_CUBIC, delay: 0.25 }}
            aria-hidden
          />

          {!reduceMotion && (
            <motion.div
              className="pointer-events-none absolute -inset-10"
              animate={{ rotate: 360 }}
              transition={{ duration: 4.5, repeat: Infinity, ease: "linear" }}
              aria-hidden
            >
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  background:
                    "conic-gradient(from 0deg, transparent 0deg, var(--theme-accent) 36deg, transparent 80deg)",
                  WebkitMaskImage:
                    "radial-gradient(circle, transparent 48%, black 48.5%, black 50%, transparent 50.5%)",
                  maskImage:
                    "radial-gradient(circle, transparent 48%, black 48.5%, black 50%, transparent 50.5%)",
                }}
              />
            </motion.div>
          )}

          <motion.div
            initial={{ opacity: 0, scale: 0.85, y: 18, filter: "blur(16px)" }}
            animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease: EASE_OUT_CUBIC }}
            className="relative"
          >
            <Image
              src="/splash.png"
              alt="ProtonShift"
              width={240}
              height={240}
              priority
              className="relative z-10 drop-shadow-[0_0_60px_var(--theme-glow-primary)]"
            />
          </motion.div>
        </div>

        <motion.div
          className="mt-7 flex flex-col items-center gap-2"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.5, ease: EASE_OUT_CUBIC }}
        >
          <h1
            className="text-2xl font-bold uppercase tracking-[0.32em] text-foreground"
            style={{
              textShadow:
                "1px 0 0 var(--theme-secondary), -1px 0 0 var(--theme-accent), 0 0 30px var(--theme-glow-primary)",
            }}
          >
            ProtonShift
          </h1>
          <div
            className="h-px w-44 opacity-90"
            style={{
              background:
                "linear-gradient(90deg, transparent 0%, var(--theme-accent) 50%, transparent 100%)",
            }}
            aria-hidden
          />
        </motion.div>

        <motion.div
          className="mt-8 flex w-64 flex-col items-center gap-3"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55, duration: 0.4, ease: EASE_OUT_CUBIC }}
        >
          <div className="relative h-px w-full overflow-hidden rounded-full bg-neon-cyan/15">
            <motion.div
              className="absolute inset-y-0 w-1/3 rounded-full"
              style={{
                background:
                  "linear-gradient(90deg, transparent, var(--theme-accent), transparent)",
                boxShadow: "0 0 8px var(--theme-glow-primary)",
              }}
              animate={reduceMotion ? { x: "0%" } : { x: ["-100%", "300%"] }}
              transition={{
                duration: 1.4,
                repeat: reduceMotion ? 0 : Infinity,
                ease: "easeInOut",
              }}
              aria-hidden
            />
          </div>
          <div className="flex items-center gap-2.5">
            <div className="flex gap-1" aria-hidden>
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="size-1.5 shrink-0 rounded-full bg-neon-cyan shadow-[0_0_6px_var(--theme-glow-primary)]"
                  animate={{ opacity: reduceMotion ? 1 : [0.2, 1, 0.2] }}
                  transition={{
                    duration: 1.2,
                    repeat: reduceMotion ? 0 : Infinity,
                    delay: i * 0.2,
                    ease: "easeInOut",
                  }}
                />
              ))}
            </div>
            <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-text-muted">
              Initializing core
            </span>
          </div>
        </motion.div>

        <motion.p
          className="mt-10 font-mono text-[10px] uppercase tracking-[0.35em] text-text-muted/50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.85, duration: 0.5 }}
        >
          Linux Game Configuration Toolkit
        </motion.p>
      </div>

      <motion.div
        className="pointer-events-none absolute bottom-5 left-6 font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted/40"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.0, duration: 0.4 }}
        aria-hidden
      >
        REV 0.8 · BUILD A
      </motion.div>

      <motion.div
        className="pointer-events-none absolute bottom-5 right-6 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-text-muted/40"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.0, duration: 0.4 }}
        aria-hidden
      >
        <span className="size-1 rounded-full bg-success shadow-[0_0_6px_rgba(34,197,94,0.55)]" />
        <span>System · Online</span>
      </motion.div>
    </motion.div>
  );
}

function AmbientBlobs() {
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden>
      <div
        className="absolute -top-1/3 left-1/2 size-[80vmin] -translate-x-1/2 rounded-full opacity-90 blur-[80px]"
        style={{
          background: "radial-gradient(circle, var(--color-blob-a), transparent 60%)",
        }}
      />
      <div
        className="absolute -bottom-1/3 left-[15%] size-[60vmin] rounded-full opacity-80 blur-[100px]"
        style={{
          background: "radial-gradient(circle, var(--color-blob-b), transparent 60%)",
        }}
      />
      <div
        className="absolute -bottom-1/4 right-[10%] size-[55vmin] rounded-full opacity-70 blur-[100px]"
        style={{
          background: "radial-gradient(circle, var(--color-blob-c), transparent 60%)",
        }}
      />
    </div>
  );
}

function ScanGrid() {
  return (
    <div
      className="pointer-events-none absolute inset-0 opacity-[0.07]"
      style={{
        backgroundImage:
          "linear-gradient(var(--theme-accent) 1px, transparent 1px), linear-gradient(90deg, var(--theme-accent) 1px, transparent 1px)",
        backgroundSize: "44px 44px",
        WebkitMaskImage:
          "radial-gradient(ellipse at center, black 25%, transparent 80%)",
        maskImage: "radial-gradient(ellipse at center, black 25%, transparent 80%)",
      }}
      aria-hidden
    />
  );
}

function HudCorners() {
  const corners = [
    { className: "top-6 left-6 border-l border-t rounded-tl-md", delay: 0.1 },
    { className: "top-6 right-6 border-r border-t rounded-tr-md", delay: 0.15 },
    { className: "bottom-6 left-6 border-l border-b rounded-bl-md", delay: 0.2 },
    { className: "bottom-6 right-6 border-r border-b rounded-br-md", delay: 0.25 },
  ] as const;

  return (
    <div aria-hidden>
      {corners.map(({ className, delay }) => (
        <motion.div
          key={className}
          className={`pointer-events-none absolute size-12 border-neon-cyan/45 ${className}`}
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: EASE_OUT_CUBIC, delay }}
        />
      ))}
    </div>
  );
}

function ShimmerEdges() {
  return (
    <>
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px opacity-50"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, var(--theme-accent) 18%, var(--theme-secondary) 50%, var(--theme-tertiary) 82%, transparent 100%)",
        }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px opacity-60"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, var(--theme-accent) 18%, var(--theme-secondary) 50%, var(--theme-tertiary) 82%, transparent 100%)",
        }}
        aria-hidden
      />
    </>
  );
}
