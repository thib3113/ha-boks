import getpass
import logging
import random
import sys

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_LOGGER = logging.getLogger(__name__)

# --- Constants ---
FIREBASE_API_KEY = "AIzaSyCCFV6WH7Wa4oZlwdmHrTcq-YbVR6or7qo"
BOKS_API_BASE_URL = "https://api.boks.app"
APP_VERSION = "19.9.1"
APP_PACKAGE_NAME = "com.boks.app"

FIREBASE_AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

# Common Mobile User Agents with their Chrome Major Version
USER_AGENTS = [
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; CPH2581 Build/UKQ1.230924.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.81 Mobile Safari/537.36",
        "version": "131"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; CPH2449 Build/UKQ1.230924.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.102 Mobile Safari/537.36",
        "version": "130"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; CPH2491 Build/TP1A.220905.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.88 Mobile Safari/537.36",
        "version": "128"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; CPH2551 Build/UKQ1.230924.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.39 Mobile Safari/537.36",
        "version": "131"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; 23127PN0CG Build/UKQ1.230804.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.81 Mobile Safari/537.36",
        "version": "131"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; 23090RA98G Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.6668.100 Mobile Safari/537.36",
        "version": "129"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; 23049PCD8G Build/UKQ1.230804.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.58 Mobile Safari/537.36",
        "version": "130"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; 2306EP901G Build/UKQ1.230804.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.81 Mobile Safari/537.36",
        "version": "131"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 15; Pixel 9 Pro Build/AP1A.240405.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/132.0.6800.0 Mobile Safari/537.36",
        "version": "132"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; Pixel 7a Build/UQ1A.240105.004; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.6668.70 Mobile Safari/537.36",
        "version": "129"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; motorola edge 40 Build/T1TL33.1-44-6; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.127 Mobile Safari/537.36",
        "version": "128"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; XQ-DQ72 Build/67.1.A.2.112; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.102 Mobile Safari/537.36",
        "version": "130"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; CPH2305 Build/TP1A.220905.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/127.0.6533.103 Mobile Safari/537.36",
        "version": "127"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.81 Mobile Safari/537.36",
        "version": "131"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 15; Pixel 8 Build/AP1A.240405.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.102 Mobile Safari/537.36",
        "version": "130"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 14; SM-A546B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.6668.100 Mobile Safari/537.36",
        "version": "129"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 13; 2312DRA50G Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.88 Mobile Safari/537.36",
        "version": "128"
    },
    {
        "ua": "Mozilla/5.0 (Linux; Android 12; SM-G991B Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
        "version": "91"
    }
]

class BoksClient:
    def __init__(self):
        self.session = requests.Session()
        selected_agent = random.choice(USER_AGENTS)
        self.user_agent = selected_agent["ua"]
        self.chrome_version = selected_agent["version"]

        _LOGGER.info("Using User-Agent: %s", self.user_agent)
        _LOGGER.info("Detected Chrome Version: %s", self.chrome_version)

        self.session.headers.update({
            "Connection": "keep-alive",
            "sec-ch-ua-platform": "\"Android\"",
            "sec-ch-ua": f"\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"{self.chrome_version}\", \"Android WebView\";v=\"{self.chrome_version}\"",
            "sec-ch-ua-mobile": "?0",
            "App-Version": APP_VERSION,
            "source": "app",
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://localhost",
            "X-Requested-With": APP_PACKAGE_NAME,
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://localhost/",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def authenticate(self, email, password) -> str:
        """Authenticate with Firebase and return ID Token."""
        _LOGGER.info("Authenticating user: %s", email)
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            response = self.session.post(FIREBASE_AUTH_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            id_token = data.get("idToken")

            if not id_token:
                _LOGGER.error("No ID Token in response")
                sys.exit(1)

            self.session.headers["Authorization"] = f"Bearer {id_token}"
            _LOGGER.info("Authentication successful.")
            return id_token

        except requests.exceptions.RequestException as e:
            _LOGGER.error("Authentication failed: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                _LOGGER.error("Response: %s", e.response.text)
            sys.exit(1)

    def get_parcels_and_bokses(self) -> dict:
        """Call the parcelsAndBokses endpoint."""
        url = f"{BOKS_API_BASE_URL}/api/mobile/parcelsAndBokses"
        _LOGGER.info("Calling %s", url)

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _LOGGER.error("Failed to fetch parcels and bokses: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                _LOGGER.error("Response: %s", e.response.text)
            return {}

def main():
    email = input("Enter your Boks account email: ")
    password = getpass.getpass("Enter your Boks account password: ")

    client = BoksClient()
    client.authenticate(email, password)

    data = client.get_parcels_and_bokses()

    bokses = data.get("bokses", [])
    if not bokses:
        _LOGGER.warning("No Boks devices found in the account.")
        return

    print("\n--- Boks Devices Found ---")
    for boks in bokses:
        name = boks.get("name", "Unknown")
        boks_id = boks.get("id", "Unknown ID")
        mac = boks.get("macAddress", "Unknown MAC")

        pcb = boks.get("pcb", {})
        # Assuming configurationKey might be directly in the boks object or in the pcb object
        # Based on user info, it's in this endpoint's response.
        # We will dump the relevant part to look for it.

        # Check common places for config key
        config_key = boks.get("configurationKey")
        if not config_key and pcb:
             config_key = pcb.get("configurationKey")

        print(f"\nName: {name}")
        print(f"ID: {boks_id}")
        print(f"MAC: {mac}")

        if config_key:
            print(f"Configuration Key: {config_key}")
        else:
            print("Configuration Key: Not found or null in this response.")

        # Debug: print keys available in 'boks' to see if we missed something
        # _LOGGER.debug(f"Keys available in boks object: {list(boks.keys())}")
        # if pcb:
        #    _LOGGER.debug(f"Keys available in pcb object: {list(pcb.keys())}")

if __name__ == "__main__":
    main()
