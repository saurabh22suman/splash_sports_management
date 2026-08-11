export function titleForPath(pathname: string): string {
  if (pathname === "/admin/login") return "Splashh Admin";
  if (pathname === "/admin/users") return "Splashh Admin · Users";
  if (pathname === "/admin/invoices/new") return "Splashh Admin · New invoice";
  if (pathname.startsWith("/admin/invoices/")) return "Splashh Admin · Invoice";
  if (pathname === "/admin/invoices") return "Splashh Admin · Invoices";
  if (pathname === "/admin/facilities/new") return "Splashh Admin · New facility";
  if (pathname.startsWith("/admin/facilities/")) return "Splashh Admin · Facility";
  if (pathname === "/admin") return "Splashh Admin · Facilities";
  if (pathname === "/login") return "Splashh · Log in";
  if (pathname === "/book/bookings") return "Splashh · My bookings";
  if (pathname.startsWith("/book/facilities/")) return "Splashh · Facility details";
  if (pathname === "/book") return "Splashh · Facilities";
  return "Splashh";
}
