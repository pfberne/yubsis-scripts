# Livrable mission JCS - Pierre-François Berne

## 0. Configuration des scripts

Les scripts sont disponible sur GitHub (https://github.com/martinlehoux/JCS1-odoo-scripts). On peut les déployer n'importe où sur chaque serveur, mais usuellement dans `/opt/JCS1-odoo-scripts` :

- `cd /opt`
- `git clone https://github.com/pfberne/JCS1-odoo-scripts`

C'est ensuite les crontab qui permettent d'activer les scripts un par un.

Il faut ensuite copier le fichier `/opt/JCS1-odoo-scripts/conf.example.py` vers `/opt/JCS1-odoo-scripts/conf.py` puis modifier ce nouveau fichier  sur chaque serveur.

```python
# -*- coding: utf-8 -*-
SERVER_NAME = "localhost" # Le nom du serveur pour les mails
EMAILS = ['martin@lehoux.net'] # Les emails à qui envoyer les rapports
SENDER_EMAIL = "sender@mail.com" # L'email from du seveur, pas besoin de modifier
SMTP_SERVER = "mail.ikoula.fr" # Le serveur mail, pas besoin de modifier
BACKUP_ROOT_PROD = '/var/backups/odoo' # L'endroit où sont stockés les backups, pas besoin de modifier en temps normal
BACKUP_ROOT_TEST = '/var/backups/odoo/test' # Un endroit où le script peut effectuer de fausses simulations pour tester
DISK_PARTITIONS = ['/'] # Les différentes partitions du serveur, normalement pas besoin de changer
```



## 1. Sauvegardes

**Tests : Succès**

### 1.1. Configuration d'Odoo

Avant toute chose, il faut permettre au serveur Odoo d'accéder au serveur de stockage (exemple: `179.0.196.127`). Pour cela, on se connecte en shell avec le compte `odoo` et on génère une clé RSA. 

> La clé n'a besoin d'être générée qu'une seule fois par serveur. On peut vérifier si une clé existe avec `ssh-add` (`Could not open a connection to your authentication agent.` si il n'y a pas de clé).

- `su - odoo -s /bin/bash`
- `ssh-keygen`
- On valide toute les étapes. Ne surtout pas mettre de mot de passe.
- Les clés se trouvent dans `/opt/odoo/.ssh/` :
  - `/opt/odoo/.ssh/id_rsa` Clé privé à ne jamais partager
  - `/opt/odoo/.ssh/id_rsa.pub` Clé publique à partager
- `cat /opt/odoo/.ssh/id_rsa.pub` affiche la clé, la copier
- On ajoute cette clé au fichier d'autorisation du serveur de stockage :
- `su backup`
- `cd ~`
- `backup@JCS1-odoo-Stockage: nano .ssh/authorized_keys`
- Chaque ligne du fichier correspond à une clé d'un autre serveur qui peut se connecter en SSH à ce compte. Ajouter sur une nouvelle ligne le contenu de la clé publique du serveur Odoo.
- On peut vérifier le succès avec la commande suivante depuis le serveur Odoo : `odoo@JCS1-odoo: ssh backup@179.0.196.127`

On utilise pour effectuer les sauvegardes un module Odoo : **Database Auto-Backup** qu'il faut installer pour chaque base de données de chqaue serveur.

Pour accéder à la configuration, on va dans **Settings** avec un compte administrateur, puis on utilise **Activate the developer mode** en bas à droite.

On retourne ensuite dans **Settings**, puis **Technical > Database Structure > Automated backups** dans la barre supérieure.

**Configuration :**

- **Folder :** /var/backups/odoo/serveur/database/daily
- **Method :** Remote SFTP server
- **Backup format :** zip (include filestore)
- **SFTP Server :** 179.0.196.127
- **SFTP Port :** 22
- **Username in the SFTP Server :** backup
- **SFTP Password Private key location :** /opt/odoo/.ssh/id_rsa

On peut vérifier la connection avec le bouton en dessous.

### 1.2. Configuration du serveur de sauvegarde

Le script de rotation des sauvegardes se trouve dans `/opt/JCS1-odoo-scripts/file_rotation.py`. Une entrée crontab pour l'utilisateur `backup` est déjà configurée : `0 4 * * * python3 /opt/JCS1-odoo-scripts/file_rotation.py`. La seule partie du script à modifier est la configuration :

```python
## CONFIG
DEFAULT_RETENTION_POLICY = RetentionPolicy(weeks=4, months=12)
RETENTION_POLICIES = {}
```

Si on veut une autre politique que celle par défaut (4 semaines et 12 mois), il faut rajouter une entrée dans `RETENTION_POLICIES` :

```python
RETENTION_POLICIES = {
  '<serveur>/<database>': RetentionPolicy(weeks=12, months=24)
}
```

On peut tester le bon fonctionnement du script avec `python3 -m unittest /opt/file-rotation.py`.

Les sauvegardes se trouvent dans `/var/backups/odoo` avec l'architecture suivante :

```
<serveur>
    <database>
        daily # backups gérés par Odoo Automated backups
            2020_03_01_03_00_01.dump.zip
            ...
        weekly # Backups hebdo créés par le script
           	...
        monthly # Backups mensuels créés par le script
            ...
```

## 2. Sécurité

### 2.1. Unattended upgrades

**Tests : Succès**

C'est l'outil de mise à jour automatique des paquets APT. Les mises à jour sont sûres, c'est-à-dire qu'elles n'introduisent pas de cassures dans l'utilisation des logiciels. Pour les mises à jour de plus grande ampleur, il faut toujours les faire à la main.

- `apt install unattended-upgrades`
- `/etc/apt/apt.conf.d/50unattended-upgrades` est le fichier de configuration des mises à jour. Le modèle fonctionnel est fourni et à copier sur le serveur.
- `/etc/apt/apt.conf.d/20auto-upgrades ` est le fichier de planification des mises à jour.
- `/var/log/unattended-upgrades/unattended-upgrades.log` contient les historiques des mises à jour effectuées :

```
2020-04-05 06:43:18,785 INFO Initial blacklisted packages: 
2020-04-05 06:43:18,786 INFO Initial whitelisted packages: 
2020-04-05 06:43:18,786 INFO Starting unattended upgrades script
2020-04-05 06:43:18,786 INFO Allowed origins are: ['origin=Debian,codename=stretch,label=Debian-Security']
2020-04-05 06:44:53,379 INFO No packages found that can be upgraded unattended and no pending auto-removals
```

On pourra remarquer que tous les paquets ne sont pas mis à jour, seulement les essentiels.

### 2.2. Fail2ban

**Tests: Succès**

- `apt install fail2ban`
- `/etc/fail2ban/jail.conf` est le fichier de configuration système, **à ne pas modifier**
- `/etc/fail2ban/jail.local` est le fichier de configuration modifiable. Le modèle fonctionnel est fourni et à copier sur le serveur.

## 3. Monitoring

### 3.1. Divers

**Tests: En cours**

Le script `/opt/JCS1-odoo-scripts/monitoring.py` permet d'effectuer les vérifications communes à tous les serveurs. Le crontab habituel est `0 18 * * 5 python3 /opt/JCS1-odoo-scripts/backup-check.py` pour un résumé chaque vendredi à 18h.

On peut tester le bon fonctionnement du script avec `python3 -m unittest /opt/JCS1-odoo-scripts/monitoring.py`.

**Modules :**

- **Espace disque :** Vérifie les espaces disques des partitions dans `DISK_PARTITIONS`
- **Mises à jour APT :** Vérifie les mises à jour en attente
- **Taille des fichiers logs :** Liste les fichiers logs groupés par fonction

### 3.2. État des sauvegardes

**Tests: Succès**

Le script `/opt/JCS1-odoo-scripts/backup_check.py` permet de vérifier l'état des sauvegardes. Il est à utiliser conjointement avec `/opt/JCS1-odoo-scripts/file_rotation.py`. Une entrée crontab pour l'utilisateur `backup` est à créer : `0 18 * * 5 python3 /opt/JCS1-odoo-scripts/backup-check.py`. Cette entrée correspond à un résumé chaque vendredi à 18h. Pour choisir une autre fréquence, se référer à https://crontab.guru.

On peut tester le bon fonctionnement du script avec `python3 -m unittest /opt/JCS1-odoo-scripts/backup_check.py`.

Le script envoie un mail qui donne pour chaque base la dernière sauvegarde journalière, hebdomadaire ainsi que mensuelle, et indique une erreur si elle est trop ancienne.

## 4. Liste des changements
- **v1.0 :** Version initiale
