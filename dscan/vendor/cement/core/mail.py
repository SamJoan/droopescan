"""Cement core mail module."""

from ..core import interface, handler
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


def mail_validator(klass, obj):
    """Validates a handler implementation against the IMail interface."""

    members = [
        '_setup',
        'send',
    ]

    # FIX ME: Validate Meta/Configuration Defaults Here

    interface.validate(IMail, obj, members)


class IMail(interface.Interface):

    """
    This class defines the Mail Handler Interface.  Classes that
    implement this handler must provide the methods and attributes defined
    below.

    Implementations do *not* subclass from interfaces.

    **Configuration**

    Implementations much support the following configuration settings:

     * **to** - Default ``to`` addresses (list, or comma separated depending
       on the ConfigHandler in use)
     * **from_addr** - Default ``from_addr`` address
     * **cc** - Default ``cc`` addresses (list, or comma separated depending
       on the ConfigHandler in use)
     * **bcc** - Default ``bcc`` addresses (list, or comma separated depending
       on the ConfigHandler in use)
     * **subject** - Default ``subject``
     * **subject_prefix** - Additional string to prepend to the ``subject``

    **Usage**

    .. code-block:: python

        from cement.core import mail

        class MyMailHandler(object):
            class Meta:
                interface = mail.IMail
                label = 'my_mail_handler'
            ...

    """
    # pylint: disable=W0232, C0111, R0903
    class IMeta:

        """Interface meta-data."""

        label = 'mail'
        """The label (or type identifier) of the interface."""

        validator = mail_validator
        """Interface validator function."""

    # Must be provided by the implementation
    Meta = interface.Attribute('Handler meta-data')

    def _setup(app_obj):
        """
        The _setup function is called during application initialization and
        must 'setup' the handler object making it ready for the framework
        or the application to make further calls to it.

        :param app_obj: The application object.
        :returns: None

        """

    def send(body, **kwargs):
        """
        Send a mail message.  Keyword arguments override configuration
        defaults (cc, bcc, etc).

        :param body: The message body to send
        :type body: multiline string
        :keyword to: List of recipients (generally email addresses)
        :type to: list
        :keyword from_addr: Address (generally email) of the sender
        :type from_addr: string
        :keyword cc: List of CC Recipients
        :type cc: list
        :keyword bcc: List of BCC Recipients
        :type bcc: list
        :keyword subject: Message subject line
        :type subject: string
        :returns: Boolean (``True`` if message is sent successfully, ``False``
         otherwise)

        **Usage**

        .. code-block:: python

            # Using all configuration defaults
            app.send('This is my message body')

            # Overriding configuration defaults
            app.send('My message body'
                to=['john@example.com'],
                from_addr='me@example.com',
                cc=['jane@example.com', 'rita@example.com'],
                subject='This is my subject',
                )

        """


class CementMailHandler(handler.CementBaseHandler):

    """
    Base class that all Mail Handlers should sub-class from.

    **Configuration Options**

    This handler supports the following configuration options under a

    """
    class Meta:

        """
        Handler meta-data (can be passed as keyword arguments to the parent
        class).
        """

        #: String identifier of this handler implementation.
        label = None

        #: The interface that this handler class implements.
        interface = IMail

        #: Configuration default values
        config_defaults = {
            'to': [],
            'from_addr': 'noreply@example.com',
            'cc': [],
            'bcc': [],
            'subject': 'Default Subject Line',
            'subject_prefix': '',
        }

    def __init__(self, *args, **kw):
        super(CementMailHandler, self).__init__(*args, **kw)

    def _setup(self, app_obj):
        super(CementMailHandler, self)._setup(app_obj)
        self._validate_config()

    def send(self, body, **kw):
        raise NotImplementedError   # pragma: nocover

    def _validate_config(self):
        # convert comma separated strings to lists (ConfigParser)
        for item in ['to', 'cc', 'bcc']:
            if item in self.app.config.keys(self._meta.config_section):
                value = self.app.config.get(self._meta.config_section, item)

                # convert a comma-separated string to a list
                if type(value) is str:
                    value_list = value.split(',')

                    # clean up extra space if they had it inbetween commas
                    value_list = [x.strip() for x in value_list]

                    # set the new extensions value in the config
                    self.app.config.set(self._meta.config_section, item,
                                        value_list)
