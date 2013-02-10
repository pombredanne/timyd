import smtplib
import string
import time

from timyd import Action


class MailSender(object):
    def __init__(self, **options):
        self._from_addr = options.get('sender', 'timyd@example.org')
        self._server = None

    def send_mail(self, to, subject, body, **options):
        if isinstance(to, tuple):
            to = list(to)
        elif not isinstance(to, list):
            to = [to]
        data = string.join((
                'From: %s' % self._from_addr,
                'To: %s' % string.join(to, ', '),
                'Subject: %s' % subject,
                '',
                body),
                '\r\n')
        if self._server is None:
            self._server = smtplib.SMTP(options['smtp_host'],
                                       options.get('smtp_port', 25))
        self._server.sendmail(self._from_addr, to, data)

    def quit(self):
        if self._server is not None:
            self._server.quit()
            self._server = None


class MailAlertAction(Action):
    """Sends an alert when a service's status changes.
    """

    _DEFAULT_SUBJECT = '[timyd] [{site}] Service {service} is {short_status}'

    _DEFAULT_BODY = ('Service: {service}\n'
             'Date: {date} {time}\n'
             'Previous status: {old_status}\n'
             'Status: {new_status}\n')

    def __init__(self, recipients, **options):
        self._recipients = recipients
        self._options = options
        self._sender = MailSender(**options)

    def register_status_change(self, site, service, old_status, new_status):
        if old_status is None:
            old_status = "(unknown)"
        infos = {
                'date': time.strftime('%Y-%m-%d'),
                'time': time.strftime('%H:%M:%S'),
                'site': site,
                'service': service,
                'old_status': old_status,
                'new_status': new_status,
                'short_status': new_status and "ok" or "error"}
        subject = self._options.get('subject_format')
        if subject is None:
            subject = self._DEFAULT_SUBJECT.format(**infos)
        elif isinstance(subject, dict):
            subject = subject[new_status]
        body = self._options.get('body_format')
        if body is None:
            body = self._DEFAULT_BODY.format(**infos)
        elif isinstance(body, dict):
            body = body[new_status]
        self._sender.send_mail(
                self._recipients,
                subject,
                body,
                **self._options)

    def end_run(self):
        self._sender.quit()
