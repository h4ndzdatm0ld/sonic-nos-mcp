#!/usr/bin/env python3
"""Scripts for code formatting and validation."""

import subprocess
import sys


def format_code() -> None:
    """Run comprehensive code formatting and validation."""
    print("🚀 Running comprehensive code formatting and validation...")

    # Define source directories
    src_dirs = ["src/", "test/"]

    # Step 1: Run ruff formatting (auto-fix)
    print("\n📝 Step 1: Ruff formatting...")
    try:
        result = subprocess.run(["uv", "run", "ruff", "format"] + src_dirs, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("✅ Ruff formatting completed")
            if result.stdout.strip():
                print(f"📄 Output: {result.stdout.strip()}")
        else:
            print(f"❌ Ruff formatting failed: {result.stderr}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ruff formatting error: {e}")
        sys.exit(1)

    # Step 2: Run ruff linting with auto-fix
    print("\n🔍 Step 2: Ruff linting (with auto-fix)...")
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "--fix"] + src_dirs, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("✅ Ruff linting passed")
            if result.stdout.strip():
                print(f"📄 Output: {result.stdout.strip()}")
        else:
            print(f"❌ Ruff linting failed: {result.stderr}")
            if result.stdout.strip():
                print(f"📄 Output: {result.stdout.strip()}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ruff linting error: {e}")
        sys.exit(1)

    # Step 3: Run black formatting (backup formatter)
    print("\n⚫ Step 3: Black formatting...")
    try:
        result = subprocess.run(
            ["uv", "run", "hatch", "run", "black"] + src_dirs, capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            print("✅ Black formatting completed")
            if result.stdout.strip():
                print(f"📄 Output: {result.stdout.strip()}")
        else:
            print(f"❌ Black formatting failed: {result.stderr}")
            # Don't exit on black failure if ruff worked
            print("⚠️  Continuing since ruff formatting succeeded...")
    except Exception as e:
        print(f"⚠️  Black formatting error (continuing): {e}")

    # Step 4: Validate with ruff check (final validation)
    print("\n🔍 Step 4: Final ruff validation...")
    try:
        result = subprocess.run(["uv", "run", "ruff", "check"] + src_dirs, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("✅ Final ruff validation passed")
        else:
            print(f"❌ Final ruff validation failed: {result.stderr}")
            print(f"📄 Output: {result.stdout}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ruff validation error: {e}")
        sys.exit(1)

    # Step 5: MyPy type checking validation
    print("\n🔧 Step 5: MyPy type checking...")
    try:
        result = subprocess.run(["uv", "run", "mypy", "src/"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("✅ MyPy type checking passed")
        else:
            print("❌ MyPy type checking failed:")
            print(f"📄 Errors:\n{result.stdout}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ MyPy type checking error: {e}")
        sys.exit(1)

    print("\n🎉 All formatting and validation steps completed successfully!")
    print("📋 Summary:")
    print("  ✅ Ruff formatting applied")
    print("  ✅ Ruff linting issues fixed")
    print("  ✅ Black formatting applied")
    print("  ✅ Final ruff validation passed")
    print("  ✅ MyPy type checking passed")


if __name__ == "__main__":
    format_code()
