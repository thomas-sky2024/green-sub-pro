import re


# ---------------------------------------------------------------------------
# Quality presets
# Software codecs (libx264/libx265) use CRF + preset.
# HW codecs (videotoolbox) use average bitrate.
# Format: (crf_x264, crf_x265, hw_mbps_video, audio_kbps)
# ---------------------------------------------------------------------------
QUALITY_PRESETS = {
    "Low":    (28, 32,  4,  128),
    "Medium": (20, 24,  8,  192),
    "Best":   (14, 16, 20,  320),
}


class FFmpegBuilder:
    """
    Stateless utility that builds FFmpeg CLI command arrays.

    Key behaviours:
    - No outline stroke by default (Outline=0).
    - Outline opacity is a first-class parameter (0–100 %).
    - Quality presets drive CRF or HW bitrate.
    - Resolution is passed in so 9:16 portrait is fully supported.
    """

    # ------------------------------------------------------------------ #
    #  Colour helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
        """
        Convert #RRGGBB → ASS &H(AA)(BB)(GG)(RR).
        alpha: 0 = fully opaque, 255 = fully transparent (ASS convention).
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            hex_color = 'FFFFFF'
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"&H{alpha:02X}{b}{g}{r}"

    # ------------------------------------------------------------------ #
    #  Style string parser                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_styles(s: str) -> dict:
        """Parse the comma-separated key=value style string from the UI."""
        d: dict = {
            'FontName':      'Arial',
            'FontSize':      50,
            'MarginV':       60,
            'Shadow':        2,
            'Outline':       0,           # 0 = no outline by default
            'PrimaryColour': '#FFFFFF',
            'OutlineColour': '#000000',
            'OutlineAlpha':  0,           # 0=opaque … 255=transparent (ASS)
            'Bold':          '0',
            'Italic':        '0',
        }
        int_keys = {'FontSize', 'MarginV', 'Shadow', 'Outline', 'OutlineAlpha'}
        for key in d:
            m = re.search(rf'{re.escape(key)}=([^,]+)', s)
            if m:
                val = m.group(1).strip()
                d[key] = int(val) if key in int_keys else val
        return d

    # ------------------------------------------------------------------ #
    #  Filter builder                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_subtitle_filter(safe_sub_path: str, sub_styles_str: str) -> str:
        """
        Returns the full  subtitles='path':force_style='...'  filter string.

        Outline handling:
          - If Outline == 0 → no visible stroke (BorderStyle=1, Outline=0).
          - If Outline  > 0 → outline with user-controlled opacity.
        OutlineAlpha 0 = fully opaque, 255 = fully transparent (ASS).
        """
        s = FFmpegBuilder._parse_styles(sub_styles_str)

        ass_primary = FFmpegBuilder._hex_to_ass_color(s['PrimaryColour'], alpha=0)
        ass_outline = FFmpegBuilder._hex_to_ass_color(
            s['OutlineColour'],
            alpha=min(255, max(0, s['OutlineAlpha']))
        )

        outline_val  = s['Outline']   # 0 = no stroke
        border_style = 1              # outline+shadow style (Outline=0 → invisible)

        force_style = (
            f"FontName={s['FontName']},"
            f"FontSize={s['FontSize']},"
            f"PrimaryColour={ass_primary},"
            f"OutlineColour={ass_outline},"
            f"MarginV={s['MarginV']},"
            f"BorderStyle={border_style},"
            f"Outline={outline_val},"
            f"Shadow={s['Shadow']},"
            f"Bold={s['Bold']},"
            f"Italic={s['Italic']},"
            f"Alignment=2"
        )

        safe_path = (safe_sub_path
                     .replace('\\', '\\\\')
                     .replace(':', '\\:')
                     .replace("'", "\\'"))

        return f"subtitles='{safe_path}':force_style='{force_style}'"

    # ------------------------------------------------------------------ #
    #  Quality helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _quality_flags(codec: str, quality: str) -> list:
        crf_264, crf_265, hw_mbps, audio_kbps = QUALITY_PRESETS.get(
            quality, QUALITY_PRESETS["Medium"]
        )
        flags: list = []

        if codec == "libx264":
            preset = {"Low": "fast", "Medium": "medium", "Best": "slow"}[quality]
            flags += ["-crf", str(crf_264), "-preset", preset]
        elif codec == "libx265":
            preset = {"Low": "fast", "Medium": "medium", "Best": "slow"}[quality]
            flags += ["-crf", str(crf_265), "-preset", preset, "-tag:v", "hvc1"]
        elif codec in ("h264_videotoolbox", "hevc_videotoolbox"):
            flags += ["-b:v", f"{hw_mbps}M", "-realtime", "0"]
            if quality == "Best":
                flags += ["-q:v", "60"]
        else:
            flags += ["-crf", str(crf_264)]

        flags += ["-b:a", f"{audio_kbps}k"]
        return flags

    # ------------------------------------------------------------------ #
    #  Burn command                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_burn_command(
        input_video: str,
        safe_sub_path: str,
        output_path: str,
        bg_hex: str,
        sub_styles: str,
        video_codec: str = "libx264",
        duration_sec: float = 0.0,
        quality: str = "Medium",
        resolution: str = "1920x1080",
    ) -> list:
        bg_color = bg_hex.lstrip("#")
        w, h = (int(x) for x in resolution.split('x'))
        w += w % 2;  h += h % 2          # must be even
        res_str = f"{w}x{h}"

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=#{bg_color}:s={res_str}:r=25",
            "-i", input_video,
        ]

        if safe_sub_path:
            sf = FFmpegBuilder.build_subtitle_filter(safe_sub_path, sub_styles)
            cmd += ["-filter_complex", f"[0:v]{sf}[v]",
                    "-map", "[v]", "-map", "1:a?"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a?"]

        cmd += ["-c:v", video_codec, "-c:a", "aac"]
        cmd += FFmpegBuilder._quality_flags(video_codec, quality)
        cmd += ["-progress", "pipe:1", "-nostats"]

        if duration_sec > 0:
            cmd += ["-t", str(duration_sec)]

        cmd.append(output_path)
        return cmd

    # ------------------------------------------------------------------ #
    #  Preview command                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_preview_command(
        input_video: str,
        safe_sub_path: str,
        output_path: str,
        time_sec: float,
        sub_styles: str,
        bg_hex: str = "00FF00",
        resolution: str = "1920x1080",
    ) -> list:
        bg_color = bg_hex.lstrip("#")
        w, h = (int(x) for x in resolution.split('x'))
        w += w % 2;  h += h % 2
        res_str = f"{w}x{h}"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(max(0.0, time_sec)),
            "-f", "lavfi",
            "-i", f"color=c=#{bg_color}:s={res_str}:r=25",
        ]

        if safe_sub_path:
            sf = FFmpegBuilder.build_subtitle_filter(safe_sub_path, sub_styles)
            cmd += ["-filter_complex", f"[0:v]{sf}[v]", "-map", "[v]"]
        else:
            cmd += ["-map", "0:v"]

        cmd += ["-frames:v", "1", "-q:v", "1", "-f", "image2", output_path]
        return cmd
