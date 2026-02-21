import subprocess
force_style = 'FontName=Arial,FontSize=50,PrimaryColour=&H000000FF'
escaped_style = force_style.replace(',', '\\,')
cmd = [
    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=green:s=1280x720:d=2',
    '-filter_complex', f'[0:v]subtitles=test.srt:force_style={escaped_style}[v]',
    '-map', '[v]', 'out_debug5.mp4'
]
print(cmd)
result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stderr)
