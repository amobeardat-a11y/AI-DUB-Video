"""
tests/test_pipeline.py — Unit tests cho VietDub pipeline modules
Chạy: pytest tests/ -v
"""
import sys
import os
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ============================================================
# Test: VTT Parser
# ============================================================

class TestVttParser:
    SAMPLE_VTT = """WEBVTT

1
00:00:01.000 --> 00:00:03.500
Hello, this is the first line.

2
00:00:04.000 --> 00:00:06.000
<c.color>And this is second line</c.color>

3
00:00:07.500 --> 00:00:09.000
Multiple words on
this line together.

"""

    def test_parse_basic_entries(self):
        from backend.pipeline.downloader import parse_vtt_content
        entries = parse_vtt_content(self.SAMPLE_VTT)
        assert len(entries) == 3

    def test_parse_timestamps(self):
        from backend.pipeline.downloader import parse_vtt_content
        entries = parse_vtt_content(self.SAMPLE_VTT)
        assert entries[0].start == pytest.approx(1.0)
        assert entries[0].end == pytest.approx(3.5)

    def test_parse_strips_html_tags(self):
        from backend.pipeline.downloader import parse_vtt_content
        entries = parse_vtt_content(self.SAMPLE_VTT)
        assert "<c" not in entries[1].text
        assert "And this is second line" in entries[1].text

    def test_parse_multiline_merges(self):
        from backend.pipeline.downloader import parse_vtt_content
        entries = parse_vtt_content(self.SAMPLE_VTT)
        assert "Multiple words" in entries[2].text

    def test_parse_empty_string(self):
        from backend.pipeline.downloader import parse_vtt_content
        entries = parse_vtt_content("")
        assert entries == []


# ============================================================
# Test: VTT Time Parser
# ============================================================

class TestVttTimeParsing:
    def test_standard_format(self):
        from backend.pipeline.downloader import parse_vtt_time
        assert parse_vtt_time("00:01:23.456") == pytest.approx(83.456)

    def test_hours(self):
        from backend.pipeline.downloader import parse_vtt_time
        assert parse_vtt_time("01:00:00.000") == pytest.approx(3600.0)

    def test_short_format(self):
        from backend.pipeline.downloader import parse_vtt_time
        assert parse_vtt_time("01:30.500") == pytest.approx(90.5)


# ============================================================
# Test: SRT Export
# ============================================================

class TestSrtExport:
    def test_export_creates_file(self):
        from backend.pipeline.downloader import SubtitleEntry
        from backend.pipeline.translator import export_srt

        entries = [
            SubtitleEntry(start=1.0, end=3.0, text="Xin chào thế giới"),
            SubtitleEntry(start=4.0, end=6.5, text="Đây là dòng thứ hai"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w") as f:
            path = f.name

        try:
            export_srt(entries, path)
            content = open(path, encoding="utf-8").read()

            assert "Xin chào thế giới" in content
            assert "Đây là dòng thứ hai" in content
            assert "00:00:01,000 --> 00:00:03,000" in content
            assert "1\n" in content
            assert "2\n" in content
        finally:
            os.unlink(path)

    def test_export_srt_timestamp_format(self):
        from backend.pipeline.downloader import SubtitleEntry
        from backend.pipeline.translator import export_srt

        entries = [SubtitleEntry(start=3661.5, end=3663.0, text="Test")]

        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w") as f:
            path = f.name

        try:
            export_srt(entries, path)
            content = open(path, encoding="utf-8").read()
            # 3661.5 = 1h 1m 1s 500ms
            assert "01:01:01,500" in content
        finally:
            os.unlink(path)


# ============================================================
# Test: Translator (offline — không gọi API)
# ============================================================

class TestTranslatorOffline:
    def test_translate_empty_list(self):
        from backend.pipeline.translator import translate_subtitles
        result = translate_subtitles([])
        assert result == []

    def test_translate_preserves_timestamps(self):
        """Timestamps phải được giữ nguyên sau khi dịch."""
        from backend.pipeline.downloader import SubtitleEntry
        from backend.pipeline.translator import translate_subtitles
        import unittest.mock as mock

        entries = [
            SubtitleEntry(start=1.0, end=3.0, text="Hello world"),
            SubtitleEntry(start=4.0, end=6.0, text="How are you?"),
        ]

        # Mock Gemini để không gọi API thật
        with mock.patch("backend.pipeline.translator._translate_batch_gemini") as mock_gemini:
            mock_gemini.return_value = ["Xin chào thế giới", "Bạn có khỏe không?"]
            
            # Set env để dùng Gemini mock
            os.environ["GEMINI_API_KEY"] = "fake_key_for_test"
            result = translate_subtitles(entries, batch_size=10)
            
        assert result[0].start == 1.0
        assert result[0].end == 3.0
        assert result[1].start == 4.0
        assert result[1].end == 6.0
