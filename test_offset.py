import subprocess
import os

srt_content = "1\n00:00:03,000 --> 00:00:06,000\nDelayed Subtitle\n"
with open('/tmp/test_off.srt', 'w') as f:
    f.write(srt_content)

cmd = [
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=green:s=1280x720:d=10',
    '-filter_complex', "[0:v]subtitles=/tmp/test_off.srt:force_style='FontName=Arial,FontSize=50'[v]",
    '-map', '[v]', '/tmp/out_off.mp4'
]
res = subprocess.run(cmd, capture_output=True, text=True)

# Try snapshotting at 00:00:04 where sub is supposed to be
cmd_snap = [
    'ffmpeg', '-y', '-ss', '4', '-i', '/tmp/out_off.mp4', '-frames:v', '1', '/tmp/off_snap.png'
]
subprocess.run(cmd_snap, capture_output=True)

print("Size of snap:", os.path.getsize('/tmp/off_snap.png'))

## Now test mapping the time offset from an input file. Wait, in lavfi color=c=green, the PTS starts at 0.
## If the subtitle starts at 1 hour (01:00:03), then the color source must be 1 hour long for it to appear
## OR we must instruct the subtitle filter to subtract the start time of the actual video.
