class DQException(Exception):
    """Define a base class for DataQuickExceptions, and subclass all specific exceptions from this"""
    pass


class LoaderException(DQException):
    """Generic exception for expected bad things happening inside loader functions"""
    pass


class LoaderNotFound(LoaderException):
    """Raise when no loader was found"""
    pass


class IncorrectFileType(LoaderException):
    """Raise this exception when a file is determined to be an incorrect type for the loader function"""
    pass
