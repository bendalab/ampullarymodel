"""
Setup script that compiles Qt resources before building the package.
"""

import subprocess
import sys
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.develop import develop
from setuptools.command.install import install


class BuildQtResources:
    """Mixin class to add Qt resource compilation to setuptools commands."""
    
    def run_build_resources(self):
        """Execute the resource compilation script."""
        print("Compiling Qt resources...")
        try:
            result = subprocess.run([sys.executable, "build_resources.py"], 
                                  capture_output=True, text=True, check=True)
            print(result.stdout)
            if result.stderr:
                print("Warnings:", result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Resource compilation failed: {e}")
            print("stdout:", e.stdout)
            print("stderr:", e.stderr)
            raise


class BuildPyCommand(build_py, BuildQtResources):
    """Custom build_py command that compiles resources first."""
    
    def run(self):
        self.run_build_resources()
        super().run()


class DevelopCommand(develop, BuildQtResources):
    """Custom develop command that compiles resources first."""
    
    def run(self):
        self.run_build_resources()
        super().run()


class InstallCommand(install, BuildQtResources):
    """Custom install command that compiles resources first."""
    
    def run(self):
        self.run_build_resources()
        super().run()


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_py": BuildPyCommand,
            "develop": DevelopCommand, 
            "install": InstallCommand,
        }
    )