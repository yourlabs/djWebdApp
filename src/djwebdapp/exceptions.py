

class BaseException(Exception):
    pass


class PermanentError(BaseException):
    pass


class TemporaryError(BaseException):
    pass


class DependencyError(BaseException):
    pass


class AbortedDependencyError(DependencyError):
    def __init__(self, dependency, ascendency):
        self.dependency = dependency
        self.ascendency = ascendency

    def transactions(self):
        return [self.dependency] + self.ascendency

    def transactions_pks(self):
        return [tx.pk for tx in self.transactions()]


class ExcludedDependencyError(DependencyError):
    pass
