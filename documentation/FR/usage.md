# Événements et Automatisations (Utilisation) dans l'Intégration Boks pour Home Assistant

Ce document explique comment utiliser les événements exposés par l'intégration Boks pour les automatisations Home Assistant. L'exploitation de ces événements vous permet de créer des automatisations puissantes basées sur l'activité de votre appareil Boks.

## Aperçu de l'Entité Événement (Event Entity)

L'intégration Boks expose une entité `event` (par exemple, `event.boks_logs`) qui se déclenche chaque fois que de nouvelles données de journal sont récupérées de votre appareil Boks. Cette entité sert de point central pour toutes les activités historiques enregistrées par votre Boks.

En plus de l'entité `event`, l'intégration émet également des événements sur le bus d'événements Home Assistant avec le type d'événement `boks_log_entry`. Ces événements contiennent les mêmes données que l'entité `event` et peuvent être utilisés dans les automatisations comme alternative aux déclencheurs basés sur l'état.

Lorsqu'un événement se déclenche, il contient un attribut `event_type` et potentiellement d'autres données qui décrivent ce qui s'est passé.

## Types d'Événements Disponibles

Voici les valeurs `event_type` courantes que vous pourriez recevoir :

*   `door_opened` : La porte du Boks a été ouverte.
*   `door_closed` : La porte du Boks a été fermée.
*   `code_ble_valid` : Un code valide a été entré via Bluetooth Low Energy (BLE).
*   `code_key_valid` : Un code valide a été entré via le clavier physique.
*   `code_ble_invalid` : Une tentative de code invalide a été effectuée via BLE.
*   `code_key_invalid` : Une tentative de code invalide a été effectuée via le clavier physique.
*   `error` : Une erreur s'est produite sur l'appareil Boks.
*   ... et potentiellement d'autres types d'événements indiquant divers états ou actions.

## Exemples de Déclencheurs d'Automatisation

Vous pouvez utiliser le déclencheur "Événement" dans les automatisations Home Assistant pour réagir à des valeurs `event_type` spécifiques de votre Boks.

### Exemple 1 : Notification lors de l'ouverture de la porte du Boks

Cette automatisation envoie une notification à votre application mobile chaque fois que la porte du Boks est ouverte.

```yaml
alias: Notifier quand la porte du Boks est ouverte
description: "Envoie une notification à votre téléphone lorsque la porte du Boks est ouverte."
trigger:
  - platform: state
    entity_id: event.boks_logs # Surveiller l'entité événement Boks
condition:
  - condition: template # Utiliser une condition de template pour vérifier l'attribut event_type
    value_template: "{{ state_attr('event.boks_logs', 'event_type') == 'door_opened' }}"
action:
  - service: notify.mobile_app_iphone # Remplacez par votre service de notification
    data:
      message: "Votre Boks a été ouverte !"
mode: queued
```

> ⚠️ **Avertissement** : Lorsque vous utilisez l'entité `event.boks_logs` dans les automatisations, assurez-vous d'utiliser le nom d'entité correct car il peut varier en fonction du nom de votre appareil. Vérifiez le nom de l'entité dans votre instance Home Assistant pour garantir l'exactitude.

*   **Explication** :
    *   Le `trigger` écoute tout changement d'état sur `event.boks_logs`.
    *   La `condition` vérifie ensuite si l'attribut `event_type` de `event.boks_logs` est `door_opened`.
    *   Si la condition est remplie, l'`action` envoie une notification.

### Exemple 2 : Enregistrer tous les événements Boks dans une notification persistante

Cette automatisation crée une notification persistante dans Home Assistant pour chaque événement de votre Boks.

```yaml
alias: Enregistrer tous les événements Boks
description: "Crée une notification persistante pour chaque événement signalé par le Boks."
trigger:
  - platform: state
    entity_id: event.boks_logs
action:
  - service: persistent_notification.create
    data_template:
      title: "Événement Boks : {{ state_attr('event.boks_logs', 'event_type') }}"
      message: "Nouvel événement reçu du Boks : {{ states('event.boks_logs') }} à {{ now().strftime('%H:%M:%S') }}. Détails : {{ state_attr('event.boks_logs', 'event_data') | tojson }}"
mode: queued
```

*   **Explication** :
    *   Cette automatisation se déclenche sur tout changement d'état de `event.boks_logs`.
    *   Elle crée ensuite une notification persistante avec l'`event_type` dans le titre et un message plus détaillé incluant l'état brut et toute `event_data`.

[Ajouter d'autres exemples ou des détails sur des cas d'utilisation spécifiques pour les automatisations.]