import { useNoIndex } from "../hooks/useNoIndex";

export function NoIndexOnAdmin() {
  useNoIndex("/admin");
  return null;
}
