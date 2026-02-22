# Prérequis pour l'Intégration Boks pour Home Assistant

Avant d'installer et de configurer l'intégration Boks pour Home Assistant, assurez-vous de satisfaire aux prérequis suivants.

## Exigences Matérielles

1.  **Un appareil Boks** : Vous devez posséder une boîte à colis connectée Boks.
2.  **Intégration Bluetooth Home Assistant avec un Relais Actif** :
    Pour contrôler votre Boks (déverrouiller, récupérer les logs), Home Assistant doit pouvoir établir une **connexion active** avec l'appareil. L'écoute passive (passive scanning) ne suffit pas.

    Cela peut être réalisé grâce à :
    *   **Un adaptateur Bluetooth local** : Branché directement sur la machine (USB ou intégré, ex: Raspberry Pi). Ils supportent généralement les connexions actives par défaut.
    *   **Un Proxy Bluetooth ESPHome (Recommandé)** : Idéal si votre Boks est éloignée de votre serveur.
        *   ⚠️ **Important** : Le proxy doit être en mode **ACTIF**. C'est généralement le cas par défaut (`active: true`), mais vérifiez votre configuration.
        *   Voir la **[documentation ESPHome](https://esphome.io/components/bluetooth_proxy/)**.
    *   ❌ **Shelly (Attention)** : La plupart des appareils Shelly (Gen 2/3) utilisés comme proxys Bluetooth ne supportent **PAS** les connexions actives (GATT).
        *   Si vous voyez le message *"Cet adaptateur ne prend pas en charge les connexions actives (GATT)"* (ou en anglais *"This adapter does not support making active (GATT) connections"*) dans Home Assistant, **cela ne fonctionnera pas** pour ouvrir la Boks.
        *   Ils peuvent éventuellement servir à détecter la présence ou la batterie (passif), mais pas à déverrouiller.

    **Diagnostic** :
    *   Si votre Boks est détectée mais que les commandes (déverrouillage) échouent systématiquement, vérifiez que votre proxy supporte bien les connexions actives (privilégiez ESPHome ou USB Local).

## Exigences relatives aux Identifiants (Credentials)

Pour utiliser pleinement l'intégration, vous aurez besoin des identifiants suivants :

1.  **Code Permanent (Obligatoire)** : Il s'agit du code PIN à 6 caractères que vous utilisez généralement pour ouvrir manuellement votre Boks (par exemple, `1234AB`). Ce code est essentiel pour la fonctionnalité de déverrouillage de base.
2.  **Clef de Configuration (Fortement Recommandé)** : Nécessaire pour les fonctionnalités avancées (gestion des colis en ligne, génération de codes).
3.  **Clef Maître (Expert)** : Nécessaire pour la **Génération de Codes Hors Ligne** (calcul de PINs valides sans Bluetooth).
    *   Voir le guide dédié : **[Comment récupérer vos Clefs](RETRIEVE_KEYS.md)**.
