"""Common File System Utilities."""

import os
import shutil


def abspath(path):
    """
    Return an absolute path, while also expanding the '~' user directory
    shortcut.

    :param path: The original path to expand.
    :rtype: str

    """
    return os.path.abspath(os.path.expanduser(path))


def backup(path, suffix='.bak'):
    """
    Rename a file or directory safely without overwriting an existing
    backup of the same name.

    :param path: The path to the file or directory to make a backup of.
    :param suffix: The suffix to rename files with.
    :returns: The new path of backed up file/directory
    :rtype: str

    """
    count = -1
    new_path = None
    while True:
        if os.path.exists(path):
            if count == -1:
                new_path = "%s%s" % (path, suffix)
            else:
                new_path = "%s%s.%s" % (path, suffix, count)
            if os.path.exists(new_path):
                count += 1
                continue
            else:
                if os.path.isfile(path):
                    shutil.copy(path, new_path)
                elif os.path.isdir(path):
                    shutil.copytree(path, new_path)
                break
        else:
            break
    return new_path

# Kinda dirty, but should resolve issues on Windows per #183
if 'HOME' in os.environ:
    HOME_DIR = abspath(os.environ['HOME'])
else:
    HOME_DIR = abspath('~')  # pragma: nocover
