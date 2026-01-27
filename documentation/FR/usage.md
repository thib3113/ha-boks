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

## 🚀 Blueprint (Automatisations Simplifiées)

Pour simplifier la configuration, nous fournissons un **Blueprint** prêt à l'emploi qui regroupe les scénarios les plus courants.

### 📥 [Importer le Blueprint Boks Notifications](../../blueprints/automation/boks_notifications.yaml)

Ce Blueprint vous permet de configurer en quelques clics :
*   ✅ Notification de colis livré
*   🚪 Notification d'ouverture de porte
*   🚨 Alerte en cas de code faux
*   🔋 Alerte batterie faible

Pour l'utiliser :
1.  Copiez le fichier `blueprints/automation/boks_notifications.yaml` dans votre dossier `blueprints/automation/`.
2.  Allez dans **Paramètres > Automatisations et scènes > Blueprints**.
3.  Cherchez "Boks Notifications" et cliquez sur "Créer une automatisation".

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

### 2. Alerte Porte Restée Ouverte
Si la porte reste ouverte plus de 5 minutes, recevez une alerte.
*Note : L'entité `lock` est considérée comme "déverrouillée" tant que la porte est physiquement ouverte.*

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
