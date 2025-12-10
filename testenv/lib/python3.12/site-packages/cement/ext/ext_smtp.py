"""
Cement smtp extension module.
"""

from __future__ import annotations
import os
from datetime import datetime, timezone
import smtplib
from email.header import Header
from email.charset import Charset, BASE64, QP
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders
from email.utils import format_datetime, make_msgid
from typing import Any, Optional, Dict, Union, Tuple, TYPE_CHECKING
from ..core import mail
from ..utils import fs
from ..utils.misc import minimal_logger, is_true

if TYPE_CHECKING:
    from ..core.foundation import App  # pragma: nocover

LOG = minimal_logger(__name__)


class SMTPMailHandler(mail.MailHandler):

    """
    This class implements the :ref:`IMail <cement.core.mail>`
    interface, and is based on the `smtplib
    <http://docs.python.org/dev/library/smtplib.html>`_ standard library.

    """

    class Meta(mail.MailHandler.Meta):

        """Handler meta-data."""

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
            'files': None,
            # define controlling of mail encoding
            'charset': 'utf-8',
            'header_encoding': None,
            'body_encoding': None,
            'date_enforce': True,
            'msgid_enforce': True,
            'msgid_str': None,
            'msgid_domain': None,
        }

    _meta: Meta  # type: ignore

    def _get_params(self, **kw: Any) -> Dict[str, Any]:
        params = dict()

        # some keyword args override configuration defaults
        for item in [
            'to', 'from_addr', 'cc', 'bcc', 'subject', 'subject_prefix', 'files',
            'charset', 'header_encoding', 'body_encoding',
            'date_enforce', 'msgid_enforce', 'msgid_str',
        ]:
            config_item = self.app.config.get(self._meta.config_section, item)
            params[item] = kw.get(item, config_item)

        # others don't
        for item in [
            'ssl', 'tls', 'host', 'port', 'auth', 'username', 'password',
            'timeout', 'msgid_domain'
        ]:
            params[item] = self.app.config.get(self._meta.config_section, item)

        # some are only set by message
        for item in ['date', 'message_id', 'return_path', 'reply_to']:
            value = kw.get(item, None)
            if value is not None and str.strip(f'{value}') != '':
                params[item] = kw.get(item, config_item)

        # take all X-headers as is
        for item in kw.keys():
            if len(item) > 2 and item.startswith(('x-', 'X-', 'x_', 'X_')):
                value = kw.get(item, None)
                if value is not None:
                    params[f'X-{item[2:]}'] = value

        return params

    def send(self, body: Union[str, Tuple[str, str]], **kw: Any) -> bool:
        """
        Send an email message via SMTP.  Keyword arguments override
        configuration defaults (cc, bcc, etc).

        Args:
            body (tuple): The message body to send. Tuple is treated as:
                ``(<text>, <html>)``. If a single string is passed it will be
                converted to ``(<text>)``. At minimum, a text version is
                required.

        Keyword Args:
            to (list): List of recipients (generally email addresses)
            from_addr (str): Address (generally email) of the sender
            cc (list): List of CC Recipients
            bcc (list): List of BCC Recipients
            subject (str): Message subject line
            subject_prefix (str): Prefix for message subject line (useful to
                override if you want to remove/change the default prefix).
            files (list): List of file paths to attach to the message. Can be
                ``[ '/path/to/file.ext', ... ]`` or alternative filename can
                be defined by passing a list of tuples in the form of
                ``[ ('alt-name.ext', '/path/to/file.ext'), ...]``

        Returns:
            bool:``True`` if message is sent successfully, ``False`` otherwise

        Example:

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
            server = smtplib.SMTP_SSL(params['host'],
                                      params['port'],
                                      params['timeout'])
            LOG.debug(f"{self._meta.label} : initiating smtp over ssl")

        else:
            server = smtplib.SMTP(params['host'],  # type: ignore
                                  params['port'],
                                  params['timeout'])
            LOG.debug(f"{self._meta.label} : initiating smtp")

        if self.app.debug is True:
            server.set_debuglevel(9)

        if is_true(params['tls']):
            LOG.debug(f"{self._meta.label} : initiating tls")
            server.starttls()

        if is_true(params['auth']):
            server.login(params['username'], params['password'])

        msg = self._make_message(body, **params)
        res = server.send_message(msg)

        server.quit()

        # FIXME: should deprecate for 3.0 and change in 3.2
        # For smtplib this would be "senderrs" (dict), but for backward compat
        # we need to return bool
        # https://github.com/python/cpython/blob/3.13/Lib/smtplib.py#L899
        self.app.log.error(f"SMTPHandler Errors: {res}")
        if len(res) > 0:
            # this will be difficult to test with Mailpit as it accepts everything... no cover
            return False  # pragma: nocover
        else:
            return True

    def _header(self, value: Optional[str] = None, _charset: Optional[Charset] = None,
                **params: Dict[str, Any]) -> Header:
        header = Header(value, charset=_charset) if params['header_encoding'] else value
        return header  # type: ignore

    def _make_message(self, body: Union[str, Tuple[str, str]], **params: Dict[str, Any]) \
                      -> MIMEMultipart:
        # use encoding for header parts
        cs_header = Charset(params['charset'])  # type: ignore
        if params['header_encoding'] == 'base64':
            cs_header.header_encoding = BASE64
        elif params['header_encoding'] == 'qp' or params['body_encoding'] == 'quoted-printable':
            cs_header.header_encoding = QP

        # use encoding for body parts
        cs_body = Charset(params['charset'])  # type: ignore
        if params['body_encoding'] == 'base64':
            cs_body.body_encoding = BASE64
        elif params['body_encoding'] == 'qp' or params['body_encoding'] == 'quoted-printable':
            cs_body.body_encoding = QP

        # setup body parts
        partText = None
        partHtml = None

        if type(body) not in [str, tuple, dict]:
            error_msg = "Message body must be string, " \
                        "tuple ('<text>', '<html>') or " \
                        "dict {'text': '<text>', 'html': '<html>'}"
            raise TypeError(error_msg)

        if isinstance(body, str):
            partText = MIMEText(body, 'plain', _charset=cs_body)  # type: ignore
        elif isinstance(body, tuple):
            # handle plain text
            if len(body) >= 1 and body[0] and str.strip(body[0]) != '':
                partText = MIMEText(str.strip(body[0]),
                                    'plain',
                                    _charset=cs_body)  # type: ignore
            # handle html
            if len(body) >= 2 and body[1] and str.strip(body[1]) != '':
                partHtml = MIMEText(str.strip(body[1]),
                                    'html',
                                    _charset=cs_body)  # type: ignore
        elif isinstance(body, dict):
            # handle plain text
            if 'text' in body and str.strip(body['text']) != '':
                partText = MIMEText(str.strip(body['text']),
                                              'plain',
                                              _charset=cs_body)
            # handle html
            if 'html' in body and str.strip(body['html']) != '':
                partHtml = MIMEText(str.strip(body['html']), 'html', _charset=cs_body)

        # To define the correct message content-type
        # we need to indentify the content of this mail.
        # If only "text" exists => text/plain, if only
        # "html" exists => text/html, if "text" and
        # "html" exists => multipart/alternative. In
        # any case that files exists => multipart/mixed.
        # Set message charset and encoding based on parts
        if params['files']:
            msg = MIMEMultipart('mixed')
            msg.set_charset(params['charset'])  # type: ignore
        elif partText and partHtml:
            msg = MIMEMultipart('alternative')
            msg.set_charset(params['charset'])  # type: ignore
        elif partHtml:
            msg = MIMEBase('text', 'html')  # type: ignore
            msg.set_charset(cs_body)
        else:
            msg = MIMEBase('text', 'plain')  # type: ignore
            msg.set_charset(cs_body)

        # create message
        msg['From'] = params['from_addr']  # type: ignore
        msg['To'] = ', '.join(params['to'])
        if params['cc']:
            msg['Cc'] = ', '.join(params['cc'])
        if params['bcc']:
            msg['Bcc'] = ', '.join(params['bcc'])
        if params['subject_prefix'] not in [None, '']:
            msg['Subject'] = self._header(f"{params['subject_prefix']} {params['subject']}",
                                          _charset=cs_header, **params)  # type: ignore
        else:
            msg['Subject'] = self._header(params['subject'],  # type: ignore
                                          _charset=cs_header,
                                          **params)

        # check for date
        if is_true(params['date_enforce']) and not params.get('date', None):
            params['date'] = format_datetime(datetime.now(timezone.utc))  # type: ignore
        # check for message-id
        if is_true(params['msgid_enforce']) and not params.get('message_id', None):
            params['message_id'] = make_msgid(params['msgid_str'],  # type: ignore
                                              params['msgid_domain'])  # type: ignore

        # check for message headers
        if params.get('date', None):
            msg['Date'] = params['date']  # type: ignore
        if params.get('message_id', None):
            msg['Message-Id'] = params['message_id']  # type: ignore
        if params.get('return_path', None):
            msg['Return-Path'] = params['return_path']  # type: ignore
        if params.get('reply_to', None):
            msg['Reply-To'] = params['reply_to']  # type: ignore

        # check for X-headers
        for item in params.keys():
            if item.startswith('X-'):
                msg.add_header(item.title(),
                               self._header(f'{params[item]}',  # type: ignore
                                            _charset=cs_header, **params))

        # append the body parts
        if params['files']:
            # multipart/mixed
            if partHtml:
                # when html exists, create always a related part to include
                # the body alternatives and eventually files as related
                # attachments (e.g. images).
                rel = MIMEMultipart('related')
                # create an alternative part to include bodies for text and html
                alt = MIMEMultipart('alternative')
                # body text and body html
                if partText:
                    alt.attach(partText)
                alt.attach(partHtml)
                rel.attach(alt)
                msg.attach(rel)
            else:
                # only body text or no body
                if partText:
                    msg.attach(partText)
                else:
                    # no body no files = empty message = just headers
                    pass  # pragma: no cover
        else:
            # multipart/alternative
            if partText and partHtml:
                # plain/text and plain/html
                msg.attach(partText)
                msg.attach(partHtml)
            else:
                # plain/text or plain/html only so just append payload
                if partText:
                    msg.set_payload(partText.get_payload(), charset=cs_body)
                elif partHtml:
                    msg.set_payload(partHtml.get_payload(), charset=cs_body)
                else:
                    # no body no files = empty message = just headers
                    pass  # pragma: no cover

        # attach files
        if params['files']:
            for in_path in params['files']:
                # support for alternative file name if its tuple or dict
                # like [
                #       'path/simple.ext',
                #       ('altname.ext', 'path/filename.ext'),
                #       ('altname.ext', 'path/filename.ext', 'content_id'),
                #       {'name': 'altname', 'path': 'path/filename.ext', cid: 'cidname'},
                #      ]
                if isinstance(in_path, tuple):
                    altname = os.path.basename(in_path[0])
                    path = in_path[1]
                    cid = in_path[2] if len(in_path) >= 3 else None
                elif isinstance(in_path, dict):
                    altname = os.path.basename(in_path.get('name', None))
                    path = in_path.get('path')
                    cid = in_path.get('cid', None)
                else:
                    altname = None
                    path = in_path
                    cid = None

                path = fs.abspath(path)
                if not altname:
                    altname = os.path.basename(path)

                # add attachment payload from file
                with open(path, 'rb') as file:
                    # check for embedded image or regular attachments
                    if cid:
                        part = MIMEImage(file.read())
                    else:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())

                # encoder
                encoders.encode_base64(part)

                # embedded inline or attachment
                if cid:
                    part.add_header(
                        'Content-Disposition',
                        f'inline; filename={altname}',
                    )
                    part.add_header('Content-ID', f'<{cid}>')
                    msg.attach(part)
                else:
                    # altname header
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={altname}',
                    )
                    msg.attach(part)

        return msg


def load(app: App) -> None:
    app.handler.register(SMTPMailHandler)
