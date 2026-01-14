"""Model block loading utilities for PyEdgeTwin."""

from __future__ import annotations

import logging
from typing import Any

from pyedgetwin.models.base import ModelBlock, ModelBlockContext
from pyedgetwin.runtime.config import ModelConfig
from pyedgetwin.runtime.errors import ModelBlockError
from pyedgetwin.utils.importlib import load_class

logger = logging.getLogger(__name__)


def load_model_block(
    config: ModelConfig,
    context: ModelBlockContext,
) -> ModelBlock:
    """
    Load and initialize a model block from configuration.

    This function:
    1. Dynamically imports the model class using the module_path
    2. Instantiates the class
    3. Calls init() with the provided context

    Args:
        config: Model configuration containing module_path and params
        context: Runtime context to pass to the model's init()

    Returns:
        Initialized ModelBlock instance ready for processing

    Raises:
        ModelBlockError: If loading or initialization fails
    """
    logger.info(f"Loading model block: {config.module_path}")

    try:
        # Load the class
        cls = load_class(config.module_path)
        logger.debug(f"Loaded class: {cls.__name__}")

        # Validate it's a ModelBlock subclass
        if not issubclass(cls, ModelBlock):
            raise ModelBlockError(
                f"Class {config.module_path} does not inherit from ModelBlock",
                details={"class": cls.__name__, "bases": [b.__name__ for b in cls.__bases__]},
            )

        # Create instance
        instance = cls()
        logger.debug(f"Created instance of {cls.__name__}")

        # Initialize with context
        instance.init(context)
        logger.info(
            f"Initialized model block {cls.__name__} "
            f"(version={config.version}, params={list(config.params.keys())})"
        )

        return instance

    except ModelBlockError:
        raise
    except ImportError as e:
        raise ModelBlockError(
            f"Failed to import model block: {e}",
            details={"module_path": config.module_path},
        )
    except Exception as e:
        raise ModelBlockError(
            f"Failed to initialize model block: {e}",
            details={"module_path": config.module_path, "error_type": type(e).__name__},
        )


def create_context(
    asset_id: str,
    twin_id: str,
    model_version: str,
    params: dict[str, Any],
) -> ModelBlockContext:
    """
    Create a ModelBlockContext from components.

    Args:
        asset_id: Physical asset identifier
        twin_id: Digital twin identifier
        model_version: Version of the model
        params: Model-specific parameters

    Returns:
        Configured ModelBlockContext
    """
    return ModelBlockContext(
        asset_id=asset_id,
        twin_id=twin_id,
        model_version=model_version,
        config=params,
    )


def validate_model_output(output: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that model output contains required keys.

    Args:
        output: Output dictionary from model.process()

    Returns:
        Tuple of (is_valid, list of missing keys)
    """
    required_keys = {"raw_value", "twin_estimate", "anomaly_flag"}
    missing = required_keys - set(output.keys())
    return len(missing) == 0, list(missing)
