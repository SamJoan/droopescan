"""Common Shell Utilities."""

import os
import sys
from subprocess import Popen, PIPE
from multiprocessing import Process
from threading import Thread
from ..core.meta import MetaMixin
from ..core.exc import FrameworkError


def exec_cmd(cmd_args, *args, **kw):
    """
    Execute a shell call using Subprocess.  All additional `*args` and
    `**kwargs` are passed directly to subprocess.Popen.  See `Subprocess
    <http://docs.python.org/library/subprocess.html>`_ for more information
    on the features of `Popen()`.

    :param cmd_args: List of command line arguments.
    :type cmd_args: list.
    :param args: Additional arguments are passed to Popen().
    :param kwargs: Additional keyword arguments are passed to Popen().
    :returns: The (stdout, stderror, return_code) of the command.
    :rtype: tuple

    Usage:

    .. code-block:: python

        from cement.utils import shell

        stdout, stderr, exitcode = shell.exec_cmd(['echo', 'helloworld'])

    """
    if 'stdout' not in kw.keys():
        kw['stdout'] = PIPE
    if 'stderr' not in kw.keys():
        kw['stderr'] = PIPE

    proc = Popen(cmd_args, *args, **kw)
    (stdout, stderr) = proc.communicate()
    proc.wait()
    return (stdout, stderr, proc.returncode)


def exec_cmd2(cmd_args, *args, **kw):
    """
    Similar to exec_cmd, however does not capture stdout, stderr (therefore
    allowing it to print to console).  All additional `*args` and
    `**kwargs` are passed directly to subprocess.Popen.  See `Subprocess
    <http://docs.python.org/library/subprocess.html>`_ for more information
    on the features of `Popen()`.

    :param cmd_args: List of command line arguments.
    :type cmd_args: list.
    :param args: Additional arguments are passed to Popen().
    :param kwargs: Additional keyword arguments are passed to Popen().
    :returns: The integer return code of the command.
    :rtype: int

    Usage:

    .. code-block:: python

        from cement.utils import shell

        exitcode = shell.exec_cmd2(['echo', 'helloworld'])

    """
    proc = Popen(cmd_args, *args, **kw)
    proc.wait()
    return proc.returncode


def spawn_process(target, start=True, join=False, *args, **kwargs):
    """
    A quick wrapper around multiprocessing.Process().  By default the start()
    function will be called before the spawned process object is returned.
    See `MultiProcessing
    <https://docs.python.org/2/library/multiprocessing.html>`_ for more
    information on the features of `Process()`.

    :param target: The target function to execute in the sub-process.
    :param start: Call start() on the process before returning the process
        object.
    :param join: Call join() on the process before returning the process
        object.  Only called if start=True.
    :param args: Additional arguments are passed to Process().
    :param kwargs: Additional keyword arguments are passed to Process().
    :returns: The process object returned by Process().

    Usage:

    .. code-block:: python

        from cement.utils import shell

        def add(a, b):
            print(a + b)

        p = shell.spawn_process(add, args=(12, 27))
        p.join()

    """
    proc = Process(target=target, *args, **kwargs)

    if start and not join:
        proc.start()
    elif start and join:
        proc.start()
        proc.join()
    return proc


def spawn_thread(target, start=True, join=False, *args, **kwargs):
    """
    A quick wrapper around threading.Thread().  By default the start()
    function will be called before the spawned thread object is returned
    See `Threading
    <https://docs.python.org/2/library/threading.html>`_ for more
    information on the features of `Thread()`.

    :param target: The target function to execute in the thread.
    :param start: Call start() on the thread before returning the thread
        object.
    :param join: Call join() on the thread before returning the thread
        object.  Only called if start=True.
    :param args: Additional arguments are passed to Thread().
    :param kwargs: Additional keyword arguments are passed to Thread().
    :returns: The thread object returned by Thread().

    Usage:

    .. code-block:: python

        from cement.utils import shell

        def add(a, b):
            print(a + b)

        t = shell.spawn_thread(add, args=(12, 27))
        t.join()

    """
    thr = Thread(target=target, *args, **kwargs)

    if start and not join:
        thr.start()
    elif start and join:
        thr.start()
        thr.join()
    return thr


class Prompt(MetaMixin):

    """
    A wrapper around `raw_input` or `input` (py3) whose purpose is to limit
    the redundent tasks of gather usr input.  Can be used in several ways
    depending on the use case (simple input, options, and numbered
    selection).

    :param text: The text displayed at the input prompt.

    Usage:

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
        # The text that is displayed to prompt the user
        text = "Tell me someting interesting:"

        #: A default value to use if the user doesn't provide any input
        default = None

        #: Options to provide to the user.  If set, the input must match one
        #: of the items in the options selection.
        options = None

        #: Separator to use within the option selection (non-numbered)
        options_separator = ','

        #: Display options in a numbered list, where the user can enter a
        #: number.  Useful for long selections.
        numbered = False

        #: The text to display along with the numbered selection for user
        #: input.
        selection_text = "Enter the number for your selection:"

        #: Whether or not to automatically prompt() the user once the class
        #: is instantiated.
        auto = True

        #: Whether to treat user input as case insensitive (only used to
        #: compare user input with available options).
        case_insensitive = True

        #: Whether or not to clear the terminal when prompting the user.
        clear = False

        #: Command to issue when clearing the terminal.
        clear_command = 'clear'

        #: Max attempts to get proper input from the user before giving up.
        max_attempts = 10

        #: Raise an exception when max_attempts is hit?  If not, Prompt
        #: passes the input through as `None`.
        max_attempts_exception = True

    def __init__(self, text=None, *args, **kw):
        if text is not None:
            kw['text'] = text
        super(Prompt, self).__init__(*args, **kw)

        self.input = None
        if self._meta.auto:
            self.prompt()

    def _prompt(self):
        if self._meta.clear:
            os.system(self._meta.clear_command)

        text = ""
        if self._meta.options is not None:
            if self._meta.numbered is True:
                text = text + self._meta.text + "\n\n"
                count = 1
                for option in self._meta.options:
                    text = text + "%s: %s\n" % (count, option)
                    count += 1
                text = text + "\n"
                text = text + self._meta.selection_text
            else:
                sep = self._meta.options_separator
                text = "%s [%s]" % (self._meta.text,
                                    sep.join(self._meta.options))
        else:
            text = self._meta.text

        if sys.version_info[0] < 3:                     # pragma: nocover
            self.input = raw_input("%s " % text)        # pragma: nocover
        else:                                           # pragma: nocover
            self.input = input("%s " % text)            # pragma: nocover

        if self.input == '' and self._meta.default is not None:
            self.input = self._meta.default
        elif self.input == '':
            self.input = None

    def prompt(self):
        """
        Prompt the user, and store their input as `self.input`.
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
                    except (IndexError, ValueError) as e:
                        self.input = None
                        continue
                else:
                    if self._meta.case_insensitive is True:
                        lower_options = [x.lower()
                                         for x in self._meta.options]
                        if not self.input.lower() in lower_options:
                            self.input = None
                            continue
                    else:
                        if self.input not in self._meta.options:
                            self.input = None
                            continue

        self.process_input()
        return self.input

    def process_input(self):
        """
        Does not do anything.  Is intended to be used in a sub-class to handle
        user input after it is prompted.
        """
        pass
