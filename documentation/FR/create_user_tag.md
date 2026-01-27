# Créer un Badge Utilisateur Boks (DIY)

Ce guide explique comment transformer un badge NFC standard en "Badge Utilisateur" compatible avec votre Boks, permettant l'ouverture de la porte via le lecteur NFC.

## Pré-requis

1.  **Un Badge NFC Vierge :**
    *   Type : **Mifare Classic 1K** (UID 4 octets).
    *   *Note :* Pas besoin de badge "Magic" (UID modifiable) sauf si vous voulez cloner un badge existant. Un badge Mifare standard à 1€ suffit.
2.  **Un Smartphone Android avec NFC.**
3.  **L'application :** [Mifare Classic Tool (MCT)](https://play.google.com/store/apps/details?id=de.syss.MifareClassicTool).

---

## La Technique

La Boks ne lit pas n'importe quel badge. Pour être détecté, le badge doit posséder une **clé spécifique** sur son **Secteur 1**. Sans cette clé, la Boks ignore le badge.

*   **Clé A (Secteur 1) :** `873D9EF6C1A0`

---

## Procédure pas à pas (avec MCT)

### Étape 1 : Ajouter la Clé dans MCT

1.  Lancez **Mifare Classic Tool**.
2.  Allez dans **"Edit/Analyze Key File"**.
3.  Ouvrez le fichier `std.keys` (ou créez-en un nouveau).
4.  Ajoutez une nouvelle ligne avec la clé suivante :
    `873D9EF6C1A0`
5.  Appuyez sur l'icône **Disquette** pour sauvegarder.

### Étape 2 : Écrire la Clé sur le Badge

1.  Retournez au menu principal et choisissez **"Write Tag"**.
2.  Sélectionnez le mode **"Write Block"**.
3.  Dans le champ **Block Number**, entrez : **`7`**.
    *   *Pourquoi 7 ?* C'est le dernier bloc du Secteur 1, qui contient les clés d'accès.
4.  Dans le champ **Data (Hex)**, copiez-collez exactement ceci :
    `873D9EF6C1A07F078840FFFFFFFFFFFF`
    *   `873D9EF6C1A0` : La Clé A (User Scan).
    *   `7F078840` : Les permissions (Access Bits).
    *   `FFFFFFFFFFFF` : La Clé B (Défaut).
5.  Posez votre badge vierge sur le lecteur NFC de votre téléphone.
6.  Appuyez sur **"Write Block"**.
7.  MCT va vous demander quelles clés utiliser pour accéder au badge ("Map Keys to Sectors").
    *   Sélectionnez le fichier `std.keys` (qui contient `FFFFFFFFFFFF`, la clé par défaut des badges vierges).
    *   Lancez le mapping/écriture.
8.  Confirmez l'avertissement ("Writing to Sector Trailer...").

### Étape 3 : Vérifier le Badge

1.  Retournez au menu principal -> **"Read Tag"**.
2.  Scannez votre badge.
3.  Vérifiez le **Secteur 1** :
    *   Le **Bloc 5** (le deuxième du secteur 1) doit être vide (que des `00` ou `FF`, mais surtout **pas** `AA 07` au début).
    *   Si le bloc 5 contient `AA 07`, effacez-le (écrivez des `00` dans le bloc 5 via "Write Block"), sinon la Boks croira que c'est un badge La Poste !

---

## Utilisation avec Home Assistant

Une fois votre badge préparé :

1.  Dans Home Assistant, allez dans **Outils de développement** -> **Services**.
2.  Lancez le service `boks.nfc_scan_start`.
3.  Posez votre badge sur la Boks (la LED bleue clignote).
4.  Vous devriez recevoir une notification "Badge NFC Découvert" avec l'UID du badge (ex: `A1B2C3D4`).
5.  Utilisez le service `boks.nfc_register_tag` avec cet UID et un nom (ex: "Badge Papa") pour l'ajouter.
6.  C'est fini ! Votre badge ouvre maintenant la porte.
