"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useEnvVars() {
  return useQuery({
    queryKey: ["env-vars"],
    queryFn: api.getEnvVars,
    staleTime: 10_000,
  });
}

export function useSetEnvVars() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: Record<string, string>) => api.setEnvVars(vars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["env-vars"] });
    },
  });
}

export function useEnvPresets() {
  return useQuery({
    queryKey: ["env-presets"],
    queryFn: api.getEnvPresets,
    staleTime: 60_000,
  });
}
