"""
WARNING: THIS EXTENSION IS EXPERIMENTAL

Experimental extension may (and probably will) change at any time.  Please do
not rely on these features until they are more fully vetted.

The Reload Config Framework Extension enables applications built on Cement to
easily reload configuration settings any time configuration files are
modified without stopping/restarting the process.

Requirements
------------

 * Python 2.6+, Python 3+
 * Python Modules: pyinotify
 * Linux (Kernel 2.6.13+)



Features
--------

 * Application configuration files (``CementApp.Meta.config_files``) are
   reloaded if modified.
 * Application plugin configuration files (Anything found in
   (``CementApp.Meta.plugin_config_dirs``) are reloaded if modified.
 * The framework calls ``CementApp.config.parse_file()`` on any watched files
   once the kernel has signaled a modification.
 * New configurations settings are accessible via ``CementApp.config`` nearly
   immediately once the kernel (inotify) picks up the change.
 * Provides a ``pre_reload_config`` and ``post_reload_config`` hook so that
   applications can tie into the event and perform operations any time a
   configuration file is modified.
 * Asynchronously monitors configuration files for changes via inotify.  Long
   running processes are not blocked by the operations performed when files
   are detected to be modified.


Limitations
-----------

 * Currently this extension only re-parses configuration files into the
   config handler.  Some applications may need further work in-order to truly
   honor those changes.  For example, if a configuration settings toggles
   something on or off, or triggers something else to happen (like making an
   API connection, etc)... this extension does not currently handle that, and
   it is left up to the application developer to tie into the events via the
   provided hooks.
 * Only available on Linux based systems.


Configuration
-------------

This extension does not currently honor any configuration settings.


Hooks
-----

This extension defines the following hooks:

pre_reload_config
^^^^^^^^^^^^^^^^^

Run right before any framework actions are performed once modifications to
any of the watched files are detected.  Expects a single argument, which is
the ``app`` object, and does not expect anything in return.

.. code-block:: python

    def my_pre_reload_config_hook(app):
        # do something with app?
        pass

post_reload_config
^^^^^^^^^^^^^^^^^^

Run right after any framework actions are performed once modifications to any
of the watched files are detected.  Expects a single argument, which is the
``app`` object, and does not expect anything in return.

.. code-block:: python

    def my_post_reload_config_hook(app):
        # do something with app?
        pass


Usage
-----

The following example shows how to add the reload_config extension, as well as
perform an arbitrary action any time configuration changes are detected.

.. code-block:: python

    from time import sleep
    from cement.core.exc import CaughtSignal
    from cement.core import hook
    from cement.core.foundation import CementApp
    from cement.core.controller import CementBaseController, expose

    def print_foo(app):
        print "Foo => %s" % app.config.get('myapp', 'foo')

    class Base(CementBaseController):
        class Meta:
            label = 'base'

        @expose(hide=True)
        def default(self):
            print('Inside Base.default()')

            # simulate a long running process
            while True:
                sleep(30)

    class MyApp(CementApp):
        class Meta:
            label = 'myapp'
            base_controller = Base
            extensions = ['reload_config']


    with MyApp() as app:
        # run this anytime the configuration has changed
        hook.register('post_reload_config', print_foo)

        try:
            app.run()
        except CaughtSignal as e:
            # maybe do something... but catch it regardless so app.close() is
            # called when exiting `with` cleanly.
            print(e)


The following would output something like the following when ``~/.myapp.conf``
or any other configuration file is modified (spaces added for clarity):

.. code-block:: console

    Inside Base.default()


    2015-05-05 03:00:32,023 (DEBUG) cement.ext.ext_reload_config : config
                                    path modified: mask=IN_CLOSE_WRITE,
                                    path=/home/vagrant/.myapp.conf
    2015-05-05 03:00:32,023 (DEBUG) cement.core.config : config file
                                    '/home/vagrant/.myapp.conf' exists,
                                    loading settings...
    2015-05-05 03:00:32,023 (DEBUG) cement.core.hook : running hook
                                    'post_reload_config' (<function print_foo
                                    at 0x7f1b52a5ab70>) from __main__
    Foo => bar


    2015-05-05 03:00:32,023 (DEBUG) cement.ext.ext_reload_config : config
                                    path modified: mask=IN_CLOSE_WRITE,
                                    path=/home/vagrant/.myapp.conf
    2015-05-05 03:00:32,023 (DEBUG) cement.core.config : config file
                                    '/home/vagrant/.myapp.conf' exists,
                                    loading settings...
    2015-05-05 03:00:32,023 (DEBUG) cement.core.hook : running hook
                                    'post_reload_config' (<function print_foo
                                    at 0x7f1b52a5ab70>) from __main__
    Foo => bar2


    2015-05-05 03:00:32,023 (DEBUG) cement.ext.ext_reload_config : config
                                    path modified: mask=IN_CLOSE_WRITE,
                                    path=/home/vagrant/.myapp.conf
    2015-05-05 03:00:32,023 (DEBUG) cement.core.config : config file
                                    '/home/vagrant/.myapp.conf' exists,
                                    loading settings...
    2015-05-05 03:00:32,023 (DEBUG) cement.core.hook : running hook
                                    'post_reload_config' (<function print_foo
                                    at 0x7f1b52a5ab70>) from __main__
    Foo => bar3


"""

import os
import signal
import pyinotify
from ..core import backend, hook
from ..utils.misc import minimal_logger
from ..utils import shell, fs

LOG = minimal_logger(__name__)
MASK = pyinotify.IN_CLOSE_WRITE
NOTIFIER = None


class ConfigEventHandler(pyinotify.ProcessEvent):

    def __init__(self, app, watched_files, **kw):
        self.app = app
        self.watched_files = watched_files
        super(ConfigEventHandler, self).__init__()

    def process_default(self, event):
        if event.pathname in self.watched_files:
            LOG.debug('config path modified: mask=%s, path=%s' %
                      (event.maskname, event.pathname))
            for res in hook.run('pre_reload_config', self.app):
                pass
            self.app.config.parse_file(event.pathname)
            for res in hook.run('post_reload_config', self.app):
                pass


def spawn_watcher(app):
    global NOTIFIER

    # directories to tell inotify to watch
    watched_dirs = []

    # files to actual perform actions on
    watched_files = []

    # watch manager
    wm = pyinotify.WatchManager()

    # watch all config files, and plugin config files
    watched_files = []

    for plugin_dir in app._meta.plugin_config_dirs:
        plugin_dir = fs.abspath(plugin_dir)
        if not os.path.exists(plugin_dir):
            continue

        if plugin_dir not in watched_dirs:
            watched_dirs.append(plugin_dir)

        # just want the first one... looks wierd, but python 2/3 compat
        res = os.walk(plugin_dir)
        for path, dirs, files in os.walk(plugin_dir):
            plugin_config_files = files
            break

        for plugin_config in plugin_config_files:
            full_plugin_path = os.path.join(plugin_dir, plugin_config)
            if full_plugin_path not in watched_files:
                watched_files.append(full_plugin_path)

    for path in app._meta.config_files:
        if os.path.exists(path):
            if path not in watched_files:
                watched_files.append(path)

            this_dir = os.path.dirname(path)
            if this_dir not in watched_dirs:
                watched_dirs.append(this_dir)

    for path in watched_dirs:
        wm.add_watch(path, MASK, rec=True)

    # event handler
    eh = ConfigEventHandler(app, watched_files)

    # notifier
    NOTIFIER = pyinotify.ThreadedNotifier(wm, eh)
    NOTIFIER.start()


def kill_watcher(app):
    if NOTIFIER.isAlive():
        NOTIFIER.stop()


def signal_handler(signum, frame):
    if signum in [signal.SIGTERM, signal.SIGINT]:
        if NOTIFIER.isAlive():
            NOTIFIER.stop()


def load(app):
    hook.define('pre_reload_config')
    hook.define('post_reload_config')
    hook.register('pre_run', spawn_watcher)
    hook.register('pre_close', kill_watcher)
    hook.register('signal', signal_handler)
