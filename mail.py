# -*- coding: utf-8 -*-
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart

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
        client.quit()