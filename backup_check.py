import smtplib
import unittest
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import os

from conf import BACKUP_ROOT_PROD, BACKUP_ROOT_TEST, SERVER_NAME, SENDER_EMAIL, EMAILS
from file_rotation import Database, get_filename_from_datetime


class Email(MIMEMultipart):
    backup_root = BACKUP_ROOT_PROD

    def __init__(self, backup_root=BACKUP_ROOT_PROD):
        super().__init__("alternative")
        self.timestamp = datetime.datetime.now().replace(microsecond=0)
        self['Subject'] = "{server} : Rapport de sauvegardes - {date}".format(
            server=SERVER_NAME,
            date=self.timestamp
        )
        self['From'] = SENDER_EMAIL

    def get_database_state(self, database):
        now = datetime.datetime.now()
        if not database.last_daily_datetime:
            return "Journalière manquante"
        if now - database.last_daily_datetime > datetime.timedelta(days=0 + 2):
            return "Journalière : il y a {} jours".format((now - database.last_daily_datetime).days)
        if not database.last_weekly_datetime:
            return "Hebdomadaire manquante"
        if not database.last_monthly_datetime:
            return "Mensuelle manquante"
        if now - database.last_weekly_datetime > datetime.timedelta(days=7 + 2):
            return "Hebdomadaire : il y a {} jours".format((now - database.last_weekly_datetime).days)
        if now - database.last_monthly_datetime > datetime.timedelta(days=30 + 2):
            return "Hebdomadaire : il y a {} jours".format((now - database.last_monthly_datetime).days)
        return "OK"

    def get_database_summary(self, database):
        """
        Args:
            database (Database)
        Returns:
            html (str)
            plain (str)
        """
        items = [
            database.ip,
            database.name,
            database.last_daily_datetime or "inexistante",
            database.last_weekly_datetime or "inexistante",
            database.last_monthly_datetime or "inexistante",
            self.get_database_state(database)
        ]
        line = "".join(["<td>%s</td>" % str(item) for item in items])
        html = "<tr>" + line + "</tr>"
        plain = "| ".join(["{:<30}".format(str(item)) for item in items]) + "\n"
        return html, plain

    def get_summary(self):
        """
        Returns:
            html (str)
            plain (str)
        """
        headers = [
            "Serveur",
            "Base",
            "Journalière",
            "Hebdomadaire",
            "Mensuelle",
            "Etat"
        ]
        headline = "".join(["<th>%s</th>" % header for header in headers])
        html =  "<h1>Rapport de sauvegardes</h1><table><thead><tr>" + headline + "</tr></thead><tbody>"
        plain = "| ".join(["{:<30}".format(header) for header in headers]) + "\n"
        plain += "-" * (len(headers) * 32 - 2) + "\n"
        for server in os.listdir(BACKUP_ROOT_PROD):
            for name in os.listdir(os.path.join(BACKUP_ROOT_PROD, server)):
                database = Database(server, name)
                db_html, db_plain = self.get_database_summary(database)
                html += db_html
                plain += db_plain
        html += "</tbody></table>"
        return html, plain


if __name__ == "__main__":
    # client = smtplib.SMTP(SMTP_SERVER)
    message = Email()
    
    html, plain = message.get_summary()
    html = MIMEText(html, 'html')
    plain = MIMEText(plain, 'plain')

    message.attach(html)
    message.attach(plain)

    for email in EMAILS:
        message['To'] = email
        with open('email.eml', 'w') as f:
            f.write(str(message))
        # client.sendmail(SENDER_EMAIL, email, message.as_string())

    # client.quit()

class BackupCheckTest(unittest.TestCase):
    def setUp(self):
        self.email = Email(BACKUP_ROOT_TEST)
        self.database = Database('localhost', 'Database2', BACKUP_ROOT_TEST)
        self.now = datetime.datetime.now().replace(microsecond=0)

    def tearDown(self):
        shutil.rmtree(BACKUP_ROOT_TEST, ignore_errors=True)

    def _generate_data(self, database, freq, dt):
        open(os.path.join(
            BACKUP_ROOT_TEST,
            database.ip,
            database.name,
            freq,
            get_filename_from_datetime(dt)
        ), 'wb').close()

    def test_get_database_state(self):
        self.assertEqual(self.email.get_database_state(self.database), "Journalière manquante")
        
        self._generate_data(self.database, 'daily', self.now - datetime.timedelta(days=2))
        self.assertEqual(self.email.get_database_state(self.database), "Journalière : il y a 2 jours")

        self._generate_data(self.database, 'daily', self.now)
        self.assertEqual(self.email.get_database_state(self.database), "Hebdomadaire manquante")

        self.database.rotate()
        self.assertEqual(self.email.get_database_state(self.database), "OK")
