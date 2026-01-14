"""Dynamic import utilities for PyEdgeTwin."""

import importlib
from typing import Any, TypeVar

T = TypeVar("T")


def load_class(module_path: str) -> type[Any]:
    """
    Load a class from a module path string.

    Args:
        module_path: String in format "package.module:ClassName"
                    Examples:
                    - "mypackage.models:KalmanFilter"
                    - "examples.motor_filtering.model_blocks.kalman:KalmanFilterModel"

    Returns:
        The class object (not an instance)

    Raises:
        ImportError: If the module cannot be imported
        AttributeError: If the class is not found in the module
        ValueError: If the module_path format is invalid
    """
    if ":" not in module_path:
        raise ValueError(
            f"Invalid module_path format: '{module_path}'. Expected 'package.module:ClassName'"
        )

    module_name, class_name = module_path.rsplit(":", 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Failed to import module '{module_name}': {e}") from e

    try:
        cls = getattr(module, class_name)
    except AttributeError as e:
        raise AttributeError(
            f"Class '{class_name}' not found in module '{module_name}'. "
            f"Available: {[n for n in dir(module) if not n.startswith('_')]}"
        ) from e

    if not isinstance(cls, type):
        raise TypeError(f"'{module_path}' refers to {type(cls).__name__}, not a class")

    return cls


def load_instance(
    module_path: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Load a class and instantiate it with the given arguments.

    Args:
        module_path: String in format "package.module:ClassName"
        *args: Positional arguments to pass to the constructor
        **kwargs: Keyword arguments to pass to the constructor

    Returns:
        An instance of the loaded class

    Raises:
        ImportError: If the module cannot be imported
        AttributeError: If the class is not found in the module
        ValueError: If the module_path format is invalid
        TypeError: If instantiation fails
    """
    cls = load_class(module_path)
    return cls(*args, **kwargs)


def get_module_path(cls: type[Any]) -> str:
    """
    Get the module path string for a class.

    Args:
        cls: A class object

    Returns:
        String in format "package.module:ClassName"
    """
    return f"{cls.__module__}:{cls.__name__}"
