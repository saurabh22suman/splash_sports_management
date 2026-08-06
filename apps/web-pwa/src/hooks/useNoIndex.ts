import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function useNoIndex(whenPathStartsWith: string) {
  const { pathname } = useLocation();
  useEffect(() => {
    if (!pathname.startsWith(whenPathStartsWith)) return;
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, [pathname, whenPathStartsWith]);
}
