

class BaseException(Exception):
    """ Base exception class for all exceptions of this package. """
    pass


class PermanentError(BaseException):
    """ Raised when a transaction can not be deployed. """


class TemporaryError(BaseException):
    """ Raised when a transaction has not been deployed. """
