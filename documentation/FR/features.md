# Fonctionnalités de l'Intégration Boks pour Home Assistant

Ce document détaille les fonctionnalités fournies par l'intégration Boks pour Home Assistant.

## Fonctionnalités de Base (Disponibles avec Code Permanent uniquement)

Ces fonctionnalités sont accessibles dès que le Code Permanent (PIN) est configuré.

### 🔓 Contrôle d'Accès
*   **Entité Verrou (Lock)** : Déverrouillez votre Boks depuis Home Assistant.

### 📊 Surveillance et Capteurs
*   **Niveau de batterie** : Surveillez l'état de la batterie.
*   **Température de batterie** : Surveillez la température de la batterie.
*   **Comptage des codes** : Visualisez combien de codes (permanents, à usage unique) sont stockés sur la boîte.
*   **Nombre de journaux** : Visualisez combien de journaux sont stockés sur la boîte.
*   **Dernière connexion** : Visualisez l'horodatage de la dernière connexion réussie à l'appareil.
*   **Dernier événement** : Visualisez le dernier événement de l'appareil.
*   **Statut de maintenance** : Visualisez le statut des opérations de maintenance.
*   **Format de mesure** : Visualisez le format de mesure de batterie utilisé par l'appareil.
*   **Type de batterie** : Visualisez le type de batterie installé dans l'appareil.
*   **Capteurs de diagnostic de batterie** : Visualisez les mesures détaillées de tension de batterie (disponibilité dépend du format de mesure).

### 📜 Journalisation (Logs)
L'intégration récupère automatiquement l'historique de la Boks et émet des événements (`event.boks_log_entry`) :
*   Ouvertures (Bluetooth, Clavier, Clef)
*   Fermetures
*   Erreurs et tentatives invalides

### 📦 Suivi de Colis (Mode Manuel)
L'entité `todo.parcels` est disponible pour lister vos colis attendus.
*   **Sans Config Key** : Vous devez gérer les codes manuellement (créer le code sur la boîte, puis l'ajouter dans la description de la tâche).
*   L'intégration validera quand même la tâche si elle voit passer ce code dans les logs.

---

## Fonctionnalités Avancées (Nécessite la Clef de Configuration)

Ces fonctionnalités nécessitent d'avoir renseigné la **Clef de Configuration** (8 caractères).

### ✨ Gestion Automatique des Codes
C'est la véritable puissance de l'intégration.

*   **Génération Automatique** : Ajoutez une tâche "Colis Amazon" dans la Todo List, et l'intégration va **créer automatiquement** un code PIN unique sur la Boks et l'ajouter à la description de la tâche.

### 🧩 Extension Navigateur
L'utilisation de l'[Extension Web Boks](https://github.com/thib3113/ha-boks-webextension) facilite la vie lors de vos commandes :
1.  Vous êtes sur un site marchand (ex: Amazon), dans le champ "Digicode" ou "Instructions de livraison".
2.  **Clic droit** dans le champ -> sélectionnez **"Générer un code Boks"**.
3.  Entrez une description (ex: "Livraison Livres").
4.  L'extension communique avec Home Assistant pour générer le code et l'insère automatiquement dans le champ texte.

