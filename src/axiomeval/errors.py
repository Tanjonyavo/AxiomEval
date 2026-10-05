"""Expected user-facing failures, without raw configuration contents."""


class AxiomEvalError(Exception):
    """Base class for expected AxiomEval failures."""


class ConfigurationError(AxiomEvalError):
    """Configuration cannot be read or does not match the schema."""


class ValidationError(AxiomEvalError):
    """A domain invariant is violated."""
