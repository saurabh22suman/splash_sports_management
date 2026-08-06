import { Button } from "@splashh/ui";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@splashh/api-client";
import { homeForRoles } from "../lib/role-routing";

export function RoleMismatch({ required }: { required: string[] }) {
  const navigate = useNavigate();
  const roles = useAuthStore((s) => s.roles);
  const home = homeForRoles(roles);
  return (
    <main className="container max-w-md py-12 text-center">
      <h1 className="text-2xl font-semibold">Not authorized</h1>
      <p className="mt-2 text-muted-foreground">
        This area is for {required.join(" / ")} only.
      </p>
      <div className="mt-6 flex justify-center gap-2">
        <Button onClick={() => navigate(home, { replace: true })}>Go to your home</Button>
        <Button variant="ghost" asChild>
          <Link to="/login">Switch account</Link>
        </Button>
      </div>
    </main>
  );
}
