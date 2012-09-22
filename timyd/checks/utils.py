from timyd import Service, CheckFailure


class InvertedCheckPassed(CheckFailure):
    pass


class InvertedCheckUnexpectedError(CheckFailure):
    pass


class InverseCheck(Service):
    """Inverse check; succeeds only if the given check fails.
    """

    def __init__(self, name, check, with_error=None):
        Service.__init__(self, name)
        self._check = check
        self._with_error = with_error

    def check(self):
        status = self._check.status
        if status == '': # no exception: ok
            raise InvertedCheckPassed
        elif self._with_error != () and status not in self._with_error:
            raise InvertedCheckUnexpectedError
