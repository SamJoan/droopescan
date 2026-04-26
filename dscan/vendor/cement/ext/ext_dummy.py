"""Dummy Framework Extension"""

from ..core import backend, output, handler, mail
from ..utils.misc import minimal_logger

LOG = minimal_logger(__name__)


class DummyOutputHandler(output.CementOutputHandler):

    """
    This class is an internal implementation of the
    :ref:`IOutput <cement.core.output>` interface. It does not take any
    parameters on initialization, and does not actually output anything.

    """
    class Meta:

        """Handler meta-data"""

        interface = output.IOutput
        """The interface this class implements."""

        label = 'dummy'
        """The string identifier of this handler."""

        display_override_option = False

    def render(self, data_dict, template=None):
        """
        This implementation does not actually render anything to output, but
        rather logs it to the debug facility.

        :param data_dict: The data dictionary to render.
        :param template: The template parameter is not used by this
            implementation at all.
        :returns: None

        """
        LOG.debug("not rendering any output to console")
        LOG.debug("DATA: %s" % data_dict)
        return None


class DummyMailHandler(mail.CementMailHandler):

    """
    This class implements the :ref:`IMail <cement.core.mail>`
    interface, but is intended for use in development as no email is actually
    sent.

    **Usage**

    .. code-block:: python

        class MyApp(CementApp):
            class Meta:
                label = 'myapp'
                mail_handler = 'dummy'

        # create, setup, and run the app
        app = MyApp()
        app.setup()
        app.run()

        # fake sending an email message
        app.mail.send('This is my fake message',
            subject='This is my subject',
            to=['john@example.com', 'rita@example.com'],
            from_addr='me@example.com',
            )

    The above will print the following to console:

    .. code-block:: text

        ======================================================================
        DUMMY MAIL MESSAGE
        ----------------------------------------------------------------------

        To: john@example.com, rita@example.com
        From: me@example.com
        CC:
        BCC:
        Subject: This is my subject

        ---

        This is my fake message

        ----------------------------------------------------------------------

    **Configuration**

    This handler supports the following configuration settings:

     * **to** - Default ``to`` addresses (list, or comma separated depending
       on the ConfigHandler in use)
     * **from_addr** - Default ``from_addr`` address
     * **cc** - Default ``cc`` addresses (list, or comma separated depending
       on the ConfigHandler in use)
     * **bcc** - Default ``bcc`` addresses (list, or comma separated depending
       on the ConfigHandler in use)
     * **subject** - Default ``subject``
     * **subject_prefix** - Additional string to prepend to the ``subject``


    You can add these to any application configuration file under a
    ``[mail.dummy]`` section, for example:

    **~/.myapp.conf**

    .. code-block:: text

        [myapp]

        # set the mail handler to use
        mail_handler = dummy


        [mail.dummy]

        # default to addresses (comma separated list)
        to = me@example.com

        # default from address
        from = someone_else@example.com

        # default cc addresses (comma separated list)
        cc = jane@example.com, rita@example.com

        # default bcc addresses (comma separated list)
        bcc = blackhole@example.com, someone_else@example.com

        # default subject
        subject = This is The Default Subject

        # additional prefix to prepend to the subject
        subject_prefix = MY PREFIX >

    """

    class Meta:
        #: Unique identifier for this handler
        label = 'dummy'

    def _get_params(self, **kw):
        params = dict()
        for item in ['to', 'from_addr', 'cc', 'bcc', 'subject']:
            config_item = self.app.config.get(self._meta.config_section, item)
            params[item] = kw.get(item, config_item)

        # also grab the subject_prefix
        params['subject_prefix'] = self.app.config.get(
            self._meta.config_section,
            'subject_prefix'
        )

        return params

    def send(self, body, **kw):
        """
        Mimic sending an email message, but really just print what would be
        sent to console.  Keyword arguments override configuration
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
            app.mail.send('This is my message body')

            # Overriding configuration defaults
            app.mail.send('My message body'
                to=['john@example.com'],
                from_addr='me@example.com',
                cc=['jane@example.com', 'rita@example.com'],
                subject='This is my subject',
                )

        """
        # shorted config values
        params = self._get_params(**kw)
        msg = "\n" + "=" * 77 + "\n"
        msg += "DUMMY MAIL MESSAGE\n"
        msg += "-" * 77 + "\n\n"
        msg += "To: %s\n" % ', '.join(params['to'])
        msg += "From: %s\n" % params['from_addr']
        msg += "CC: %s\n" % ', '.join(params['cc'])
        msg += "BCC: %s\n" % ', '.join(params['bcc'])

        if params['subject_prefix'] not in [None, '']:
            msg += "Subject: %s %s\n\n---\n\n" % (params['subject_prefix'],
                                                  params['subject'])
        else:
            msg += "Subject: %s\n\n---\n\n" % params['subject']
        msg += body + "\n"

        msg += "\n" + "-" * 77 + "\n"

        print(msg)
        return True


def load(app):
    handler.register(DummyOutputHandler)
    handler.register(DummyMailHandler)
