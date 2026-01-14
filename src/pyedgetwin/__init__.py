"""
PyEdgeTwin - Python-first runtime for hybrid model deployment on edge devices.

This package provides a container-native runtime framework for deploying
hybrid (physics + data-driven) models on streaming industrial telemetry.
"""

__version__ = "0.1.0"
__author__ = "Aero Shariati"
__email__ = "h.jannatabadi@iat.rwth-aachen.de"

from pyedgetwin.io.base import BaseConnector
from pyedgetwin.models.base import ModelBlock, ModelBlockContext
from pyedgetwin.sinks.base import BaseSink

__all__ = [
    "__version__",
    "ModelBlock",
    "ModelBlockContext",
    "BaseSink",
    "BaseConnector",
]
