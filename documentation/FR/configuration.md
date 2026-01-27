# Guide de Configuration pour l'Intégration Boks pour Home Assistant

Ce guide explique comment configurer l'intégration Boks pour Home Assistant après son installation.

## Configuration Initiale

1.  **Naviguez vers les Intégrations** : Dans votre interface Home Assistant, allez dans **Paramètres** -> **Appareils et Services**.
2.  **Ajouter une Intégration** : Cliquez sur le bouton "Ajouter une intégration" (généralement un signe plus bleu dans le coin inférieur droit).
3.  **Recherchez Boks** : Dans la barre de recherche, tapez "Boks" et sélectionnez l'intégration.
4.  **Découverte de l'appareil** : L'intégration devrait automatiquement découvrir votre appareil Boks s'il se trouve à portée Bluetooth de votre serveur Home Assistant ou d'un proxy Bluetooth ESPHome. Sélectionnez l'appareil Boks découvert.
5.  **Formulaire de Configuration** : Une boîte de dialogue de configuration apparaît.

### Niveaux d'Authentifiants

*   **Code Permanent Uniquement** : Entrez votre code PIN (6 caractères). Permet l'ouverture, la lecture batterie et logs de base.
*   **Clef de Configuration/Maître** (Recommandé) : Permet la génération automatique de codes et la gestion avancée des colis.

## Options du Système

Une fois l'intégration installée, vous pouvez modifier ses options en cliquant sur **Configurer** sur la carte de l'intégration Boks.

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
3.  Ajustez les paramètres selon vos besoins et enregistrez.
