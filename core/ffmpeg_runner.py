import subprocess
import threading
import time
import re
from typing import Callable, Optional


class RenderResult:
    def __init__(self, success: bool, output_path: str, duration_sec: float = 0.0, error_message: str = ""):
        self.success = success
        self.output_path = output_path
        self.duration_sec = duration_sec
        self.error_message = error_message


class FFmpegRunner:
    """
    Spawns FFmpeg subprocesses, parses structured progress, and emits events safely.

    Fixes vs original:
    - `out_time_ms` in FFmpeg's -progress output is actually **microseconds**.
      The original code divided by 1_000_000 (correct) but only accepted
      `.isdigit()` values, which rejects negative sentinels like "-1".
      We now guard with a try/except and clamp to >= 0.
    - Removed the `self._process.communicate()` call after the stdout-read loop.
      `communicate()` tries to read stdout again which blocks forever because
      the pipe is already at EOF.  We now read stderr via a background thread
      while stdout is consumed in the main loop.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False

    def run_command(
        self,
        cmd: list,
        total_duration_sec: float,
        progress_callback: Callable[[float, str], None] = None,
    ) -> RenderResult:
        """
        Executes an FFmpeg command list. Parses stdout for `-progress pipe:1`
        percentage updates.
        """
        self._cancelled = False
        start_time = time.time()

        try:
            # Debug log
            try:
                with open("/tmp/ffcmd.log", "w") as f:
                    f.write("\n".join(cmd))
            except Exception:
                pass

            # Collect stderr in a background thread to avoid deadlocks
            stderr_lines: list = []

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
            )

            def _drain_stderr():
                for line in self._process.stderr:
                    stderr_lines.append(line)

            stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
            stderr_thread.start()

            # Read stdout (where -progress pipe:1 writes key=value pairs)
            for line in self._process.stdout:
                if self._cancelled:
                    self._process.terminate()
                    self._process.wait()
                    return RenderResult(False, "", 0.0, "Job cancelled by user.")

                if progress_callback and total_duration_sec > 0:
                    if line.startswith("out_time_ms="):
                        raw = line.split("=", 1)[1].strip()
                        try:
                            current_us = int(raw)
                            if current_us >= 0:
                                current_sec = current_us / 1_000_000.0
                                pct = min((current_sec / total_duration_sec) * 100.0, 100.0)
                                progress_callback(pct, "")
                        except ValueError:
                            pass

            self._process.stdout.close()
            self._process.wait()
            stderr_thread.join(timeout=5)

            if self._process.returncode != 0 and not self._cancelled:
                err_text = "".join(stderr_lines[-40:])  # last 40 lines are enough
                return RenderResult(False, "", 0.0, f"FFmpeg Error (code {self._process.returncode}):\n{err_text}")

            elapsed_sec = time.time() - start_time
            output_path = cmd[-1] if cmd else "unknown_output"
            return RenderResult(True, output_path, elapsed_sec)

        except FileNotFoundError:
            return RenderResult(False, "", 0.0, "FFmpeg binary not found. Is it installed?")
        except Exception as e:
            return RenderResult(False, "", 0.0, f"Runner exception: {str(e)}")
        finally:
            self._process = None

    def capture_single_frame(self, cmd: list) -> bool:
        """
        Executes an instantaneous command like frame extraction without progress piping.
        """
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            if result.returncode != 0:
                print(f"Frame Extract Error: {result.stderr.decode(errors='replace')}")
                return False
            return True
        except subprocess.CalledProcessError as e:
            print(f"Frame Extract Error: {e.stderr.decode(errors='replace') if e.stderr else str(e)}")
            return False
        except subprocess.TimeoutExpired:
            print("Frame extraction timed out.")
            return False

    def cancel(self):
        """Immediately terminates the running FFmpeg instance."""
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
