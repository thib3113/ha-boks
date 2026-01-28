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

*   **1. Code Permanent Uniquement (Requis pour le Fonctionnement de Base)**
    *   **Saisie** : Entrez votre code de déverrouillage Boks à 6 caractères (par exemple, `1234AB`) dans le champ "Code Permanent". Laissez le champ "Authentifiant" vide.
    *   **Fonctionnalités Activées** :
        *   **Déverrouillage Boks** : Contrôlez l'entité `lock` pour ouvrir votre Boks.
        *   **Capteur de Niveau de Batterie** : Surveillez l'état de la batterie de votre appareil Boks (les données de batterie ne sont disponibles qu'après l'ouverture de la porte). Note : Les entités de batterie peuvent nécessiter un redémarrage de l'intégration pour apparaître.
        *   **Capteur de Comptage des Codes** : Surveillez le nombre de Codes Permanents, Standard et Multi-usage stockés sur votre appareil.
        *   **Journalisation des Événements** : Recevez les événements opérationnels de base de votre Boks (par exemple, porte ouverte/fermée, tentatives de code valides/invalides) via l'entité `event.<nom>_logs`.
        *   **Liste de Tâches (Fonctionnalité de Base)** : Une entité `todo.<nom>_parcels` sera créée. Vous pouvez l'utiliser pour suivre les colis (avec descriptions), mais vous devrez gérer manuellement (créer et associer) tous les codes PIN. L'intégration tentera toujours de valider et de marquer les tâches comme terminées si elle détecte un code associé manuellement dans ses journaux et émettra des événements `boks_parcel_completed`. En "Mode Dégradé" (lorsqu'aucune Clef de Configuration n'est fournie), le suivi des colis est disponible sans génération de code.

*   **2. Clef de Configuration ou Clef Maître (Optionnel, Recommandé pour les Fonctionnalités Avancées)**
    *   **Saisie** : En plus de votre "Code Permanent", entrez votre **Clef de Configuration** (8 caractères hexadécimaux) ou **Clef Maître** (64 caractères hexadécimaux) dans le champ "Authentifiant".
        *   *Conseil* : Fournir la **Clef Maître** est recommandé car elle offre plus de capacités et pourrait prendre en charge de futures fonctionnalités telles que la génération de codes hors ligne. Actuellement, la Clef de Configuration et la Clef Maître activent le même ensemble de fonctionnalités avancées.
    *   **Fonctionnalités Activées** :
        *   **Toutes les Fonctionnalités du Code Permanent Uniquement**
        *   **Intégration Améliorée de la Liste de Tâches (Gestion des Colis)** : L'entité `todo.<nom>_parcels` offre une fonctionnalité complète.
            *   **Génération Automatique de PIN** : Lorsque vous ajoutez un élément à la liste `todo.<nom>_parcels` avec une description (par exemple, "Colis Amazon"), l'intégration générera automatiquement un code PIN unique associé à cette entrée de colis.
            *   **Support des Descriptions** : Vous pouvez ajouter des descriptions significatives à vos éléments de liste de tâches, qui sont liés aux codes PIN générés.
            *   **Responsabilité de l'Utilisateur pour les PIN Modifiés** : Si vous modifiez manuellement un code PIN généré automatiquement pour un élément de liste de tâches, l'intégration reconnaîtra le changement mais ne gérera plus automatiquement ce PIN spécifique. Vous devenez responsable de sa gestion.
            *   **Achèvement Automatique des Tâches et Émission d'Événements** : L'intégration marquera automatiquement les tâches comme terminées lorsqu'elle détectera que le code associé est utilisé dans ses journaux et émettra des événements `boks_parcel_completed`.

6.  **Soumettre** : Cliquez sur "Soumettre" pour finaliser la configuration et activer l'intégration avec les fonctionnalités sélectionnées.

## Options du Système

Une fois l'intégration installée, vous pouvez modifier ses options en cliquant sur **Configurer** sur la carte de l'intégration Boks (via Appareils et Services).

### Paramètres Disponibles

*   **Intervalle de mise à jour (minutes)** (`scan_interval`) :
    *   Définit la fréquence à laquelle Home Assistant tente de se connecter à la Boks pour vérifier son état (ex: batterie).
    *   *Note* : Une fréquence trop élevée peut réduire la durée de vie de la batterie.

*   **Intervalle de rafraîchissement complet (heures)** (`full_refresh_interval`) :
    *   Définit la fréquence d'une synchronisation complète des données (logs, configuration profonde).

*   **Code permanent pour l'ouverture (optionnel)** (`master_code`) :
    *   Permet de modifier le code utilisé par défaut par l'action "Ouvrir" (`lock.open`). Utile si vous avez changé le code sur le boîtier manuellement.

*   **Anonymiser les logs** (`anonymize_logs`) :
    *   **Très Important pour le Support** : Si cette option est activée, tous les codes PIN et identifiants sensibles seront remplacés par des valeurs factices (ex: `1234AB`) dans les journaux de débogage Home Assistant.
    *   Activez cette option **avant** de partager vos logs pour une demande d'aide ou un rapport de bug.

## Configuration Avancée

### Persistance du Format de Batterie

L'appareil Boks prend en charge différents formats de mesure de batterie, qui sont automatiquement détectés par l'intégration :

*   **measure-single** : Mesure simple du niveau de batterie (service de batterie standard)
*   **measures-t1-t5-t10** : Mesures multiples à différents intervalles de temps
*   **measures-first-min-mean-max-last** : Mesures détaillées incluant les valeurs min, moyenne et max

L'intégration détecte automatiquement le format de batterie lors de la première ouverture de la porte et le stocke dans la configuration. Cela garantit que les capteurs de diagnostic de batterie appropriés sont créés et disponibles même lorsque l'appareil est hors ligne. Si le format de batterie change (par exemple, en raison d'une mise à jour du firmware), l'intégration le détectera et mettra à jour le format stocké lors de la prochaine ouverture de la porte.

## Reconfiguration d'une Intégration Existante

Si vous devez modifier le Code Permanent ou l'Authentifiant pour une intégration Boks déjà configurée :

1.  Allez dans **Paramètres** -> **Appareils et Services**.
2.  Trouvez votre intégration Boks et cliquez sur "Configurer".
3.  Ajustez les paramètres selon vos besoins et enregistrez. Cela mettra à jour les fonctionnalités disponibles en fonction des nouveaux authentifiants fournis.
