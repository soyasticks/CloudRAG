"""
Unit tests for validation.py.

Run with: python -m pytest backend/tests/ -v
(from repo root, with backend/ on PYTHONPATH, or run inside backend/)

These deliberately do NOT require AWS credentials or network access —
validation logic should be testable in complete isolation.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.validation import validate_upload, validate_question, ValidationError


def test_validate_upload_rejects_non_pdf():
    with pytest.raises(ValidationError):
        validate_upload("notes.txt", "text/plain", 1000)


def test_validate_upload_rejects_oversized_file():
    with pytest.raises(ValidationError):
        validate_upload("policy.pdf", "application/pdf", 999_999_999)


def test_validate_upload_rejects_empty_file():
    with pytest.raises(ValidationError):
        validate_upload("policy.pdf", "application/pdf", 0)


def test_validate_upload_accepts_valid_pdf():
    validate_upload("policy.pdf", "application/pdf", 50_000)  # should not raise


def test_validate_question_rejects_none():
    with pytest.raises(ValidationError):
        validate_question(None)


def test_validate_question_rejects_empty_string():
    with pytest.raises(ValidationError):
        validate_question("")


def test_validate_question_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        validate_question("   \t\n")


def test_validate_question_accepts_normal_question():
    validate_question("What is the leave policy?")  # should not raise


def test_validate_question_rejects_too_long():
    with pytest.raises(ValidationError):
        validate_question("a" * 10_000)

