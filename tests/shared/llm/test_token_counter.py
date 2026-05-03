"""Token counter — tests for universal pythonic token estimation.

No API dependencies. Tests verify the byte-length heuristic
produces reasonable estimates for real-world content.
"""

import base64
import struct

import pytest

from shared.llm.token_counter import (
    count_text_tokens,
    count_image_tokens,
    count_image_tokens_from_url,
    estimate_context_tokens,
    fits_in_context,
    _read_image_dimensions,
)


# ── Text token counting ──────────────────────────────────

class TestCountTextTokens:
    def test_short_english_text(self):
        """'Hello world' ≈ 2-3 tokens across all LLMs."""
        tokens = count_text_tokens("Hello world")
        assert 2 <= tokens <= 4

    def test_realistic_prompt(self):
        """A 200-word prompt should be ~250-350 tokens."""
        prompt = "Analyze this apartment listing. " * 25  # ~200 words
        tokens = count_text_tokens(prompt)
        assert 150 <= tokens <= 400

    def test_json_data_package(self):
        """JSON with real listing data — typical LLM context."""
        listing_json = '{"title": "Alexan Braker Pointe", "address": "10801 N Mopac Expy, Austin, TX, 78759", "price": 1445.0, "bedrooms": 1, "bathrooms": 1, "sqft": 720, "amenities": ["Pool", "Gym", "Parking"]}'
        tokens = count_text_tokens(listing_json)
        assert 30 <= tokens <= 80

    def test_empty_string_returns_zero(self):
        assert count_text_tokens("") == 0

    def test_none_returns_zero(self):
        assert count_text_tokens(None) == 0

    def test_unicode_text(self):
        """Non-English text uses more bytes per character."""
        korean_text = "서울 아파트 분석"  # "Seoul apartment analysis"
        tokens = count_text_tokens(korean_text)
        assert tokens >= 3  # At least a few tokens

    def test_long_document(self):
        """10K words ≈ 12-15K tokens."""
        long_text = "The apartment complex features modern amenities. " * 500
        tokens = count_text_tokens(long_text)
        assert 5_000 <= tokens <= 20_000


# ── Image token counting ─────────────────────────────────

def _make_png(width: int, height: int) -> bytes:
    """Create minimal PNG header with given dimensions."""
    header = b'\x89PNG\r\n\x1a\n'
    # IHDR chunk
    ihdr_data = struct.pack('>II', width, height) + b'\x08\x02\x00\x00\x00'
    ihdr_crc = b'\x00\x00\x00\x00'  # placeholder
    ihdr_length = struct.pack('>I', len(ihdr_data))
    ihdr_chunk = ihdr_length + b'IHDR' + ihdr_data + ihdr_crc
    return header + ihdr_chunk


def _make_jpeg(width: int, height: int) -> bytes:
    """Create minimal JPEG header with SOF0 marker containing dimensions."""
    soi = b'\xff\xd8'
    # SOF0 marker
    sof0_marker = b'\xff\xc0'
    sof0_length = struct.pack('>H', 11)  # segment length
    sof0_data = b'\x08' + struct.pack('>HH', height, width) + b'\x03\x00\x00\x00'
    return soi + sof0_marker + sof0_length + sof0_data


class TestCountImageTokens:
    def test_png_1_megapixel(self):
        """1000x1000 PNG ≈ 1,600 tokens."""
        png_data = _make_png(1000, 1000)
        tokens = count_image_tokens(png_data)
        assert 1_400 <= tokens <= 1_800

    def test_png_4_megapixel(self):
        """2000x2000 PNG ≈ 6,400 tokens."""
        png_data = _make_png(2000, 2000)
        tokens = count_image_tokens(png_data)
        assert 5_000 <= tokens <= 8_000

    def test_jpeg_standard_photo(self):
        """1920x1080 JPEG ≈ 3,300 tokens."""
        jpeg_data = _make_jpeg(1920, 1080)
        tokens = count_image_tokens(jpeg_data)
        assert 2_500 <= tokens <= 4_500

    def test_small_thumbnail(self):
        """200x200 thumbnail ≈ minimal tokens."""
        png_data = _make_png(200, 200)
        tokens = count_image_tokens(png_data)
        assert 100 <= tokens <= 200

    def test_base64_encoded_image(self):
        """Accepts base64-encoded image data."""
        png_data = _make_png(800, 600)
        base64_data = base64.b64encode(png_data).decode("ascii")
        tokens = count_image_tokens(base64_data)
        assert tokens >= 100

    def test_empty_data_returns_default(self):
        tokens = count_image_tokens(b"")
        assert tokens == 1_200  # DEFAULT_IMAGE_TOKENS

    def test_invalid_data_returns_default(self):
        tokens = count_image_tokens(b"not an image")
        assert tokens >= 1_200


class TestCountImageTokensFromUrl:
    def test_default_estimate(self):
        tokens = count_image_tokens_from_url("https://photos.zillowstatic.com/fp/photo.jpg")
        assert tokens == 1_600  # 1.0 megapixel default

    def test_custom_megapixels(self):
        tokens = count_image_tokens_from_url("https://example.com/large.jpg", estimated_megapixels=4.0)
        assert tokens == 6_400


# ── Image dimension reading ───────────────────────────────

class TestReadImageDimensions:
    def test_reads_png_dimensions(self):
        png_data = _make_png(1024, 768)
        width, height = _read_image_dimensions(png_data)
        assert width == 1024
        assert height == 768

    def test_reads_jpeg_dimensions(self):
        jpeg_data = _make_jpeg(1920, 1080)
        width, height = _read_image_dimensions(jpeg_data)
        assert width == 1920
        assert height == 1080

    def test_unknown_format_returns_none(self):
        width, height = _read_image_dimensions(b"GIF89a\x00\x00")
        assert width is None
        assert height is None


# ── Context estimation ────────────────────────────────────

class TestEstimateContextTokens:
    def test_text_only(self):
        parts = ["Analyze this listing.", '{"price": 1445, "beds": 2}']
        tokens = estimate_context_tokens(parts)
        assert tokens > 0

    def test_text_plus_images(self):
        parts = ["Analyze this floor plan."]
        tokens_text_only = estimate_context_tokens(parts, image_count=0)
        tokens_with_image = estimate_context_tokens(parts, image_count=1)
        assert tokens_with_image > tokens_text_only
        assert tokens_with_image - tokens_text_only >= 1_000  # At least 1K tokens for image

    def test_multiple_images(self):
        tokens = estimate_context_tokens(["prompt"], image_count=5, average_image_megapixels=2.0)
        assert tokens >= 5 * 2 * 1_600  # 5 images × 2MP × 1600 tokens/MP


class TestFitsInContext:
    def test_short_prompt_fits(self):
        assert fits_in_context(["Hello, analyze this apartment."], max_context_tokens=200_000) is True

    def test_massive_prompt_does_not_fit(self):
        huge_text = "x " * 500_000  # ~500K tokens
        assert fits_in_context([huge_text], max_context_tokens=200_000) is False

    def test_many_images_may_not_fit(self):
        """50 high-res 2MP images would be ~160K tokens — exceeds 100K limit."""
        total_tokens = estimate_context_tokens(["prompt"], image_count=50, average_image_megapixels=2.0)
        assert total_tokens > 100_000  # 50 × 2MP × 1,600 = 160K — way over

    def test_reserves_output_tokens(self):
        """Should account for output token reservation."""
        # Text that's close to the limit
        text = "word " * 48_000  # ~48K tokens
        assert fits_in_context(
            [text], max_context_tokens=50_000, reserve_for_output=4_096
        ) is False
