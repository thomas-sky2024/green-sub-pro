import subprocess
cmd = [
    "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=green:s=1280x720:d=2",
    "-filter_complex", "[0:v]subtitles='test.srt':force_style='FontName=Arial,FontSize=50'[v]",
    "-map", "[v]", "out_debug3.mp4"
]
result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stderr)
