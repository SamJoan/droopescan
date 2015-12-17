
class FileEmptyException(RuntimeError):
    pass

class CannotResumeException(RuntimeError):
    pass

class UnknownCMSException(RuntimeError):
    pass

class VersionFingerprintFailed(RuntimeError):
    pass

class MissingMajorException(Exception):
    pass
