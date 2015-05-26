class PluginInitialisationError(BaseException):
    pass

class NetworkConnectionError(BaseException):
    pass

class RemoteServerError(BaseException):
    pass

class MessageInvalidError(BaseException):
    pass

class InputDataError(BaseException):
    pass

##
# AsyncServerException is used to wrap communication exceptions.

class AsyncServerException(Exception):
    pass