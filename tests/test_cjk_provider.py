"""Verified third-party download: opt-in only, pinned hash, no game writes."""
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from tools.cjk_provider import download_verified_exe


class DownloadTests(unittest.TestCase):
    def test_download_exact_hash_into_temporary_directory(self):
        data = b'owner-reviewed-test-fixture'
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'Fallout2.exe'
            calls = []

            def opener(request, timeout):
                calls.append((request.full_url, timeout))
                return BytesIO(data)

            self.assertEqual(download_verified_exe(target, expected, opener), target)
            self.assertEqual(target.read_bytes(), data)
            self.assertTrue(calls[0][0].startswith('https://raw.githubusercontent.com/NovaRain/'))
            with self.assertRaisesRegex(ValueError, "overwrite"):
                download_verified_exe(target, expected, opener)

    def test_hash_mismatch_never_writes_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'Fallout2.exe'
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                download_verified_exe(target, '0' * 64,
                                      lambda request, timeout: BytesIO(b'untrusted'))
            self.assertFalse(target.exists())

    def test_oversized_payload_never_writes_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'Fallout2.exe'
            with self.assertRaisesRegex(ValueError, "exceeded"):
                download_verified_exe(target, '0' * 64,
                                      lambda request, timeout: BytesIO(b'x' * (2 * 1024 * 1024 + 1)))
            self.assertFalse(target.exists())

    def test_invalid_expected_hash_rejected_before_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Invalid"):
                download_verified_exe(Path(directory) / 'donor.exe', 'not-sha')


if __name__ == "__main__":
    unittest.main()
