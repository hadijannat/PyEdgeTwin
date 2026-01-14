"""Unit tests for dynamic import utilities."""

from __future__ import annotations

import pytest

from pyedgetwin.utils.importlib import load_class, load_instance, get_module_path
from pyedgetwin.models.base import ModelBlock


class TestLoadClass:
    """Tests for load_class function."""

    def test_load_valid_class(self) -> None:
        """Test loading a valid class."""
        cls = load_class("pyedgetwin.models.base:ModelBlock")
        assert cls is ModelBlock

    def test_load_from_tests(self) -> None:
        """Test loading a class from test fixtures."""
        cls = load_class("tests.fixtures.mock_model:MockModel")
        assert cls.__name__ == "MockModel"
        assert issubclass(cls, ModelBlock)

    def test_invalid_format_raises(self) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Expected"):
            load_class("invalid_path_without_colon")

    def test_missing_module_raises(self) -> None:
        """Test that missing module raises ImportError."""
        with pytest.raises(ImportError, match="Failed to import"):
            load_class("nonexistent.module:SomeClass")

    def test_missing_class_raises(self) -> None:
        """Test that missing class raises AttributeError."""
        with pytest.raises(AttributeError, match="not found"):
            load_class("pyedgetwin.models.base:NonexistentClass")


class TestLoadInstance:
    """Tests for load_instance function."""

    def test_load_instance(self) -> None:
        """Test loading and instantiating a class."""
        instance = load_instance("tests.fixtures.mock_model:MockModel")
        assert instance is not None
        assert hasattr(instance, "process")


class TestGetModulePath:
    """Tests for get_module_path function."""

    def test_get_module_path(self) -> None:
        """Test getting module path from a class."""
        path = get_module_path(ModelBlock)
        assert path == "pyedgetwin.models.base:ModelBlock"
