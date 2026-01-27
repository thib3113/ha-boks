# Utilisation : Services, Événements et Automatisations

Ce document est un guide complet pour interagir avec votre Boks via Home Assistant, que ce soit manuellement via des services ou automatiquement via des automatisations.

## 🛠️ Services Disponibles

L'intégration Boks expose plusieurs services pour contrôler votre appareil. Vous pouvez les appeler depuis **Outils de développement > Services** ou les utiliser dans vos scripts et automatisations.

### Contrôle de la Porte

#### `lock.open` (ou `boks.open_door`)
Ouvre la porte de la Boks.
*   **Entité** : `lock.votre_boks_porte`
*   **Code (Optionnel)** : Si omis, l'intégration utilise le "Code Permanent" configuré. Si vous spécifiez un code, c'est celui-ci qui sera utilisé (utile pour tester des codes à usage unique).

### Gestion des Colis

#### `todo.add_item` (ou `boks.add_parcel`)
Ajoute un colis à attendre.
*   **Entité** : `todo.votre_boks_colis`
*   **Description** : Le nom du colis.
    *   *Mode Auto* : Entrez juste le nom (ex: "Amazon"). L'intégration génère un code et met à jour le titre (ex: "1234AB - Amazon").
    *   *Mode Manuel* : Entrez le code suivi du nom (ex: "1234AB - Amazon").

### Gestion des Codes

#### `boks.add_master_code` / `boks.delete_master_code`
Gère les codes permanents (accès famille, livreur régulier).
*   **Index** : Emplacement mémoire (0-99).
*   **Code** : Le code PIN à 6 caractères.

#### `boks.add_single_code` / `boks.delete_single_code`
Gère les codes à usage unique manuellement (si vous n'utilisez pas la liste de tâches).

### Maintenance

#### `boks.sync_logs`
Force une synchronisation immédiate des journaux avec la Boks (nécessite une connexion Bluetooth active).

#### `boks.set_configuration`
Modifie les paramètres internes (ex: activer/désactiver la reconnaissance des badges La Poste).

---

## 📡 Détail des Événements

L'intégration Boks émet des événements riches que vous pouvez utiliser pour des automatisations avancées.

### Entité et Bus d'Événements

Vous pouvez écouter les événements de deux manières :
1.  **Entité** : `event.votre_boks_logs` (Le dernier événement est stocké dans l'attribut `event_type`).
2.  **Bus d'Événements** : `boks_log_entry` (Contient la charge utile complète à chaque nouvel événement).

### Structure des Données

Voici les données disponibles dans la charge utile de l'événement (`trigger.event.data`) :

| Champ | Description | Exemple |
| :--- | :--- | :--- |
| `type` | Le type d'événement (voir liste ci-dessous) | `code_ble_valid` |
| `device_id` | L'ID de l'appareil Home Assistant | `abcdef123456...` |
| `timestamp` | Date et heure de l'événement | `2023-10-27T10:00:00+00:00` |
| `code` | Le code PIN utilisé (si applicable) | `1234AB` |
| `user` | L'index utilisateur ou nom (si connu) | `0` (Master Code Index) |
| `extra_data` | Données brutes supplémentaires | `{...}` |

### Types d'Événements (`event_type`)

| Type | Description |
| :--- | :--- |
| `door_opened` | La porte a été ouverte. |
| `door_closed` | La porte a été fermée. |
| `code_ble_valid` | Ouverture réussie via Bluetooth (App ou HA). |
| `code_key_valid` | Ouverture réussie via le clavier physique. |
| `code_ble_invalid` | Code erroné saisi via Bluetooth. |
| `code_key_invalid` | Code erroné saisi sur le clavier. |
| `nfc_opening` | Ouverture via un badge NFC. |
| `key_opening` | Ouverture via la clé mécanique de secours. |
| `error` | Erreur système générique. |
| `power_on` | L'appareil a démarré (mise sous tension). |
| `power_off` | L'appareil s'est éteint (ex: piles retirées). |
| `ble_reboot` | Le module Bluetooth a redémarré. |
| `history_erase` | L'historique des logs a été effacé. |

---

## 🚀 Blueprints (Automatisations Prêtes à l'Emploi)

Pour vous simplifier la vie, nous fournissons plusieurs Blueprints adaptés à différents besoins.

### 📥 1. [Notification de Colis Livré](../../blueprints/automation/boks_parcel_delivered.yaml)
Vous envoie une notification quand un code de la liste de colis est utilisé.

### 📥 2. [Alerte Sécurité (Code Invalide)](../../blueprints/automation/boks_security_alert.yaml)
Notification critique immédiate si un code PIN erroné est saisi sur la Boks.

### 📥 3. [Alerte Batterie Faible](../../blueprints/automation/boks_battery_alert.yaml)
Surveillance robuste de la batterie (avec gestion des redémarrages HA et temporisation pour éviter les fausses alertes).

### 📥 4. [Alerte Porte Restée Ouverte](../../blueprints/automation/boks_door_left_open.yaml)
Vérifie intelligemment si la porte est restée ouverte.
*   *Particularité* : Effectue une vérification active (synchronisation Bluetooth) avant d'envoyer l'alerte pour s'assurer que la porte est réellement ouverte.

---

## 🤖 Exemples d'Automatisations (Configuration Manuelle)

Si vous préférez créer vos propres automatisations sur mesure, voici des exemples concrets.

### 1. Notification de Livraison (Colis Déposé)
Soyez notifié quand un livreur utilise le code associé à un colis attendu.

```yaml
alias: "Boks: Colis Livré"
description: "Envoie une notification quand un code de colis est utilisé."
trigger:
  - platform: event
    event_type: boks_parcel_completed
condition: []
action:
  - service: notify.mobile_app_votre_telephone
    data:
      title: "📦 Colis Livré !"
      message: "Le colis '{{ trigger.event.data.description }}' a été déposé avec le code {{ trigger.event.data.code }}."
```

### 2. Alerte Porte Restée Ouverte (Version Simple)
Si la porte reste ouverte plus de 5 minutes, recevez une alerte.
*Note : Pour une version plus fiable qui vérifie l'état réel, utilisez le Blueprint fourni.*

```yaml
alias: "Boks: Alerte Porte Ouverte"
trigger:
  - platform: state
    entity_id: lock.ma_boks_porte
    to: "unlocked"
    for:
      hours: 0
      minutes: 5
      seconds: 0
action:
  - service: notify.mobile_app_votre_telephone
    data:
      message: "⚠️ Attention, la porte de la Boks est ouverte depuis 5 minutes !"
```

### 3. Alerte Batterie Faible
Surveillez le niveau de batterie pour ne jamais être pris au dépourvu.

```yaml
alias: "Boks: Batterie Faible"
trigger:
  - platform: numeric_state
    entity_id: sensor.ma_boks_batterie
    below: 20
action:
  - service: notify.mobile_app_votre_telephone
    data:
      message: "🔋 Batterie Boks faible ({{ states('sensor.ma_boks_batterie') }}%). Pensez à remplacer les piles."
```

### 4. Tentative d'Intrusion (Code Faux)
Soyez alerté si quelqu'un essaie des codes invalides.

```yaml
alias: "Boks: Code Invalide"
trigger:
  - platform: state
    entity_id: event.ma_boks_journaux
    attribute: event_type
    to: "code_ble_invalid"
  - platform: state
    entity_id: event.ma_boks_journaux
    attribute: event_type
    to: "code_key_invalid"
action:
  - service: notify.mobile_app_votre_telephone
    data:
      message: "🚨 Code invalide tenté sur la Boks !"
```

### 5. Notification d'Ouverture (Générique)
Savoir qui a ouvert la boîte (Famille, Facteur, etc.).

```yaml
alias: "Boks: Nouvelle Ouverture"
trigger:
  - platform: state
    entity_id: event.ma_boks_journaux
    attribute: event_type
    to:
      - "code_ble_valid"
      - "code_key_valid"
      - "nfc_opening"
      - "key_opening"
action:
  - service: notify.mobile_app_votre_telephone
    data:
      title: "Boks Ouverte"
      message: >
        La Boks a été ouverte.
        Type : {{ state_attr('event.ma_boks_journaux', 'event_type') }}
        Info : {{ state_attr('event.ma_boks_journaux', 'extra_data') }}
```
