import subprocess
import os

srt_content = "1\n00:00:00,000 --> 00:00:05,000\nHello World\n"
with open('/tmp/test_sub.srt', 'w') as f: f.write(srt_content)

def check_sub(name, filter_str):
    out = f'/tmp/out_{name.replace(" ", "_")}.mp4'
    if os.path.exists(out): os.remove(out)
    cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=green:s=1280x720:d=2', '-filter_complex', filter_str, '-map', '[v]', out]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if 'No such' in res.stderr or 'Error' in res.stderr or 'Unable' in res.stderr:
        print(f"[{name}] CRASHED")
    else:
        # Check size of output to see if it rendered successfully
        size = os.path.getsize(out)
        print(f"[{name}] WORKED, size: {size}")

check_sub("single_quotes", "[0:v]subtitles=/tmp/test_sub.srt:force_style='FontName=Arial,FontSize=50'[v]")
check_sub("escape_comma", "[0:v]subtitles=/tmp/test_sub.srt:force_style=FontName=Arial\\,FontSize=50[v]")
check_sub("triple_escape", "[0:v]subtitles=/tmp/test_sub.srt:force_style=FontName=Arial\\\\\\,FontSize=50[v]")
