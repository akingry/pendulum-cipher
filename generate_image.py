"""
Double Pendulum Random Image Generator

Generates a 1080x1080 image using random numbers from two chaotic double pendulums.
Each pixel's RGB values (0-255) come from the pendulum positions + elapsed time.
"""

import numpy as np
from scipy.integrate import odeint
from PIL import Image
import hashlib
import time
import os

# Constants
G = 9.81  # Gravity

class DoublePendulum:
    """Simulates a double pendulum using Lagrangian mechanics."""
    
    def __init__(self, L1=1.0, L2=1.0, m1=1.0, m2=1.0, theta1=np.pi/2, theta2=np.pi/2, 
                 omega1=0.0, omega2=0.0):
        self.L1 = L1
        self.L2 = L2
        self.m1 = m1
        self.m2 = m2
        self.state = np.array([theta1, omega1, theta2, omega2])
        
    def derivatives(self, state, t):
        """Compute derivatives for the double pendulum ODEs."""
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
        """Advance the simulation by dt seconds."""
        t = np.array([0, dt])
        result = odeint(self.derivatives, self.state, t)
        self.state = result[1]
    
    def get_bob2_position(self):
        """Get (x, y) of the second bob in meters."""
        theta1, _, theta2, _ = self.state
        x1 = self.L1 * np.sin(theta1)
        y1 = self.L1 * np.cos(theta1)
        x2 = x1 + self.L2 * np.sin(theta2)
        y2 = y1 + self.L2 * np.cos(theta2)
        return x2, y2


def generate_random_bytes(pendulum1, pendulum2, elapsed, num_bytes):
    """
    Generate random bytes using pendulum states and elapsed time.
    
    Uses SHA-256 to hash the combined state, then extracts bytes.
    For more bytes than 32, we iterate with a counter.
    """
    result = bytearray()
    counter = 0
    
    x1, y1 = pendulum1.get_bob2_position()
    x2, y2 = pendulum2.get_bob2_position()
    
    # Get all state variables for maximum entropy
    state1 = pendulum1.state
    state2 = pendulum2.state
    
    while len(result) < num_bytes:
        # Combine all values into entropy string
        entropy_string = f"{x1:.15f}{y1:.15f}{x2:.15f}{y2:.15f}{elapsed:.15f}"
        entropy_string += f"{state1[0]:.15f}{state1[1]:.15f}{state1[2]:.15f}{state1[3]:.15f}"
        entropy_string += f"{state2[0]:.15f}{state2[1]:.15f}{state2[2]:.15f}{state2[3]:.15f}"
        entropy_string += f"{counter}"
        
        # Hash and append
        hash_bytes = hashlib.sha256(entropy_string.encode()).digest()
        result.extend(hash_bytes)
        counter += 1
    
    return bytes(result[:num_bytes])


def generate_image(width=1080, height=1080, output_path=None):
    """
    Generate a random image using double pendulum chaos.
    
    Each pixel's R, G, B values (0-255) come from the pendulum system.
    """
    if output_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f"chaos_image_{timestamp}.png"
    
    print(f"Generating {width}x{height} image...")
    print("Initializing double pendulums...")
    
    # Create two pendulums with different initial conditions
    pendulum1 = DoublePendulum(
        L1=1.2, L2=1.0, m1=1.5, m2=1.0,
        theta1=np.pi * 0.75, theta2=np.pi * 0.5,
        omega1=0.1, omega2=0.0
    )
    
    pendulum2 = DoublePendulum(
        L1=1.0, L2=1.2, m1=1.0, m2=1.5,
        theta1=np.pi * 0.6, theta2=np.pi * 0.8,
        omega1=0.0, omega2=0.15
    )
    
    # Total bytes needed: width * height * 3 (RGB)
    total_pixels = width * height
    total_bytes = total_pixels * 3
    
    print(f"Generating {total_bytes:,} random bytes for {total_pixels:,} pixels...")
    
    # Create image array
    image_data = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Time step for simulation
    dt = 0.001  # 1ms steps for more chaos
    elapsed = 0.0
    
    # Generate pixels row by row
    start_time = time.time()
    
    for y in range(height):
        if y % 100 == 0:
            progress = (y / height) * 100
            print(f"  Progress: {progress:.1f}% (row {y}/{height})")
        
        # Step the simulation forward
        pendulum1.step(dt)
        pendulum2.step(dt)
        elapsed += dt
        
        # Generate bytes for this row (width * 3 bytes)
        row_bytes = generate_random_bytes(pendulum1, pendulum2, elapsed, width * 3)
        
        # Fill the row
        for x in range(width):
            idx = x * 3
            image_data[y, x, 0] = row_bytes[idx]      # R
            image_data[y, x, 1] = row_bytes[idx + 1]  # G
            image_data[y, x, 2] = row_bytes[idx + 2]  # B
        
        # Extra simulation steps between rows for more variation
        for _ in range(5):
            pendulum1.step(dt)
            pendulum2.step(dt)
            elapsed += dt
    
    generation_time = time.time() - start_time
    print(f"  Progress: 100.0% (row {height}/{height})")
    print(f"Generation complete in {generation_time:.2f} seconds")
    
    # Create and save image
    image = Image.fromarray(image_data, mode='RGB')
    image.save(output_path)
    
    print(f"Image saved to: {output_path}")
    print(f"Final simulation time: {elapsed:.3f} seconds")
    
    return output_path


if __name__ == "__main__":
    import sys
    
    # Allow custom output path from command line
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        output_path = None
    
    generate_image(output_path=output_path)
