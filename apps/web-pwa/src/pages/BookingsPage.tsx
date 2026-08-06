import { Card, CardContent, CardHeader, CardTitle } from "@splashh/ui";

export function BookingsPage() {
  return (
    <main className="container py-6">
      <h1 className="text-2xl font-semibold">Bookings</h1>
      <p className="text-sm text-muted-foreground">Today's bookings view coming soon.</p>
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Placeholder</CardTitle>
        </CardHeader>
        <CardContent>
          Cross-tenant bookings list. To activate: query the `by-resource` endpoint for each
          facility in the tenant and group by start time.
        </CardContent>
      </Card>
    </main>
  );
}
