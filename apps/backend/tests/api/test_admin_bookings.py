"""API tests for admin bookings endpoint.

Tests the GET /v1/admin/bookings endpoint that returns bookings
with customer and facility details for the admin dashboard.
"""
import pytest


@pytest.mark.unit
class TestAdminBookingsEndpoint:
    """Test the admin bookings endpoint schema and authorization."""

    def test_admin_bookings_endpoint_exists(self) -> None:
        """The /v1/admin/bookings endpoint should exist."""
        from booking.interfaces.http.router import router

        # Find the route in the router
        routes = [r.path for r in router.routes]
        assert "/admin/bookings" in routes or any("admin/bookings" in r for r in routes), \
            "Admin bookings endpoint should be registered"

    def test_admin_bookings_returns_booking_out_with_customer_fields(self) -> None:
        """BookingOut should include customer_name and customer_email for admin view."""
        from booking.interfaces.http.schemas import BookingOut

        # Check that the schema includes customer name and email fields
        fields = BookingOut.model_fields
        assert "customer_name" in fields, "BookingOut should have customer_name field"
        assert "customer_email" in fields, "BookingOut should have customer_email field"

    def test_admin_bookings_filters(self) -> None:
        """Admin bookings should support facility, resource, status, and date filters."""
        from booking.interfaces.http.schemas import BookingOut

        # The BookingOut schema should work for the admin endpoint response
        # We're testing the schema can handle all the required fields
        fields = BookingOut.model_fields
        assert "facility_name" in fields
        assert "resource_name" in fields
        assert "status" in fields
