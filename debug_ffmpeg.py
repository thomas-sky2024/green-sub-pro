from core.ffmpeg_builder import FFmpegBuilder
import sys
cmd = FFmpegBuilder.build_burn_command("input.mp4", "/tmp/dummy.srt", "output.mp4", "00FF00", "FontSize=50")
print(" ".join(cmd))
