import threading
import uuid
from typing import Callable

from core.ffmpeg_builder import FFmpegBuilder
from core.ffmpeg_runner import FFmpegRunner, RenderResult
from core.subtitle_manager import SubtitleManager


class JobQueue:
    """
    Background worker thread that sequences rendering tasks.
    States: pending → running → completed | failed | cancelled
    """

    def __init__(self, callback: Callable[[float, str], None]):
        self._queue: list = []
        self._current_job = None
        self._worker_thread = None
        self._runner = FFmpegRunner()
        self._subtitle_manager = SubtitleManager()
        self._progress_callback = callback

    def add_job(
        self,
        input_video: str,
        subtitle_path: str,
        output_path: str,
        bg_color: str,
        sub_styles: str,
        duration: float,
        codec: str = "libx264",
        quality: str = "Medium",
        resolution: str = "1920x1080",
    ) -> str:
        job_id = str(uuid.uuid4())
        self._queue.append({
            "id":       job_id,
            "input":    input_video,
            "subtitle": subtitle_path,
            "output":   output_path,
            "bg_color": bg_color,
            "styles":   sub_styles,
            "duration": duration,
            "codec":    codec,
            "quality":  quality,
            "resolution": resolution,
            "state":    "pending",
        })
        if not self._worker_thread or not self._worker_thread.is_alive():
            self._start_worker()
        return job_id

    def _start_worker(self):
        self._worker_thread = threading.Thread(
            target=self._process_queue, daemon=False
        )
        self._worker_thread.start()

    def _process_queue(self):
        while self._queue:
            job = self._queue.pop(0)
            self._current_job = job
            job["state"] = "running"
            try:
                temp_sub = self._subtitle_manager.create_safe_copy(job["subtitle"])
                cmd = FFmpegBuilder.build_burn_command(
                    job["input"], temp_sub, job["output"],
                    job["bg_color"], job["styles"],
                    video_codec=job["codec"],
                    duration_sec=job["duration"],
                    quality=job["quality"],
                    resolution=job["resolution"],
                )
                res: RenderResult = self._runner.run_command(
                    cmd, job["duration"], self._progress_callback
                )
                if res.success:
                    job["state"] = "completed"
                    self._progress_callback(101.0, "Success")
                else:
                    job["state"] = "cancelled" if "cancelled" in res.error_message.lower() else "failed"
                    self._progress_callback(-1.0, res.error_message)
            except Exception as e:
                job["state"] = "failed"
                self._progress_callback(-1.0, str(e))
            finally:
                self._subtitle_manager.cleanup()
                self._current_job = None

    def cancel_current_job(self):
        if self._current_job and self._current_job["state"] == "running":
            self._runner.cancel()

    def clear_queue(self):
        self._queue.clear()
        self.cancel_current_job()
