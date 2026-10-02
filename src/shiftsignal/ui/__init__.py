"""Rerunnable UI entry point; the standalone host owns page configuration."""
from shiftsignal import __version__
from shiftsignal.ui import signal_theme
from shiftsignal.ui.app import render

APP_INFO = {"product": "Shift Signal", "version": __version__, "repo": "cannibalization-analysis", "slug": "shift"}
__all__ = ["APP_INFO", "render", "signal_theme"]
