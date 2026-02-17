// --- I18N CONFIGURATION ---
const LANG = navigator.language.startsWith('fr') ? 'fr' : 'en';

const TEXTS = {
    fr: {
        title: "Mise à jour Boks",
        download_short: "Télécharger le firmware (.zip)",
        target_version: "Version Cible : {version}",
        https_title: "Attention :",
        https_msg: "Le Bluetooth Web ne fonctionne qu'en HTTPS.",
        download_link: "Télécharger le firmware manuellement",
        backup_link: "Utiliser l'outil de secours en ligne (HTTPS)",
        backup_not_ready: "L'outil de secours en ligne arrive bientôt !",
        label_name: "Appareil",
        label_battery: "Batterie",
        label_version: "Version Soft",
        label_hw: "Version Hard",
        btn_connect: "1. Rechercher & Connecter",
        btn_reconnect: "Re-connecter (Mode Flash)",
        btn_prepare: "2. Activer le mode Mise à jour",
        btn_flash: "3. Lancer le flash",
        step_1: "Étape 1 : Rapprochez-vous et connectez votre Boks.",
        step_2: "Étape 2 : Préparez l'appareil pour recevoir le nouveau firmware.",
        step_3: "Étape 3 : L'appareil est en mode bootloader. Prêt pour le transfert.",
        reboot_wait: "La Boks va redémarrer. Cliquez sur Re-connecter et cherchez l'appareil nommé 'DfuTarg' dans la liste.",
        status_ready: "Prêt",
        status_searching: "Recherche en cours...",
        status_preparing: "Préparation de l'appareil...",
        status_flashing: "Flashage en cours...",
        status_success: "MISE À JOUR RÉUSSIE !",
        error_fw: "Erreur lors du chargement du fichier firmware.",
        error_gatt: "Erreur Bluetooth : ",
        error_battery: "Batterie trop faible pour flasher (> {level}% requis).",
        error_hw: "Matériel incompatible détecté !",
        warn_already_updated: "L'appareil est déjà à la version cible.",
        dfu_bootloader: "Bootloader",
        dfu_unknown: "Inconnue / Mode DFU",
        device_in_dfu: "Mode Récupération (DfuTarg)",
        timeout_note: "Note : Si aucun flash n'est lancé, la Boks redémarrera seule en mode normal (bip sonore) après quelques minutes.",
        reboot_manual: "Le transfert est fini. Si l'appareil ne redémarre pas, utilisez les boutons de secours ci-dessous.",
        dfu_explanation: "<strong>Note sur la progression :</strong> Pour garantir une sécurité maximale et éviter toute corruption, la Boks valide chaque bloc de données reçu. Il est normal de voir des messages 'Sync check' ou d'avoir l'impression que la barre de progression recule légèrement : cela signifie simplement qu'un petit morceau est renvoyé pour être corrigé afin d'être parfait. L'essentiel est que le pourcentage global continue d'avancer.",
        btn_delete: "Supprimer le package de mise à jour",
        delete_success: "Package supprimé avec succès.",
        delete_error: "Erreur lors de la suppression."
    },
    en: {
        title: "Boks Update",
        download_short: "Download firmware (.zip)",
        target_version: "Target Version: {version}",
        https_title: "Warning:",
        https_msg: "Web Bluetooth requires HTTPS.",
        download_link: "Download firmware manually",
        backup_link: "Use online backup tool (HTTPS)",
        backup_not_ready: "Online backup tool coming soon!",
        label_name: "Device",
        label_battery: "Battery",
        label_version: "Software Version",
        label_hw: "Hardware Version",
        btn_connect: "1. Search & Connect",
        btn_reconnect: "Reconnect (Flash Mode)",
        btn_prepare: "2. Enable Update Mode",
        btn_flash: "3. Start Real Flashing",
        step_1: "Step 1: Get close and connect your Boks.",
        step_2: "Step 2: Prepare the device for the new firmware.",
        step_3: "Step 3: Device is in bootloader mode. Ready for transfer.",
        reboot_wait: "The Boks will reboot. Click Reconnect and look for a device named 'DfuTarg' in the list.",
        status_ready: "Ready",
        status_searching: "Searching...",
        status_preparing: "Preparing device...",
        status_flashing: "Flashing...",
        status_success: "UPDATE SUCCESSFUL!",
        error_fw: "Error loading firmware file.",
        error_gatt: "Bluetooth Error: ",
        error_battery: "Battery too low to flash (> {level}% required).",
        error_hw: "Incompatible hardware detected!",
        warn_already_updated: "The device is already at the target version.",
        dfu_bootloader: "Bootloader",
        dfu_unknown: "Unknown / DFU Mode",
        device_in_dfu: "Recovery Mode (DfuTarg)",
        timeout_note: "Note: If no flash is started, the Boks will reboot to normal mode (beep) after a few minutes.",
        reboot_manual: "Transfer finished. If the device does not reboot, use the recovery buttons below.",
        dfu_explanation: "<strong>Note on progress:</strong> To ensure maximum safety and prevent corruption, the Boks validates every data block received. It is normal to see 'Sync check' messages or feel that the progress bar jumps back slightly: this simply means a small part is being re-sent to ensure it's perfect. As long as the overall percentage advances, the process is working correctly.",
        btn_delete: "Delete Update Package",
        delete_success: "Update package deleted successfully.",
        delete_error: "Error deleting package."
    }
};

/**
 * Translates a key and replaces {key} placeholders with data object values
 */
function t(key, data = {}) {
    let text = (TEXTS[LANG] || TEXTS['en'])[key] || key;
    for (const [k, v] of Object.entries(data)) {
        text = text.replace(`{${k}}`, v);
    }
    return text;
}