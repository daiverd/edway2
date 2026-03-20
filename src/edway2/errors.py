"""Exception classes for edway2."""


class EdwayError(Exception):
    """Base exception."""

    pass


class ParseError(EdwayError):
    """Command parsing failed."""

    pass


class RangeError(EdwayError):
    """Invalid block range."""

    pass


class FileError(EdwayError):
    """File operation failed."""

    pass


class AudioError(EdwayError):
    """Audio operation failed."""

    pass
