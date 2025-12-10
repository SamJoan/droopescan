"""
Cement generate extension module.
"""

from __future__ import annotations
import re
import os
import inspect
import yaml  # type: ignore
import shutil
from typing import Any, Callable, Dict, TYPE_CHECKING
from .. import Controller, minimal_logger, shell
from ..utils.version import VERSION, get_version

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


class GenerateTemplateAbstractBase(Controller):
    class Meta(Controller.Meta):
        pass

    _meta: Meta  # type: ignore

    def _generate(self, source: str, dest: str) -> None:
        msg = f'Generating {self.app._meta.label} {self._meta.label} in {dest}'
        self.app.log.info(msg)
        data: Dict[str, Dict[str, Any]] = {}

        # builtin vars
        maj_min = float(f'{VERSION[0]}.{VERSION[1]}')
        data['cement'] = {}
        data['cement']['version'] = get_version()
        data['cement']['major_version'] = VERSION[0]
        data['cement']['minor_version'] = VERSION[1]
        data['cement']['major_minor_version'] = maj_min

        f = open(os.path.join(source, '.generate.yml'))
        yaml_load: Callable = yaml.full_load if hasattr(yaml, 'full_load') else yaml.load
        g_config = yaml_load(f)
        f.close()

        vars = g_config.get('variables', {})
        exclude_list = g_config.get('exclude', [])
        ignore_list = g_config.get('ignore', [])

        # default ignore the .generate.yml config
        g_config_yml = r'^(.*)[\/\\\\]%s[\/\\\\]\.generate\.yml$' % \
                       self._meta.label
        ignore_list.append(g_config_yml)

        var_defaults: Dict = {
            'name': None,
            'prompt': None,
            'validate': None,
            'case': None,
            'default': None,
        }

        for defined_var in vars:
            var = var_defaults.copy()
            var.update(defined_var)
            for key in ['name', 'prompt']:
                assert var[key] is not None, \
                    f"Required generate config key missing: {key}"

            val: Any = None
            if var['default'] is not None and self.app.pargs.defaults:
                val = var['default']

            elif var['default'] is not None:
                default_text = f" [{var['default']}]"

            else:
                default_text = ''   # pragma: nocover

            if val is None:
                class MyPrompt(shell.Prompt):
                    class Meta:
                        text = f"{var['prompt']}{default_text}:"
                        default = var.get('default', None)

                p = MyPrompt()
                val = p.prompt()    # pragma: nocover

            if var['case'] in ['lower', 'upper', 'title']:
                val = getattr(val, var['case'])()
            elif var['case'] is not None:
                self.app.log.warning(
                    "Invalid configuration for variable " +
                    f"'{var['name']}': " +
                    "case must be one of lower, upper, or title."
                )

            if var['validate'] is not None:
                assert re.match(var['validate'], val), \
                    f"Invalid Response (must match: '{var['validate']}')"

            data[var['name']] = val

        try:
            self.app.template.copy(source, dest, data,
                                   force=self.app.pargs.force,
                                   ignore=ignore_list,
                                   exclude=exclude_list)
        except AssertionError as e:
            if re.match('(.*)already exists(.*)', e.args[0]):
                raise AssertionError(e.args[0] + ' (try: --force)')
            else:
                raise  # pragma: nocover

    def _clone(self, source: str, dest: str) -> None:
        msg = f'Cloning {self.app._meta.label} {self._meta.label} template to {dest}'
        self.app.log.info(msg)

        if os.path.exists(dest) and self.app.pargs.force is True:
            shutil.rmtree(dest)
        elif os.path.exists(dest):
            msg = f"Destination path already exists: {dest} (try: --force)"
            raise AssertionError(msg)

        shutil.copytree(source, dest)

    def _default(self) -> None:
        source = self._meta.source_path
        dest = self.app.pargs.dest

        if self.app.pargs.clone is True:
            self._clone(source, dest)
        else:
            self._generate(source, dest)


def setup_template_items(app: App) -> None:
    template_dirs = []
    template_items = []

    # look in app template dirs
    for path in app._meta.template_dirs:
        subpath = os.path.join(path, 'generate')
        if os.path.exists(subpath) and subpath not in template_dirs:
            template_dirs.append(subpath)

    # use app template module, find its path on filesystem
    if app._meta.template_module is not None:
        mod_parts = app._meta.template_module.split('.')
        mod_name = mod_parts.pop()
        try:
            mod = app.__import__(mod_name, from_module='.'.join(mod_parts))
            mod_path = os.path.dirname(inspect.getfile(mod))
            subpath = os.path.join(mod_path, 'generate')

            if os.path.exists(subpath) and subpath not in template_dirs:
                template_dirs.append(subpath)

        # FIXME: not exactly sure how to test for this so not covering
        except AttributeError:                                # pragma: nocover
            msg = 'unable to load template module' + \
                  f"{mod} from {'.'.join(mod_parts)}"   # pragma: nocover
            app.log.debug(msg)                                # pragma: nocover

    for path in template_dirs:
        for item in os.listdir(path):
            if item not in template_items:
                template_items.append(item)

            class GenerateTemplate(GenerateTemplateAbstractBase):
                class Meta:
                    label = item
                    stacked_on = 'generate'
                    stacked_type = 'nested'
                    help = f'generate {item} from template'
                    arguments = [
                        # ------------------------------------------------------
                        (['dest'],
                         {'help': 'destination directory path'}),
                        # ------------------------------------------------------
                        (['-f', '--force'],
                         {'help': 'force operation if destination exists',
                          'dest': 'force',
                          'action': 'store_true'}),
                        # ------------------------------------------------------
                        (['-D', '--defaults'],
                         {'help': 'use all default variable values',
                          'dest': 'defaults',
                          'action': 'store_true'}),
                        # ------------------------------------------------------
                        (['--clone'],
                         {'help': 'clone this template to destination path',
                          'dest': 'clone',
                          'action': 'store_true'}),
                    ]
                    source_path = os.path.join(path, item)

            app.handler.register(GenerateTemplate)


class Generate(Controller):
    class Meta(Controller.Meta):
        label = 'generate'
        stacked_on = 'base'
        stacked_type = 'nested'
        config_section = 'generate'

    _meta: Meta  # type: ignore

    def _setup(self, app: App) -> None:
        super(Generate, self)._setup(app)

    def _default(self) -> None:
        self._parser.print_help()


def load(app: App) -> None:
    app.handler.register(Generate)
    app.hook.register('pre_run', setup_template_items)
