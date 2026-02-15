#!/usr/bin/env python3
# HB_SCRIPT_KIND: GENERATE
# HB_SCRIPT_SIDE_EFFECTS: FS_READ, FS_WRITE
# HB_SCRIPT_SCOPE: docs
# HB_SCRIPT_IDEMPOTENT: YES
# HB_SCRIPT_ENTRYPOINT: python scripts/generate/docs/generate_docs_soot.py
# HB_SCRIPT_OUTPUTS: generated_docs

"""
Documentation Generation Script for HB Track Backend

Generates: (Hb Track - Backend/docs/_generated/*)
- openapi.json: OpenAPI 3.x specification from FastAPI app
- schema.sql: Database schema dump from PostgreSQL (pg_dump)
- alembic_state.txt: Current migration state (heads + current)
- manifest.json: Generation manifest with git commit, timestamp, and file checksums

Output directory: Hb Track - Backend/docs/_generated/ (backend repo root)

Usage:
    python scripts/generate_docs.py --all
    python scripts/generate_docs.py --openapi
    python scripts/generate_docs.py --schema
    python scripts/generate_docs.py --alembic

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (for schema dump)
    DATABASE_URL_SYNC: PostgreSQL psycopg2 connection string (for alembic, optional)
    BASE_URL: Backend URL for OpenAPI fallback (default: http://localhost:8000)
"""
import argparse
import hashlib
import json
import os
import subprocess
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load .env from backend root
BACKEND_ROOT = Path(__file__).resolve().parent.parent
env_path = BACKEND_ROOT / '.env'
load_dotenv(dotenv_path=env_path)

# Output to backend repo: Hb Track - Backend/docs/_generated/
# Use env var HB_DOCS_GENERATED_DIR if set, else default to docs/_generated
GENERATED_DIR_NAME = os.getenv("HB_DOCS_GENERATED_DIR", "_generated")
OUTPUT_DIR = BACKEND_ROOT / "docs" / GENERATED_DIR_NAME
# Secondary output: repo-level docs/_generated
REPO_OUTPUT_DIR = BACKEND_ROOT.parent / "docs" / GENERATED_DIR_NAME


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=BACKEND_ROOT
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate SHA256 checksum of file."""
    if not file_path.exists():
        return ""
    
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def generate_manifest(output_dir: Path, generated_files: list) -> bool:
    """
    Generate manifest.json with git commit, timestamp, and file checksums.
    
    Args:
        output_dir: Directory containing generated files
        generated_files: List of filenames that were generated
    """
    manifest_file = output_dir / "manifest.json"
    
    try:
        git_commit = get_git_commit()
        generated_at = datetime.now(timezone.utc).isoformat() + "Z"
        
        files_info = []
        for filename in generated_files:
            file_path = output_dir / filename
            files_info.append({
                "filename": filename,
                "checksum": calculate_file_checksum(file_path),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            })
        
        manifest = {
            "git_commit": git_commit,
            "generated_at": generated_at,
            "backend_root": str(BACKEND_ROOT),
            "generator_script": "scripts/generate_docs.py",
            "files": files_info
        }
        
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Manifest written to {manifest_file}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to generate manifest: {e}")
        return False


# =============================================================================
# OPENAPI GENERATION
# =============================================================================

def generate_openapi(output_dir: Path) -> bool:
    """
    Generate openapi.json from FastAPI app.

    Strategy:
    1. Try app.openapi() directly (faster, no server needed)
    2. If fails, fallback to HTTP GET at BASE_URL/api/v1/openapi.json
    """
    output_file = output_dir / "openapi.json"

    # Attempt 1: Direct app.openapi()
    try:
        # Add backend root to path for imports
        sys.path.insert(0, str(BACKEND_ROOT))

        # Set dummy JWT_SECRET if not present (required for config load)
        if not os.getenv("JWT_SECRET"):
            os.environ["JWT_SECRET"] = "dummy-secret-for-openapi-generation"

        from app.main import app
        schema = app.openapi()

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        print(f"[OK] OpenAPI spec written to {output_file}")
        return True

    except Exception as e:
        print(f"[WARN] app.openapi() failed: {e}")

    # Attempt 2: HTTP fallback
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    url = f"{base_url}/api/v1/openapi.json"

    try:
        import urllib.request
        import ssl

        # Create context that allows self-signed certs for local dev
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        print(f"[INFO] Trying HTTP fallback: {url}")

        with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
            schema = json.load(resp)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        print(f"[OK] OpenAPI spec written to {output_file} (via HTTP fallback)")
        return True

    except Exception as e:
        print(f"[ERROR] HTTP fallback also failed: {e}")
        print(f"        Ensure the backend is running at {base_url} or fix import errors")
        return False


# =============================================================================
# TRAINING PERMISSIONS REPORT (docs/_generated)
# =============================================================================

def generate_training_permissions_report() -> bool:
    """
    Generate Training permissions report (docs/_generated/trd_training_permissions_report.txt).
    Runs after OpenAPI generation to keep artifacts deterministic.
    """
    report_script = BACKEND_ROOT.parent / "docs" / "scripts" / "trd_extract_training_permissions_report.py"
    if not report_script.exists():
        print(f"[WARN] Permissions report script not found: {report_script}")
        return False

    try:
        subprocess.run(
            [sys.executable, str(report_script)],
            check=True,
            cwd=BACKEND_ROOT.parent,
        )
        print(f"[OK] Training permissions report generated via {report_script}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to generate permissions report: {e}")
        return False


# =============================================================================
# SCHEMA SQL GENERATION
# =============================================================================

def generate_schema_sql(output_dir: Path) -> bool:
    """
    Generate schema.sql using pg_dump --schema-only.

    Requires:
    - DATABASE_URL environment variable
    - pg_dump installed (PostgreSQL client tools)
    """
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url:
        print("[ERROR] DATABASE_URL not set")
        return False

    # Clean URL: remove driver prefixes
    clean_url = database_url
    clean_url = clean_url.replace("postgresql+asyncpg://", "postgresql://")
    clean_url = clean_url.replace("postgresql+psycopg2://", "postgresql://")
    clean_url = clean_url.replace("postgresql+psycopg://", "postgresql://")

    # Parse connection URL
    parsed = urlparse(clean_url)

    if not all([parsed.hostname, parsed.username, parsed.path]):
        print(f"[ERROR] Invalid DATABASE_URL format")
        return False

    # Build pg_dump command
    pg_dump_args = [
        "pg_dump",
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        "-h", parsed.hostname,
        "-p", str(parsed.port or 5432),
        "-U", parsed.username,
        "-d", parsed.path.lstrip("/").split("?")[0],  # Remove query params
    ]

    # Set password via environment
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""

    # Handle SSL mode for Neon
    if "sslmode" in database_url:
        env["PGSSLMODE"] = "require"

    output_file = output_dir / "schema.sql"

    try:
        print(f"[INFO] Running pg_dump for {parsed.hostname}...")

        # Use text=False to capture bytes (avoids encoding issues)
        result = subprocess.run(
            pg_dump_args,
            capture_output=True,
            text=False,
            env=env,
            timeout=120,  # 2 minutes for remote DBs
            check=False,
        )

        if result.returncode != 0:
            err = (result.stderr or b"").decode("utf-8", errors="replace")
            print(f"[ERROR] pg_dump failed: {err}")
            return False

        # Write as bytes to preserve encoding
        header = f"-- Schema dump generated: {datetime.now(timezone.utc).isoformat()}Z\n"
        header += f"-- Source: {parsed.hostname}\n\n"

        with open(output_file, "wb") as f:
            f.write(header.encode("utf-8"))
            f.write(result.stdout or b"")

        print(f"[OK] Schema written to {output_file}")
        return True

    except FileNotFoundError:
        print("[ERROR] pg_dump not found. Install PostgreSQL client tools:")
        print("        Windows: https://www.postgresql.org/download/windows/")
        print("        macOS: brew install libpq")
        print("        Linux: apt install postgresql-client")
        return False

    except subprocess.TimeoutExpired:
        print("[ERROR] pg_dump timed out (network issue or large schema)")
        return False


# =============================================================================
# ALEMBIC STATE GENERATION
# =============================================================================

def generate_alembic_state(output_dir: Path) -> bool:
    """
    Generate alembic_state.txt with heads and current revision.

    Uses:
    - DATABASE_URL_SYNC if set
    - Falls back to DATABASE_URL (converts to psycopg2 format)
    """
    db_url_sync = os.getenv("DATABASE_URL_SYNC")
    db_url = os.getenv("DATABASE_URL")

    if not db_url_sync and not db_url:
        print("[ERROR] DATABASE_URL_SYNC or DATABASE_URL must be set")
        return False

    alembic_ini = BACKEND_ROOT / "alembic.ini"

    if not alembic_ini.exists():
        print(f"[ERROR] alembic.ini not found at {alembic_ini}")
        return False

    # Prepare environment
    env = os.environ.copy()

    # If DATABASE_URL_SYNC not set, derive from DATABASE_URL
    if not db_url_sync and db_url:
        sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        # Ensure it has psycopg2 driver
        if not sync_url.startswith("postgresql+psycopg2://"):
            sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")
        env["DATABASE_URL_SYNC"] = sync_url
        print(f"[INFO] Using DATABASE_URL converted to sync format")

    output_file = output_dir / "alembic_state.txt"
    output_lines = []

    try:
        # Get alembic heads
        print("[INFO] Running alembic heads...")
        result_heads = subprocess.run(
            ["alembic", "-c", str(alembic_ini), "heads"],
            capture_output=True,
            text=True,
            cwd=BACKEND_ROOT,
            env=env,
            timeout=30
        )

        output_lines.append("=== ALEMBIC HEADS ===")
        output_lines.append(result_heads.stdout.strip() or "(no output)")
        if result_heads.returncode != 0 and result_heads.stderr:
            output_lines.append(f"stderr: {result_heads.stderr.strip()}")
        output_lines.append("")

        # Get alembic current
        print("[INFO] Running alembic current...")
        result_current = subprocess.run(
            ["alembic", "-c", str(alembic_ini), "current"],
            capture_output=True,
            text=True,
            cwd=BACKEND_ROOT,
            env=env,
            timeout=30
        )

        output_lines.append("=== ALEMBIC CURRENT ===")
        output_lines.append(result_current.stdout.strip() or "(no output)")
        if result_current.returncode != 0 and result_current.stderr:
            output_lines.append(f"stderr: {result_current.stderr.strip()}")
        output_lines.append("")

        # Add timestamp
        output_lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}Z")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))

        print(f"[OK] Alembic state written to {output_file}")
        return True

    except FileNotFoundError:
        print("[ERROR] alembic command not found. Install with: pip install alembic")
        return False

    except subprocess.TimeoutExpired:
        print("[ERROR] Alembic command timed out")
        return False


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate documentation artifacts for HB Track",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--all", action="store_true", help="Generate all docs (default)")
    parser.add_argument("--openapi", action="store_true", help="Generate openapi.json")
    parser.add_argument("--schema", action="store_true", help="Generate schema.sql")
    parser.add_argument("--alembic", action="store_true", help="Generate alembic_state.txt")
    parser.add_argument("--output", type=str, help="Custom output directory")

    args = parser.parse_args()

    # Default to --all if no specific flag
    if not (args.openapi or args.schema or args.alembic):
        args.all = True

    # Determine output directory
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"HB Track Documentation Generator")
    print(f"{'='*60}")
    print(f"Output directory: {output_dir}")
    print(f"Backend root: {BACKEND_ROOT}")
    print(f"{'='*60}\n")

    results = []
    generated_files = []

    if args.all or args.openapi:
        success = generate_openapi(output_dir)
        results.append(("OpenAPI", success))
        if success:
            generated_files.append("openapi.json")
            # copy to repo-level docs
            try:
                REPO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output_dir / "openapi.json", REPO_OUTPUT_DIR / "openapi.json")
            except Exception:
                pass
            perm_success = generate_training_permissions_report()
            results.append(("Training Permissions Report", perm_success))

    if args.all or args.schema:
        success = generate_schema_sql(output_dir)
        results.append(("Schema SQL", success))
        if success:
            generated_files.append("schema.sql")
            try:
                REPO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output_dir / "schema.sql", REPO_OUTPUT_DIR / "schema.sql")
            except Exception:
                pass

    if args.all or args.alembic:
        success = generate_alembic_state(output_dir)
        results.append(("Alembic State", success))
        if success:
            generated_files.append("alembic_state.txt")
            try:
                REPO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(output_dir / "alembic_state.txt", REPO_OUTPUT_DIR / "alembic_state.txt")
            except Exception:
                pass

    # Generate manifest with all successfully generated files
    if generated_files:
        manifest_success = generate_manifest(output_dir, generated_files)
        results.append(("Manifest", manifest_success))
        # also produce a manifest in repo-level docs
        try:
            REPO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            manifest_success_repo = generate_manifest(REPO_OUTPUT_DIR, generated_files)
            results.append(("Manifest (repo)", manifest_success_repo))
        except Exception:
            results.append(("Manifest (repo)", False))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, success in results:
        status = "[OK]" if success else "[FAILED]"
        print(f"  {status} {name}")

    print(f"\nOutput files in: {output_dir}")

    all_success = all(success for _, success in results)
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()