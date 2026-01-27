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
*   `nfc_opening` : Ouverture de la Boks via un badge NFC.
*   `nfc_tag_registering` : Un badge a été scanné pendant une procédure d'enregistrement.
*   `error` : Une erreur s'est produite sur l'appareil Boks.
*   ... et potentiellement d'autres types d'événements indiquant divers états ou actions.
