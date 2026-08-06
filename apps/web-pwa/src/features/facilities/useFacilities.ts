import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@splashh/api-client";
import { facilitiesApi } from "./api";

export function useFacilities() {
  return useQuery({ queryKey: queryKeys.facilities.list("me"), queryFn: facilitiesApi.list });
}
export function useFacility(id: string | undefined) {
  return useQuery({
    queryKey: id ? queryKeys.facilities.detail(id) : ["facility", "none"],
    queryFn: () => facilitiesApi.get(id!),
    enabled: !!id,
  });
}
export function useResources(facilityId: string | undefined) {
  return useQuery({
    queryKey: facilityId ? queryKeys.resources.listByFacility(facilityId) : ["resources", "none"],
    queryFn: () => facilitiesApi.listResources(facilityId!),
    enabled: !!facilityId,
  });
}
