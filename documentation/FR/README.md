# Intégration Boks pour Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub License](https://img.shields.io/github/license/thib3113/ha-boks?color=blue)](../../LICENSE)

Bienvenue dans la documentation française de l'intégration Boks pour Home Assistant.

## 📚 Table des Matières

Ce guide est divisé en plusieurs sections pour vous accompagner de l'installation à l'utilisation avancée :

*   **[Introduction](README.md)** : Vue d'ensemble du projet.
*   **[Fonctionnalités](features.md)** : Découvrez ce que cette intégration permet de faire (Contrôle, Capteurs, Suivi de Colis...).
*   **[Prérequis](prerequisites.md)** : Matériel (Bluetooth Proxy) et Identifiants (Code Permanent vs Clefs) nécessaires.
*   **[Installation](installation.md)** : Guide pas à pas (HACS ou Manuel).
*   **[Configuration](configuration.md)** : Comment paramétrer l'intégration et activer les fonctions avancées.
*   **[Utilisation (Événements & Automatisations)](usage.md)** : Exemples pour créer des automatisations basées sur les ouvertures de colis.
*   **[Dépannage](troubleshooting.md)** : Résolution des problèmes courants et activation des logs.

---

## Aperçu du Projet

Ceci est une intégration personnalisée pour **Home Assistant** qui vous permet de contrôler et de surveiller votre boîte à colis connectée **Boks** via **Bluetooth Low Energy (BLE)**.

Elle vous permet d'ouvrir votre Boks directement depuis Home Assistant sans avoir besoin de l'application mobile officielle ou d'une connexion internet (une fois configurée), en tirant parti des capacités Bluetooth de Home Assistant (adaptateur local ou proxys ESPHome).

## Fonctionnalités Clefs

*   🔓 **Déverrouillage local** via Bluetooth.
*   📦 **Suivi de Colis Intelligent** : Liste de tâches interactive avec génération automatique de codes (nécessite la clé de configuration).
*   🔋 **Surveillance** de la batterie.
*   📜 **Historique** des ouvertures et livraisons.

---

## ⚖️ Avis Juridique

> **⚠️ Avertissement :** Ceci est un projet non officiel développé uniquement à des fins d'interopérabilité.
> Il n'est pas affilié au fabricant de l'appareil. Aucun code ou actif propriétaire n'est distribué ici.
>
> 👉 Veuillez lire l'intégralité de l'**[Avis Juridique et Note sur la Rétro-ingénierie](../../LEGALS.md)** avant d'utiliser ce logiciel.
