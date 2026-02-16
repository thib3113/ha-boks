const CONFIG = {
    ...BOKS_PARAMS,
    boksService: "a7630001-f491-4f21-95ea-846ba586e361",
    dfuService: 0xFE59,
    batteryService: 0x180F,
    deviceInfoService: 0x180A,
    swRevChar: 0x2A28,
    hwRevChar: 0x2A26,
    batteryThreshold: 20
};

const DFU_ERRORS = {
    0x01: "Invalid Opcode",
    0x02: "Opcode not supported",
    0x03: "Invalid parameter",
    0x04: "Insufficient resources",
    0x05: "Invalid Object (Corrupt or wrong type)",
    0x07: "Unsupported type",
    0x08: "Operation not permitted (Wrong state)",
    0x0A: "Payload size exceeded",
    0x0B: "Hash failed (Integrity error)",
    0x0C: "Signature failed (Authentication error)",
    0x0D: "Hardware version error (Wrong firmware for this PCB)",
    0x0E: "Software version error (Downgrade blocked)"
};

const elements = {
    btnConnect: document.getElementById('btn-connect'),
    btnStart: document.getElementById('btn-start'),
    status: document.getElementById('status-text'),
    progressSent: document.getElementById('progress-sent'),
    progressSentText: document.getElementById('progress-sent-text'),
    progressVal: document.getElementById('progress-fill'),
    progressValText: document.getElementById('progress-text'),
    logs: document.getElementById('log-container'),
    httpsWarning: document.getElementById('https-warning'),
    deviceInfo: document.getElementById('device-info'),
    infoName: document.getElementById('info-name'),
    infoBattery: document.getElementById('info-battery'),
    infoVersion: document.getElementById('info-version'),
    infoHw: document.getElementById('info-hw'),
    instruction: document.getElementById('instruction-text'),
    actionArea: document.getElementById('action-area'),
    btnFinalize: document.getElementById('btn-finalize'),
    btnDisconnect: document.getElementById('btn-disconnect'),
    btnClear: document.getElementById('btn-clear'),
    explanation: document.getElementById('dfu-explanation'),
    backupLink: document.getElementById('ui-backup-link'), topDownloadLink: document.getElementById('ui-top-download-link')
};

let firmwareBlob = null;
let bluetoothDevice = null;
let isDfuModeActive = false;
let isFlashing = false;

window.addEventListener('beforeunload', (e) => {
    if (isFlashing) {
        const msg = "Flash in progress! Leaving this page may permanently damage your Boks.";
        e.preventDefault();
        e.returnValue = msg;
        return msg;
    }
});

function updateUIStrings() {
    if (elements.topDownloadLink) { elements.topDownloadLink.textContent = t('download_short'); elements.topDownloadLink.href = CONFIG.firmwareFile; }
    document.title = t('title');
    document.getElementById('ui-title').textContent = t('title');
    document.getElementById('ui-version-badge').textContent = t('target_version', { version: CONFIG.targetVersion });
    document.getElementById('ui-https-title').textContent = t('https_title');
    document.getElementById('ui-https-msg').textContent = t('https_msg');
    document.getElementById('ui-download-link').textContent = t('download_link');
    document.getElementById('ui-download-link').href = CONFIG.firmwareFile;

    if (elements.backupLink) {
        /* 
        const backupUrl = new URL("https://thib3113.github.io/bwb/index.html");
        // Add page target for the SPA router
        backupUrl.searchParams.set("page", "update");
        // Add query parameters for validation on the remote tool
        backupUrl.searchParams.set("target_pcb", CONFIG.expectedHw);
        backupUrl.searchParams.set("target_software", CONFIG.targetVersion);
        backupUrl.searchParams.set("target_internal_rev", CONFIG.expectedInternalRev);
        
        elements.backupLink.textContent = t('backup_link');
        elements.backupLink.href = backupUrl.toString();
        */
        elements.backupLink.textContent = t('backup_not_ready');
        elements.backupLink.style.color = "var(--text-secondary)";
        elements.backupLink.style.cursor = "default";
        elements.backupLink.onclick = (e) => e.preventDefault();
    }

    document.getElementById('ui-label-name').textContent = t('label_name');
    document.getElementById('ui-label-battery').textContent = t('label_battery');
    document.getElementById('ui-label-version').textContent = t('label_version');
    document.getElementById('ui-label-hw').textContent = t('label_hw');
    
    if (elements.explanation) elements.explanation.innerHTML = t('dfu_explanation');

    elements.btnConnect.textContent = t('btn_connect');
    elements.instruction.textContent = t('step_1');
    elements.status.textContent = t('status_ready');
}

function buf2hex(buffer) {
    return Array.prototype.map.call(new Uint8Array(buffer), x => ('00' + x.toString(16)).slice(-2)).join(' ');
}

async function debugWrite(characteristic, value, label) {
    const hex = buf2hex(value.buffer || value);
    log(`[BLE TX] ${label}: ${hex}`, 'info');
    return await characteristic.writeValue(value);
}

async function debugRead(characteristic, label) {
    const value = await characteristic.readValue();
    log(`[BLE RX] ${label}: ${buf2hex(value.buffer)}`, 'info');
    return value;
}

function log(msg, level = 'info') {
    const div = document.createElement('div');
    div.className = `log-entry ${level}`;
    const timestamp = new Date().toLocaleTimeString();
    
    let text = "";
    if (typeof msg === 'string') text = msg;
    else if (msg && msg.message) text = msg.message;
    else if (msg) text = JSON.stringify(msg);
    else text = "Log event";

    div.textContent = `[${timestamp}] ${text}`;
    elements.logs.appendChild(div);
    elements.logs.scrollTop = elements.logs.scrollHeight;
    console.log(`[${level.toUpperCase()}] ${text}`);
}

function setStatus(msg, type = '') {
    elements.status.textContent = msg;
    elements.status.className = 'status ' + type;
}

async function loadFirmware() {
    if (firmwareBlob) return;
    try {
        const response = await fetch(CONFIG.firmwareFile);
        firmwareBlob = await response.arrayBuffer();
        log(`Firmware loaded: ${firmwareBlob.byteLength} bytes`);
    } catch (e) { 
        setStatus(t('error_fw'), "error");
        log(`Failed to load firmware: ${e.message}`, 'error');
    }
}

async function readInfo(server) {
    elements.deviceInfo.classList.remove('hidden');
    const deviceName = bluetoothDevice.name || "Unknown";
    if (deviceName.includes("DfuTarg")) {
        elements.infoName.textContent = t('device_in_dfu');
        elements.infoName.className = "info-value val-error";
        isDfuModeActive = true;
    } else {
        elements.infoName.textContent = deviceName;
        elements.infoName.className = "info-value";
        isDfuModeActive = false;
    }
    
    let batteryOk = true;
    let versionMatch = false;
    let hwOk = true;

    try {
        const batSvc = await server.getPrimaryService(CONFIG.batteryService);
        const batChar = await batSvc.getCharacteristic(0x2A19);
        const val = await debugRead(batChar, "Battery");
        const level = val.getUint8(0);
        elements.infoBattery.textContent = `${level}%`;
        if (level < CONFIG.batteryThreshold) {
            elements.infoBattery.className = "info-value val-error";
            batteryOk = false;
        }
    } catch(e) { 
        elements.infoBattery.textContent = "N/A";
        log("Battery info unavailable", isDfuModeActive ? 'debug' : 'info');
    }
    
    try {
        const infoSvc = await server.getPrimaryService(CONFIG.deviceInfoService);
        const swChar = await infoSvc.getCharacteristic(CONFIG.swRevChar);
        const val = await debugRead(swChar, "SW Version");
        const currentVer = new TextDecoder().decode(val).trim();
        elements.infoVersion.textContent = currentVer;
        if (currentVer === CONFIG.targetVersion) versionMatch = true;
    } catch(e) { 
        elements.infoVersion.textContent = t('dfu_unknown');
    }

    try {
        const infoSvc = await server.getPrimaryService(CONFIG.deviceInfoService);
        const hwChar = await infoSvc.getCharacteristic(CONFIG.hwRevChar);
        const val = await debugRead(hwChar, "HW Version");
        const currentHw = new TextDecoder().decode(val).trim();
        elements.infoHw.textContent = `${CONFIG.expectedHw} (${currentHw})`;
        if (currentHw !== CONFIG.expectedInternalRev) hwOk = false;
    } catch(e) { 
        if (!isDfuModeActive) {
            elements.infoHw.textContent = CONFIG.expectedHw + " (?)";
        }
    }

    return { batteryOk, versionMatch, hwOk };
}

async function connect() {
    try {
        elements.btnConnect.disabled = true;
        setStatus(t('status_searching'), "active");

        const device = await navigator.bluetooth.requestDevice({
            filters: [{ services: [CONFIG.boksService] }, { services: [CONFIG.dfuService] }],
            optionalServices: [CONFIG.boksService, CONFIG.dfuService, CONFIG.batteryService, CONFIG.deviceInfoService]
        });

        log(`Connected to ${device.name}`);
        bluetoothDevice = device;
        const server = await device.gatt.connect();

        let isRealDfu = false;
        let isButtonless = false;

        try {
            const dfuSvc = await server.getPrimaryService(CONFIG.dfuService);
            const chars = await dfuSvc.getCharacteristics();
            isRealDfu = chars.length > 1;
            isButtonless = chars.length === 1;
        } catch(e) {}

        const checks = await readInfo(server);
        elements.btnConnect.classList.add('hidden');
        elements.btnStart.classList.remove('hidden');
        elements.btnStart.disabled = false;

        if (isRealDfu) {
            log("Real DFU mode detected.");
            setStatus(t('step_3'), "success");
            elements.instruction.textContent = t('step_3');
            elements.btnStart.textContent = t('btn_flash');
            elements.btnStart.onclick = performFlash;
        } else {
            if (!checks.hwOk || !checks.batteryOk) {
                setStatus("Compatibility issue", "error");
                elements.btnStart.disabled = true;
                return;
            }

            if (isButtonless) {
                setStatus(t('status_preparing'), "active");
                elements.instruction.textContent = t('step_2');
                elements.btnStart.textContent = t('btn_prepare');
                elements.btnStart.onclick = startAction;
            } else {
                if (checks.versionMatch) setStatus(t('warn_already_updated'), "active");
                elements.instruction.textContent = t('step_1');
                elements.btnStart.textContent = t('btn_prepare');
                elements.btnStart.onclick = startAction;
            }
        }
    } catch (e) {
        log(`Connection error: ${e.message}`, 'error');
        setStatus("Bluetooth error", "error");
        elements.btnConnect.disabled = false;
    }
}

async function startAction() {
    try {
        elements.btnStart.disabled = true;
        const server = await bluetoothDevice.gatt.connect();
        const dfuSvc = await server.getPrimaryService(CONFIG.dfuService);
        const chars = await dfuSvc.getCharacteristics();

        if (chars.length === 1) {
            log("Triggering DFU reboot...");
            const chr = chars[0];
            await chr.startNotifications();
            await debugWrite(chr, new Uint8Array([0x01]), "Enter Bootloader");
            setStatus(t('status_preparing'), "active");
            elements.instruction.textContent = t('reboot_wait');
            elements.btnConnect.textContent = t('btn_reconnect');
            elements.btnConnect.classList.remove('hidden');
            elements.btnConnect.disabled = false;
            elements.btnStart.classList.add('hidden');
        } else {
            await performFlash();
        }
    } catch (e) { 
        log(`Failed: ${e.message}`, 'error');
        setStatus("Error: " + e.message, "error"); 
        elements.btnStart.disabled = false; 
    }
}

async function performFlash() {
    try {
        isFlashing = true;
        elements.btnStart.disabled = true;
        elements.progressSent.style.width = '0%';
        elements.progressVal.style.width = '0%';
        if (elements.explanation) elements.explanation.classList.remove('hidden');
        setStatus("Initializing flash...", "active");
        
        const pkg = new SecureDfuPackage(firmwareBlob);
        await pkg.load();
        const image = await pkg.getAppImage() || await pkg.getBaseImage();
        
        log(`Flash ready: ${image.type} (${image.imageData.byteLength} bytes)`);

        const strategies = [
            { prn: 20, packetSize: 120, name: "Turbo", maxRetries: 3 },
            { prn: 10, packetSize: 60, name: "Standard", maxRetries: 2 },
            { prn: 1, packetSize: 20, name: "Safe", maxRetries: 1 }
        ];

        for (const strategy of strategies) {
            for (let attempt = 1; attempt <= strategy.maxRetries; attempt++) {
                try {
                    const attemptInfo = strategy.maxRetries > 1 ? ` (Attempt ${attempt}/${strategy.maxRetries})` : "";
                    log(`Attempting flash with strategy: ${strategy.name}${attemptInfo} [PRN=${strategy.prn}, MTU=${strategy.packetSize}]`);
                    
                    // Re-instantiate DFU for each attempt to clear internal state
                    const dfu = new SecureDfu();
                    dfu.packetReceiptNotification = strategy.prn; 
                    dfu.packetSize = strategy.packetSize;
                    dfu.forceRestart = true; 

                    dfu.addEventListener('log', e => {
                        const msg = e.message || String(e);
                        let enhancedMsg = msg;
                        if (msg.includes('error 0x')) {
                            const match = msg.match(/0x([0-9A-Fa-f]+)/);
                            if (match) {
                                const code = parseInt(match[1], 16);
                                if (DFU_ERRORS[code]) enhancedMsg += ` (${DFU_ERRORS[code]})`;
                            }
                        }
                        log(`[DFU SDK] ${enhancedMsg}`, enhancedMsg.toLowerCase().includes('failed') ? 'warning' : 'debug');
                    });

                    dfu.addEventListener('progress', e => {
                        const total = e.totalBytes || image.imageData.byteLength;
                        const pSent = (e.sentBytes / total) * 100;
                        const pVal = (e.validatedBytes / total) * 100;

                        elements.progressSent.style.width = `${pSent}%`;
                        elements.progressSentText.textContent = `${Math.round(pSent)}%`;
                        elements.progressVal.style.width = `${pVal}%`;
                        elements.progressValText.textContent = `${Math.round(pVal)}%`;
                        
                        if (pVal < 100) {
                            setStatus(`Flashing: ${Math.round(pVal)}%`);
                        } else {
                            setStatus("100% - Finishing up...", "active");
                        }
                    });

                    if (bluetoothDevice && !bluetoothDevice.gatt.connected) {
                         log("Reconnecting...");
                         await new Promise(r => setTimeout(r, 1000));
                    }

                    await dfu.update(bluetoothDevice, image.initData, image.imageData);
                    
                    log("Flash successful! Rebooting device...");
                    setStatus(t('status_success'), "success");
                    elements.instruction.textContent = t('reboot_manual');
                    elements.btnStart.classList.add('hidden');

                    if (bluetoothDevice && bluetoothDevice.gatt.connected) {
                        log("Disconnecting...", "info");
                        await bluetoothDevice.gatt.disconnect();
                    }
                    return; // EXIT SUCCESS

                } catch (e) {
                    let errorMsg = e.message || String(e);
                    log(`Strategy ${strategy.name} attempt ${attempt} failed: ${errorMsg}`, 'warning');
                    
                    // Force disconnect between attempts
                    if (bluetoothDevice && bluetoothDevice.gatt.connected) {
                        try { await bluetoothDevice.gatt.disconnect(); } catch(err) {}
                    }

                    if (attempt < strategy.maxRetries) {
                        setStatus(`Retrying in ${strategy.name} mode...`, "warning");
                        await new Promise(r => setTimeout(r, 2000));
                    } else if (strategy === strategies[strategies.length - 1]) {
                        throw e; // No more strategies left
                    } else {
                        setStatus(`Switching to ${strategies[strategies.indexOf(strategy)+1].name} mode...`, "warning");
                        await new Promise(r => setTimeout(r, 2000));
                    }
                }
            }
        }

    } catch (e) { 
        let errorMsg = e.message || String(e);
        if (errorMsg.includes('0x')) {
            const match = errorMsg.match(/0x([0-9A-Fa-f]+)/);
            if (match) {
                const code = parseInt(match[1], 16);
                if (DFU_ERRORS[code]) errorMsg += ` (${DFU_ERRORS[code]})`;
            }
        }
        log(`FLASH FAILED: ${errorMsg}`, 'error');
        setStatus("Error: " + errorMsg, "error"); 
        elements.btnStart.disabled = false;
        elements.actionArea.classList.remove('hidden');
    } finally {
        isFlashing = false;
    }
}

async function sendDfuRaw(opcode, label) {
    try {
        log(`Sending manual opcode ${label}...`);
        const server = await bluetoothDevice.gatt.connect();
        const svc = await server.getPrimaryService(CONFIG.dfuService);
        const chars = await svc.getCharacteristics();
        const cpChar = chars.find(c => c.properties.write || c.uuid.includes('8ec90001'));
        if (cpChar) {
            await debugWrite(cpChar, new Uint8Array([opcode]), label);
            log(`Success: ${label} sent.`);
        } else throw new Error("Control Point not found");
    } catch (e) { log(`Error ${label}: ${e.message}`, 'error'); }
}

elements.btnConnect.addEventListener('click', connect);
elements.btnFinalize.onclick = () => sendDfuRaw(0x04, "Manual Execute");
elements.btnDisconnect.onclick = async () => {
    if (bluetoothDevice && bluetoothDevice.gatt.connected) {
        log("Force disconnection...");
        await bluetoothDevice.gatt.disconnect();
    }
};
elements.btnClear.onclick = async () => {
    log("Resetting DFU cache...", "warning");
    try { await sendDfuRaw(0x04, "Reset State"); } catch(e) {}
    if (bluetoothDevice) await bluetoothDevice.gatt.disconnect();
};

updateUIStrings();

if (window.isSecureContext && navigator.bluetooth) {
    elements.mainInterface = document.getElementById('main-interface');
    if (elements.mainInterface) elements.mainInterface.classList.remove('hidden');
    loadFirmware();
} else {
    elements.httpsWarning.classList.remove('hidden');
    // Ensure it's very visible
    elements.httpsWarning.style.border = "2px solid var(--error-color)";
    elements.httpsWarning.style.backgroundColor = "#ffebee";
    
    if (!window.isSecureContext) {
        log("NOT A SECURE CONTEXT: Web Bluetooth is disabled by the browser.", 'error');
    } else {
        log("Web Bluetooth is not available in this browser.", 'error');
    }
}