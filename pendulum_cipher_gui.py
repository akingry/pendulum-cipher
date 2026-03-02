"""
Pendulum Cipher GUI - Visual Chaos-Based Encryption

Watch the pendulums generate your keystream in real-time!
"""

import numpy as np
from scipy.integrate import odeint
import hashlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time

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
    
    def get_positions(self, scale=80):
        """Get bob positions in pixels."""
        theta1, _, theta2, _ = self.state
        x1 = self.L1 * np.sin(theta1) * scale
        y1 = self.L1 * np.cos(theta1) * scale
        x2 = x1 + self.L2 * np.sin(theta2) * scale
        y2 = y1 + self.L2 * np.cos(theta2) * scale
        return x1, y1, x2, y2
    
    def get_state_bytes(self):
        return self.state.tobytes()


class PendulumCipher:
    """Encryption system using chaotic double pendulums."""
    
    def __init__(self, key: str):
        self.key = key
        self.pendulum1, self.pendulum2 = self._derive_pendulums(key)
        self.dt = 0.001
        self.time = 0.0
        
    def _derive_pendulums(self, key: str):
        key_bytes = hashlib.sha512(key.encode('utf-8')).digest()
        
        def bytes_to_float(b1, b2):
            return ((b1 << 8) | b2) / 65536.0
        
        params = []
        for i in range(16):
            params.append(bytes_to_float(key_bytes[i*2], key_bytes[i*2 + 1]))
        
        L1_1 = 0.8 + params[0] * 0.8
        L2_1 = 0.8 + params[1] * 0.8
        m1_1 = 0.5 + params[2] * 1.5
        m2_1 = 0.5 + params[3] * 1.5
        theta1_1 = np.pi * (0.2 + params[4] * 0.6)
        theta2_1 = np.pi * (0.2 + params[5] * 0.6)
        omega1_1 = (params[6] - 0.5) * 2.0
        omega2_1 = (params[7] - 0.5) * 2.0
        
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
        self.pendulum1.step(self.dt)
        self.pendulum2.step(self.dt)
        self.time += self.dt
        
        state_data = (
            self.pendulum1.get_state_bytes() +
            self.pendulum2.get_state_bytes() +
            np.array([self.time], dtype=np.float64).tobytes()
        )
        
        return hashlib.sha256(state_data).digest()
    
    def generate_keystream(self, length: int) -> bytes:
        stream = bytearray()
        while len(stream) < length:
            block = self._generate_keystream_block()
            stream.extend(block)
        return bytes(stream[:length])
    
    def reset(self):
        self.pendulum1, self.pendulum2 = self._derive_pendulums(self.key)
        self.time = 0.0
    
    def warmup(self, steps, dt=0.02):
        """Run simulation for 'steps' iterations without generating keystream.
        This lets the chaos develop before encryption begins."""
        for _ in range(steps):
            self.pendulum1.step(dt)
            self.pendulum2.step(dt)
            self.time += dt
    
    def encrypt(self, plaintext: bytes) -> bytes:
        self.reset()
        keystream = self.generate_keystream(len(plaintext))
        return bytes(p ^ k for p, k in zip(plaintext, keystream))
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        self.reset()
        keystream = self.generate_keystream(len(ciphertext))
        return bytes(c ^ k for c, k in zip(ciphertext, keystream))


class PendulumCipherGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pendulum Cipher - Chaos-Based Encryption")
        self.root.configure(bg='#1a1a2e')
        self.root.geometry("1000x750")
        self.root.resizable(True, True)
        
        # Cipher state
        self.cipher = None
        self.animating = False
        self.animation_steps = 0
        self.target_steps = 0
        self.pending_output = None
        self.pending_keystream = None
        
        # Warmup steps - how many simulation steps to run before generating keystream
        # More steps = more chaos = different keystream
        self.warmup_steps = 180  # ~3 seconds at 60fps
        
        # Colors
        self.bg_color = '#1a1a2e'
        self.fg_color = '#e8e8e8'
        self.accent1 = '#ff6b6b'
        self.accent2 = '#4ecdc4'
        self.accent3 = '#ffe66d'
        
        self.setup_ui()
        
    def setup_ui(self):
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background=self.bg_color, foreground=self.fg_color, font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'), foreground=self.accent3)
        
        # Main container
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side - Pendulum visualization
        left_frame = tk.Frame(main_frame, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas for pendulums
        canvas_frame = tk.Frame(left_frame, bg='#0f0f1a', relief=tk.RIDGE, bd=2)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.canvas = tk.Canvas(canvas_frame, width=500, height=350, bg='#0f0f1a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Status display
        self.status_var = tk.StringVar(value="Enter a key to initialize pendulums")
        status_label = tk.Label(left_frame, textvariable=self.status_var, bg=self.bg_color, 
                                fg=self.accent2, font=('Consolas', 10))
        status_label.pack(fill=tk.X)
        
        # Keystream display
        keystream_frame = tk.Frame(left_frame, bg='#0f0f1a', relief=tk.RIDGE, bd=2)
        keystream_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(keystream_frame, text="Keystream (hex):", bg='#0f0f1a', fg=self.accent3,
                font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, padx=5, pady=2)
        
        self.keystream_var = tk.StringVar(value="")
        keystream_label = tk.Label(keystream_frame, textvariable=self.keystream_var, bg='#0f0f1a',
                                   fg='#888888', font=('Consolas', 9), wraplength=480, justify=tk.LEFT)
        keystream_label.pack(fill=tk.X, padx=5, pady=5)
        
        # Right side - Controls
        right_frame = tk.Frame(main_frame, bg=self.bg_color, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # Title
        title = tk.Label(right_frame, text="🔐 PENDULUM CIPHER", bg=self.bg_color, 
                        fg=self.accent3, font=('Segoe UI', 16, 'bold'))
        title.pack(pady=(0, 15))
        
        # Key input
        key_frame = tk.Frame(right_frame, bg=self.bg_color)
        key_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(key_frame, text="Encryption Key:", bg=self.bg_color, fg=self.fg_color,
                font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        
        self.key_entry = tk.Entry(key_frame, font=('Consolas', 12), show='●', width=35)
        self.key_entry.pack(fill=tk.X, pady=2)
        self.key_entry.bind('<KeyRelease>', self.on_key_change)
        
        self.show_key_var = tk.BooleanVar(value=False)
        show_key_cb = tk.Checkbutton(key_frame, text="Show key", variable=self.show_key_var,
                                     command=self.toggle_key_visibility, bg=self.bg_color, 
                                     fg=self.fg_color, selectcolor='#2a2a4e', activebackground=self.bg_color)
        show_key_cb.pack(anchor=tk.W)
        
        # Warmup time slider
        warmup_frame = tk.Frame(right_frame, bg=self.bg_color)
        warmup_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(warmup_frame, text="Chaos Warmup Time:", bg=self.bg_color, fg=self.fg_color,
                font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        
        self.warmup_var = tk.IntVar(value=180)  # Default 3 seconds (180 frames @ 60fps)
        
        slider_row = tk.Frame(warmup_frame, bg=self.bg_color)
        slider_row.pack(fill=tk.X)
        
        self.warmup_slider = tk.Scale(slider_row, from_=30, to=600, orient=tk.HORIZONTAL,
                                      variable=self.warmup_var, bg=self.bg_color, fg=self.fg_color,
                                      highlightthickness=0, troughcolor='#2a2a4e', length=280,
                                      command=self.on_warmup_change)
        self.warmup_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.warmup_label = tk.Label(slider_row, text="3.0s", bg=self.bg_color, fg=self.accent2,
                                     font=('Consolas', 10), width=6)
        self.warmup_label.pack(side=tk.RIGHT)
        
        tk.Label(warmup_frame, text="(More time = more chaos = different keystream)", 
                bg=self.bg_color, fg='#666688', font=('Segoe UI', 8)).pack(anchor=tk.W)
        
        # Input text
        input_frame = tk.Frame(right_frame, bg=self.bg_color)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tk.Label(input_frame, text="Input (plaintext or hex ciphertext):", bg=self.bg_color, 
                fg=self.fg_color, font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        
        self.input_text = tk.Text(input_frame, font=('Consolas', 10), height=6, width=40,
                                  bg='#2a2a4e', fg=self.fg_color, insertbackground=self.fg_color)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(right_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=10)
        
        encrypt_btn = tk.Button(btn_frame, text="🔒 ENCRYPT", command=self.encrypt,
                               font=('Segoe UI', 11, 'bold'), bg='#2d6a4f', fg='white',
                               activebackground='#40916c', width=15, height=2)
        encrypt_btn.pack(side=tk.LEFT, padx=5)
        
        decrypt_btn = tk.Button(btn_frame, text="🔓 DECRYPT", command=self.decrypt,
                               font=('Segoe UI', 11, 'bold'), bg='#9d4edd', fg='white',
                               activebackground='#c77dff', width=15, height=2)
        decrypt_btn.pack(side=tk.RIGHT, padx=5)
        
        # Output text
        output_frame = tk.Frame(right_frame, bg=self.bg_color)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tk.Label(output_frame, text="Output:", bg=self.bg_color, fg=self.fg_color,
                font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        
        self.output_text = tk.Text(output_frame, font=('Consolas', 10), height=6, width=40,
                                   bg='#2a2a4e', fg=self.accent2, insertbackground=self.fg_color)
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Copy button
        copy_btn = tk.Button(output_frame, text="📋 Copy Output", command=self.copy_output,
                            font=('Segoe UI', 9), bg='#4a4a6e', fg='white')
        copy_btn.pack(anchor=tk.E, pady=5)
        
        # File operations
        file_frame = tk.Frame(right_frame, bg=self.bg_color)
        file_frame.pack(fill=tk.X, pady=5)
        
        self.encrypt_file_btn = tk.Button(file_frame, text="📁 Encrypt File", command=self.encrypt_file,
                 font=('Segoe UI', 9), bg='#4a4a6e', fg='white', width=15)
        self.encrypt_file_btn.pack(side=tk.LEFT, padx=5)
        self.decrypt_file_btn = tk.Button(file_frame, text="📂 Decrypt File", command=self.decrypt_file,
                 font=('Segoe UI', 9), bg='#4a4a6e', fg='white', width=15)
        self.decrypt_file_btn.pack(side=tk.RIGHT, padx=5)
        
        # Progress bar for file operations
        self.progress_frame = tk.Frame(right_frame, bg=self.bg_color)
        self.progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, 
                                            maximum=100, mode='determinate', length=380)
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.pack_forget()  # Hidden initially
        
        self.progress_label = tk.Label(self.progress_frame, text="", bg=self.bg_color,
                                       fg=self.accent2, font=('Consolas', 9))
        self.progress_label.pack()
        self.progress_label.pack_forget()  # Hidden initially
        
        # Store references to controls for disabling
        self.controls = [self.key_entry, self.input_text, self.output_text,
                        encrypt_btn, decrypt_btn, copy_btn, 
                        self.encrypt_file_btn, self.decrypt_file_btn]
        
        # Draw initial canvas
        self.draw_idle_canvas()
        
    def draw_idle_canvas(self):
        """Draw placeholder when no key is entered."""
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 500
        h = self.canvas.winfo_height() or 350
        
        self.canvas.create_text(w//2, h//2, text="Enter a key to see\nthe pendulums", 
                               fill='#444466', font=('Segoe UI', 14), justify=tk.CENTER)
    
    def disable_controls(self):
        """Disable all controls during file operations."""
        for ctrl in self.controls:
            try:
                ctrl.config(state=tk.DISABLED)
            except:
                pass
        # Show progress bar
        self.progress_bar.pack(fill=tk.X)
        self.progress_label.pack()
        self.progress_var.set(0)
        
    def enable_controls(self):
        """Re-enable all controls after file operations."""
        for ctrl in self.controls:
            try:
                ctrl.config(state=tk.NORMAL)
            except:
                pass
        # Hide progress bar
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        
    def update_progress(self, current, total, operation="Processing"):
        """Update the progress bar."""
        percent = (current / total) * 100 if total > 0 else 0
        self.progress_var.set(percent)
        size_str = f"{current:,} / {total:,} bytes"
        self.progress_label.config(text=f"{operation}: {size_str} ({percent:.1f}%)")
        self.root.update_idletasks()
        
    def draw_pendulums(self):
        """Draw both pendulums on the canvas."""
        if not self.cipher:
            return
            
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 500
        h = self.canvas.winfo_height() or 350
        
        # Origins for both pendulums
        origin1 = (w // 3, h // 3)
        origin2 = (2 * w // 3, h // 3)
        
        # Labels
        self.canvas.create_text(origin1[0], 30, text="Pendulum 1", fill=self.accent1, 
                               font=('Segoe UI', 10, 'bold'))
        self.canvas.create_text(origin2[0], 30, text="Pendulum 2", fill=self.accent2,
                               font=('Segoe UI', 10, 'bold'))
        
        # Draw pendulum 1
        x1, y1, x2, y2 = self.cipher.pendulum1.get_positions(scale=70)
        self.draw_single_pendulum(origin1, x1, y1, x2, y2, self.accent1, '#ffaaaa')
        
        # Draw pendulum 2
        x1, y1, x2, y2 = self.cipher.pendulum2.get_positions(scale=70)
        self.draw_single_pendulum(origin2, x1, y1, x2, y2, self.accent2, '#aaffee')
        
    def draw_single_pendulum(self, origin, x1, y1, x2, y2, color1, color2):
        """Draw a single double pendulum."""
        ox, oy = origin
        
        # First arm
        self.canvas.create_line(ox, oy, ox + x1, oy + y1, fill='white', width=3)
        # Second arm
        self.canvas.create_line(ox + x1, oy + y1, ox + x2, oy + y2, fill='white', width=3)
        
        # Pivot
        self.canvas.create_oval(ox - 6, oy - 6, ox + 6, oy + 6, fill='#444466', outline='')
        
        # First bob
        self.canvas.create_oval(ox + x1 - 10, oy + y1 - 10, ox + x1 + 10, oy + y1 + 10,
                               fill=color1, outline='')
        # Second bob
        self.canvas.create_oval(ox + x2 - 12, oy + y2 - 12, ox + x2 + 12, oy + y2 + 12,
                               fill=color2, outline='')
        
    def on_key_change(self, event=None):
        """Handle key entry changes."""
        key = self.key_entry.get()
        if key:
            self.cipher = PendulumCipher(key)
            self.draw_pendulums()
            self.status_var.set(f"Key loaded: {len(key)} characters")
        else:
            self.cipher = None
            self.draw_idle_canvas()
            self.status_var.set("Enter a key to initialize pendulums")
            
    def toggle_key_visibility(self):
        """Toggle key visibility."""
        if self.show_key_var.get():
            self.key_entry.config(show='')
        else:
            self.key_entry.config(show='●')
    
    def on_warmup_change(self, value):
        """Update warmup label when slider changes."""
        steps = int(value)
        seconds = steps / 60.0
        self.warmup_label.config(text=f"{seconds:.1f}s")
        self.warmup_steps = steps
            
    def start_timed_animation(self):
        """Start the animation after computation is complete."""
        self.animating = True
        self.animation_steps = 0
        self.animate_encryption(0)
    
    def animate_encryption(self, num_bytes):
        """Animate the pendulums during encryption."""
        if not self.cipher or not self.animating:
            return
            
        # Step the simulation
        self.cipher.pendulum1.step(0.02)
        self.cipher.pendulum2.step(0.02)
        self.animation_steps += 1
        
        # Update display
        self.draw_pendulums()
        
        # Update keystream display
        progress = min(self.animation_steps / self.target_steps, 1.0)
        self.status_var.set(f"Generating keystream... {int(progress * 100)}%")
        
        if self.animation_steps < self.target_steps:
            self.root.after(16, lambda: self.animate_encryption(num_bytes))
        else:
            self.animating = False
            self.status_var.set("✓ Complete!")
            # Now display the pending output
            if self.pending_output is not None:
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", self.pending_output)
                self.keystream_var.set(self.pending_keystream or "")
                self.pending_output = None
                self.pending_keystream = None
            
    def encrypt(self):
        """Encrypt the input text."""
        key = self.key_entry.get()
        if not key:
            messagebox.showerror("Error", "Please enter an encryption key")
            return
            
        plaintext = self.input_text.get("1.0", tk.END).strip()
        if not plaintext:
            messagebox.showerror("Error", "Please enter text to encrypt")
            return
        
        # Store plaintext for use after animation
        self.pending_plaintext = plaintext.encode('utf-8')
        self.pending_mode = 'encrypt'
        
        # Initialize cipher - this is the REAL cipher that will be used
        self.cipher = PendulumCipher(key)
        
        # Animation IS the warmup - same cipher object
        self.animating = True
        self.animation_steps = 0
        self.target_steps = self.warmup_steps  # 180 steps = ~3 seconds
        
        self.status_var.set("Warming up chaos...")
        self.animate_warmup()
        
    def decrypt(self):
        """Decrypt the input hex."""
        key = self.key_entry.get()
        if not key:
            messagebox.showerror("Error", "Please enter an encryption key")
            return
            
        ciphertext_hex = self.input_text.get("1.0", tk.END).strip()
        if not ciphertext_hex:
            messagebox.showerror("Error", "Please enter hex ciphertext to decrypt")
            return
        
        try:
            ciphertext = bytes.fromhex(ciphertext_hex)
        except ValueError:
            messagebox.showerror("Error", "Invalid hex format")
            return
        
        # Store ciphertext for use after animation
        self.pending_ciphertext = ciphertext
        self.pending_mode = 'decrypt'
        
        # Initialize cipher - this is the REAL cipher that will be used
        self.cipher = PendulumCipher(key)
        
        # Animation IS the warmup - same cipher object
        self.animating = True
        self.animation_steps = 0
        self.target_steps = self.warmup_steps  # 180 steps = ~3 seconds
        
        self.status_var.set("Warming up chaos...")
        self.animate_warmup()
    
    def animate_warmup(self):
        """Animate the pendulum warmup - this IS the real computation."""
        if not self.cipher or not self.animating:
            return
        
        # Step the REAL cipher's pendulums (0.02s per frame for visible motion)
        self.cipher.pendulum1.step(0.02)
        self.cipher.pendulum2.step(0.02)
        self.cipher.time += 0.02
        self.animation_steps += 1
        
        # Update display
        self.draw_pendulums()
        
        # Update progress
        progress = min(self.animation_steps / self.target_steps, 1.0)
        self.status_var.set(f"Warming up chaos... {int(progress * 100)}%")
        
        if self.animation_steps < self.target_steps:
            self.root.after(16, self.animate_warmup)
        else:
            # Warmup complete - now generate keystream and encrypt/decrypt
            self.animating = False
            self.complete_operation()
    
    def complete_operation(self):
        """Generate keystream from warmed-up pendulums and complete encrypt/decrypt."""
        if self.pending_mode == 'encrypt':
            # Generate keystream from the warmed-up state
            keystream = self.cipher.generate_keystream(len(self.pending_plaintext))
            ciphertext = bytes(p ^ k for p, k in zip(self.pending_plaintext, keystream))
            hex_output = ciphertext.hex()
            
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", hex_output)
            keystream_preview = hex_output[:64] + ('...' if len(hex_output) > 64 else '')
            self.keystream_var.set(keystream_preview)
            self.status_var.set(f"✓ Encrypted! (warmup: {self.target_steps} steps)")
            
        elif self.pending_mode == 'decrypt':
            # Generate keystream from the warmed-up state
            keystream = self.cipher.generate_keystream(len(self.pending_ciphertext))
            decrypted = bytes(c ^ k for c, k in zip(self.pending_ciphertext, keystream))
            
            try:
                output = decrypted.decode('utf-8')
            except:
                hex_str = decrypted.hex()
                output = ' '.join(hex_str[i:i+2] for i in range(0, min(len(hex_str), 200), 2))
                if len(hex_str) > 200:
                    output += f'... ({len(decrypted)} bytes total)'
            
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", output)
            self.keystream_var.set(f"(decrypted {len(self.pending_ciphertext)} bytes)")
            self.status_var.set(f"✓ Decrypted! (warmup: {self.target_steps} steps)")
        
    def finish_operation(self, output, keystream_preview):
        """Complete the encryption/decryption operation."""
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", output)
        self.keystream_var.set(keystream_preview)
        
    def copy_output(self):
        """Copy output to clipboard."""
        output = self.output_text.get("1.0", tk.END).strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(output)
        self.status_var.set("✓ Copied to clipboard!")
        
    def encrypt_file(self):
        """Encrypt a file."""
        key = self.key_entry.get()
        if not key:
            messagebox.showerror("Error", "Please enter an encryption key")
            return
            
        input_path = filedialog.askopenfilename(title="Select file to encrypt")
        if not input_path:
            return
            
        output_path = filedialog.asksaveasfilename(
            title="Save encrypted file as",
            defaultextension=".enc",
            initialfile=input_path.split('/')[-1] + ".enc"
        )
        if not output_path:
            return
        
        def do_encrypt_file():
            try:
                self.root.after(0, self.disable_controls)
                
                # Read file
                with open(input_path, 'rb') as f:
                    plaintext = f.read()
                total_size = len(plaintext)
                
                # Initialize cipher
                cipher = PendulumCipher(key)
                cipher.reset()
                
                # Process in chunks with progress
                chunk_size = 4096
                ciphertext = bytearray()
                
                for i in range(0, total_size, chunk_size):
                    chunk = plaintext[i:i+chunk_size]
                    keystream = cipher.generate_keystream(len(chunk))
                    encrypted_chunk = bytes(p ^ k for p, k in zip(chunk, keystream))
                    ciphertext.extend(encrypted_chunk)
                    
                    # Update progress
                    self.root.after(0, lambda curr=i+len(chunk), tot=total_size: 
                                   self.update_progress(curr, tot, "Encrypting"))
                    
                    # Update pendulum animation
                    if self.cipher:
                        self.cipher.pendulum1.step(0.05)
                        self.cipher.pendulum2.step(0.05)
                        self.root.after(0, self.draw_pendulums)
                
                # Write output
                with open(output_path, 'wb') as f:
                    f.write(ciphertext)
                
                self.root.after(0, self.enable_controls)
                self.root.after(0, lambda: messagebox.showinfo("Success", 
                    f"Encrypted {total_size:,} bytes\nSaved to: {output_path}"))
                self.root.after(0, lambda: self.status_var.set(f"✓ Encrypted {total_size:,} bytes"))
                
            except Exception as e:
                self.root.after(0, self.enable_controls)
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        # Initialize cipher for animation
        self.cipher = PendulumCipher(key)
        threading.Thread(target=do_encrypt_file, daemon=True).start()
            
    def decrypt_file(self):
        """Decrypt a file."""
        key = self.key_entry.get()
        if not key:
            messagebox.showerror("Error", "Please enter an encryption key")
            return
            
        input_path = filedialog.askopenfilename(title="Select file to decrypt")
        if not input_path:
            return
            
        default_name = input_path.replace('.enc', '') if input_path.endswith('.enc') else input_path + ".dec"
        output_path = filedialog.asksaveasfilename(
            title="Save decrypted file as",
            initialfile=default_name.split('/')[-1]
        )
        if not output_path:
            return
        
        def do_decrypt_file():
            try:
                self.root.after(0, self.disable_controls)
                
                # Read file
                with open(input_path, 'rb') as f:
                    ciphertext = f.read()
                total_size = len(ciphertext)
                
                # Initialize cipher
                cipher = PendulumCipher(key)
                cipher.reset()
                
                # Process in chunks with progress
                chunk_size = 4096
                plaintext = bytearray()
                
                for i in range(0, total_size, chunk_size):
                    chunk = ciphertext[i:i+chunk_size]
                    keystream = cipher.generate_keystream(len(chunk))
                    decrypted_chunk = bytes(c ^ k for c, k in zip(chunk, keystream))
                    plaintext.extend(decrypted_chunk)
                    
                    # Update progress
                    self.root.after(0, lambda curr=i+len(chunk), tot=total_size: 
                                   self.update_progress(curr, tot, "Decrypting"))
                    
                    # Update pendulum animation
                    if self.cipher:
                        self.cipher.pendulum1.step(0.05)
                        self.cipher.pendulum2.step(0.05)
                        self.root.after(0, self.draw_pendulums)
                
                # Write output
                with open(output_path, 'wb') as f:
                    f.write(plaintext)
                
                self.root.after(0, self.enable_controls)
                self.root.after(0, lambda: messagebox.showinfo("Success", 
                    f"Decrypted {total_size:,} bytes\nSaved to: {output_path}"))
                self.root.after(0, lambda: self.status_var.set(f"✓ Decrypted {total_size:,} bytes"))
                
            except Exception as e:
                self.root.after(0, self.enable_controls)
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        # Initialize cipher for animation
        self.cipher = PendulumCipher(key)
        threading.Thread(target=do_decrypt_file, daemon=True).start()
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PendulumCipherGUI()
    app.run()
