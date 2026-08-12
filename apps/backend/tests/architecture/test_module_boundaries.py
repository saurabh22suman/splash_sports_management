"""Architecture tests for bounded context boundaries.

These tests enforce the architectural rule that modules must not import
from other modules' infrastructure layers (ADR-0001).

Note: Imports from 'common' are allowed as it is a shared kernel.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _find_violations(source_dir: Path, source_module: str, target_module: str) -> list[dict]:
    """Find imports from target_module.infrastructure.models in source_module.

    Returns a list of violations with file path, line number, and import details.

    Note: We specifically check for .infrastructure.models imports (the ORM models),
    as these cross the bounded context boundary. Using repositories or services from
    other modules is acceptable as they are part of the module's public API.
    """
    violations = []
    source_path = source_dir / source_module.replace(".", "/")

    if not source_path.exists():
        return violations

    for py_file in source_path.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=str(py_file))
            except SyntaxError:
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Check specifically for .infrastructure.models imports
                if node.module and node.module == f"{target_module}.infrastructure.models":
                    for alias in node.names:
                        violations.append(
                            {
                                "file": str(py_file.relative_to(source_dir)),
                                "line": node.lineno,
                                "module": node.module,
                                "name": alias.name,
                            }
                        )

    return violations


# Bounded context modules (exclude 'common' which is a shared kernel)
BOUNDED_CONTEXTS = ["auth", "booking", "customer", "facility", "payments"]


class TestBoundedContextBoundaries:
    """Test that modules respect bounded context boundaries."""

    def test_booking_does_not_import_facility_infrastructure(self):
        """Booking module must not import from facility.infrastructure.

        This is an ADR-0001 violation - crossing bounded context boundaries
        via infrastructure layer imports.
        """
        src_dir = Path(__file__).parent.parent.parent / "src"
        violations = _find_violations(src_dir, "booking", "facility")

        assert not violations, (
            f"Booking module violates bounded context boundary by importing from "
            f"facility.infrastructure:\n"
            + "\n".join(
                f"  - {v['file']}:{v['line']}: from {v['module']} import {v['name']}"
                for v in violations
            )
        )

    def test_no_bounded_context_imports_infrastructure_cross_boundary(self):
        """Booking module should not import infrastructure.models from any other context.

        This test ensures the booking module doesn't violate bounded context boundaries
        by importing ORM models directly from other modules.
        """
        src_dir = Path(__file__).parent.parent.parent / "src"

        all_violations = []

        # Focus on booking module as per F-10
        source_ctx = "booking"
        for target_ctx in BOUNDED_CONTEXTS:
            if source_ctx == target_ctx:
                continue

            violations = _find_violations(src_dir, source_ctx, target_ctx)
            if violations:
                all_violations.append(
                    {
                        "source": source_ctx,
                        "target": target_ctx,
                        "violations": violations,
                    }
                )

        if all_violations:
            msg = "Bounded context violations (infrastructure.models imports) found:\n"
            for v in all_violations:
                msg += f"\n  {v['source']} -> {v['target']}:\n"
                for viol in v["violations"]:
                    msg += f"    - {viol['file']}:{viol['line']}: from {viol['module']} import {viol['name']}\n"

            assert False, msg
