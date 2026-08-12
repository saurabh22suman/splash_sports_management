import { queryKeys } from "@splashh/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type FacilityInput,
  type FacilityUpdateInput,
  type ResourceInput,
  type ResourceUpdateInput,
  adminFacilitiesApi,
} from "./api";

export function useAdminFacilities() {
  return useQuery({ queryKey: queryKeys.facilities.list("me"), queryFn: adminFacilitiesApi.list });
}
export function useAdminFacility(id: string | undefined) {
  return useQuery({
    queryKey: id ? queryKeys.facilities.detail(id) : ["facility", "none"],
    queryFn: () => adminFacilitiesApi.get(id!),
    enabled: !!id,
  });
}
export function useAdminResources(facilityId: string | undefined) {
  return useQuery({
    queryKey: facilityId ? queryKeys.resources.listByFacility(facilityId) : ["resources", "none"],
    queryFn: () => adminFacilitiesApi.listResources(facilityId!),
    enabled: !!facilityId,
  });
}
export function useCreateFacility() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: FacilityInput) => adminFacilitiesApi.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["facilities"] });
    },
  });
}
export function useUpdateFacility() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: FacilityUpdateInput }) =>
      adminFacilitiesApi.update(id, input),
    onSuccess: (f) => {
      qc.invalidateQueries({ queryKey: ["facilities"] });
      qc.setQueryData(queryKeys.facilities.detail(f.id), f);
    },
  });
}
export function useDeactivateFacility() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFacilitiesApi.deactivate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["facilities"] });
    },
  });
}
export function useCreateResource(facilityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ResourceInput) => adminFacilitiesApi.createResource(facilityId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.resources.listByFacility(facilityId) });
    },
  });
}
export function useUpdateResource(facilityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: ResourceUpdateInput }) =>
      adminFacilitiesApi.updateResource(id, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.resources.listByFacility(facilityId) });
    },
  });
}
export function useDeactivateResource(facilityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminFacilitiesApi.deactivateResource(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.resources.listByFacility(facilityId) });
    },
  });
}
