from cement.core import handler, controller
from cement import ex
from dscan.common import template
from dscan.common.plugins_util import Plugin, plugins_get
from dscan.plugins import HumanBasePlugin
from subprocess import call, check_output
import dscan.common.release_api as ra
import re
import sys, os

def c(*args, **kwargs):
    ret = call(*args, **kwargs)
    if ret != 0:
        raise RuntimeError("Command %s failed." % args[0])

    return ret

class Release(HumanBasePlugin):

    class Meta:
        label = 'release'
        hide = True
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['-s', '--skip-external'], dict(action='store_true', help='Skip external tests.',
                required=False, default=False)),
        ]

    def ship(self):
        skip_external = self.app.pargs.skip_external

        ra.check_pypirc()
        ra.test_all(skip_external)
        version_nb = ra.changelog_modify()

        try:
            c(['git', 'add', '.'])
            c(['git', 'commit', '-m', 'Tagging version \'%s\'' %
                version_nb])

            curr_branch = check_output(['git', 'rev-parse',
                '--abbrev-ref', 'HEAD']).strip()
            c(['git', 'checkout', 'master'])
            c(['git', 'merge', curr_branch])

            c(['git', 'tag', version_nb])

            c(['git', 'clean', '-dXff'])

            is_release = '^[0-9.]*$'
            pypi_repo = 'pypi' if re.match(is_release, version_nb) else 'test'
            c(['python', 'setup.py', 'sdist', 'upload', '-r', pypi_repo])
            c(['python', 'setup.py', 'bdist_wheel', 'upload', '-r', pypi_repo])

            call('git remote | xargs -l git push --all', shell=True)
            call('git remote | xargs -l git push --tags', shell=True)
        finally:
            # Go back to development with the new commits from master.
            c(['git', 'checkout', 'development'])
            c(['git', 'merge', 'master'])

    @ex(help='', hide=True)
    def default(self):
        self.ship()

def load(app=None):
    app.handler.register(Release)

