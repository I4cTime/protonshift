"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useSystemInfo() {
  return useQuery({
    queryKey: ["system"],
    queryFn: api.getSystemInfo,
    staleTime: 15_000,
  });
}

export function useSetPowerProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profile: string) => api.setPowerProfile(profile),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["system"] });
    },
  });
}
