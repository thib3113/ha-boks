# Comment récupérer votre Clef de Configuration (Configuration Key)

Pour débloquer les fonctionnalités avancées de l'intégration Boks (notamment la **gestion des colis** et la **création de codes**), vous avez besoin de la **Configuration Key**.

> **Note :** Cette clef n'est **PAS** nécessaire pour l'utilisation basique (Ouverture de la porte, lecture des logs, niveau de batterie). Le Code Permanent (PIN) suffit pour cela.

## Qu'est-ce que la Configuration Key ?

C'est une chaîne de 8 caractères hexadécimaux (ex: `A1B2C3D4`).
Techniquement, il s'agit des **8 derniers caractères** de la **Master Key** (une clef de 64 caractères).

> **A propos de la Master Key :**
> La Master Key complète (64 caractères) ne peut être obtenue que lors de l'initialisation de la Boks (premier appairage) ou lors d'une procédure de "re-génération" des codes (qui nécessite elle-même la Config Key précédente).
>
> Cependant, son intérêt est aujourd'hui très limité pour Home Assistant, car la **Configuration Key** suffit pour activer toutes les fonctionnalités avancées (y compris la génération de codes via l'intégration).

## Méthode 1 : Via le script Cloud (Recommandé)

Un script Python est fourni dans le dossier `scripts/` de cette intégration. Il se connecte à votre compte Boks (via l'API cloud) pour récupérer vos appareils et leurs clefs.

**⚠️ Note sur le blocage de l'application :**
Cette méthode utilise les mêmes serveurs que l'application officielle. 
*   Si votre compte est bloqué dans l'application (en attente de migration), le script ne pourra **pas** récupérer la clef (elle apparaîtra vide).
*   Cette méthode ne fonctionne donc que si votre compte a été migré.

**Avantage :** Pas besoin d'accès physique à la Boks, ni d'Android, ni de câbles. Fonctionne avec votre email et mot de passe Boks.

### Prérequis
1.  Un ordinateur avec **Python 3** installé.
2.  La librairie `requests` installée (`pip install requests`).

### Étapes

1.  Ouvrez un terminal dans le dossier de l'intégration.
2.  Allez dans le dossier `scripts` et lancez le script :

```bash
cd scripts
python get_config_key.py
```

1. Entrez votre **Email** et votre **Mot de Passe** de compte Boks quand demandé.
    *   *Note de confidentialité : Vos identifiants sont utilisés uniquement pour cette session afin d'interroger l'API Boks. Ils ne sont ni enregistrés ni envoyés ailleurs.*
2. Le script affichera la liste de vos Boks avec leurs **Configuration Keys**.

Copiez la clé (8 caractères) et collez-la dans la configuration de l'intégration Home Assistant.

## Méthode 2 : Extraction Manuelle (Android - Avancé)

Si la méthode Cloud ne fonctionne pas, vous pouvez tenter de récupérer les données depuis l'application Android.

### 1. Récupérer les données
Vous devez obtenir le dossier de base de données de l'application.
*   **Chemin Android** : `/data/user/0/com.boks.app/app_webview/Default/IndexedDB/`
*   **Contraintes** : L'application désactivant généralement la sauvegarde standard (`allowBackup=false`), un simple `adb backup` ne fonctionnera pas.
    *   **Root** : Si votre téléphone est rooté, vous pouvez accéder directement au chemin ci-dessus.
    *   **Outils Constructeurs** : Certains outils de sauvegarde propriétaires (Samsung Smart Switch, Xiaomi Backup, OnePlus Switch, etc.) peuvent parfois contourner cette restriction et inclure les données d'application.
    *   Copiez le dossier extrait sur votre ordinateur.

### 2. Analyser les données

**Méthode Rapide (Peut suffire) :**
Vous pouvez d'abord essayer d'utiliser la commande `strings` (Linux/Mac) ou un éditeur de texte hexadécimal sur les fichiers `.ldb` pour chercher `"configurationKey"`.
Si vous avez de la chance (données non compressées), vous trouverez la clé directement.

**Méthode Robuste (Recommandée si la méthode rapide échoue) :**
LevelDB compressant souvent les données, la méthode simple peut échouer. Dans ce cas, utilisez l'outil spécialisé **[dfindexeddb](https://github.com/google/dfindexeddb)** :

1.  Installez l'outil : `pip install dfindexeddb`
2.  Analysez votre dossier :
    ```bash
    dfindexeddb db -s /chemin/vers/votre/dossier/IndexedDB/ --format chrome --use_manifest
    ```
3.  Cherchez `"configurationKey"` dans le résultat.

Vous devriez trouver une structure JSON contenant :
`"configurationKey":"XXXXXXXX"`

C'est cette valeur `XXXXXXXX` (8 caractères) qu'il vous faut.

## Méthode 3 : Extraction Manuelle (iOS - Avancé)

Si vous possédez un iPhone et que vous avez utilisé l'application Boks dessus, vous pouvez extraire la clef depuis une sauvegarde.

### 1. Récupérer les données

**Prérequis :**
*   Un ordinateur (Windows ou Mac).
*   **iMazing** (la version gratuite permet de faire des sauvegardes).
*   **iBackupBot** (ou tout autre explorateur de sauvegarde iOS comme iExplorer).

**Étapes :**
1.  **Backup** : Créez une sauvegarde locale **non-chiffrée** avec iMazing. *Il est impératif que le chiffrement soit désactivé pour accéder aux fichiers.*
2.  **Navigation** : Utilisez iBackupBot pour explorer la sauvegarde et allez dans :
    `User App Files` > `com.boks.app` > `Library` > `WebKit` > `WebsiteData` > `Default` > `IndexedDB`.
3.  **Cible** : Identifiez le dossier contenant la base la plus lourde (environ 120 KB) et localisez le fichier `IndexedDB.sqlite3`.
4.  **Export** : Extrayez ce fichier sur votre ordinateur.

### 2. Analyser les données

**Méthode Automatisée (iOS 15+) :**
WebKit utilise un format SQLite spécifique à partir d'iOS 15, géré par l'outil **dfindexeddb**.

1.  Installez l'outil : `pip install dfindexeddb`
2.  Lancez l'analyse :
    ```bash
    dfindexeddb db -s IndexedDB.sqlite3 --format safari
    ```
3.  Cherchez `"configurationKey"` dans le résultat JSON.

**Méthode de Secours (iOS 14 ou inférieur) :**
Si le script renvoie une erreur `ParserError: 10 is not the expected CurrentVersion`, la version de WebKit est plus ancienne.

1.  Ouvrez le fichier `IndexedDB.sqlite3` avec un éditeur hexadécimal (ex: **WinHex**, **Hex Fiend**).
2.  Recherchez la chaîne ANSI `configurationKey`.
3.  La clé se trouve juste après l'une des occurrences.
    *   *Note : L'encodage peut être en UTF-16 (un octet `00` entre chaque caractère).*

## Que faire si aucune méthode ne fonctionne ? (Dernier recours)

Si la Méthode 1 (Cloud) vous renvoie une erreur ou une clé vide, et que vous n'avez pas de sauvegarde locale (Méthodes 2 & 3), voici les causes probables et les solutions :

### 1. Votre compte n'est pas "Migré"
Boks a imposé une migration payante pour continuer à utiliser leurs services Cloud. Si vous n'avez pas payé cette migration, l'API Cloud ne renverra pas votre `Configuration Key`.
*   **Vérification** : Ouvrez l'application officielle Boks. Si elle vous demande de payer pour accéder à vos boks ou si vos boks n'apparaissent plus, vous n'êtes pas migré.
*   **Solution** : Vous devez effectuer cette migration au moins une fois pour débloquer l'accès API officiel et permettre au script de récupération de fonctionner.

### 2. La clé n'est pas "remontée" sur le Cloud
Parfois, même avec un compte migré, l'API ne renvoie pas la clé si aucune action récente n'a "forcé" sa synchronisation.
*   **Astuce** : Dans l'application officielle, créez un **nouveau code permanent** (vous pourrez le supprimer juste après). Cette action force souvent l'application à synchroniser les clés de sécurité avec le serveur. Relancez ensuite le script de la **Méthode 1**.

### Pourquoi faire cet effort ? (Indépendance Totale)
Une fois que vous avez récupéré cette **Configuration Key** (8 caractères) :
1.  **Sauvegardez-la précieusement.**
2.  **Devenez indépendant** : Vous n'aurez **plus jamais** besoin des serveurs Boks (au cas où l'entreprise fasse faillite, une nouvelle fois...) ni de l'application officielle pour piloter votre Boks. Cette clé permet d'utiliser n'importe quelle application tierce (comme cette intégration Home Assistant) pour générer des codes et communiquer directement en Bluetooth.
