from timyd import Service, CheckFailure


class InvertedCheckPassed(CheckFailure):
    pass


class InvertedCheckUnexpectedError(CheckFailure):
    def __init__(self, error):
        self._error = error

    def __str__(self):
        return str(self._error)


class InverseCheck(Service):
    """Inverse check; succeeds only if the given check fails.
    """

    def __init__(self, name, check, with_error=None):
        Service.__init__(self, name)
        self._check = check
        self._with_error = set()
        for error in with_error:
            if isinstance(error, basestring):
                self._with_error.add(error)
            elif isinstance(error, type) and issubclass(error, Exception):
                self._with_error.add(error.__name__)
            else:
                raise TypeError(
                        "InverseCheck expects a list of exception classes; "
                        "got a list with a %s" % type(error))

    def check(self):
        status = self._check.status
        if status == '': # no exception: ok
            raise InvertedCheckPassed
        elif self._with_error and status not in self._with_error:
            raise InvertedCheckUnexpectedError(status)

    def dependencies(self):
        return (self._check,)
