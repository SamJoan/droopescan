
from warnings import warn

DEPRECATIONS = {
    '3.0.8-1': "Environment variable CEMENT_FRAMEWORK_LOGGING is deprecated in favor of CEMENT_LOG, and will be removed in Cement v3.2.0",  # noqa: E501
    '3.0.8-2': "App.Meta.framework_logging will be changed or removed in Cement v3.2.0",  # noqa: E501
    '3.0.10-1': "The FATAL logging facility is deprecated in favor of CRITICAL, and will be removed in future versions of Cement.",  # noqa: E501
}


def deprecate(deprecation_id: str) -> None:
    deprecation_id = str(deprecation_id)
    msg = DEPRECATIONS[deprecation_id]
    total_msg = f"{msg}. See: https://docs.builtoncement.com/release-information/deprecations#{deprecation_id}"  # noqa: E501
    warn(total_msg, DeprecationWarning, stacklevel=2)
