# Dépannage de l'Intégration Boks pour Home Assistant

Ce document fournit des conseils sur la façon de dépanner les problèmes courants et d'activer la journalisation de débogage pour l'intégration Boks pour Home Assistant.

## Activation de la Journalisation de Débogage

> **⚠️ Avertissement de Sécurité :** L'activation du mode debug affichera des informations sensibles dans vos journaux. **Avant de partager vos logs publiquement**, veuillez activer l'option **"Anonymiser les logs"** dans les réglages de l'intégration. Cela remplacera automatiquement vos données privées (clefs, codes PIN) par des valeurs factices (ex: `1234AB`, `1A3B5C7E`).

Lorsque vous rencontrez des problèmes avec l'intégration Boks, l'activation de la journalisation de débogage peut fournir des informations précieuses sur son fonctionnement et aider à identifier la cause première des problèmes.

Pour activer la journalisation de débogage, ajoutez la configuration suivante à votre fichier `configuration.yaml` de Home Assistant :

```yaml
logger:
  default: info
  logs:
    custom_components.boks: debug
```

Après avoir ajouté cela, redémarrez votre instance Home Assistant. Une fois redémarré, vérifiez vos journaux Home Assistant (généralement `home-assistant.log` dans votre répertoire de configuration) pour les messages précédés de `custom_components.boks`. Ces journaux contiendront des informations détaillées sur les activités de l'intégration, y compris la communication Bluetooth, l'envoi de commandes et les réponses.

## Problèmes Courants et Solutions

### 1. Appareil Boks non découvert

*   **Vérifiez le Bluetooth** : Assurez-vous que le Bluetooth est activé et fonctionne sur votre serveur Home Assistant ou votre proxy ESPHome. Vérifiez que d'autres appareils Bluetooth sont détectables.
*   **Portée** : Assurez-vous que votre appareil Boks est à proximité de votre adaptateur Bluetooth Home Assistant ou de votre proxy ESPHome. La portée Bluetooth peut être limitée.
*   **Proxy ESPHome** : Si vous utilisez un proxy ESPHome, assurez-vous qu'il est correctement configuré et connecté à Home Assistant. Vérifiez ses journaux pour les erreurs liées au Bluetooth.
*   **Redémarrage de l'Intégration/Home Assistant** : Parfois, un simple redémarrage de l'intégration Boks (depuis Appareils et Services -> Boks -> Recharger) ou de Home Assistant lui-même peut résoudre les problèmes de découverte. Si les entités de batterie ne s'affichent pas correctement, essayez de redémarrer l'intégration.

### 2. Impossible de se connecter ou de contrôler le Boks

*   **Code Permanent/Authentifiant** : Vérifiez attentivement que le Code Permanent et tout Authentifiant optionnel (Clef de Configuration/Clef Maître) sont correctement saisis dans la configuration de l'intégration. Les fautes de frappe sont courantes.
*   **Statut du Boks** : Assurez-vous que votre appareil Boks est sous tension et que son Bluetooth est actif.
*   **Autres Connexions** : Assurez-vous qu'aucun autre appareil (par exemple, l'application mobile officielle Boks) n'est actuellement connecté à votre Boks via Bluetooth, car cela peut empêcher Home Assistant de se connecter.
*   **Interférences** : Minimisez les interférences Bluetooth potentielles provenant d'autres appareils.

### 3. Fonctionnalités ne fonctionnant pas (par exemple, pas de journaux, pas de comptage de codes)

*   **Authentifiant Fourni** : Ces fonctionnalités nécessitent la fourniture d'une Clef de Configuration ou d'une Clef Maître lors de la configuration. Si vous n'en avez pas fourni, ou si vous en avez fourni une incorrecte, ces fonctionnalités ne fonctionneront pas.
*   **Permissions** : Assurez-vous que l'Authentifiant fourni dispose des autorisations nécessaires pour l'appareil Boks.
*   **Firmware de l'Appareil** : Un très ancien firmware Boks pourrait ne pas prendre en charge certaines fonctionnalités ou mécanismes de journalisation. Assurez-vous que le firmware de votre Boks est à jour si possible.

### 4. Les capteurs de diagnostic de batterie n'affichent pas d'informations détaillées

*   **Format de Batterie** : Les capteurs de diagnostic de batterie détaillés (par exemple, tension min, max, moyenne) ne sont disponibles que lorsque l'appareil Boks prend en charge le format de mesure de batterie approprié. Certains appareils peuvent uniquement prendre en charge le rapport de niveau de batterie de base.
*   **Première Ouverture de la Porte** : Les informations sur le format de batterie sont détectées lors de la première ouverture de la porte de l'appareil. Si les capteurs n'affichent pas d'informations détaillées, essayez d'ouvrir la porte du Boks, puis redémarrez l'intégration pour forcer une reconnexion et une redétection du format de batterie.
*   **Compatibilité de l'Appareil** : Les anciens appareils Boks peuvent ne pas prendre en charge les diagnostics avancés de batterie. Vérifiez la version matérielle de votre appareil pour déterminer ses capacités.

### 5. L'intégration devient indisponible ou déconnectée

*   **Stabilité Bluetooth** : Les connexions Bluetooth peuvent parfois être instables. Assurez-vous que votre matériel Bluetooth est fiable.
*   **Distance/Obstructions** : Une distance trop importante ou des obstructions physiques (murs, métal) entre votre adaptateur/proxy Bluetooth Home Assistant et le Boks peuvent entraîner des déconnexions.
*   **Niveau de Batterie** : Un niveau de batterie faible dans votre appareil Boks peut affecter la connectivité Bluetooth. Vérifiez le capteur de niveau de batterie.

### 6. La porte ne se ferme pas correctement après plusieurs ouvertures rapides

**Q:** "J'ai ouvert la porte trop rapidement deux fois (soit avec cette app, soit plusieurs), et elle refuse de se fermer ?"

**A:** "Il faut maintenir la porte fermée, puis taper un code permanent (master code en anglais), la serrure va refaire son cycle complet, et ensuite on devrait pouvoir la fermer correctement."

### 7. Problèmes Connus (Bugs Firmware)

*   **Suppression multiple de codes à usage unique (Single Use)** :
    Il existe un bug dans le firmware de la Boks qui permet de supprimer plusieurs fois le même code à usage unique valide (par exemple, si vous créez le code `11223344`, vous pouvez envoyer la commande de suppression plusieurs fois avec succès).
    Ce comportement se produit uniquement lorsque la Boks contient **plus de 3 326 codes à usage unique**. En dessous de ce seuil, la Boks retourne correctement une erreur si l'on tente de supprimer un code déjà supprimé.
    *Note : Bien que statistiquement improbable, ce comportement est anormal et suggère un problème de gestion de la mémoire qui pourrait potentiellement affecter ou supprimer d'autres codes enregistrés.*

Si vous continuez à rencontrer des problèmes après avoir suivi ces étapes et examiné les journaux de débogage, veuillez ouvrir une issue sur le [dépôt GitHub](https://github.com/thib3113/ha-boks/issues), en fournissant vos journaux de débogage (expurgés des informations sensibles) et une description détaillée du problème.
