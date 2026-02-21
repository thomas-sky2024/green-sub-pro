import unittest
from core.ffmpeg_builder import FFmpegBuilder

class TestFFmpegBuilder(unittest.TestCase):

    def test_hex_to_ass_color(self):
        # White
        self.assertEqual(FFmpegBuilder._hex_to_ass_color("#FFFFFF"), "&H00FFFFFF")
        # Red
        self.assertEqual(FFmpegBuilder._hex_to_ass_color("#FF0000"), "&H000000FF")
        # Green
        self.assertEqual(FFmpegBuilder._hex_to_ass_color("#00FF00"), "&H0000FF00")
        # Blue
        self.assertEqual(FFmpegBuilder._hex_to_ass_color("#0000FF"), "&H00FF0000")
        # Opaque black with custom opacity (0x55 = 85)
        self.assertEqual(FFmpegBuilder._hex_to_ass_color("#000000", 85), "&H55000000")

    def test_build_subtitle_filter(self):
        safe_path = "/tmp/safe_sub.srt"
        style_str = "FontName=Helvetica,FontSize=42,PrimaryColour=#FF0000,OutlineColour=#00FF00,MarginV=50,Shadow=1"
        
        filter_str = FFmpegBuilder.build_subtitle_filter(safe_path, style_str)
        
        self.assertIn("subtitles='/tmp/safe_sub.srt'", filter_str)
        self.assertIn("force_style='FontName=Helvetica", filter_str)
        self.assertIn("FontSize=42", filter_str)
        self.assertIn("PrimaryColour=&H000000FF", filter_str) 
        self.assertIn("OutlineColour=&H0000FF00", filter_str)
        self.assertIn("MarginV=50", filter_str)
        self.assertIn("Shadow=1", filter_str)
        self.assertIn("Bold=0", filter_str)
        self.assertIn("Italic=0", filter_str)
        self.assertIn("Alignment=2", filter_str)
        
    def test_build_subtitle_filter_with_font_styles(self):
        safe_path = "/tmp/safe_sub.srt"
        style_str = "Bold=-1,Italic=-1"
        
        filter_str = FFmpegBuilder.build_subtitle_filter(safe_path, style_str)
        self.assertIn("Bold=-1", filter_str)
        self.assertIn("Italic=-1", filter_str)


    def test_build_burn_command(self):
        cmd = FFmpegBuilder.build_burn_command(
            input_video="input.mp4",
            safe_sub_path="/tmp/sub.srt",
            output_path="output.mp4",
            bg_hex="00FF00",
            sub_styles="FontSize=20",
            video_codec="libx264"
        )
        
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("input.mp4", cmd)
        self.assertIn("-filter_complex", cmd)
        self.assertIn("output.mp4", cmd)
        self.assertIn("-progress", cmd)
        self.assertIn("pipe:1", cmd)

if __name__ == '__main__':
    unittest.main()
