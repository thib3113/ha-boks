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

### 1. Accéder à la Page de Mise à Jour
Une fois qu'une mise à jour est préparée, l'intégration génère une page accessible à l'adresse suivante :
`http://<adresse-ip-home-assistant>:<port>/local/boks/index.html`

*(Remarque : Remplacez `<adresse-ip-home-assistant>` par l'IP locale ou le nom de domaine de votre Home Assistant)*

### 2. Effectuer la Mise à Jour
*   Ouvrez cette page sur un appareil doté de **capacités Bluetooth** (smartphone, ordinateur portable).
*   Assurez-vous d'être **physiquement proche** de votre Boks.
*   Suivez les instructions à l'écran pour connecter et flasher le nouveau firmware.

### 3. Zones Blanches / Pas de Réseau
La page de mise à jour nécessite une connexion à votre instance Home Assistant pour se charger.

**Si votre Boks est située dans une zone sans couverture réseau (ex : sous-sol sans WiFi/4G) :**

1.  **Télécharger le fichier ZIP :** Avant de vous rendre à l'emplacement de la Boks, accédez à la page de mise à jour et téléchargez le fichier `.zip` du firmware (généralement disponible via un lien sur la page ou à `/local/boks/v<version>/firmware.zip`).
2.  **Utiliser une Application Mobile :** Installez l'application **nRF Connect for Mobile** (disponible sur Android et iOS).
3.  **Flasher Manuellement :** Utilisez l'application nRF Connect pour vous connecter à votre Boks et téléverser manuellement le fichier `.zip` téléchargé.


### 4. Mode "Page en Cache" (Processus en deux étapes)
Alternativement, vous pouvez utiliser la page web même si vous n'avez pas d'accès internet *à l'emplacement de la Boks*, sans avoir besoin de l'application nRF Connect.

1.  **Étape 1 (En Ligne) :** Ouvrez la page de mise à jour (`/local/boks/index.html`) sur votre smartphone tant que vous êtes **connecté au WiFi** (ou avez de la 4G).
    *   La page va automatiquement télécharger le fichier firmware et le stocker dans la mémoire de votre navigateur (cache).
    *   Attendez que la page soit complètement chargée.
2.  **Étape 2 (Hors Ligne) :** **Ne fermez pas l'onglet.** Déplacez-vous jusqu'à votre Boks (même si vous perdez la connexion WiFi/4G).
3.  **Étape 3 (Flash) :** Puisque le firmware est déjà chargé dans la page, vous pouvez cliquer sur "Connecter" et effectuer la mise à jour comme si vous étiez en ligne.
