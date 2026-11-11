"""Unit and integration tests for BayanGate CLI and SDK functions (BG-004)."""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bayan_gate
from bayan_gate.cli import (
    build_parser,
    cmd_demo,
    cmd_redact,
    cmd_scan,
    main,
    parse_types_arg,
)
from bayan_gate.models import EntityType, MaskingPolicy


class TestBayanGateCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

        # Create sample document with PII
        self.sample_file = self.test_dir / "sample_doc.txt"
        self.sample_text = (
            "عقد توريد:\n"
            "الطرف الأول: شركة التقنية (سجل: 1010123456)\n"
            "الممثل: م. طارق، هوية وطنية: 1082345678\n"
            "جوال: 0501234567 | بريد: tariq@tech.sa\n"
            "حساب بنكي: SA03 8000 0000 6080 1016 7519\n"
        )
        self.sample_file.write_text(self.sample_text, encoding="utf-8")

        # Create clean document without PII
        self.clean_file = self.test_dir / "clean_doc.txt"
        self.clean_text = "تقرير عام عن أعمال الربع الثالث ومؤشرات الأداء التشغيلي."
        self.clean_file.write_text(self.clean_text, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------
    # 1. Type Argument Parsing
    # -------------------------------------------------------------
    def test_parse_types_arg_valid(self):
        types = parse_types_arg("SAUDI_NATIONAL_ID, GCC_IBAN, phone_number")
        self.assertEqual(types, {
            EntityType.SAUDI_NATIONAL_ID,
            EntityType.GCC_IBAN,
            EntityType.PHONE_NUMBER,
        })

    def test_parse_types_arg_empty(self):
        self.assertIsNone(parse_types_arg(None))
        self.assertIsNone(parse_types_arg(""))
        self.assertIsNone(parse_types_arg("   "))

    def test_parse_types_arg_invalid(self):
        with self.assertRaises(ValueError):
            parse_types_arg("SAUDI_NATIONAL_ID, INVALID_TYPE_NAME")

    # -------------------------------------------------------------
    # 2. CLI Redact Subcommand Tests
    # -------------------------------------------------------------
    def test_cli_redact_to_file(self):
        parser = build_parser()
        out_file = self.test_dir / "redacted.txt"
        audit_file = self.test_dir / "audit.json"

        args = parser.parse_args([
            "redact",
            "-i", str(self.sample_file),
            "-o", str(out_file),
            "--policy", "full",
            "--audit-log", str(audit_file),
        ])

        with patch("sys.stderr", new=io.StringIO()):
            code = args.func(args)

        self.assertEqual(code, 0)
        self.assertTrue(out_file.exists())
        self.assertTrue(audit_file.exists())

        redacted_content = out_file.read_text(encoding="utf-8")
        self.assertIn("[REDACTED_SAUDI_NATIONAL_ID]", redacted_content)
        self.assertIn("[REDACTED_PHONE_NUMBER]", redacted_content)
        self.assertIn("[REDACTED_GCC_IBAN]", redacted_content)
        self.assertNotIn("1082345678", redacted_content)

        audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
        self.assertGreaterEqual(audit_data["redaction_count"], 3)
        self.assertNotIn("1082345678", str(audit_data))

    def test_cli_redact_partial_policy(self):
        parser = build_parser()
        out_file = self.test_dir / "redacted_partial.txt"

        args = parser.parse_args([
            "redact",
            "-i", str(self.sample_file),
            "-o", str(out_file),
            "--policy", "partial",
        ])

        with patch("sys.stderr", new=io.StringIO()):
            code = args.func(args)

        self.assertEqual(code, 0)
        redacted_content = out_file.read_text(encoding="utf-8")
        self.assertIn("108****678", redacted_content)

    def test_cli_redact_stdin_to_stdout(self):
        parser = build_parser()
        args = parser.parse_args(["redact", "--policy", "full"])

        with patch("sys.stdin", new=io.StringIO("National ID: 1082345678")), \
             patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("National ID: [REDACTED_SAUDI_NATIONAL_ID]", output)

    def test_cli_redact_file_not_found(self):
        parser = build_parser()
        args = parser.parse_args(["redact", "-i", str(self.test_dir / "missing.txt")])

        with patch("sys.stderr", new=io.StringIO()) as fake_err:
            code = args.func(args)
            err_output = fake_err.getvalue()

        self.assertEqual(code, 1)
        self.assertIn("not found", err_output)

    # -------------------------------------------------------------
    # 3. CLI Scan Subcommand Tests
    # -------------------------------------------------------------
    def test_cli_scan_clean_document(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "-i", str(self.clean_file)])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        # Clean document exits with code 0
        self.assertEqual(code, 0)
        self.assertIn("Zero sensitive entities detected", output)

    def test_cli_scan_pii_detected_exit_code(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "-i", str(self.sample_file)])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        # Detected PII exits with code 3 (for pre-commit/CI pipeline checks)
        self.assertEqual(code, 3)
        self.assertIn("Detected", output)
        self.assertIn("SAUDI_NATIONAL_ID", output)

    def test_cli_scan_json_mode(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "-i", str(self.sample_file), "--json"])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 3)
        data = json.loads(output)
        self.assertGreaterEqual(data["detected_count"], 3)
        self.assertIn("SAUDI_NATIONAL_ID", data["entity_type_counts"])

    # -------------------------------------------------------------
    # 4. CLI Demo Subcommand
    # -------------------------------------------------------------
    def test_cli_demo(self):
        parser = build_parser()
        args = parser.parse_args(["demo"])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = args.func(args)
            output = fake_out.getvalue()

        self.assertEqual(code, 0)
        self.assertIn("BayanGate — Sensitive Data Redactor Engine", output)
        self.assertIn("REDACT_FULL", output)
        self.assertIn("MASK_PARTIAL", output)

    # -------------------------------------------------------------
    # 5. Main Parser and Entrypoint
    # -------------------------------------------------------------
    def test_main_no_subcommand(self):
        with patch.object(sys, "argv", ["bayan-gate"]), \
             patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = main()
            output = fake_out.getvalue()

        self.assertEqual(code, 1)
        self.assertIn("usage: bayan-gate", output)

    def test_main_help_flag(self):
        with patch.object(sys, "argv", ["bayan-gate", "--help"]), \
             patch("sys.stdout", new=io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    # -------------------------------------------------------------
    # 6. Python SDK Top-Level Convenience Functions
    # -------------------------------------------------------------
    def test_sdk_detect_function(self):
        text = "Citizen ID: 1082345678"
        spans = bayan_gate.detect(text)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].entity_type, EntityType.SAUDI_NATIONAL_ID)

    def test_sdk_redact_function(self):
        text = "Citizen ID: 1082345678"
        res = bayan_gate.redact(text, policy=MaskingPolicy.REDACT_FULL)
        self.assertEqual(res.redacted_text, "Citizen ID: [REDACTED_SAUDI_NATIONAL_ID]")

    def test_sdk_stream_redact_function(self):
        in_stream = io.StringIO("Line 1: 1082345678\nLine 2: 0501234567\n")
        out_stream = io.StringIO()
        bayan_gate.stream_redact(in_stream, out_stream, policy=MaskingPolicy.REDACT_FULL)
        output = out_stream.getvalue()
        self.assertIn("Line 1: [REDACTED_SAUDI_NATIONAL_ID]\n", output)
        self.assertIn("Line 2: [REDACTED_PHONE_NUMBER]\n", output)


if __name__ == "__main__":
    unittest.main()
