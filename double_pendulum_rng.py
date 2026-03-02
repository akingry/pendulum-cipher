"""
Double Pendulum Random Number Generator

Uses the chaotic motion of two double pendulums to generate random numbers.
The randomness comes from:
1. The x,y positions of each pendulum's second bob
2. The elapsed time in seconds

Double pendulums are chaotic systems - tiny differences in initial conditions
lead to vastly different trajectories, making them excellent entropy sources.
"""

import numpy as np
from scipy.integrate import odeint
import pygame
import sys
import hashlib
import time

# Constants
G = 9.81  # Gravity
SCALE = 150  # Pixels per meter
FPS = 60
DT = 1/FPS

# Colors
BLACK = (10, 10, 20)
WHITE = (255, 255, 255)
RED = (255, 80, 80)
BLUE = (80, 150, 255)
YELLOW = (255, 220, 80)
GREEN = (80, 255, 120)
GRAY = (60, 60, 80)
DARK_GRAY = (30, 30, 45)

class DoublePendulum:
    """Simulates a double pendulum using Lagrangian mechanics."""
    
    def __init__(self, L1=1.0, L2=1.0, m1=1.0, m2=1.0, theta1=np.pi/2, theta2=np.pi/2, 
                 omega1=0.0, omega2=0.0, color1=RED, color2=YELLOW):
        self.L1 = L1  # Length of first arm
        self.L2 = L2  # Length of second arm
        self.m1 = m1  # Mass of first bob
        self.m2 = m2  # Mass of second bob
        self.color1 = color1
        self.color2 = color2
        
        # State: [theta1, omega1, theta2, omega2]
        self.state = np.array([theta1, omega1, theta2, omega2])
        
        # Trail for the second bob
        self.trail = []
        self.max_trail = 500
        
    def derivatives(self, state, t):
        """Compute derivatives for the double pendulum ODEs."""
        theta1, omega1, theta2, omega2 = state
        L1, L2, m1, m2 = self.L1, self.L2, self.m1, self.m2
        
        delta = theta2 - theta1
        den1 = (m1 + m2) * L1 - m2 * L1 * np.cos(delta) ** 2
        den2 = (L2 / L1) * den1
        
        # Angular accelerations from Lagrangian mechanics
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
        
        # Update trail
        x2, y2 = self.get_bob2_position()
        self.trail.append((x2, y2))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)
    
    def get_bob1_position(self):
        """Get (x, y) of the first bob in meters."""
        theta1 = self.state[0]
        x1 = self.L1 * np.sin(theta1)
        y1 = self.L1 * np.cos(theta1)
        return x1, y1
    
    def get_bob2_position(self):
        """Get (x, y) of the second bob in meters."""
        theta1, _, theta2, _ = self.state
        x1 = self.L1 * np.sin(theta1)
        y1 = self.L1 * np.cos(theta1)
        x2 = x1 + self.L2 * np.sin(theta2)
        y2 = y1 + self.L2 * np.cos(theta2)
        return x2, y2
    
    def draw(self, screen, origin):
        """Draw the pendulum on the pygame screen."""
        ox, oy = origin
        
        # Get positions in pixels
        x1, y1 = self.get_bob1_position()
        x2, y2 = self.get_bob2_position()
        
        px1 = int(ox + x1 * SCALE)
        py1 = int(oy + y1 * SCALE)
        px2 = int(ox + x2 * SCALE)
        py2 = int(oy + y2 * SCALE)
        
        # Draw trail
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = int(255 * i / len(self.trail))
                trail_color = (self.color2[0], self.color2[1], self.color2[2])
                # Fade effect
                fade = i / len(self.trail)
                faded_color = tuple(int(c * fade * 0.5) for c in trail_color)
                
                tx1, ty1 = self.trail[i-1]
                tx2, ty2 = self.trail[i]
                pygame.draw.line(screen, faded_color,
                               (int(ox + tx1 * SCALE), int(oy + ty1 * SCALE)),
                               (int(ox + tx2 * SCALE), int(oy + ty2 * SCALE)), 1)
        
        # Draw arms
        pygame.draw.line(screen, WHITE, (ox, oy), (px1, py1), 3)
        pygame.draw.line(screen, WHITE, (px1, py1), (px2, py2), 3)
        
        # Draw pivot
        pygame.draw.circle(screen, GRAY, (ox, oy), 8)
        
        # Draw bobs
        pygame.draw.circle(screen, self.color1, (px1, py1), 12)
        pygame.draw.circle(screen, self.color2, (px2, py2), 15)


class DoublePendulumRNG:
    """Random number generator using two chaotic double pendulums."""
    
    def __init__(self):
        pygame.init()
        self.width = 1400
        self.height = 800
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Double Pendulum Random Number Generator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", 18)
        self.font_large = pygame.font.SysFont("Consolas", 28, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 14)
        
        # Create two pendulums with slightly different initial conditions
        # This small difference will lead to vastly different trajectories (chaos!)
        self.pendulum1 = DoublePendulum(
            L1=1.2, L2=1.0, m1=1.5, m2=1.0,
            theta1=np.pi * 0.75, theta2=np.pi * 0.5,
            omega1=0.1, omega2=0.0,
            color1=RED, color2=YELLOW
        )
        
        self.pendulum2 = DoublePendulum(
            L1=1.0, L2=1.2, m1=1.0, m2=1.5,
            theta1=np.pi * 0.6, theta2=np.pi * 0.8,
            omega1=0.0, omega2=0.15,
            color1=BLUE, color2=GREEN
        )
        
        self.start_time = time.time()
        self.generated_numbers = []
        self.last_generation_time = 0
        self.generation_interval = 1.0  # Generate a number every second
        self.paused = False
        
    def generate_random_number(self, bits=32):
        """
        Generate a random number using the current state of both pendulums.
        
        Uses:
        1. x, y coordinates of pendulum 1's second bob
        2. x, y coordinates of pendulum 2's second bob
        3. Current elapsed time in seconds
        
        These values are combined and hashed to produce the random number.
        """
        elapsed = time.time() - self.start_time
        
        # Get positions of both second bobs
        x1, y1 = self.pendulum1.get_bob2_position()
        x2, y2 = self.pendulum2.get_bob2_position()
        
        # Also get angular velocities for extra entropy
        omega1_1 = self.pendulum1.state[1]
        omega1_2 = self.pendulum1.state[3]
        omega2_1 = self.pendulum2.state[1]
        omega2_2 = self.pendulum2.state[3]
        
        # Combine all values into a string with high precision
        entropy_string = f"{x1:.15f}{y1:.15f}{x2:.15f}{y2:.15f}{elapsed:.15f}"
        entropy_string += f"{omega1_1:.15f}{omega1_2:.15f}{omega2_1:.15f}{omega2_2:.15f}"
        
        # Hash the string using SHA-256
        hash_bytes = hashlib.sha256(entropy_string.encode()).digest()
        
        # Extract the requested number of bits
        num_bytes = (bits + 7) // 8
        random_bytes = hash_bytes[:num_bytes]
        
        # Convert to integer
        random_number = int.from_bytes(random_bytes, byteorder='big')
        
        # Mask to exact bit count
        random_number &= (1 << bits) - 1
        
        return random_number, elapsed, (x1, y1), (x2, y2)
    
    def draw_info_panel(self):
        """Draw the information panel on the right side."""
        panel_x = 950
        panel_width = 430
        
        # Panel background
        pygame.draw.rect(self.screen, DARK_GRAY, (panel_x, 20, panel_width, 760), border_radius=15)
        pygame.draw.rect(self.screen, GRAY, (panel_x, 20, panel_width, 760), 2, border_radius=15)
        
        y = 40
        
        # Title
        title = self.font_large.render("CHAOTIC RNG", True, WHITE)
        self.screen.blit(title, (panel_x + 20, y))
        y += 45
        
        # Current time
        elapsed = time.time() - self.start_time
        time_text = self.font.render(f"Elapsed: {elapsed:.3f} s", True, YELLOW)
        self.screen.blit(time_text, (panel_x + 20, y))
        y += 35
        
        # Pendulum 1 info
        x1, y1_pos = self.pendulum1.get_bob2_position()
        p1_title = self.font.render("Pendulum 1 (Bob 2):", True, YELLOW)
        self.screen.blit(p1_title, (panel_x + 20, y))
        y += 25
        p1_pos = self.font_small.render(f"  x: {x1:+.6f}  y: {y1_pos:+.6f}", True, WHITE)
        self.screen.blit(p1_pos, (panel_x + 20, y))
        y += 30
        
        # Pendulum 2 info
        x2, y2_pos = self.pendulum2.get_bob2_position()
        p2_title = self.font.render("Pendulum 2 (Bob 2):", True, GREEN)
        self.screen.blit(p2_title, (panel_x + 20, y))
        y += 25
        p2_pos = self.font_small.render(f"  x: {x2:+.6f}  y: {y2_pos:+.6f}", True, WHITE)
        self.screen.blit(p2_pos, (panel_x + 20, y))
        y += 40
        
        # Divider
        pygame.draw.line(self.screen, GRAY, (panel_x + 20, y), (panel_x + panel_width - 20, y), 1)
        y += 20
        
        # Generated numbers
        gen_title = self.font.render("Generated Numbers (32-bit):", True, WHITE)
        self.screen.blit(gen_title, (panel_x + 20, y))
        y += 30
        
        # Show last 15 generated numbers
        for i, (num, t, _, _) in enumerate(self.generated_numbers[-15:]):
            # Alternate colors for readability
            color = (180, 220, 255) if i % 2 == 0 else (220, 180, 255)
            hex_str = f"{num:08X}"
            num_text = self.font_small.render(f"t={t:6.2f}s  0x{hex_str}  ({num:>10})", True, color)
            self.screen.blit(num_text, (panel_x + 20, y))
            y += 22
        
        # Instructions at bottom
        y = 700
        pygame.draw.line(self.screen, GRAY, (panel_x + 20, y), (panel_x + panel_width - 20, y), 1)
        y += 15
        
        instructions = [
            "[SPACE] Generate number now",
            "[P] Pause/Resume simulation",
            "[R] Reset pendulums",
            "[ESC] Quit"
        ]
        for inst in instructions:
            text = self.font_small.render(inst, True, (150, 150, 170))
            self.screen.blit(text, (panel_x + 20, y))
            y += 18
    
    def draw_chaos_explanation(self):
        """Draw a small explanation box."""
        text_lines = [
            "Double pendulums are chaotic systems.",
            "Tiny differences → wildly different paths.",
            "Combined positions + time = random numbers!"
        ]
        
        y = 700
        for line in text_lines:
            text = self.font_small.render(line, True, (120, 120, 150))
            self.screen.blit(text, (30, y))
            y += 18
    
    def reset_pendulums(self):
        """Reset both pendulums with new random initial conditions."""
        self.pendulum1 = DoublePendulum(
            L1=1.0 + np.random.random() * 0.4,
            L2=1.0 + np.random.random() * 0.4,
            m1=1.0 + np.random.random() * 0.5,
            m2=1.0 + np.random.random() * 0.5,
            theta1=np.pi * (0.3 + np.random.random() * 0.6),
            theta2=np.pi * (0.3 + np.random.random() * 0.6),
            omega1=np.random.random() * 0.3 - 0.15,
            omega2=np.random.random() * 0.3 - 0.15,
            color1=RED, color2=YELLOW
        )
        
        self.pendulum2 = DoublePendulum(
            L1=1.0 + np.random.random() * 0.4,
            L2=1.0 + np.random.random() * 0.4,
            m1=1.0 + np.random.random() * 0.5,
            m2=1.0 + np.random.random() * 0.5,
            theta1=np.pi * (0.3 + np.random.random() * 0.6),
            theta2=np.pi * (0.3 + np.random.random() * 0.6),
            omega1=np.random.random() * 0.3 - 0.15,
            omega2=np.random.random() * 0.3 - 0.15,
            color1=BLUE, color2=GREEN
        )
        
        self.start_time = time.time()
        self.generated_numbers = []
    
    def run(self):
        """Main simulation loop."""
        running = True
        
        # Origins for the two pendulums
        origin1 = (300, 280)
        origin2 = (650, 280)
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # Manual generation
                        result = self.generate_random_number()
                        self.generated_numbers.append(result)
                        print(f"Generated: 0x{result[0]:08X} ({result[0]}) at t={result[1]:.3f}s")
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.reset_pendulums()
            
            if not self.paused:
                # Step the simulation
                self.pendulum1.step(DT)
                self.pendulum2.step(DT)
                
                # Auto-generate numbers at interval
                elapsed = time.time() - self.start_time
                if elapsed - self.last_generation_time >= self.generation_interval:
                    result = self.generate_random_number()
                    self.generated_numbers.append(result)
                    self.last_generation_time = elapsed
                    print(f"Generated: 0x{result[0]:08X} ({result[0]}) at t={result[1]:.3f}s")
            
            # Draw
            self.screen.fill(BLACK)
            
            # Draw pendulum labels
            label1 = self.font.render("Pendulum 1", True, YELLOW)
            label2 = self.font.render("Pendulum 2", True, GREEN)
            self.screen.blit(label1, (origin1[0] - 55, 50))
            self.screen.blit(label2, (origin2[0] - 55, 50))
            
            # Draw pendulums
            self.pendulum1.draw(self.screen, origin1)
            self.pendulum2.draw(self.screen, origin2)
            
            # Draw info panel
            self.draw_info_panel()
            
            # Draw explanation
            self.draw_chaos_explanation()
            
            # Draw pause indicator
            if self.paused:
                pause_text = self.font_large.render("PAUSED", True, (255, 100, 100))
                self.screen.blit(pause_text, (400, 20))
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        pygame.quit()
        
        # Print summary
        print("\n" + "="*60)
        print("GENERATED NUMBERS SUMMARY")
        print("="*60)
        for num, t, pos1, pos2 in self.generated_numbers:
            print(f"t={t:8.3f}s | 0x{num:08X} | {num:>10} | P1({pos1[0]:+.4f},{pos1[1]:+.4f}) P2({pos2[0]:+.4f},{pos2[1]:+.4f})")


if __name__ == "__main__":
    rng = DoublePendulumRNG()
    rng.run()
