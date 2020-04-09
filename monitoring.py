# -*- coding: utf-8 -*-
import shutil
import unittest
import os
try:
    import apt
except ImportError:
    apt = None

from mail import Email
from conf import BACKUP_ROOT_PROD, DISK_PARTITIONS

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

class Module:
    title = None
    headers = None

    @classmethod
    def make_table(cls, data):
        """
        Args:
            data (list(list(str))) Each line must be the same len as headers
        Returns:
            html (str)
            plain (str)
        """
        html = "<h1>{}</h1>".format(cls.title)
        plain = cls.title + '\n' + '='*len(cls.title) + '\n'
        html += "<table><thead><tr>"
        for header in cls.headers:
            html += "<th>{}</th>".format(header)
            plain += header + ", "
        html += "</tr></thead><tbody>"
        plain += "\n"
        for line in data:
            assert len(line) == len(cls.headers)
            html += "<tr>"
            for item in line:
                html += "<td>{}</td>".format(item)
                plain += str(item) + ", "
            html += "</tr>"
            plain += "\n"
        html += "</tbody></table>"
        plain += "\n"
        return html, plain

    @staticmethod
    def get_data():
        raise NotImplementedError

class DiskModule(Module):
    title = 'Espace disque'
    headers = ['Partition', 'Used', 'Total', 'Percent']

    @staticmethod
    def get_data():
        data = []
        used = 0
        for part in DISK_PARTITIONS:
            disk_usage = shutil.disk_usage(part)
            used += disk_usage.used
            data.append([
                part,
                sizeof_fmt(disk_usage.used),
                '',
                "{:.2%}".format(disk_usage.used / disk_usage.total)
            ])
        data.append([
            'TOTAL',
            sizeof_fmt(used),
            sizeof_fmt(disk_usage.total),
            "{:.2%}".format(used / disk_usage.total)
        ])
        return data

class AptModule(Module):
    title = 'Mises à jour'
    headers = ['Nom', 'Installé', 'Disponible']

    @staticmethod
    def get_data():
        data = []
        cache = apt.Cache()
        cache.update()
        for pkg in cache:
            if pkg.is_upgradable:
                data.append([pkg.name, pkg.installed, pkg.candidate])
        return data


MODULES = Module.__subclasses__()


class MEmail(Email):
    backup_root = BACKUP_ROOT_PROD
    title = "Rapport de monitoring"


if __name__ == "__main__":
    message = MEmail()
    html, plain = "", ""
    for module in MODULES:
        _html, _plain = module.make_table(module.get_data())
        html += _html
        plain += _plain
    message.send()
    print(plain)
