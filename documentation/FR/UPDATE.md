# Système de Mise à Jour Boks

Les Boks sont basées sur des puces **nRF52**. Le système de mise à jour est conçu pour être **protégé**.

Si une personne envoie un faux paquet de mise à jour, la Boks refusera de l'installer. Il y a donc peu de risque à installer un fichier ZIP provenant d'internet.

## ⚠️ Note Importante pour les "Boks non-NFC" (V3 / nRF52811)

Pour les **Boks non-NFC** (aussi appelées Boks V3, fonctionnant sur nRF52811), veuillez noter le comportement suivant :

*   **Une mise à jour invalide supprimera le logiciel précédent.**
*   Par conséquent, la Boks restera en attente d'un logiciel valide et **ne redémarrera jamais** sur l'ancienne version.

Ce comportement est différent des **Boks NFC** (V4 / nRF52833), qui elles redémarreront sur leur logiciel précédent en cas d'échec de la mise à jour.

## Procédure de Mise à Jour via l'Intégration

L'intégration simplifie la procédure de mise à jour en générant une page web dédiée pour flasher votre Boks.

**Aucune application externe n'est requise.** La page web gère tout le processus, même si votre Boks se trouve dans une zone sans couverture (ex : sous-sol).

### Workflow Standard (Fonctionne Hors Ligne)

Le processus de mise à jour est conçu en deux étapes pour s'adapter aux Boks situées en zones blanches (sans WiFi/4G) :

1.  **Étape 1 : Préparation (En Ligne)**
    *   Idéalement, restez chez vous connecté en **WiFi**.
    *   Ouvrez le lien de la page de mise à jour fourni par l'intégration :
        `http://<adresse-ip-home-assistant>:<port>/local/boks/index.html`
    *   **Note de compatibilité :** Si votre connexion n'est pas sécurisée (HTTP) ou si vous utilisez un iPhone/iPad, la page le détectera automatiquement et vous proposera un lien vers un outil de secours en ligne sécurisé permettant de faire la mise à jour.
    *   **Attendez que la page soit complètement chargée.** Le fichier firmware est téléchargé automatiquement et stocké dans la mémoire de votre navigateur.
    *   *Ne fermez pas l'onglet.*

2.  **Étape 2 : Flash (Sur Place)**
    *   Marchez jusqu'à l'emplacement de votre Boks. **Vous n'avez plus besoin de connexion internet.**
    *   Assurez-vous que le Bluetooth est activé sur votre appareil.
    *   Cliquez sur le bouton **"Connecter"** sur la page.
    *   Sélectionnez votre Boks dans la liste.
    *   Suivez les instructions à l'écran pour lancer la mise à jour.

### Dépannage / Fallback Manuel

Si vous ne pouvez pas utiliser l'interface web (ex : navigateur incompatible ou restrictions iOS), vous pouvez effectuer une mise à jour manuelle :

1.  **Télécharger le fichier ZIP :** Sur la page de mise à jour, cherchez le lien de téléchargement pour récupérer le fichier `.zip`.
2.  **Utiliser nRF Connect :** Installez l'application **nRF Connect for Mobile** (Android/iOS).
3.  **Flasher Manuellement :** Utilisez l'application pour vous connecter à votre Boks et téléverser le fichier `.zip`.
