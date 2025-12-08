# Guide d'Installation pour l'Intégration Boks pour Home Assistant

Ce guide fournit des instructions étape par étape pour l'installation de l'intégration Boks pour Home Assistant. Vous pouvez choisir entre une installation via HACS (recommandé) ou une installation manuelle.

[![Ouvrez votre instance Home Assistant et ouvrez un dépôt dans le Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=thib3113&repository=ha-boks&category=Integration)
[![Ajouter l'Intégration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=boks)

## Option 1 : Via HACS (Home Assistant Community Store) - Recommandé

HACS simplifie la gestion des intégrations personnalisées, rendant les mises à jour plus faciles.

1.  **Assurez-vous que HACS est installé** : Si vous n'avez pas HACS installé, suivez d'abord le guide d'installation officiel de HACS.
2.  **Ouvrez HACS** : Dans votre interface Home Assistant, naviguez vers **HACS**.
3.  **Allez dans Intégrations** : Cliquez sur "Intégrations" dans la barre latérale de HACS.
4.  **Ajouter un Dépôt Personnalisé** : Cliquez sur les trois points dans le coin supérieur droit de l'écran (⋮) et sélectionnez "Dépôts personnalisés".
5.  **Saisissez les Détails du Dépôt** :
    *   **URL du Dépôt** : `thib3113/ha-boks` (ou l'URL GitHub complète de ce dépôt).
    *   **Catégorie** : Sélectionnez "Intégration".
6.  **Ajouter et Télécharger** : Cliquez sur "Ajouter". Le dépôt devrait maintenant apparaître. Recherchez "Boks" dans HACS, puis cliquez dessus et sélectionnez "Télécharger".
7.  **Redémarrez Home Assistant** : Une fois le téléchargement terminé, **redémarrez votre instance Home Assistant** pour que l'intégration soit chargée.

## Option 2 : Installation Manuelle

Si vous préférez ne pas utiliser HACS ou si vous rencontrez des problèmes, vous pouvez installer l'intégration manuellement.

1.  **Téléchargez la Version** : Rendez-vous sur la [page des versions de ce dépôt](https://github.com/thib3113/ha-boks/releases) et téléchargez le fichier `boks.zip` de la dernière version.
2.  **Décompressez le Fichier** : Extrayez le contenu du fichier `boks.zip` téléchargé. Vous devriez trouver un dossier nommé `boks`.
3.  **Copiez vers les Composants Personnalisés** : Copiez l'intégralité du dossier `boks` dans le répertoire `custom_components/` de votre Home Assistant.
    *   Le répertoire `custom_components` est généralement situé dans le répertoire de configuration de votre Home Assistant (par exemple, `/config/custom_components/`). S'il n'existe pas, créez-le.
    *   Le chemin final devrait ressembler à `chemin/vers/homeassistant/config/custom_components/boks/`.
4.  **Redémarrez Home Assistant** : Après avoir copié les fichiers, **redémarrez votre instance Home Assistant** pour que l'intégration soit chargée.
