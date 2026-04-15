"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Gamepad2, Settings, Cpu, Gauge, Joystick } from "lucide-react";
import { motion } from "motion/react";
import { ThemeSwitcher } from "./theme-switcher";
import { WindowControls } from "./window-controls";

const NAV_ITEMS = [
  { href: "/", label: "Games", icon: Gamepad2 },
  { href: "/environment", label: "Environment", icon: Settings },
  { href: "/system", label: "System", icon: Cpu },
  { href: "/mangohud", label: "MangoHud", icon: Gauge },
  { href: "/controllers", label: "Controllers", icon: Joystick },
] as const;

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="relative z-50 flex items-center gap-2 px-6 py-3 bg-surface-elevated/80 backdrop-blur-xl border-b-2 border-neon-cyan/30 shadow-glow-sm app-region-drag">
      <motion.div
        className="flex items-center gap-2 mr-6 select-none"
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Image
          src="/logo-nav.png"
          alt=""
          width={52}
          height={52}
          className="rounded-xl drop-shadow-[0_0_12px_var(--theme-glow-primary)]"
          priority
        />
        <h1 className="text-lg font-bold tracking-wide">
          <span className="text-neon-cyan">Proton</span><span className="text-neon-pink">Shift</span>
        </h1>
      </motion.div>
      <nav className="flex gap-2 app-region-no-drag">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link key={href} href={href}>
              <motion.div
                className={`
                  relative flex items-center gap-2 px-4 py-2 rounded-full
                  border transition-colors cursor-pointer
                  ${
                    active
                      ? "border-transparent text-neon-cyan"
                      : "border-neon-cyan/30 text-text-secondary hover:border-neon-cyan hover:bg-neon-cyan/10 hover:text-neon-cyan"
                  }
                `}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {active && (
                  <motion.div
                    className="absolute inset-0 rounded-full bg-neon-cyan/20 border border-neon-cyan shadow-glow-sm"
                    layoutId="nav-active-pill"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <Icon className="size-4 relative z-10" />
                <span className="text-sm font-medium relative z-10">{label}</span>
              </motion.div>
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-2 app-region-no-drag">
        <ThemeSwitcher />
        <WindowControls />
      </div>
    </header>
  );
}
