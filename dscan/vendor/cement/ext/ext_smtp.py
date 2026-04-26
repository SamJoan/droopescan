
import smtplib
from ..core import handler, mail
from ..utils.misc import minimal_logger, is_true

LOG = minimal_logger(__name__)


class SMTPMailHandler(mail.CementMailHandler):

    """
    This class implements the :ref:`IMail <cement.core.mail>`
    interface, and is based on the `smtplib
    <http://docs.python.org/dev/library/smtplib.html>`_ standard library.

    **Usage**

    .. code-block:: python

        class MyApp(CementApp):
            class Meta:
                label = 'myapp'
                mail_handler = 'smtp'

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
     * **host** - The SMTP host server
     * **port** - The SMTP host server port
     * **timeout** - The timeout in seconds before terminating a connection
     * **ssl** - Whether to initiate SSL or not
     * **tls** - Whether to use TLS or not (requires SSL)
     * **auth** - Whether or not to initiate SMTP authentication
     * **username** - SMTP authentication username
     * **password** - SMTP authentication password

    You can add these to any application configuration file under a
    ``[mail.smtp]`` section, for example:

    **~/.myapp.conf**

    .. code-block:: text

        [myapp]

        # set the mail handler to use
        mail_handler = smtp


        [mail.smtp]

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

        # smtp host server
        host = localhost

        # smtp host port
        port = 465

        # timeout in seconds
        timeout = 30

        # whether or not to establish an ssl connection
        ssl = 1

        # whether or not to use start tls
        tls = 1

        # whether or not to initiate smtp auth
        auth = 1

        # smtp auth username
        username = john.doe

        # smtp auth password
        password = oober_secure_password

    """

    class Meta:
        #: Unique identifier for this handler
        label = 'smtp'

        #: Configuration default values
        config_defaults = {
            'to': [],
            'from_addr': 'noreply@localhost',
            'cc': [],
            'bcc': [],
            'subject': None,
            'subject_prefix': None,
            'host': 'localhost',
            'port': '25',
            'timeout': 30,
            'ssl': False,
            'tls': False,
            'auth': False,
            'username': None,
            'password': None,
        }

    def _get_params(self, **kw):
        params = dict()

        # some keyword args override configuration defaults
        for item in ['to', 'from_addr', 'cc', 'bcc', 'subject']:
            config_item = self.app.config.get(self._meta.config_section, item)
            params[item] = kw.get(item, config_item)

        # others don't
        other_params = ['ssl', 'tls', 'host', 'port', 'auth', 'username',
                        'password', 'timeout']
        for item in other_params:
            params[item] = self.app.config.get(self._meta.config_section,
                                               item)

        # also grab the subject_prefix
        params['subject_prefix'] = self.app.config.get(
            self._meta.config_section,
            'subject_prefix'
        )

        return params

    def send(self, body, **kw):
        """
        Send an email message via SMTP.  Keyword arguments override
        configuration defaults (cc, bcc, etc).

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
                from_addr='me@example.com',
                to=['john@example.com'],
                cc=['jane@example.com', 'rita@example.com'],
                subject='This is my subject',
                )

        """
        params = self._get_params(**kw)

        if is_true(params['ssl']):
            server = smtplib.SMTP_SSL(params['host'], params['port'],
                                      params['timeout'])
            LOG.debug("%s : initiating ssl" % self._meta.label)
            if is_true(params['tls']):
                LOG.debug("%s : initiating tls" % self._meta.label)
                server.starttls()

        else:
            server = smtplib.SMTP(params['host'], params['port'],
                                  params['timeout'])

        if is_true(params['auth']):
            server.login(params['username'], params['password'])

        if self.app.debug is True:
            server.set_debuglevel(9)

        msg = ""
        msg += "From: %s\r\nTo: %s\r\n" % (params['from_addr'],
                                           ', '.join(params['to']))
        msg += "Cc: %s\r\n" % ', '.join(params['cc'])
        msg += "Bcc: %s\r\n" % ', '.join(params['bcc'])
        if params['subject_prefix'] not in [None, '']:
            msg += "Subject: %s %s\r\n\r\n" % (params['subject_prefix'],
                                               params['subject'])
        else:
            msg += "Subject: %s\r\n\r\n" % params['subject']
        msg += body + "\n"

        server.sendmail(params['from_addr'],
                        params['to'] + params['cc'] + params['bcc'],
                        msg)
        server.quit()


def load(app):
    handler.register(SMTPMailHandler)
