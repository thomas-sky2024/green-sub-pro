import os
from typing import Dict, Any, Optional


class MediaEngine:
    """Wrapper for FFmpeg/FFprobe operations."""

    @staticmethod
    def get_media_info(filepath: str) -> Dict[str, Any]:
        try:
            import ffmpeg
            probe = ffmpeg.probe(filepath)
        except ImportError:
            return MediaEngine._probe_fallback(filepath)
        except Exception as e:
            print(f"FFprobe error: {e}")
            return {}

        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        info: Dict[str, Any] = {
            'format':      probe['format'].get('format_name', 'unknown'),
            'duration':    float(probe['format'].get('duration', 0.0)),
            'size':        int(probe['format'].get('size', 0)),
            'video_codec': video_stream['codec_name'] if video_stream else None,
            'audio_codec': audio_stream['codec_name'] if audio_stream else None,
        }
        if video_stream:
            info['width']  = int(video_stream.get('width', 0))
            info['height'] = int(video_stream.get('height', 0))
            fps_str = video_stream.get('r_frame_rate', '0/1')
            try:
                num, den = map(int, fps_str.split('/'))
                info['fps'] = num / den if den else 0.0
            except Exception:
                info['fps'] = 0.0
        return info

    @staticmethod
    def _probe_fallback(filepath: str) -> Dict[str, Any]:
        import subprocess, json
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", filepath],
                capture_output=True, text=True, timeout=15,
            )
            data = json.loads(result.stdout)
            fmt = data.get('format', {})
            streams = data.get('streams', [])
            vs = next((s for s in streams if s.get('codec_type') == 'video'), None)
            as_ = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            info: Dict[str, Any] = {
                'format':      fmt.get('format_name', 'unknown'),
                'duration':    float(fmt.get('duration', 0.0)),
                'size':        int(fmt.get('size', 0)),
                'video_codec': vs.get('codec_name') if vs else None,
                'audio_codec': as_.get('codec_name') if as_ else None,
            }
            if vs:
                info['width']  = int(vs.get('width', 0))
                info['height'] = int(vs.get('height', 0))
                fps_str = vs.get('r_frame_rate', '0/1')
                try:
                    num, den = map(int, fps_str.split('/'))
                    info['fps'] = num / den if den else 0.0
                except Exception:
                    info['fps'] = 0.0
            return info
        except Exception as e:
            print(f"ffprobe fallback error: {e}")
            return {}

    @staticmethod
    def extract_preview_frame(
        video_path: str,
        subtitle_path: Optional[str],
        time_sec: float,
        output_path: str,
        sub_styles: str = "",
        bg_hex: str = "00FF00",
        resolution: str = "1920x1080",
    ) -> bool:
        from core.ffmpeg_builder import FFmpegBuilder
        from core.ffmpeg_runner import FFmpegRunner
        from core.subtitle_manager import SubtitleManager

        sm = SubtitleManager()
        try:
            temp_sub = None
            if subtitle_path and os.path.exists(subtitle_path):
                temp_sub = sm.create_safe_copy(subtitle_path)
            cmd = FFmpegBuilder.build_preview_command(
                video_path, temp_sub, output_path,
                time_sec, sub_styles, bg_hex, resolution,
            )
            return FFmpegRunner().capture_single_frame(cmd)
        except Exception as e:
            print(f"Preview error: {e}")
            return False
        finally:
            sm.cleanup()

    _global_queue = None

    @classmethod
    def get_queue(cls):
        from core.job_queue import JobQueue
        if cls._global_queue is None:
            cls._global_queue = JobQueue(
                lambda pct, msg: print(f"Progress: {pct}% {msg}")
            )
        return cls._global_queue

    @staticmethod
    def render_green_sub(
        video_path: str,
        subtitle_path: str,
        output_path: str,
        bg_color: str = '00FF00',
        sub_styles: str = "",
        progress_callback=None,
        codec: str = "libx264",
        quality: str = "Medium",
        resolution: str = "1920x1080",
    ):
        info = MediaEngine.get_media_info(video_path)
        duration = info.get('duration', 10.0)
        queue = MediaEngine.get_queue()
        if progress_callback:
            queue._progress_callback = progress_callback
        return queue.add_job(
            video_path, subtitle_path, output_path,
            bg_color, sub_styles, duration,
            codec=codec, quality=quality, resolution=resolution,
        )
