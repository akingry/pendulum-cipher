"""
Pendulum Cipher - Chaos-Based Encryption

Uses two deterministic double pendulums to generate a keystream.
Same key → same initial conditions → same stream → reversible XOR encryption.

This is a learning tool demonstrating chaos-based cryptography.
Not recommended for actual secrets (use AES instead).
"""

import numpy as np
from scipy.integrate import odeint
import hashlib
import argparse
import os
import sys

# Constants
G = 9.81


class DoublePendulum:
    """Deterministic double pendulum simulation."""
    
    def __init__(self, L1, L2, m1, m2, theta1, theta2, omega1, omega2):
        self.L1 = L1
        self.L2 = L2
        self.m1 = m1
        self.m2 = m2
        self.state = np.array([theta1, omega1, theta2, omega2], dtype=np.float64)
        
    def derivatives(self, state, t):
        theta1, omega1, theta2, omega2 = state
        L1, L2, m1, m2 = self.L1, self.L2, self.m1, self.m2
        
        delta = theta2 - theta1
        den1 = (m1 + m2) * L1 - m2 * L1 * np.cos(delta) ** 2
        den2 = (L2 / L1) * den1
        
        alpha1 = (m2 * L1 * omega1**2 * np.sin(delta) * np.cos(delta) +
                  m2 * G * np.sin(theta2) * np.cos(delta) +
                  m2 * L2 * omega2**2 * np.sin(delta) -
                  (m1 + m2) * G * np.sin(theta1)) / den1
        
        alpha2 = (-m2 * L2 * omega2**2 * np.sin(delta) * np.cos(delta) +
                  (m1 + m2) * G * np.sin(theta1) * np.cos(delta) -
                  (m1 + m2) * L1 * omega1**2 * np.sin(delta) -
                  (m1 + m2) * G * np.sin(theta2)) / den2
        
        return np.array([omega1, alpha1, omega2, alpha2])
    
    def step(self, dt):
        t = np.array([0, dt])
        result = odeint(self.derivatives, self.state, t)
        self.state = result[1]
    
    def get_state_bytes(self):
        """Convert current state to bytes for hashing."""
        return self.state.tobytes()


class PendulumCipher:
    """Encryption system using chaotic double pendulums."""
    
    def __init__(self, key: str):
        """Initialize cipher with a password/key."""
        self.key = key
        self.pendulum1, self.pendulum2 = self._derive_pendulums(key)
        self.dt = 0.001  # Simulation timestep
        self.time = 0.0
        
    def _derive_pendulums(self, key: str):
        """
        Derive pendulum initial conditions from the key.
        Uses SHA-512 to get enough bytes for all parameters.
        """
        # Hash the key to get deterministic bytes
        key_bytes = hashlib.sha512(key.encode('utf-8')).digest()
        
        # Split into values (0.0 to 1.0 range)
        def bytes_to_float(b1, b2):
            """Convert 2 bytes to a float in [0, 1)."""
            return ((b1 << 8) | b2) / 65536.0
        
        # Extract 16 parameters from 32 bytes
        params = []
        for i in range(16):
            params.append(bytes_to_float(key_bytes[i*2], key_bytes[i*2 + 1]))
        
        # Pendulum 1 parameters
        L1_1 = 0.8 + params[0] * 0.8    # Length 1: 0.8 to 1.6
        L2_1 = 0.8 + params[1] * 0.8    # Length 2: 0.8 to 1.6
        m1_1 = 0.5 + params[2] * 1.5    # Mass 1: 0.5 to 2.0
        m2_1 = 0.5 + params[3] * 1.5    # Mass 2: 0.5 to 2.0
        theta1_1 = np.pi * (0.2 + params[4] * 0.6)   # Angle 1: 0.2π to 0.8π
        theta2_1 = np.pi * (0.2 + params[5] * 0.6)   # Angle 2: 0.2π to 0.8π
        omega1_1 = (params[6] - 0.5) * 2.0   # Velocity: -1 to 1
        omega2_1 = (params[7] - 0.5) * 2.0
        
        # Pendulum 2 parameters
        L1_2 = 0.8 + params[8] * 0.8
        L2_2 = 0.8 + params[9] * 0.8
        m1_2 = 0.5 + params[10] * 1.5
        m2_2 = 0.5 + params[11] * 1.5
        theta1_2 = np.pi * (0.2 + params[12] * 0.6)
        theta2_2 = np.pi * (0.2 + params[13] * 0.6)
        omega1_2 = (params[14] - 0.5) * 2.0
        omega2_2 = (params[15] - 0.5) * 2.0
        
        p1 = DoublePendulum(L1_1, L2_1, m1_1, m2_1, theta1_1, theta2_1, omega1_1, omega2_1)
        p2 = DoublePendulum(L1_2, L2_2, m1_2, m2_2, theta1_2, theta2_2, omega1_2, omega2_2)
        
        return p1, p2
    
    def _generate_keystream_block(self):
        """
        Generate 32 bytes of keystream by stepping the simulation
        and hashing the combined state.
        """
        # Step both pendulums
        self.pendulum1.step(self.dt)
        self.pendulum2.step(self.dt)
        self.time += self.dt
        
        # Combine states with time
        state_data = (
            self.pendulum1.get_state_bytes() +
            self.pendulum2.get_state_bytes() +
            np.array([self.time], dtype=np.float64).tobytes()
        )
        
        # Hash to produce keystream block
        return hashlib.sha256(state_data).digest()
    
    def generate_keystream(self, length: int) -> bytes:
        """Generate `length` bytes of keystream."""
        stream = bytearray()
        while len(stream) < length:
            block = self._generate_keystream_block()
            stream.extend(block)
        return bytes(stream[:length])
    
    def reset(self):
        """Reset pendulums to initial state (for decryption)."""
        self.pendulum1, self.pendulum2 = self._derive_pendulums(self.key)
        self.time = 0.0
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt bytes using XOR with keystream."""
        self.reset()
        keystream = self.generate_keystream(len(plaintext))
        ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream))
        return ciphertext
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt bytes using XOR with keystream (same operation as encrypt)."""
        self.reset()
        keystream = self.generate_keystream(len(ciphertext))
        plaintext = bytes(c ^ k for c, k in zip(ciphertext, keystream))
        return plaintext


def encrypt_text(plaintext: str, key: str) -> str:
    """Encrypt a string, return hex-encoded ciphertext."""
    cipher = PendulumCipher(key)
    ciphertext = cipher.encrypt(plaintext.encode('utf-8'))
    return ciphertext.hex()


def decrypt_text(ciphertext_hex: str, key: str) -> str:
    """Decrypt hex-encoded ciphertext, return plaintext string."""
    cipher = PendulumCipher(key)
    ciphertext = bytes.fromhex(ciphertext_hex)
    plaintext = cipher.decrypt(ciphertext)
    return plaintext.decode('utf-8')


def encrypt_file(input_path: str, output_path: str, key: str):
    """Encrypt a file."""
    cipher = PendulumCipher(key)
    with open(input_path, 'rb') as f:
        plaintext = f.read()
    ciphertext = cipher.encrypt(plaintext)
    with open(output_path, 'wb') as f:
        f.write(ciphertext)
    return len(plaintext)


def decrypt_file(input_path: str, output_path: str, key: str):
    """Decrypt a file."""
    cipher = PendulumCipher(key)
    with open(input_path, 'rb') as f:
        ciphertext = f.read()
    plaintext = cipher.decrypt(ciphertext)
    with open(output_path, 'wb') as f:
        f.write(plaintext)
    return len(ciphertext)


def demo():
    """Run a demonstration of the cipher."""
    print("=" * 60)
    print("PENDULUM CIPHER DEMONSTRATION")
    print("=" * 60)
    print()
    
    key = "MySecretKey123"
    message = "Hello, World! This is a secret message encrypted with chaos."
    
    print(f"Key:       '{key}'")
    print(f"Plaintext: '{message}'")
    print()
    
    # Show keystream generation
    cipher = PendulumCipher(key)
    print("Pendulum 1 initial state:")
    print(f"  θ1={cipher.pendulum1.state[0]:.6f}, ω1={cipher.pendulum1.state[1]:.6f}")
    print(f"  θ2={cipher.pendulum1.state[2]:.6f}, ω2={cipher.pendulum1.state[3]:.6f}")
    print()
    print("Pendulum 2 initial state:")
    print(f"  θ1={cipher.pendulum2.state[0]:.6f}, ω1={cipher.pendulum2.state[1]:.6f}")
    print(f"  θ2={cipher.pendulum2.state[2]:.6f}, ω2={cipher.pendulum2.state[3]:.6f}")
    print()
    
    # Encrypt
    ciphertext_hex = encrypt_text(message, key)
    print(f"Ciphertext (hex):")
    # Print in rows of 32 chars
    for i in range(0, len(ciphertext_hex), 48):
        print(f"  {ciphertext_hex[i:i+48]}")
    print()
    
    # Decrypt
    decrypted = decrypt_text(ciphertext_hex, key)
    print(f"Decrypted: '{decrypted}'")
    print()
    
    # Verify
    if decrypted == message:
        print("✓ SUCCESS: Decryption matches original!")
    else:
        print("✗ ERROR: Decryption failed!")
    print()
    
    # Show what happens with wrong key
    print("-" * 60)
    print("Attempting decryption with WRONG key...")
    wrong_key = "WrongKey456"
    try:
        wrong_decrypt = decrypt_text(ciphertext_hex, wrong_key)
        print(f"Wrong key result: '{wrong_decrypt[:50]}...' (gibberish)")
    except:
        print("Wrong key result: <decode error - binary garbage>")
    print()
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Pendulum Cipher - Chaos-based encryption using double pendulums",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pendulum_cipher.py --demo
  python pendulum_cipher.py -e -t "Secret message" -k "mypassword"
  python pendulum_cipher.py -d -t "a1b2c3..." -k "mypassword"
  python pendulum_cipher.py -e -f secret.txt -o secret.enc -k "mypassword"
  python pendulum_cipher.py -d -f secret.enc -o secret.txt -k "mypassword"
        """
    )
    
    parser.add_argument('--demo', action='store_true', help='Run demonstration')
    parser.add_argument('-e', '--encrypt', action='store_true', help='Encrypt mode')
    parser.add_argument('-d', '--decrypt', action='store_true', help='Decrypt mode')
    parser.add_argument('-t', '--text', type=str, help='Text to encrypt/decrypt (hex for decrypt)')
    parser.add_argument('-f', '--file', type=str, help='Input file path')
    parser.add_argument('-o', '--output', type=str, help='Output file path')
    parser.add_argument('-k', '--key', type=str, help='Encryption/decryption key')
    
    args = parser.parse_args()
    
    if args.demo:
        demo()
        return
    
    if not args.key:
        print("Error: Key (-k) is required for encryption/decryption")
        sys.exit(1)
    
    if args.encrypt:
        if args.text:
            result = encrypt_text(args.text, args.key)
            print(f"Ciphertext (hex): {result}")
        elif args.file:
            if not args.output:
                args.output = args.file + ".enc"
            size = encrypt_file(args.file, args.output, args.key)
            print(f"Encrypted {size} bytes -> {args.output}")
        else:
            print("Error: Provide --text or --file to encrypt")
            sys.exit(1)
            
    elif args.decrypt:
        if args.text:
            result = decrypt_text(args.text, args.key)
            print(f"Plaintext: {result}")
        elif args.file:
            if not args.output:
                args.output = args.file.replace('.enc', '.dec')
            size = decrypt_file(args.file, args.output, args.key)
            print(f"Decrypted {size} bytes -> {args.output}")
        else:
            print("Error: Provide --text or --file to decrypt")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
