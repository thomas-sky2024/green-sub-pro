import unittest
from core.ffmpeg_runner import FFmpegRunner

class TestFFmpegRunner(unittest.TestCase):

    def test_ffmpeg_not_found(self):
        runner = FFmpegRunner()
        # Non-existent command
        res = runner.run_command(["fake_binary_that_does_not_exist", "-i", "none"], 10.0)
        self.assertFalse(res.success)
        self.assertIn("not found", res.error_message)

    def test_progress_parsing(self):
        # We can simulate FFmpeg's pipe:1 output using python -c
        mock_ffmpeg_cmd = [
            "python3", "-c",
            "import time; import sys; "
            "print('out_time_ms=1000000', flush=True); "
            "time.sleep(0.1); "
            "print('out_time_ms=5000000', flush=True); "
            "time.sleep(0.1); "
            "sys.exit(0);"
        ]
        
        runner = FFmpegRunner()
        progress_ticks = []
        
        def mock_callback(pct, msg=""):
            progress_ticks.append(pct)
            
        res = runner.run_command(mock_ffmpeg_cmd, 10.0, mock_callback)
        
        self.assertTrue(res.success)
        self.assertTrue(len(progress_ticks) >= 2)
        # 1000000 ms is 1 second. out of 10.0 seconds = 10%
        self.assertAlmostEqual(progress_ticks[0], 10.0, delta=0.1)
        # 5000000 ms is 5 seconds. out of 10.0 seconds = 50%
        self.assertAlmostEqual(progress_ticks[1], 50.0, delta=0.1)

if __name__ == '__main__':
    unittest.main()
