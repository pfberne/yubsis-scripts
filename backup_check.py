# -*- coding: utf-8 -*-
import smtplib
import unittest
import shutil
import datetime
import os

from conf import BACKUP_ROOT_PROD, BACKUP_ROOT_TEST, SERVER_NAME, SENDER_EMAIL, EMAILS
from mail import Email
from file_rotation import Database, get_filename_from_datetime


class BCEmail(Email):
    backup_root = BACKUP_ROOT_PROD
    title = "Rapport de sauvegardes"

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
            database.server,
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
    message = BCEmail()
    
    html, plain = message.get_summary()
    message.attach_all(html, plain)

    message.send()

class BackupCheckTest(unittest.TestCase):
    def setUp(self):
        self.email = BCEmail(BACKUP_ROOT_TEST)
        self.database = Database('localhost', 'Database2', BACKUP_ROOT_TEST)
        self.now = datetime.datetime.now().replace(microsecond=0)

    def tearDown(self):
        shutil.rmtree(BACKUP_ROOT_TEST, ignore_errors=True)

    def test_email(self):
        self.assertEqual(self.email['Subject'], "{} : Rapport de sauvegardes - {}".format(SERVER_NAME, self.now))

    def _generate_data(self, database, freq, dt):
        open(os.path.join(
            BACKUP_ROOT_TEST,
            database.server,
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
