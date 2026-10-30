import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from scripts.generate_synthetic_credentials import ROOT, generate_credentials, generate_dataset


class SyntheticCredentialsTests(unittest.TestCase):
    def test_formats_and_seed(self):
        values = generate_credentials(42)
        self.assertEqual(values, generate_credentials(42))
        self.assertNotEqual(values, generate_credentials(43))
        self.assertNotEqual(generate_credentials(), generate_credentials())
        formats = {
            "OPENWEATHER_API_KEY": r"[0-9a-f]{32}",
            "QPAY_STRIPE_SECRET_KEY": r"sk_test_[A-Za-z0-9]{24}",
            "QPAY_STRIPE_PUBLISHABLE_KEY": r"pk_test_[A-Za-z0-9]{24}",
            "PROYECTO_STRIPE_SECRET_KEY": r"sk_test_[A-Za-z0-9]{24}00[A-Za-z0-9]{8}",
            "PROYECTO_STRIPE_PUBLISHABLE_KEY": r"pk_test_[A-Za-z0-9]{24}00[A-Za-z0-9]{8}",
            "DANCE_GOOGLE_CLIENT_ID": r"[0-9]{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com",
            "BUILDUP_GOOGLE_CLIENT_ID": r"[0-9]{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com",
            "DANCE_GOOGLE_CLIENT_SECRET": r"[A-Za-z0-9_-]{24}",
            "BUILDUP_GOOGLE_CLIENT_SECRET": r"[A-Za-z0-9_-]{24}",
            "OCR_FLASK_SECRET_KEY": r"[A-Za-z0-9]{10}",
        }
        for name, pattern in formats.items():
            with self.subTest(name=name):
                self.assertIsNotNone(re.fullmatch(pattern, values["__SYNTHETIC_" + name + "__"]))
        uri = urlsplit(values["__SYNTHETIC_OCR_MONGODB_URI__"])
        self.assertEqual(uri.scheme, "mongodb+srv")
        self.assertTrue(uri.hostname.endswith(".example.invalid"))
        self.assertRegex(uri.username, r"^research_[A-Za-z0-9]{12}$")
        self.assertRegex(uri.password, r"^[A-Za-z0-9]{24}$")
        self.assertEqual(uri.path, "/OCRHack")
        self.assertEqual(uri.query, "retryWrites=true&w=majority")

    def make_source(self, root):
        source = root / "source"
        source.mkdir()
        data = (
            b"<orig>\r\n# \xff retained as bytes\r\n"
            + b"\r\n".join(key.encode("ascii") for key in generate_credentials(1))
            + b"\r\n<orig>\r\n<vuln>\r\n"
        )
        for variant in ("targets-orig", "targets-tags"):
            directory = source / variant
            directory.mkdir()
            (directory / "sample.py").write_bytes(data)
        (source / "unchanged.bin").write_bytes(b"\x00\xff\r\n")
        return source, data

    def test_copy_preserves_source_bytes_tags_and_duplicate_consistency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, original = self.make_source(root)
            output = root / "output"
            counts = generate_dataset(source, output, 7)
            expected = original
            for key, value in generate_credentials(7).items():
                expected = expected.replace(key.encode("ascii"), value.encode("ascii"))
            for variant in ("targets-orig", "targets-tags"):
                self.assertEqual((source / variant / "sample.py").read_bytes(), original)
                self.assertEqual((output / "examples" / variant / "sample.py").read_bytes(), expected)
            self.assertEqual((output / "examples" / "unchanged.bin").read_bytes(), b"\x00\xff\r\n")
            self.assertTrue(all(count == 2 for count in counts.values()))
            manifest = json.loads((output / "synthetic-credentials.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["synthetic"])
            self.assertEqual(manifest["values"], generate_credentials(7))
            with self.assertRaises(FileExistsError):
                generate_dataset(source, output, 8)
            self.assertEqual((output / "examples" / "targets-orig" / "sample.py").read_bytes(), expected)

    def test_overlapping_paths_are_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, original = self.make_source(root)
            for destination in (source, source / "output", root):
                with self.subTest(destination=destination), self.assertRaises(ValueError):
                    generate_dataset(source, destination)
            self.assertEqual((source / "targets-orig" / "sample.py").read_bytes(), original)
            self.assertFalse((source / "output").exists())

    def test_unknown_or_missing_placeholders_leave_no_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, original = self.make_source(root)
            sample = source / "targets-orig" / "sample.py"
            for data in (original + b"__SYNTHETIC_UNKNOWN__", b"no placeholders"):
                with self.subTest(data_length=len(data)):
                    sample.write_bytes(data)
                    other = source / "targets-tags" / "sample.py"
                    other.write_bytes(data)
                    output = root / "output"
                    with self.assertRaises(ValueError):
                        generate_dataset(source, output)
                    self.assertFalse(output.exists())
                    self.assertFalse(list(root.glob(".synthetic-*")))

    def test_cli_rejects_nonignored_output_inside_checkout(self):
        output = ROOT / "synthetic-keys-must-not-be-tracked"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_synthetic_credentials.py"),
             "--output-dir", str(output)],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the checkout", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
