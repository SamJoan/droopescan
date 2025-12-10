# Cement 2.x / 3.x compatibility shim
try:
    # Cement 3.x
    from cement.ext.ext_controller import ExtController as CementBaseController
    from cement.core.controller import Controller
except ImportError:
    # Cement 2.x
    from cement.core.controller import CementBaseController
    Controller = CementBaseController  # Alias for compatibility

__all__ = ['CementBaseController', 'Controller']
