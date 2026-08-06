import { Button } from "@splashh/ui";
import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="text-4xl font-bold">Splashh Sports</h1>
      <p className="text-muted-foreground">Book your club in seconds.</p>
      <Button asChild>
        <Link to="/login">Log in</Link>
      </Button>
    </main>
  );
}
