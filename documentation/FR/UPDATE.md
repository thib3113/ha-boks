# Système de Mise à Jour Boks

Les Boks sont basées sur des puces **nRF52**. Le système de mise à jour est conçu pour être **protégé**.

Si une personne envoie un faux paquet de mise à jour, la Boks refusera de l'installer. Il y a donc peu de risque à installer un fichier ZIP provenant d'internet.

## ⚠️ Note Importante pour les "Boks non-NFC" (V3 / nRF52811)

Pour les **Boks non-NFC** (aussi appelées Boks V3, fonctionnant sur nRF52811), veuillez noter le comportement suivant :

*   **Une mise à jour invalide supprimera le logiciel précédent.**
*   Par conséquent, la Boks restera en attente d'un logiciel valide et **ne redémarrera jamais** sur l'ancienne version.

Ce comportement est différent des **Boks NFC** (V4 / nRF52833), qui elles redémarreront sur leur logiciel précédent en cas d'échec de la mise à jour.
