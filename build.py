"""PyInstaller build script for Galaxy S9+ Recovery Console.

Creates a distributable Windows executable in dist/GalaxyS9RecoveryConsole/
"""

import subprocess
import sys
import os


def build():
    """Run PyInstaller to create the distributable executable."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "GalaxyS9RecoveryConsole",
        "--windowed",                       # No console window
        "--noconfirm",                      # Overwrite without asking
        "--clean",                          # Clean cache before building
        "--add-data", f"{os.path.join(script_dir, 'core')};core",
        "--add-data", f"{os.path.join(script_dir, 'ui')};ui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--distpath", os.path.join(script_dir, "dist"),
        "--workpath", os.path.join(script_dir, "build"),
        "--specpath", script_dir,
        os.path.join(script_dir, "main.py"),
    ]

    print("=" * 60)
    print("  Building Galaxy S9+ Recovery Console")
    print("=" * 60)
    print()
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        dist_path = os.path.join(script_dir, "dist", "GalaxyS9RecoveryConsole")
        print()
        print("=" * 60)
        print("  BUILD SUCCESSFUL")
        print(f"  Output: {dist_path}")
        print()
        print("  To run the built application:")
        print(f"    {os.path.join(dist_path, 'GalaxyS9RecoveryConsole.exe')}")
        print()
        print("  Remember to place adb.exe and scrcpy.exe in the same")
        print("  directory as the executable, or ensure they are on PATH.")
        print("=" * 60)
    else:
        print()
        print("BUILD FAILED — check the output above for errors.")
        sys.exit(1)


if __name__ == "__main__":
    build()
