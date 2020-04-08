import shutil, os
import unittest
import pathlib
import datetime

from conf import BACKUP_ROOT_PROD, BACKUP_ROOT_TEST


class RetentionPolicy:
    weeks = None
    months = None

    def __init__(self, weeks, months):
        assert isinstance(weeks, int)
        self.weeks = weeks
        assert isinstance(months, int)
        self.months = months


## CONFIG
DEFAULT_RETENTION_POLICY = RetentionPolicy(weeks=4, months=12)
RETENTION_POLICIES = {}
## For each database, add a policy, otherwise the default policy will be used.

def get_datetime_from_filename(filename):
    return datetime.datetime.strptime(filename, "%Y_%m_%d_%H_%M_%S.dump.zip")

def get_filename_from_datetime(dt):
    return dt.strftime("%Y_%m_%d_%H_%M_%S.dump.zip")

class Database:
    backup_root = BACKUP_ROOT_PROD
    ip = None
    name = None

    def __init__(self, ip, name, backup_root=BACKUP_ROOT_PROD):
        self.backup_root = backup_root
        assert isinstance(ip, str)
        self.ip = ip
        assert isinstance(name, str)
        self.name = name

        os.makedirs(self.daily_path, exist_ok=True)
        os.makedirs(self.weekly_path, exist_ok=True)
        os.makedirs(self.monthly_path, exist_ok=True)

    @property
    def path(self):
        return os.path.join(self.backup_root, self.ip, self.name)

    @property
    def daily_path(self):
        return os.path.join(self.path, 'daily')

    @property
    def weekly_path(self):
        return os.path.join(self.path, 'weekly')

    @property
    def monthly_path(self):
        return os.path.join(self.path, 'monthly')

    @property
    def retention_policy(self):
        return RETENTION_POLICIES.get(self.ip + "/" + self.name) or DEFAULT_RETENTION_POLICY

    @property
    def last_weekly_datetime(self):
        filenames = os.listdir(self.weekly_path)
        if not filenames:
            return None
        return max([get_datetime_from_filename(filename) for filename in filenames])

    @property
    def last_monthly_datetime(self):
        filenames = os.listdir(self.monthly_path)
        if not filenames:
            return None
        return max([get_datetime_from_filename(filename) for filename in filenames])

    @property
    def last_daily_datetime(self):
        filenames = os.listdir(self.daily_path)
        if not filenames:
            return None
        return max([get_datetime_from_filename(filename) for filename in filenames])

    def first_daily_datetime(self, minimum=None):
        filenames = os.listdir(self.daily_path)
        if not filenames:
            return None
        datetimes = [get_datetime_from_filename(filename) for filename in filenames]
        if minimum:
            if isinstance(minimum, datetime.datetime):
                minimum = minimum.date()
            assert isinstance(minimum, datetime.date)
            datetimes = list(filter(lambda dt: dt.date() >= minimum, datetimes))
        return min(datetimes) if datetimes else None

    def rotate(self):
        # Monthly
        latest_monthly = self.last_monthly_datetime
        if latest_monthly:
            latest_monthly = max(latest_monthly, datetime.datetime.now() - datetime.timedelta(days=30 * self.retention_policy.months))
        while not latest_monthly or latest_monthly < datetime.datetime.now() - datetime.timedelta(days=30):
            minimum = latest_monthly + datetime.timedelta(days=30) if latest_monthly else None
            to_move = self.first_daily_datetime(minimum=minimum)
            if not to_move:
                break
            shutil.copy(
                os.path.join(self.daily_path, get_filename_from_datetime(to_move)),
                os.path.join(self.monthly_path, get_filename_from_datetime(to_move)),
            )
            latest_monthly = to_move
        # Weekly
        latest_weekly = self.last_weekly_datetime
        if latest_weekly:
            latest_weekly = max(latest_weekly, datetime.datetime.now() - datetime.timedelta(days=7 * self.retention_policy.weeks))
        else:
            latest_weekly = datetime.datetime.now() - datetime.timedelta(days=7 * self.retention_policy.weeks)
        while not latest_weekly or latest_weekly < datetime.datetime.now() - datetime.timedelta(days=7):
            minimum = latest_weekly + datetime.timedelta(days=7) if latest_weekly else None
            to_move = self.first_daily_datetime(minimum=minimum)
            if not to_move:
                break
            shutil.copy(
                os.path.join(self.daily_path, get_filename_from_datetime(to_move)),
                os.path.join(self.weekly_path, get_filename_from_datetime(to_move)),
            )
            latest_weekly = to_move

    def purge(self):
        weekly_files = os.listdir(self.weekly_path)
        if weekly_files:
            datetimes = list(sorted([get_datetime_from_filename(filename) for filename in weekly_files]))
            for dt in datetimes[:-self.retention_policy.weeks]:
                os.remove(os.path.join(self.weekly_path, get_filename_from_datetime(dt)))
        monthly_files = os.listdir(self.monthly_path)
        if monthly_files:
            datetimes = list(sorted([get_datetime_from_filename(filename) for filename in monthly_files]))
            for dt in datetimes[:-self.retention_policy.months]:
                os.remove(os.path.join(self.monthly_path, get_filename_from_datetime(dt)))
            

if __name__ == "__main__":
    for server in os.listdir(BACKUP_ROOT_PROD):
        for name in os.listdir(os.path.join(BACKUP_ROOT_PROD, server)):
            database = Database(server, name)
            database.rotate()
            database.purge()


class FileRotationTest(unittest.TestCase):
    def setUp(self):
        self.database = Database('localhost', 'Database1', BACKUP_ROOT_TEST)
        RETENTION_POLICIES[self.database.path] = DEFAULT_RETENTION_POLICY
        self.now = datetime.datetime.now().replace(microsecond=0)
        # Generate 365 days of backup
        for days in range(365):
            open(os.path.join(
                BACKUP_ROOT_TEST,
                self.database.ip,
                self.database.name,
                'daily',
                get_filename_from_datetime(self.now - datetime.timedelta(days=days))
            ), 'wb').close()
        

    def tearDown(self):
        shutil.rmtree(BACKUP_ROOT_TEST, ignore_errors=True)
        
    def test_database_class(self):
        with self.assertRaises(AssertionError):
            Database('1.1.1.1', 1, BACKUP_ROOT_TEST)

        self.assertEqual(
            self.database.path,
            os.path.join(BACKUP_ROOT_TEST, 'localhost', 'Database1')
        )

        self.assertEqual(get_datetime_from_filename(get_filename_from_datetime(self.now)), self.now)

        self.assertEqual(self.database.retention_policy.weeks, 4)

        for days in range(10):
            open(os.path.join(
                BACKUP_ROOT_TEST,
                self.database.ip,
                self.database.name,
                'weekly',
                get_filename_from_datetime(self.now - datetime.timedelta(days=days))
            ), 'wb').close()
        self.assertEqual(self.database.last_weekly_datetime, self.now)
        shutil.rmtree(BACKUP_ROOT_TEST)

    def test_rotate_backups(self):
        self.assertEqual(len(os.listdir(self.database.daily_path)), 365)
        self.assertEqual(len(os.listdir(self.database.weekly_path)), 0)
        self.assertEqual(len(os.listdir(self.database.monthly_path)), 0)

        self.database.rotate()

        self.assertEqual(len(os.listdir(self.database.monthly_path)), 13)
        self.assertEqual(len(os.listdir(self.database.weekly_path)), 4)

    def test_purge_backups(self):
        for weeks in range(20):
            open(os.path.join(
                BACKUP_ROOT_TEST,
                self.database.ip,
                self.database.name,
                'weekly',
                get_filename_from_datetime(self.now - datetime.timedelta(weeks=weeks))
            ), 'wb').close()
        self.assertEqual(len(os.listdir(self.database.weekly_path)), 20)

        self.database.purge()

        self.assertEqual(len(os.listdir(self.database.weekly_path)), self.database.retention_policy.weeks)
