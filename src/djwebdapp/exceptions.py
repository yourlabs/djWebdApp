

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


class ExcludedContractError(DependencyError):
    def __init__(self, dependency, exclude_states):
        self.dependency = dependency
        self.exclude_states = exclude_states
        super().__init__(
            f'Depending {dependency} on a call with an excluded contract: {dependency.contract} {dependency.contract.state} {exclude_states}'
        )


class CallWithoutContractError(DependencyError):
    def __init__(self, call):
        super().__init__(f'Call {call} requires related .contract')
