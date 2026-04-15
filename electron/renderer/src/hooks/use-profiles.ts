"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ProfileData } from "@/lib/api";

export function useProfiles() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: api.getProfiles,
    staleTime: 10_000,
  });
}

export function useProfile(name: string | null) {
  return useQuery({
    queryKey: ["profile", name],
    queryFn: () => api.getProfile(name!),
    enabled: !!name,
  });
}

export function useSaveProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profile: ProfileData) => api.saveProfile(profile),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profiles"] });
    },
  });
}

export function useDeleteProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.deleteProfile(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profiles"] });
    },
  });
}
