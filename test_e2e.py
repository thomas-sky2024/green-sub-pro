import os
import shutil
from core.job_queue import JobQueue
from core.media_engine import MediaEngine

def progress_callback(pct, msg=""):
    print(f"Progress: {pct}% {msg}")

# Create dummy input video
os.system('ffmpeg -y -f lavfi -i testsrc=duration=5:size=1280x720:rate=25 -f lavfi -i sine=frequency=1000:duration=5 -c:v libx264 -c:a aac /tmp/dummy_in.mp4 > /dev/null 2>&1')

# Create dummy sub
srt_content = "1\n00:00:00,000 --> 00:00:05,000\nHiiiiii\n"
with open('/tmp/dummy_sub.srt', 'w') as f:
    f.write(srt_content)

q = JobQueue(progress_callback)
q.add_job(
    input_video="/tmp/dummy_in.mp4",
    subtitle_path="/tmp/dummy_sub.srt",
    output_path="/tmp/dummy_out.mp4",
    bg_color="00FF00",
    sub_styles="FontName=Arial,FontSize=100,PrimaryColour=&H000000FF",
    duration=5.0
)

# wait for thread to finish
import time
while len(q._queue) > 0 or q._current_job is not None:
    time.sleep(1)

print("Done. Output size:", os.path.getsize("/tmp/dummy_out.mp4"))
