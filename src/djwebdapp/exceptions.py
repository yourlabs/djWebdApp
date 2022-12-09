

class BaseException(Exception):
    pass


class PermanentError(BaseException):
    pass


class TemporaryError(BaseException):
    pass


class DependencyError(BaseException):
    pass


class AbortedDependencyError(DependencyError):
    def __init__(self, parent, dependencies):
        self.parent = parent
        self.dependencies = dependencies

    def transactions(self):
        return [self.parent] + self.dependencies

    def transactions_pks(self):
        return [tx.pk for tx in self.transactions()]


class ExcludedDependencyError(DependencyError):
    pass
