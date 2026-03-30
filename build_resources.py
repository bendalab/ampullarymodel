#!/usr/bin/env python3
"""
Build script to compile Qt resource and ui files (.qrc, .ui) to Python modules.
This script is executed during package build to ensure resources are available.
"""
import argparse
import subprocess
import sys

from pathlib import Path

def check_pyside_tool(tool):
    # Check if pyside6-* tool is available
    try:
        result = subprocess.run([tool, "--version"],
                                capture_output=True, text=True, check=True)
        print(f"Using {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"Error: {tool} not found. Please install PySide6.")
        return False
    return True


def compile_resources():
    """Compile all .qrc files in the project to Python modules."""
    project_root = Path(__file__).parent
    ampullary_ui_dir = project_root / "ampullary_ui"

    # Look for .qrc files
    qrc_files = list(ampullary_ui_dir.glob("*.qrc"))

    if not qrc_files:
        print("No .qrc files found to compile.")
        return True

    if not check_pyside_tool("pyside6-rcc"):
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

def compile_gui():
    """Compile all .ui files in the project to Python modules."""
    project_root = Path(__file__).parent
    package_dir = project_root / "ampullary_ui"

    # Look for .qrc files
    ui_files = list(package_dir.rglob("*.ui"))

    if not ui_files:
        print("No .ui files found to compile.")
        return True

    # Check if pyside6-uic is available
    if not check_pyside_tool("pyside6-uic"):
        return False

    success = True
    for ui_file in ui_files:
        output_name = f"{ui_file.stem}_{ui_file.suffix[1:]}.py"
        try:
            print(f"Compiling {ui_file.name} -> {output_name}")
            subprocess.run(["pyside6-uic", str(ui_file.name), "-o", str(output_name)],
                           cwd=ui_file.parent, check=True)
            print(f"Successfully compiled {ui_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"Error compiling {ui_file.name}: {e}")
            success = False

    return success


def main(args):
    """Main entry point for the build script."""
    
    if args.rcc:
        print("Building Qt resources...")
        result = compile_resources()
        if not result:
            print("Resource compilation failed.")
            return 1

    if args.ui:
        result = compile_gui()
        if not result:
            print("UI compilation failed.")
            return 1
    return 0

def create_parser():
    parser = argparse.ArgumentParser(description="build_resources. Tool for building the qt resources of the amplullary simulator gui")
    parser.add_argument("--rcc", action="store_true", 
                        help="Build the qt resources file")
    parser.add_argument("--ui", action="store_true", 
                        help="Build the qt ui file")
    return parser

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    sys.exit(main(args))
