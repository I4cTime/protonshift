"use client";

import type { ReactNode } from "react";
import { toast } from "@heroui/react";

/** App-wide notifications via HeroUI toast (requires `<ToastProvider>` in `providers.tsx`). */
export function appShowToast(message: ReactNode, kind: "success" | "error" = "success") {
  if (kind === "error") {
    return toast.danger(message, { timeout: 5000 });
  }
  return toast.success(message, { timeout: 4000 });
}
