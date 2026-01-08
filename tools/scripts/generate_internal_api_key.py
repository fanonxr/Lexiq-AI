#!/usr/bin/env python3
"""Generate a secure internal API key for service-to-service authentication.

This script generates a cryptographically secure random key suitable for use
as the INTERNAL_API_KEY for service-to-service authentication.

Usage:
    python3 tools/scripts/generate_internal_api_key.py
    python3 tools/scripts/generate_internal_api_key.py --length 64
    python3 tools/scripts/generate_internal_api_key.py --format env
"""

import argparse
import secrets
import sys


def generate_api_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure random API key.
    
    Args:
        length: Number of random bytes to generate (default: 32, which produces ~43 chars)
    
    Returns:
        URL-safe base64-encoded random string
    """
    return secrets.token_urlsafe(length)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a secure internal API key for service-to-service authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a default key (32 bytes, ~43 characters)
  python3 tools/scripts/generate_internal_api_key.py
  
  # Generate a longer key (64 bytes, ~86 characters)
  python3 tools/scripts/generate_internal_api_key.py --length 64
  
  # Generate key in .env format
  python3 tools/scripts/generate_internal_api_key.py --format env
  
  # Generate key in docker-compose format
  python3 tools/scripts/generate_internal_api_key.py --format docker
        """
    )
    
    parser.add_argument(
        "--length",
        type=int,
        default=32,
        help="Number of random bytes to generate (default: 32, minimum: 16, recommended: 32-64)"
    )
    
    parser.add_argument(
        "--format",
        choices=["raw", "env", "docker"],
        default="raw",
        help="Output format: raw (just the key), env (.env file format), docker (docker-compose format)"
    )
    
    args = parser.parse_args()
    
    # Validate length
    if args.length < 16:
        print("Error: Key length must be at least 16 bytes for security.", file=sys.stderr)
        sys.exit(1)
    
    if args.length > 128:
        print("Warning: Key length exceeds 128 bytes. This may be unnecessarily long.", file=sys.stderr)
    
    # Generate the key
    key = generate_api_key(args.length)
    
    # Output in requested format
    if args.format == "raw":
        print(key)
    elif args.format == "env":
        print("# Internal API Key for service-to-service authentication")
        print(f"INTERNAL_API_KEY_ENABLED=true")
        print(f"INTERNAL_API_KEY={key}")
        print()
        print("# For services calling api-core:")
        print(f"CORE_API_API_KEY={key}")
    elif args.format == "docker":
        print("# Add to your .env file or docker-compose.override.yml:")
        print(f"INTERNAL_API_KEY={key}")
        print()
        print("# Then reference in docker-compose.yml:")
        print("#   environment:")
        print("#     - INTERNAL_API_KEY_ENABLED=true")
        print("#     - INTERNAL_API_KEY=${INTERNAL_API_KEY:-}")
        print("#     - CORE_API_API_KEY=${INTERNAL_API_KEY:-}")
    
    # Print security reminder
    print("\n" + "="*70, file=sys.stderr)
    print("SECURITY REMINDER:", file=sys.stderr)
    print("  - Store this key securely (Azure Key Vault, AWS Secrets Manager, etc.)", file=sys.stderr)
    print("  - Never commit this key to version control", file=sys.stderr)
    print("  - Rotate this key periodically (recommended: every 90 days)", file=sys.stderr)
    print("  - Use the same key for all services (shared secret model)", file=sys.stderr)
    print("="*70, file=sys.stderr)


if __name__ == "__main__":
    main()

