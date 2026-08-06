import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@splashh/api-client";
import { adminFacilitiesApi, type FacilityInput, type ResourceInput } from "./api";

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
export function useCreateResource(facilityId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ResourceInput) => adminFacilitiesApi.createResource(facilityId, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.resources.listByFacility(facilityId) });
    },
  });
}
