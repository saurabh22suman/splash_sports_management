#!/usr/bin/env python3
"""Generate RSA key pair for JWT RS256 signing.

This script creates a key pair for development. In production, keys should be
generated once and stored securely (e.g., in a secrets manager).

Usage:
    python scripts/generate-jwt-keys.py [--output-dir ./secrets]

The script generates:
    - jwt_private.pem: Private key (keep secret!)
    - jwt_public.pem: Public key (can be shared)

Set these environment variables to use the keys:
    export JWT_PRIVATE_KEY_PATH=./secrets/jwt_private.pem
    export JWT_PUBLIC_KEY_PATH=./secrets/jwt_public.pem
    export JWT_ALGORITHM=RS256
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def generate_keypair(output_dir: Path) -> None:
    """Generate RSA-2048 key pair and save to PEM files."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating RSA-2048 key pair in {output_dir}...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_path = output_dir / "jwt_private.pem"
    private_path.write_bytes(private_pem)
    print(f"  Private key: {private_path}")
    print("  IMPORTANT: Keep this file secret! Do not commit to version control.")

    # Generate and save public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_path = output_dir / "jwt_public.pem"
    public_path.write_bytes(public_pem)
    print(f"  Public key:  {public_path}")

    # Set restrictive permissions on private key
    private_path.chmod(0o600)

    print("\nTo use these keys, set environment variables:")
    print(f"  export JWT_PRIVATE_KEY_PATH={private_path}")
    print(f"  export JWT_PUBLIC_KEY_PATH={public_path}")
    print(f"  export JWT_ALGORITHM=RS256")
    print("\nOr add to your .env file:")
    print(f"  JWT_PRIVATE_KEY_PATH={private_path}")
    print(f"  JWT_PUBLIC_KEY_PATH={public_path}")
    print(f"  JWT_ALGORITHM=RS256")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate RSA key pair for JWT RS256 signing")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./secrets"),
        help="Directory to save keys (default: ./secrets)",
    )
    args = parser.parse_args()

    try:
        generate_keypair(args.output_dir)
        return 0
    except Exception as exc:
        print(f"Error generating keys: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
