# -*- coding: utf-8 -*-
import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from conf import BACKUP_ROOT_PROD, SERVER_NAME, SENDER_EMAIL, SMTP_SERVER, EMAILS


class Email(MIMEMultipart):
    backup_root = BACKUP_ROOT_PROD
    title = None

    def __init__(self, backup_root=BACKUP_ROOT_PROD):
        super().__init__("alternative")
        self.backup_root = backup_root
        self.timestamp = datetime.datetime.now().replace(microsecond=0)
        self['Subject'] = "{server} : {title} - {date}".format(
            server=SERVER_NAME,
            title=self.title,
            date=self.timestamp
        )
        self['From'] = SENDER_EMAIL

    def send(self):
        client = smtplib.SMTP(SMTP_SERVER)
        for email in EMAILS:
            self['To'] = email
            client.sendmail(SENDER_EMAIL, email, self.as_string())
        client.close()

    def create_html(self, body):
        """Encapsulate body in valid html with style
        Args:
            body (str)
        Returns:
            html (str)
        """
        css_file = open(os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "mail.css"
        ), "r")
        html = "<html><head><style>" + css_file.read() + "</style></head>"
        html += "<body>" + body + "</body></html>"
        return html

    def attach_all(self, body, plain):
        """
        Args:
            body (str)
            plain (str)
        """
        html = self.create_html(body)
        html = MIMEText(html, 'html')
        plain = MIMEText(plain, 'plain')

        self.attach(plain)
        self.attach(html)
