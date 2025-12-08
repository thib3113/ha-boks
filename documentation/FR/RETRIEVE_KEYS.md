# Comment récupérer votre Clé de Configuration (Configuration Key)

Pour débloquer les fonctionnalités avancées de l'intégration Boks (notamment la **gestion des colis** et la **création de codes**), vous avez besoin de la **Configuration Key**.

> **Note :** Cette clé n'est **PAS** nécessaire pour l'utilisation basique (Ouverture de la porte, lecture des logs, niveau de batterie). Le Code Maître (PIN) suffit pour cela.

## Qu'est-ce que la Configuration Key ?

C'est une chaîne de 8 caractères hexadécimaux (ex: `A1B2C3D4`).
Techniquement, il s'agit des **8 derniers caractères** de la **Master Key** (une clé de 64 caractères).

> **A propos de la Master Key :**
> La Master Key complète (64 caractères) ne peut être obtenue que lors de l'initialisation de la Boks (premier appairage) ou lors d'une procédure de "re-génération" des codes (qui nécessite elle-même la Config Key précédente).
>
> Cependant, son intérêt est aujourd'hui très limité pour Home Assistant, car la **Configuration Key** suffit pour activer toutes les fonctionnalités avancées (y compris la génération de codes via l'intégration).

## Méthode 1 : Via le script Cloud (Recommandé)

Un script Python est fourni dans le dossier `scripts/` de cette intégration. Il se connecte à votre compte Boks (via l'API cloud) pour récupérer vos appareils et leurs clés.

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

3.  Entrez votre **Email** et votre **Mot de Passe** de compte Boks quand demandé.
    *   *Note de confidentialité : Vos identifiants sont utilisés uniquement pour cette session afin d'interroger l'API Boks. Ils ne sont ni enregistrés ni envoyés ailleurs.*
4.  Le script affichera la liste de vos Boks avec leurs **Configuration Keys**.

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