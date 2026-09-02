"""Safe, normalized errors returned by all enterprise connectors."""


class ConnectorError(RuntimeError):
    """Base connector failure safe to expose without leaking credentials."""


class ConnectorNotFoundError(ConnectorError):
    pass


class ConnectorInputError(ConnectorError):
    pass


class ConnectorTemporaryError(ConnectorError):
    """A transient failure that the gateway may retry."""


class ConnectorPermanentError(ConnectorError):
    """A business or client error that must not be retried automatically."""


class ApprovalRequiredError(ConnectorError):
    pass
