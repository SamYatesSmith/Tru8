"""
Tests for LocalStorageBackend.

All tests use the pytest tmp_path fixture so no real uploads directory is touched.
"""

import pytest

from app.services.storage import LocalStorageBackend


@pytest.fixture
def backend(tmp_path):
    """Create a LocalStorageBackend rooted in a temporary directory."""
    uploads_dir = tmp_path / "uploads"
    return LocalStorageBackend(base_dir=str(uploads_dir))


class TestLocalStorageBackend:
    """Tests for LocalStorageBackend (local filesystem storage)."""

    @pytest.mark.asyncio
    async def test_upload_creates_file(self, backend, tmp_path):
        """Upload returns a path and the file exists on disk."""
        data = b"hello world"
        path = await backend.upload(data, "test.txt", "text/plain")

        assert path is not None
        assert len(path) > 0
        # The file should physically exist
        from pathlib import Path

        assert Path(path).exists()

    @pytest.mark.asyncio
    async def test_upload_preserves_extension(self, backend):
        """The stored filename keeps the original file extension."""
        path = await backend.upload(b"\xff\xd8\xff", "photo.jpg", "image/jpeg")

        assert path.endswith(".jpg")

    @pytest.mark.asyncio
    async def test_download_reads_file(self, backend):
        """Downloaded bytes match what was uploaded."""
        original = b"binary content \x00\x01\x02"
        path = await backend.upload(original, "data.bin", "application/octet-stream")

        downloaded = await backend.download(path)
        assert downloaded == original

    @pytest.mark.asyncio
    async def test_download_raises_on_missing(self, backend):
        """Downloading a nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await backend.download("/nonexistent/path/file.txt")

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, backend):
        """After deletion the file no longer exists on disk."""
        path = await backend.upload(b"to be deleted", "temp.txt", "text/plain")

        result = await backend.delete(path)
        assert result is True

        from pathlib import Path

        assert not Path(path).exists()
