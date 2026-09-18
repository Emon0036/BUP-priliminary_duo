class GridWiseError(Exception):
    """Base class for expected, sanitized application errors."""


class InterpretationError(GridWiseError):
    pass


class ProviderError(InterpretationError):
    pass


class GuardrailError(InterpretationError):
    pass


class OptimizationError(GridWiseError):
    pass


class ReplayValidationError(GridWiseError):
    pass
