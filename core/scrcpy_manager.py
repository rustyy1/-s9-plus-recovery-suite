"""scrcpy launch and monitoring for Galaxy S9+ Recovery Console.

Handles locating the scrcpy executable, launching mirror sessions,
and monitoring the scrcpy process for errors.
"""

import subprocess
import shutil
import os
import threading
import logging
from typing import Optional, Callable, Tuple

logger = logging.getLogger("recovery_console.scrcpy")


class ScrcpyManager:
    """Manages scrcpy process lifecycle."""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self._scrcpy_path: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None
        self._log = log_callback or (lambda msg: None)

    # ── Discovery ──────────────────────────────────────────────────

    def find_scrcpy(self) -> Tuple[bool, str]:
        """Locate the scrcpy executable.

        Returns:
            (found: bool, path_or_error: str)
        """
        candidates = [
            shutil.which("scrcpy"),
            shutil.which("scrcpy.exe"),
        ]

        # Check alongside this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        for d in [parent_dir, script_dir]:
            candidates.append(os.path.join(d, "scrcpy.exe"))
            candidates.append(os.path.join(d, "scrcpy", "scrcpy.exe"))

        # Common install paths
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        candidates.append(os.path.join(program_files, "scrcpy", "scrcpy.exe"))
        candidates.append("C:\\scrcpy\\scrcpy.exe")

        # Check Desktop folders (e.g. scrcpy-win64-*)
        desktop_dir = os.path.dirname(parent_dir)
        if os.path.isdir(desktop_dir):
            try:
                for entry in os.listdir(desktop_dir):
                    sub = os.path.join(desktop_dir, entry)
                    if os.path.isdir(sub) and "scrcpy" in entry.lower():
                        candidates.append(os.path.join(sub, "scrcpy.exe"))
            except OSError:
                pass

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                self._scrcpy_path = candidate
                self._log(f"Found scrcpy at: {candidate}")
                return True, candidate

        msg = (
            "scrcpy not found. Install from:\n"
            "https://github.com/Genymobile/scrcpy/releases\n"
            "Extract the archive and add the directory to your PATH."
        )
        self._log(f"WARNING: {msg}")
        return False, msg

    @property
    def scrcpy_path(self) -> Optional[str]:
        return self._scrcpy_path

    @property
    def is_available(self) -> bool:
        if self._scrcpy_path is None:
            self.find_scrcpy()
        return self._scrcpy_path is not None

    @property
    def is_running(self) -> bool:
        """Check if a scrcpy session is currently active."""
        if self._process is None:
            return False
        return self._process.poll() is None

    # ── Session Management ─────────────────────────────────────────

    def start_mirror(
        self,
        serial: Optional[str] = None,
        max_size: int = 1024,
        bit_rate: str = "8M",
        stay_awake: bool = True,
        turn_screen_off: bool = False,
        window_title: str = "Galaxy S9+ Mirror",
    ) -> Tuple[bool, str]:
        """Launch a scrcpy mirroring session.

        Args:
            serial: Target device serial number.
            max_size: Maximum dimension (width or height) in pixels.
            bit_rate: Video bit rate (e.g., '8M').
            stay_awake: Keep device awake while mirroring.
            turn_screen_off: Turn off device screen while mirroring.
            window_title: Title for the scrcpy window.

        Returns:
            (success: bool, message: str)
        """
        if not self.is_available:
            return False, "scrcpy is not available"

        if self.is_running:
            return False, "A mirroring session is already running"

        cmd = [self._scrcpy_path]

        if serial:
            cmd.extend(["--serial", serial])

        cmd.extend([
            "--max-size", str(max_size),
            "--video-bit-rate", bit_rate,
            "--window-title", window_title,
        ])

        if stay_awake:
            cmd.append("--stay-awake")

        if turn_screen_off:
            cmd.append("--turn-screen-off")

        cmd_str = " ".join(cmd)
        self._log(f"Launching scrcpy: {cmd_str}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            # Wait briefly to check for immediate failure
            try:
                retcode = self._process.wait(timeout=2)
                stderr = self._process.stderr.read() if self._process.stderr else ""
                stdout = self._process.stdout.read() if self._process.stdout else ""
                output = (stderr or stdout).strip()
                self._log(f"scrcpy exited immediately (code {retcode}): {output}")
                self._process = None
                return False, f"scrcpy failed to start:\n{output}" if output else "scrcpy exited immediately"
            except subprocess.TimeoutExpired:
                # Still running after 2s — good, it's mirroring
                self._log("scrcpy is running — mirroring active")

                # Drain stderr in background to prevent pipe deadlock and capture runtime issues
                def _drain_stderr(proc):
                    try:
                        for line in proc.stderr:
                            clean_line = line.strip()
                            if clean_line:
                                logger.debug(f"scrcpy: {clean_line}")
                                if "ERROR" in clean_line or "Warn" in clean_line:
                                    self._log(f"scrcpy: {clean_line}")
                    except Exception:
                        pass

                t = threading.Thread(target=_drain_stderr, args=(self._process,), daemon=True)
                t.start()
                return True, "Mirroring started successfully"

        except FileNotFoundError:
            self._scrcpy_path = None
            msg = "scrcpy executable not found"
            self._log(f"ERROR: {msg}")
            return False, msg
        except OSError as e:
            msg = f"Failed to launch scrcpy: {e}"
            self._log(f"ERROR: {msg}")
            return False, msg

    def stop_mirror(self) -> Tuple[bool, str]:
        """Stop the current scrcpy mirroring session."""
        if not self.is_running:
            return True, "No mirroring session is active"

        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=3)

            self._log("scrcpy session stopped")
            self._process = None
            return True, "Mirroring stopped"
        except Exception as e:
            msg = f"Error stopping scrcpy: {e}"
            self._log(f"ERROR: {msg}")
            return False, msg

    def get_exit_info(self) -> Optional[str]:
        """Get information about why scrcpy exited, if it has."""
        if self._process is None:
            return None
        if self._process.poll() is None:
            return None  # Still running

        retcode = self._process.returncode
        stderr = ""
        try:
            if self._process.stderr:
                stderr = self._process.stderr.read().decode("utf-8", errors="replace")
        except Exception:
            pass

        self._process = None
        if retcode == 0:
            return "scrcpy exited normally"
        return f"scrcpy exited with code {retcode}:\n{stderr}" if stderr else f"scrcpy exited with code {retcode}"
