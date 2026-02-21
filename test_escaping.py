import subprocess

srt_content = '''1
00:00:00,000 --> 00:00:05,000
Hello World
'''
with open('/tmp/test_sub.srt', 'w') as f:
    f.write(srt_content)

def run_ffmpeg(style_str):
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=green:s=1280x720:d=2',
        '-filter_complex', f'[0:v]subtitles=/tmp/test_sub.srt:force_style={style_str}[v]',
        '-map', '[v]', '/tmp/out_debug.mp4'
    ]
    print(f"Testing: {style_str}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if 'No such filter' in res.stderr or 'Error' in res.stderr or 'Unable to' in res.stderr:
        print("FAILED")
        for line in res.stderr.split('\\n'):
            if 'Error' in line or 'No such' in line or 'Unable' in line:
                print("  ->", line.strip())
    else:
        print("SUCCESS")

# 1. No quotes, single backslash escape for comma -> translated as \, in python string it's \\,
run_ffmpeg('FontName=Arial\\,FontSize=50')

# 2. Single quotes
run_ffmpeg("'FontName=Arial,FontSize=50'")

# 3. Double escape
run_ffmpeg('FontName=Arial\\\\,FontSize=50')
