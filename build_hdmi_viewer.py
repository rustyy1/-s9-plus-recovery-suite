"""PyInstaller build script for S9+ HDMI Viewer & Controller.

Creates a standalone Windows executable in dist/S9HdmiViewer/
"""

import subprocess
import sys
import os


def build():
    """Run PyInstaller to create standalone Windows binary."""
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_dir, "main_hdmi_viewer.py")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=S9HdmiViewer",
        "--noconsole",
        "--onedir",
        "--clean",
        "--noconfirm",
        f"--paths={project_dir}",
        "--hidden-import=PySide6.QtMultimedia",
        "--hidden-import=PySide6.QtMultimediaWidgets",
        "--hidden-import=core",
        "--hidden-import=ui",
        main_script,
    ]

    print("Running PyInstaller...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=project_dir)

    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("Build successful!")
        print(f"Output directory: {os.path.join(project_dir, 'dist', 'S9HdmiViewer')}")
        print("=" * 50)
    else:
        print(f"\nBuild failed with exit code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
