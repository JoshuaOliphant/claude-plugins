"""Exception hierarchy."""


class FreightError(Exception):
    """Base class for all errors reported to desk users."""

    exit_code = 1


class ValidationError(FreightError):
    """Input could not be parsed or is out of range."""

    exit_code = 2


class RatingError(FreightError):
    """The carrier cannot rate this shipment (no lane, overweight, ...)."""

    exit_code = 3


class DataError(FreightError):
    """A tariff, lane or rate file is missing or malformed."""

    exit_code = 4
