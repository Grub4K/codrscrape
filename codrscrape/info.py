from importlib import metadata as _im

NAME = "codrscrape"
_meta = _im.metadata(NAME).json
__version__ = _meta.get("version")
__author__ = _meta.get("author")
__license__ = _meta.get("license")
__summary = _meta.get("summary")
SUMMARY = __summary if isinstance(__summary, str) else None
__copyright__ = "Copyright (c) 2022, Simon Sawicki"
