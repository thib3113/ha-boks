"""Boks PIN Generator Algorithm."""
import logging
import struct

from ..errors import BoksError

_LOGGER = logging.getLogger(__name__)

# Constants from @retro/firmware/boks_pin_algorithm.md
# IV SHA-256 used instead of standard BLAKE2s IV
IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
]

# Standard Sigma permutation table
SIGMA = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    [14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3],
    [11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4],
    [7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8],
    [9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13],
    [2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9],
    [12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11],
    [13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10],
    [6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5],
    [10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0]
]


class BoksPinGenerator:
    """Class to generate Boks PIN codes."""

    def __init__(self, master_key: str | None):
        """Initialize the generator with a master key."""
        self.master_key = master_key

    def _g(self, v, a, b, c, d, x, y):
        """Mixing function G."""
        v[a] = (v[a] + v[b] + x) & 0xFFFFFFFF
        v[d] = (((v[d] ^ v[a]) >> 16) | ((v[d] ^ v[a]) << 16)) & 0xFFFFFFFF
        v[c] = (v[c] + v[d]) & 0xFFFFFFFF
        v[b] = (((v[b] ^ v[c]) >> 12) | ((v[b] ^ v[c]) << 20)) & 0xFFFFFFFF
        v[a] = (v[a] + v[b] + y) & 0xFFFFFFFF
        v[d] = (((v[d] ^ v[a]) >> 8) | ((v[d] ^ v[a]) << 24)) & 0xFFFFFFFF
        v[c] = (v[c] + v[d]) & 0xFFFFFFFF
        v[b] = (((v[b] ^ v[c]) >> 7) | ((v[b] ^ v[c]) << 25)) & 0xFFFFFFFF

    def _compress(self, h, chunk, t0, f0):
        """Compression function (Custom variant)."""
        # Initialize work vector v
        v = list(h) + list(IV)

        v[12] ^= t0 & 0xFFFFFFFF
        v[14] ^= f0 & 0xFFFFFFFF

        m = struct.unpack('<16I', chunk)

        for i in range(10):
            s = SIGMA[i]
            self._g(v, 0, 4, 8, 12, m[s[0]], m[s[1]])
            self._g(v, 1, 5, 9, 13, m[s[2]], m[s[3]])
            self._g(v, 2, 6, 10, 14, m[s[4]], m[s[5]])
            self._g(v, 3, 7, 11, 15, m[s[6]], m[s[7]])
            self._g(v, 0, 5, 10, 15, m[s[8]], m[s[9]])
            self._g(v, 1, 6, 11, 12, m[s[10]], m[s[11]])
            self._g(v, 2, 7, 8, 13, m[s[12]], m[s[13]])
            self._g(v, 3, 4, 9, 14, m[s[14]], m[s[15]])

        for i in range(8):
            h[i] ^= v[i] ^ v[i+8]

        return h

    def generate_pin(self, pin_type: str, index: int) -> str:
        """Generate a PIN code.

        :param pin_type: 'master', 'single', or 'multi'
        :param index: The index to generate
        :return: 6-character PIN string
        :raises BoksError: If master key is missing or invalid
        """
        if not self.master_key:
            raise BoksError("master_key_required")

        try:
            key_bytes = bytes.fromhex(self.master_key)
            if len(key_bytes) != 32:
                # Try to handle potential spaces or formatting issues if user pasted it
                clean_key = self.master_key.replace(" ", "").replace("-", "")
                key_bytes = bytes.fromhex(clean_key)
                if len(key_bytes) != 32:
                    raise ValueError("Invalid key length")
        except ValueError as err:
            raise BoksError("master_key_invalid") from err

        type_map = {
            "master": "master",
            "single": "single-use",
            "multi": "multi-use"
        }

        prefix = type_map.get(pin_type, pin_type)

        # Valid prefixes check? The algorithm supports whatever string is passed.
        # But for safety we might want to restrict it. The map handles the common cases.

        h = list(IV)

        # Initial XOR with metadata
        h[0] ^= 0x01012006

        # Block 1: The Key
        block1 = key_bytes + b'\x00' * 32
        h = self._compress(h, block1, 64, 0)

        # Block 2: The Message
        msg = f"{prefix} {index}".encode()

        # Pad with null bytes to 64 bytes
        block2 = msg + b'\x00' * (64 - len(msg))

        h = self._compress(h, block2, 64 + len(msg), 0xFFFFFFFF)

        # Extract first 6 bytes
        res = b"".join(struct.pack('<I', x) for x in h)[:6]

        # Convert to Boks charset
        charset = "0123456789AB"
        pin = "".join(charset[b % 12] for b in res)

        return pin
