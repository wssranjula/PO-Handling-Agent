class ApplicationError(Exception):
    """Base class for expected application failures."""


class ResourceNotFoundError(ApplicationError):
    pass


class ConflictError(ApplicationError):
    pass


class InvalidAttachmentError(ApplicationError):
    pass


class IntegrationUnavailableError(ApplicationError):
    pass
