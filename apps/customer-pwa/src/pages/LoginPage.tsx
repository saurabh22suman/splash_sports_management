import { useNavigate } from "react-router-dom";
import { LoginForm } from "@/features/auth/LoginForm";

export function LoginPage() {
  const navigate = useNavigate();
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <LoginForm onSuccess={() => navigate("/facilities", { replace: true })} />
    </main>
  );
}
