import os
import re
import uuid
import tempfile


class SubtitleManager:
    """
    Safely manages subtitle files for FFmpeg.
    FFmpeg has notorious path escaping bugs on macOS and Windows.
    We copy the user's subtitle to a strictly alphanumeric temporary path.

    KEY FIX: SRT files with non-zero hour components (e.g. 01:00:03,599)
    or irregular whitespace/line endings are normalised before being passed
    to libass, which otherwise silently drops the affected cues.
    """

    def __init__(self):
        self.temp_files = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_safe_copy(self, original_path: str) -> str:
        """
        Copies a subtitle file to a safe /tmp location, re-encodes to
        clean UTF-8, and (for .srt) normalises the timecode block so that
        libass can always parse them reliably.
        Returns the safe path.
        """
        if not original_path or not os.path.exists(original_path):
            raise FileNotFoundError(f"Subtitle file not found: {original_path}")

        ext = os.path.splitext(original_path)[1].lower()
        if ext not in ['.srt', '.ass', '.vtt']:
            ext = '.srt'

        content = self._read_any_encoding(original_path)

        if ext == '.srt':
            content = self._normalise_srt(content)

        safe_name = f"sub_{uuid.uuid4().hex}{ext}"
        safe_path = os.path.join(tempfile.gettempdir(), safe_name)

        with open(safe_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)

        self.temp_files.append(safe_path)
        return safe_path

    def parse_srt_cues(self, path: str) -> list:
        """
        Returns a list of dicts with keys: index, start_ms, end_ms, text.
        Used by the UI to list subtitle cues for preview/navigation.
        """
        try:
            content = self._read_any_encoding(path)
            content = self._normalise_srt(content)
            return self._parse_normalised_srt(content)
        except Exception as e:
            print(f"SRT parse warning: {e}")
            return []

    def cleanup(self):
        """Removes all temporary subtitle files created by this instance."""
        for path in self.temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Warning: Failed to clean up temp subtitle {path}: {e}")
        self.temp_files.clear()

    def __del__(self):
        self.cleanup()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    _ENCODINGS = ['utf-8-sig', 'utf-8', 'utf-16', 'windows-1250', 'iso-8859-1', 'cp1252']

    def _read_any_encoding(self, path: str) -> str:
        for enc in self._ENCODINGS:
            try:
                with open(path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        # Last-resort: read as bytes, decode with replacement
        with open(path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')

    # Matches SRT timecode line:  HH:MM:SS,mmm --> HH:MM:SS,mmm
    # Tolerates extra spaces around '-->' and both ',' and '.' as ms separator
    _TC_RE = re.compile(
        r'(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})'   # start
        r'\s*-->\s*'
        r'(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})'   # end
    )

    @classmethod
    def _tc_to_ms(cls, h, m, s, ms_str) -> int:
        ms = int(ms_str.ljust(3, '0'))   # pad e.g. "07" -> "070" -> 70 ms
        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + ms

    @classmethod
    def _ms_to_srt_tc(cls, ms: int) -> str:
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, ms_part = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms_part:03d}"

    def _normalise_srt(self, content: str) -> str:
        """
        Normalises an SRT file:
        - Unifies line endings to LF
        - Strips BOM / leading whitespace
        - Pads sub-millisecond fields (e.g. ,07 -> ,070)
        - Re-writes timecode lines in canonical HH:MM:SS,mmm --> HH:MM:SS,mmm
        - Re-numbers cues sequentially
        - Ensures a blank line between cues and a trailing newline

        This fixes the common case where libass silently drops cues whose
        hour component is non-zero or whose ms field has fewer than 3 digits.
        """
        content = content.replace('\r\n', '\n').replace('\r', '\n').strip()

        lines = content.split('\n')
        out_blocks = []
        cue_index = 0

        i = 0
        while i < len(lines):
            # Skip blank lines between cues
            if not lines[i].strip():
                i += 1
                continue

            # Expect a cue number (may be absent in some malformed SRTs)
            maybe_num = lines[i].strip()
            if maybe_num.isdigit():
                i += 1
                if i >= len(lines):
                    break
            # else: line is not a number – treat as timecode directly

            # Expect timecode line
            tc_line = lines[i].strip() if i < len(lines) else ''
            tc_match = self._TC_RE.search(tc_line)
            if not tc_match:
                # Not a valid cue start – skip line
                i += 1
                continue

            i += 1
            start_ms = self._tc_to_ms(*tc_match.group(1, 2, 3, 4))
            end_ms   = self._tc_to_ms(*tc_match.group(5, 6, 7, 8))

            # Collect text lines until blank line or next cue number
            text_lines = []
            while i < len(lines):
                l = lines[i]
                if not l.strip():
                    break
                # Stop if this looks like the next cue number
                if l.strip().isdigit() and i + 1 < len(lines) and self._TC_RE.search(lines[i + 1]):
                    break
                text_lines.append(l)
                i += 1

            if not text_lines:
                text_lines = ['']   # libass needs at least an empty text line

            cue_index += 1
            tc_out = f"{self._ms_to_srt_tc(start_ms)} --> {self._ms_to_srt_tc(end_ms)}"
            block = f"{cue_index}\n{tc_out}\n" + '\n'.join(text_lines)
            out_blocks.append(block)

        return '\n\n'.join(out_blocks) + '\n'

    def _parse_normalised_srt(self, content: str) -> list:
        """Parse already-normalised SRT into a list of cue dicts."""
        cues = []
        for block in content.strip().split('\n\n'):
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            tc_match = self._TC_RE.search(lines[1])
            if not tc_match:
                continue
            start_ms = self._tc_to_ms(*tc_match.group(1, 2, 3, 4))
            end_ms   = self._tc_to_ms(*tc_match.group(5, 6, 7, 8))
            text = '\n'.join(lines[2:])
            cues.append({
                'index': len(cues) + 1,
                'start_ms': start_ms,
                'end_ms': end_ms,
                'text': text,
            })
        return cues
