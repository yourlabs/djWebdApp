class DjwebdappException(Exception):
    """Base class for all our exceptions."""


class PermanentError(DjwebdappException):
    """Non-recoverable error"""
