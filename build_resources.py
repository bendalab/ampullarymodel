#!/usr/bin/env python3
"""
Build script to compile Qt resource files (.qrc) to Python modules.
This script is executed during package build to ensure resources are available.
"""

import subprocess
import sys

from pathlib import Path


def compile_resources():
    """Compile all .qrc files in the project to Python modules."""
    project_root = Path(__file__).parent
    ampullary_ui_dir = project_root / "ampullary_ui"

    # Look for .qrc files
    qrc_files = list(ampullary_ui_dir.glob("*.qrc"))

    if not qrc_files:
        print("No .qrc files found to compile.")
        return True

    # Check if pyside6-rcc is available
    try:
        result = subprocess.run(["pyside6-rcc", "--version"],
                                capture_output=True, text=True, check=True)
        print(f"Using {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: pyside6-rcc not found. Please install PySide6.")
        return False

    success = True
    for qrc_file in qrc_files:
        # Generate output filename: resources.qrc -> resources_rc.py
        output_name = qrc_file.stem + "_rc.py"

        try:
            print(f"Compiling {qrc_file.name} -> {output_name}")
            # Change to the directory containing the .qrc file to handle relative paths
            subprocess.run(["pyside6-rcc", str(qrc_file.name), "-o", str(output_name)],
                           cwd=qrc_file.parent, check=True)
            print(f"Successfully compiled {qrc_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"Error compiling {qrc_file.name}: {e}")
            success = False

    return success


def main():
    """Main entry point for the build script."""
    print("Building Qt resources...")

    if compile_resources():
        print("Resource compilation completed successfully.")
        return 0
    else:
        print("Resource compilation failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
