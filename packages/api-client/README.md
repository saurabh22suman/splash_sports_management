# @splashh/api-client

Typed fetch layer + auth state shared by the Splashh PWAs. Wraps axios with:

- A Zustand auth store (access token, user, tenant, roles)
- A single-flight silent refresh interceptor on 401
- Typed query keys for TanStack Query
- A query client preset

## Usage

```ts
import { api, useAuthStore, queryKeys, createQueryClient, silentRefresh } from "@splashh/api-client";

// One-time at app root
const queryClient = createQueryClient();

// Read auth anywhere
const isAuthed = useAuthStore((s) => s.isAuthenticated);

// Trigger a silent refresh on app boot
useEffect(() => { silentRefresh().catch(() => undefined); }, []);
```

## Refresh flow

The `api` axios instance attaches `Authorization: Bearer <accessToken>` on
every request via a request interceptor. On 401:

1. The response interceptor calls `silentRefresh()`, which POSTs to
   `/v1/auth/refresh` (cookie is sent automatically).
2. If a refresh is already in flight, concurrent calls share the same promise.
3. On success, the new access token is stored and the original request is
   retried with the new token.
4. On failure, the auth store is cleared.

## Test

```bash
pnpm --filter @splashh/api-client test
```
