"""Common Shell Utilities."""

import os
import builtins
from getpass import getpass
from subprocess import Popen, PIPE
from multiprocessing import Process
from threading import Thread
from typing import Any, Tuple, List, Union, Callable, Optional
from ..core.meta import MetaMixin
from ..core.exc import FrameworkError


def cmd(command: str,
        capture: bool = True,
        *args: Any,
        **kwargs: Any) -> Union[Tuple[str, str, int], int]:
    """
    Wrapper around ``exec_cmd`` and ``exec_cmd2`` depending on whether
    capturing output is desired.  Defaults to setting the Popen ``shell``
    keyword argument to ``True`` (string command rather than list of command
    and arguments).

    Arguments:
        command (str): The command (and arguments) to run.
        capture (bool): Whether or not to capture output.

    Other Parameters:
        args: Additional arguments are passed to ``Popen()``.
        kwargs: Additional keyword arguments are passed to ``Popen()``.

    Returns:
        tuple: When ``capture==True``, returns the ``(stdout, stderror,
            return_code)`` of the command.
        int: When ``capture==False``, returns only the ``exitcode`` of the
            command.

    Example:

        .. code-block:: python

            from cement.utils import shell

            # execute a command and capture output
            stdout, stderr, exitcode = shell.cmd('echo helloworld')

            # execute a command but do not capture output
            exit_code = shell.cmd('echo helloworld', capture=False)

    """
    kwargs['shell'] = kwargs.get('shell', True)
    exitcode: int

    if capture is True:
        stdout: str
        stderr: str
        (stdout, stderr, exitcode) = exec_cmd(command, *args, **kwargs)
        return (stdout, stderr, exitcode)
    else:
        exitcode = exec_cmd2(command, *args, **kwargs)
        return exitcode


def exec_cmd(cmd_args: Union[str, List[str]],
             *args: Any,
             **kwargs: Any) -> Tuple[str, str, int]:
    """
    Execute a shell call using Subprocess.  All additional ``*args`` and
    ``**kwargs`` are passed directly to ``subprocess.Popen``.  See
    `Subprocess
    <http://docs.python.org/library/subprocess.html>`_ for more information
    on the features of ``Popen()``.

    Args:
        cmd_args (list): List of command line arguments.

    Other Parameters:
        args: Additional arguments are passed to ``Popen()``.
        kwargs: Additional keyword arguments are passed to ``Popen()``.

    Returns:
        tuple: The ``(stdout, stderror, return_code)`` of the command.

    Example:

        .. code-block:: python

            from cement.utils import shell

            stdout, stderr, exitcode = shell.exec_cmd(['echo', 'helloworld'])

    """
    if 'stdout' not in kwargs.keys():
        kwargs['stdout'] = PIPE
    if 'stderr' not in kwargs.keys():
        kwargs['stderr'] = PIPE

    proc = Popen(cmd_args, *args, **kwargs)
    (stdout, stderr) = proc.communicate()
    proc.wait()
    return (stdout, stderr, proc.returncode)


def exec_cmd2(cmd_args: Union[str, List[str]],
              *args: Any,
              **kwargs: Any) -> int:
    """
    Similar to ``exec_cmd``, however does not capture stdout, stderr (therefore
    allowing it to print to console).  All additional ``*args`` and
    ``**kwargs`` are passed directly to ``subprocess.Popen``.  See `Subprocess
    <http://docs.python.org/library/subprocess.html>`_ for more information
    on the features of ``Popen()``.

    Args:
        cmd_args (list): List of command line arguments

    Other Parameters:
        args: Additional arguments are passed to ``Popen()``
        kwargs: Additional keyword arguments are passed to ``Popen()``

    Returns:
        int: The integer return code of the command.

    Example:

        .. code-block:: python

            from cement.utils import shell

            exitcode = shell.exec_cmd2(['echo', 'helloworld'])

    """
    proc = Popen(cmd_args, *args, **kwargs)
    proc.wait()
    return proc.returncode


def spawn(target: Callable,
          start: bool = True,
          join: bool = False,
          thread: bool = False,
          *args: Any,
          **kwargs: Any) -> Union[Process, Thread]:
    """
    Wrapper around ``spawn_process`` and ``spawn_thread`` depending on
    desired execution model.

    Args:
        target (function): The target function to execute in the sub-process.

    Keyword Args:
        start (bool): Call ``start()`` on the process before returning the
            process object.
        join (bool): Call ``join()`` on the process before returning the
            process object.  Only called if ``start == True``.
        thread (bool): Whether to spawn as thread instead of process.

    Other Parameters:
        args: Additional arguments are passed to ``Process()``
        kwargs: Additional keyword arguments are passed to ``Process()``.

    Returns:
        object: The process object returned by Process().

    Example:

        .. code-block:: python

            from cement.utils import shell

            def add(a, b):
                print(a + b)

            p = shell.spawn(add, args=(12, 27))
            p.join()
    """
    if thread is True:
        return spawn_thread(target, start, join, *args, **kwargs)
    else:
        return spawn_process(target, start, join, *args, **kwargs)


def spawn_process(target: Callable,
                  start: bool = True,
                  join: bool = False,
                  *args: Any,
                  **kwargs: Any) -> Process:
    """
    A quick wrapper around ``multiprocessing.Process()``.  By default the
    ``start()`` function will be called before the spawned process object is
    returned. See `MultiProcessing
    <https://docs.python.org/3/library/multiprocessing.html>`_ for more
    information on the features of ``Process()``.

    Args:
        target (function): The target function to execute in the sub-process.

    Keyword Args:
        start (bool): Call ``start()`` on the process before returning the
            process object.
        join (bool): Call ``join()`` on the process before returning the
            process object.  Only called if ``start == True``.

    Other Parameters:
        args: Additional arguments are passed to ``Process()``
        kwargs: Additional keyword arguments are passed to ``Process()``.

    Returns:
        object: The process object returned by Process().

    Example:

        .. code-block:: python

            from cement.utils import shell

            def add(a, b):
                print(a + b)

            p = shell.spawn_process(add, args=(12, 27))
            p.join()

    """
    kwargs['target'] = target
    proc = Process(*args, **kwargs)

    if start and not join:
        proc.start()
    elif start and join:
        proc.start()
        proc.join()
    return proc


def spawn_thread(target: Callable,
                 start: bool = True,
                 join: bool = False,
                 *args: Any,
                 **kwargs: Any) -> Thread:
    """
    A quick wrapper around ``threading.Thread()``.  By default the ``start()``
    function will be called before the spawned thread object is returned
    See `Threading
    <https://docs.python.org/3/library/threading.html>`_ for more
    information on the features of ``Thread()``.

    Args:
        target (function): The target function to execute in the thread.

    Keyword Args:
        start (bool): Call ``start()`` on the thread before returning the
            thread object.
        join (bool): Call ``join()`` on the thread before returning the thread
            object. Only called if ``start == True``.

    Other Parameters:
        args: Additional arguments are passed to ``Thread()``.
        kwargs: Additional keyword arguments are passed to ``Thread()``.

    Returns:
        object: The thread object returned by ``Thread()``.

    Example:

        .. code-block:: python

            from cement.utils import shell

            def add(a, b):
                print(a + b)

            t = shell.spawn_thread(add, args=(12, 27))
            t.join()

    """
    kwargs['target'] = target
    thr = Thread(*args, **kwargs)

    if start and not join:
        thr.start()
    elif start and join:
        thr.start()
        thr.join()
    return thr


class Prompt(MetaMixin):

    """
    A wrapper around ``input`` whose purpose is to limit the redundent tasks of
    gather usr input.  Can be used in several ways depending on the use case
    (simple input, options, and numbered selection).

    Args:
        text (str): The text displayed at the input prompt.

    Example:

        Simple prompt to halt operations and wait for user to hit enter:

        .. code-block:: python

            p = shell.Prompt("Press Enter To Continue", default='ENTER')

        .. code-block:: text

            $ python myapp.py
            Press Enter To Continue

            $


        Provide a numbered list for longer selections:

        .. code-block:: python

            p = Prompt("Where do you live?",
                    options=[
                        'San Antonio, TX',
                        'Austin, TX',
                        'Dallas, TX',
                        'Houston, TX',
                        ],
                    numbered = True,
                    )

        .. code-block:: text

            Where do you live?

            1: San Antonio, TX
            2: Austin, TX
            3: Dallas, TX
            4: Houston, TX

            Enter the number for your selection:


        Create a more complex prompt, and process the input from the user:

        .. code-block:: python

            class MyPrompt(Prompt):
                class Meta:
                    text = "Do you agree to the terms?"
                    options = ['Yes', 'no', 'maybe-so']
                    options_separator = '|'
                    default = 'no'
                    clear = True
                    max_attempts = 99

                def process_input(self):
                    if self.input.lower() == 'yes':
                        # do something crazy
                        pass
                    else:
                        # don't do anything... maybe exit?
                        print("User doesn't agree! I'm outa here")
                        sys.exit(1)

            MyPrompt()

        .. code-block:: text

            $ python myapp.py
            [TERMINAL CLEAR]

            Do you agree to the terms? [Yes|no|maybe-so] no
            User doesn't agree! I'm outa here

            $ echo $?

            $ 1

    """
    class Meta:

        """
        Optional meta-data (can also be passed as keyword arguments to the
        parent class).
        """
        #: The text that is displayed to prompt the user
        text: str = "Tell me someting interesting:"

        #: A default value to use if the user doesn't provide any input
        default: Optional[str] = None

        #: Options to provide to the user.  If set, the input must match one
        #: of the items in the options selection.
        options: Optional[dict] = None

        #: Separator to use within the option selection (non-numbered)
        options_separator: str = ','

        #: Display options in a numbered list, where the user can enter a
        #: number.  Useful for long selections.
        numbered: bool = False

        #: The text to display along with the numbered selection for user
        #: input.
        selection_text: str = "Enter the number for your selection:"

        #: Whether or not to automatically prompt() the user once the class
        #: is instantiated.
        auto: bool = True

        #: Whether to treat user input as case insensitive (only used to
        #: compare user input with available options).
        case_insensitive: bool = True

        #: Whether or not to clear the terminal when prompting the user.
        clear: bool = False

        #: Command to issue when clearing the terminal.
        clear_command: str = 'clear'

        #: Max attempts to get proper input from the user before giving up.
        max_attempts: int = 10

        #: Raise an exception when max_attempts is hit?  If not, Prompt
        #: passes the input through as ``None``.
        max_attempts_exception: bool = True

        #: Suppress user input (use ``getpass.getpass`` instead of
        #: ``builtins.input``. Default: ``False``.
        suppress: bool = False

    def __init__(self,
                 text: Optional[str] = None,
                 *args: Any,
                 **kw: Any) -> None:
        if text is not None:
            kw['text'] = text
        super(Prompt, self).__init__(*args, **kw)

        self.input: Optional[str] = None
        if self._meta.auto:
            self.prompt()

    def _get_suppressed_input(self, text: str) -> str:
        res: str = getpass(text)  # pragma: nocover
        return res  # pragma: nocover

    def _get_unsuppressed_input(self, text: str) -> str:
        res: str = builtins.input(text)
        return res  # pragma: nocover

    def _get_input(self, text: str) -> str:
        res: str
        if self._meta.suppress is True:
            res = self._get_suppressed_input(text)  # pragma: nocover
        else:
            res = self._get_unsuppressed_input(text)  # pragma: nocover
        return res  # pragma: nocover

    def _prompt(self) -> None:
        if self._meta.clear:
            os.system(self._meta.clear_command)

        text = ""
        if self._meta.options is not None:
            if self._meta.numbered is True:
                text = text + self._meta.text + "\n\n"
                count = 1
                for option in self._meta.options:
                    text = text + f"{count}: {option}\n"
                    count += 1
                text = text + "\n"
                text = text + self._meta.selection_text
            else:
                sep = self._meta.options_separator
                text = f"{self._meta.text} [{sep.join(self._meta.options)}]"
        else:
            text = self._meta.text

        self.input = self._get_input(f"{text} ")
        if self.input == '' and self._meta.default is not None:
            self.input = self._meta.default
        elif self.input == '':
            self.input = None

    def prompt(self) -> Optional[str]:
        """
        Prompt the user, and store their input as ``self.input``.
        """

        attempt = 0
        while self.input is None:
            if attempt >= int(self._meta.max_attempts):
                if self._meta.max_attempts_exception is True:
                    raise FrameworkError("Maximum attempts exceeded getting "
                                         "valid user input")
                else:
                    return self.input

            attempt += 1
            self._prompt()

            if self.input is None:
                continue
            elif self._meta.options is not None:
                if self._meta.numbered:
                    try:
                        self.input = self._meta.options[int(self.input) - 1]
                    except (IndexError, ValueError):
                        self.input = None
                        continue
                else:
                    if self._meta.case_insensitive is True:
                        lower_options = [x.lower()
                                         for x in self._meta.options]
                        if self.input.lower() not in lower_options:
                            self.input = None
                            continue
                    else:
                        if self.input not in self._meta.options:
                            self.input = None
                            continue

        self.process_input()
        return self.input

    def process_input(self) -> None:
        """
        Does not do anything.  Is intended to be used in a sub-class to handle
        user input after it is prompted.
        """
        pass
