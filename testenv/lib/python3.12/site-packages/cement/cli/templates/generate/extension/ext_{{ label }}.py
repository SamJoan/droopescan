
from cement import minimal_logger

LOG = minimal_logger(__name__)

def {{ label }}_pre_run_hook(app):
    # do something with app
    LOG.debug('Inside {{ label }}_pre_run_hook!')

def load(app):
    # do something to extend cement
    app.hook.register('pre_run', {{ label }}_pre_run_hook)
