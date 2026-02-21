import subprocess
import os

srt_content = "1\n00:00:00,000 --> 00:00:05,000\nHello World\n"
with open('/tmp/test_sub.srt', 'w') as f: f.write(srt_content)

def test(name, filter_str):
    cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=green:s=1280x720:d=2', '-filter_complex', filter_str, '-map', '[v]', '/tmp/out_debug.mp4']
    print(f"--- {name} ---")
    print("Filter:", filter_str)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if 'No such filter' in res.stderr:
        for line in res.stderr.split('\n'):
            if 'No such filter' in line:
                print("Error:", line.strip())
    elif 'Error' in res.stderr:
        print("Failed with other error")
        for line in res.stderr.split('\n'):
            if 'Error' in line or 'Unable to' in line:
                print("Error:", line.strip())
    else:
        print("SUCCESS")

# 1. No quotes, no escaping
test("No quotes, no escape", "[0:v]subtitles=/tmp/test_sub.srt:force_style=FontName=Arial,FontSize=50[v]")

# 2. Quotes around force_style value
test("Single quotes around value", "[0:v]subtitles=/tmp/test_sub.srt:force_style='FontName=Arial,FontSize=50'[v]")

# 3. Quotes around whole subtitles arg
test("Single quotes around whole arg", "[0:v]subtitles='/tmp/test_sub.srt':force_style='FontName=Arial,FontSize=50'[v]")

# 4. No quotes, escape commas with 1 backslash
# string literal '\\' produces a string with 1 backslash
test("Escape comma 1 backslash", "[0:v]subtitles=/tmp/test_sub.srt:force_style=FontName=Arial\\,FontSize=50[v]")

# 5. No quotes, escape commas with 2 backslashes
test("Double Escape comma", "[0:v]subtitles=/tmp/test_sub.srt:force_style=FontName=Arial\\\\,FontSize=50[v]")

# 6. No quotes, escape commas with 3 backslashes
test("Triple Escape comma", "[0:v]subtitles=/tmp/test_sub.srt:force_style=FontName=Arial\\\\\\,FontSize=50[v]")

# 7. No quotes, escape commas with 4 backslashes
test("Quad Escape comma", "[0:v]subtitles=/tmp/test_sub.srt:force_style=FontName=Arial\\\\\\\\,FontSize=50[v]")
