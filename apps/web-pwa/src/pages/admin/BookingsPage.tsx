import { useMemo, useState } from "react";
import { Button, Card, CardContent, CardHeader, CardTitle, StatusPill } from "@splashh/ui";
import { useAdminBookings, type AdminBookingsParams } from "@/features/bookings/useAdminBookings";
import { useAdminFacilities } from "@/features/admin/facilities/useAdminFacilities";

function formatTime(dateString: string): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(new Date(dateString));
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(dateString));
}

function getDateString(date: Date): string {
  return date.toISOString().split("T")[0] ?? "";
}

function getStartOfDay(date: Date): string {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

function getEndOfDay(date: Date): string {
  const d = new Date(date);
  d.setHours(23, 59, 59, 999);
  return d.toISOString();
}

// Map API booking status to StatusPill status
function mapStatusToPill(status: string): "confirmed" | "cancelled" | "completed" | "pending" | "failed" {
  switch (status) {
    case "confirmed":
      return "confirmed";
    case "cancelled":
      return "cancelled";
    case "completed":
      return "completed";
    case "checked_in":
      return "confirmed"; // Use confirmed as proxy for checked in
    case "no_show":
      return "failed";
    default:
      return "pending";
  }
}

export function BookingsPage() {
  const [selectedDate, setSelectedDate] = useState<string>(getDateString(new Date()));
  const [selectedFacility, setSelectedFacility] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");

  // Build query params
  const queryParams = useMemo<AdminBookingsParams>(() => {
    const date = selectedDate ? new Date(selectedDate) : new Date();
    return {
      fromAt: getStartOfDay(date),
      toAt: getEndOfDay(date),
      facilityId: selectedFacility !== "all" ? selectedFacility : undefined,
      status: selectedStatus !== "all" ? [selectedStatus as "confirmed" | "cancelled" | "completed" | "no_show"] : undefined,
    };
  }, [selectedDate, selectedFacility, selectedStatus]);

  const { data: bookings, isLoading, error, refetch } = useAdminBookings(queryParams);
  const { data: facilities } = useAdminFacilities();

  // Status options for button filter
  const statusOptions = [
    { value: "all", label: "All" },
    { value: "confirmed", label: "Confirmed" },
    { value: "cancelled", label: "Cancelled" },
    { value: "completed", label: "Completed" },
    { value: "no_show", label: "No Show" },
  ];

  // Facility options for button filter
  const facilityOptions = useMemo(() => {
    const opts = [{ value: "all", label: "All Facilities" }];
    if (facilities) {
      facilities.forEach((f) => {
        opts.push({ value: f.id, label: f.name });
      });
    }
    return opts;
  }, [facilities]);

  // Date navigation
  const goToPreviousDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    setSelectedDate(getDateString(d));
  };

  const goToNextDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    setSelectedDate(getDateString(d));
  };

  const goToToday = () => {
    setSelectedDate(getDateString(new Date()));
  };

  return (
    <div className="container py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Bookings</h1>
      </div>

      {/* Date Navigation */}
      <div className="mb-4 flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={goToPreviousDay}>
          Previous
        </Button>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <Button variant="outline" size="sm" onClick={goToNextDay}>
          Next
        </Button>
        <Button variant="ghost" size="sm" onClick={goToToday}>
          Today
        </Button>
      </div>

      {/* Status Filter Buttons */}
      <div className="mb-3 flex flex-wrap gap-2">
        {statusOptions.map((opt) => (
          <Button
            key={opt.value}
            variant={(selectedStatus ?? "all") === opt.value ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedStatus(opt.value)}
          >
            {opt.label}
          </Button>
        ))}
      </div>

      {/* Facility Filter Buttons */}
      <div className="mb-4 flex flex-wrap gap-2">
        {facilityOptions.slice(0, 6).map((opt) => (
          <Button
            key={opt.value}
            variant={(selectedFacility ?? "all") === opt.value ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedFacility(opt.value)}
          >
            {opt.label}
          </Button>
        ))}
        {facilityOptions.length > 6 && (
          <span className="text-sm text-muted-foreground self-center">
            +{facilityOptions.length - 6} more
          </span>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading bookings...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="rounded-none border border-destructive p-4 text-center">
          <p className="text-destructive mb-3">Failed to load bookings.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      )}

      {/* Empty state */}
      {bookings?.length === 0 && !isLoading && !error && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No bookings for {formatDate(selectedDate)}</p>
          </CardContent>
        </Card>
      )}

      {/* Bookings list */}
      {bookings && bookings.length > 0 && (
        <>
          {/* Mobile: card list */}
          <ul className="space-y-3 md:hidden" role="list">
            {bookings.map((booking, idx) => (
              <li
                key={booking.id}
                className="border-2 border-border bg-card p-4 animate-rise-up motion-reduce:animate-none"
                style={{ animationDelay: `${Math.min(idx * 60, 480)}ms` }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{booking.resource_name || "Unknown Resource"}</span>
                  <StatusPill status={mapStatusToPill(booking.status)} />
                </div>
                <div className="text-sm text-muted-foreground mb-1">
                  {booking.customer_name || "Unknown Customer"}
                </div>
                <div className="text-sm text-muted-foreground mb-1">
                  {booking.customer_email}
                </div>
                <div className="text-sm font-mono">
                  {formatTime(booking.start_at)} - {formatTime(booking.end_at)}
                </div>
                {booking.facility_name && (
                  <div className="text-xs text-muted-foreground mt-1">
                    {booking.facility_name}
                  </div>
                )}
              </li>
            ))}
          </ul>

          {/* Desktop: table */}
          <Card className="hidden md:block">
            <CardHeader className="sr-only">
              <CardTitle>Bookings list</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full">
                <thead>
                  <tr className="border-b text-left text-sm text-muted-foreground">
                    <th className="pb-2 font-medium">Time</th>
                    <th className="pb-2 font-medium">Resource</th>
                    <th className="pb-2 font-medium">Customer</th>
                    <th className="pb-2 font-medium">Facility</th>
                    <th className="pb-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {bookings.map((booking, idx) => (
                    <tr
                      key={booking.id}
                      className="border-b last:border-0 animate-rise-up motion-reduce:animate-none transition-colors duration-250 ease-swim hover:bg-secondary/40"
                      style={{ animationDelay: `${Math.min(idx * 60, 480)}ms` }}
                    >
                      <td className="py-3 font-mono text-sm">
                        {formatTime(booking.start_at)} - {formatTime(booking.end_at)}
                      </td>
                      <td className="py-3 text-sm">
                        {booking.resource_name || "Unknown Resource"}
                      </td>
                      <td className="py-3 text-sm">
                        <div>{booking.customer_name || "Unknown Customer"}</div>
                        <div className="text-xs text-muted-foreground">{booking.customer_email}</div>
                      </td>
                      <td className="py-3 text-sm text-muted-foreground">
                        {booking.facility_name || "-"}
                      </td>
                      <td className="py-3">
                        <StatusPill status={mapStatusToPill(booking.status)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
