# Guide de Configuration pour l'Intégration Boks pour Home Assistant

Ce guide explique comment configurer l'intégration Boks pour Home Assistant après son installation, en se concentrant sur la manière dont les différentes entrées d'authentifiants activent diverses fonctionnalités.

## Configuration Initiale

1.  **Naviguez vers les Intégrations** : Dans votre interface Home Assistant, allez dans **Paramètres** -> **Appareils et Services**.
2.  **Ajouter une Intégration** : Cliquez sur le bouton "Ajouter une intégration" (généralement un signe plus bleu dans le coin inférieur droit).
3.  **Recherchez Boks** : Dans la barre de recherche, tapez "Boks" et sélectionnez l'intégration.
4.  **Découverte de l'appareil** : L'intégration devrait automatiquement découvrir votre appareil Boks s'il se trouve à portée Bluetooth de votre serveur Home Assistant ou d'un proxy Bluetooth ESPHome. Sélectionnez l'appareil Boks découvert.
5.  **Formulaire de Configuration** : Une boîte de dialogue de configuration apparaîtra, vous invitant à entrer les authentifiants. Le niveau de détail que vous fournissez ici détermine les fonctionnalités qui vous sont accessibles.

### Niveaux d'Authentifiants et Fonctionnalités Activées

L'intégration Boks propose une approche à plusieurs niveaux pour la fonctionnalité basée sur les authentifiants que vous fournissez lors de la configuration :

*   **1. Code Maître Uniquement (Requis pour le Fonctionnement de Base)**
    *   **Saisie** : Entrez votre code de déverrouillage Boks à 6 caractères (par exemple, `1234AB`) dans le champ "Code Maître". Laissez le champ "Authentifiant" vide.
    *   **Fonctionnalités Activées** :
        *   **Déverrouillage Boks** : Contrôlez l'entité `lock` pour ouvrir votre Boks.
        *   **Capteur de Niveau de Batterie** : Surveillez l'état de la batterie de votre appareil Boks.
        *   **Capteur de Comptage des Codes** : Surveillez le nombre de Codes Maîtres, Standard et Multi-usage stockés sur votre appareil.
        *   **Journalisation des Événements** : Recevez les événements opérationnels de base de votre Boks (par exemple, porte ouverte/fermée, tentatives de code valides/invalides) via l'entité `event.<nom>_logs`.
        *   **Liste de Tâches (Fonctionnalité de Base)** : Une entité `todo.<nom>_parcels` sera créée. Vous pouvez l'utiliser pour suivre les colis (avec descriptions), mais vous devrez gérer manuellement (créer et associer) tous les codes PIN. L'intégration tentera toujours de valider et de marquer les tâches comme terminées si elle détecte un code associé manuellement dans ses journaux et émettra des événements `boks_parcel_completed`.

*   **2. Clé de Configuration ou Clé Maître (Optionnel, Recommandé pour les Fonctionnalités Avancées)**
    *   **Saisie** : En plus de votre "Code Maître", entrez votre **Clé de Configuration** (8 caractères hexadécimaux) ou **Clé Maître** (64 caractères hexadécimaux) dans le champ "Authentifiant".
        *   *Conseil* : Fournir la **Clé Maître** est recommandé car elle offre plus de capacités et pourrait prendre en charge de futures fonctionnalités telles que la génération de codes hors ligne. Actuellement, la Clé de Configuration et la Clé Maître activent le même ensemble de fonctionnalités avancées.
    *   **Fonctionnalités Activées** :
        *   **Toutes les Fonctionnalités du Code Maître Uniquement**
        *   **Intégration Améliorée de la Liste de Tâches (Gestion des Colis)** : L'entité `todo.<nom>_parcels` offre une fonctionnalité complète.
            *   **Génération Automatique de PIN** : Lorsque vous ajoutez un élément à la liste `todo.<nom>_parcels` avec une description (par exemple, "Colis Amazon"), l'intégration générera automatiquement un code PIN unique associé à cette entrée de colis.
            *   **Support des Descriptions** : Vous pouvez ajouter des descriptions significatives à vos éléments de liste de tâches, qui sont liés aux codes PIN générés.
            *   **Responsabilité de l'Utilisateur pour les PIN Modifiés** : Si vous modifiez manuellement un code PIN généré automatiquement pour un élément de liste de tâches, l'intégration reconnaîtra le changement mais ne gérera plus automatiquement ce PIN spécifique. Vous devenez responsable de sa gestion.
            *   **Achèvement Automatique des Tâches et Émission d'Événements** : L'intégration marquera automatiquement les tâches comme terminées lorsqu'elle détectera que le code associé est utilisé dans ses journaux et émettra des événements `boks_parcel_completed`.

6.  **Soumettre** : Cliquez sur "Soumettre" pour finaliser la configuration et activer l'intégration avec les fonctionnalités sélectionnées.

## Configuration Avancée

[Ajouter des détails sur toutes les options de configuration avancées, si applicables. Par exemple, plusieurs appareils Boks, paramètres spécifiques.]

## Reconfiguration d'une Intégration Existante

Si vous devez modifier le Code Maître ou l'Authentifiant pour une intégration Boks déjà configurée :

1.  Allez dans **Paramètres** -> **Appareils et Services**.
2.  Trouvez votre intégration Boks et cliquez sur "Configurer".
3.  Ajustez les paramètres selon vos besoins et enregistrez. Cela mettra à jour les fonctionnalités disponibles en fonction des nouveaux authentifiants fournis.