import serial
import serial.tools.list_ports
import time
import threading
from tkinter import *
from tkinter import messagebox
import math

class DigitalTwinGripper:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Twin Gripper")
        self.root.geometry("900x650")
        self.root.configure(bg="#2b2b2b")
        
        self.serial_port = None
        self.current_position = 90  # Display position (0-90 range)
        self.running = True
        self.port_name = None
        self.is_animating = False  # Prevent overlapping animations
        
        # MAPPING: Display angle (0-90) to Servo angle (30-90)
        # Display 0° = Servo 30° (CLOSE)
        # Display 90° = Servo 90° (OPEN)
        
        print("="*60)
        print("🤖 DIGITAL TWIN GRIPPER")
        print("="*60)
        
        self.setup_gui()
        self.auto_detect_and_connect()
        
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
    
    def display_to_servo(self, display_angle):
        """Convert display angle (0-90) to servo angle (30-90)
        Display 0° → Servo 30°
        Display 90° → Servo 90°
        """
        # Linear mapping: servo = 30 + (display * 60/90)
        return 30 + int(display_angle * 2 / 3)
    
    def servo_to_display(self, servo_angle):
        """Convert servo angle (30-90) to display angle (0-90)
        Servo 30° → Display 0°
        Servo 90° → Display 90°
        """
        # Reverse mapping: display = (servo - 30) * 90/60
        return int((servo_angle - 30) * 1.5)
        
    def list_available_ports(self):
        """List all available COM ports"""
        ports = serial.tools.list_ports.comports()
        available = []
        print("\n📡 Available COM Ports:")
        if not ports:
            print("   ⚠️  No COM ports found!")
        for port in ports:
            print(f"   • {port.device} - {port.description}")
            available.append(port.device)
        print()
        return available
    
    def auto_detect_and_connect(self):
        """Try to automatically detect and connect to Arduino"""
        available_ports = self.list_available_ports()
        
        if not available_ports:
            self.status_label.config(text="● Error: No COM ports found", fg="#ff4444")
            messagebox.showerror("No Ports", 
                "No COM ports detected!\n\n"
                "Please:\n"
                "1. Connect your Arduino via USB\n"
                "2. Install Arduino drivers\n"
                "3. Restart the application")
            return False
        
        # Try COM7 first (as specified in original code)
        if 'COM7' in available_ports:
            if self.connect_to_port('COM7'):
                return True
        
        # If COM7 didn't work, try other ports with Arduino in the name
        for port in available_ports:
            if 'Arduino' in serial.tools.list_ports.comports()[available_ports.index(port)].description:
                print(f"🔍 Found Arduino on {port}, trying to connect...")
                if self.connect_to_port(port):
                    return True
        
        # If still no luck, try all available ports
        for port in available_ports:
            if port != 'COM7':  # Already tried this
                if self.connect_to_port(port):
                    return True
        
        # Connection failed
        self.status_label.config(text="● Connection Failed - See console", fg="#ff4444")
        self.show_troubleshooting()
        return False
    
    def connect_to_port(self, port_name):
        """Try to connect to a specific port"""
        print(f"🔌 Attempting connection to {port_name}...")
        try:
            # Close existing connection if any
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.serial_port = serial.Serial(port_name, 9600, timeout=2)
            time.sleep(2.5)  # Wait for Arduino reset
            
            # Check for READY message
            if self.serial_port.in_waiting:
                response = self.serial_port.readline().decode().strip()
                print(f"   Response: '{response}'")
            
            self.port_name = port_name
            self.status_label.config(text=f"● Connected: {port_name}", fg="#00ff00")
            self.root.title(f"Digital Twin Gripper - {port_name}")
            print(f"✅ Successfully connected to {port_name}!\n")
            return True
            
        except serial.SerialException as e:
            if "PermissionError" in str(e) or "Access is denied" in str(e):
                print(f"❌ {port_name}: Port is in use or access denied")
            else:
                print(f"❌ {port_name}: {e}")
            return False
        except Exception as e:
            print(f"❌ {port_name}: Unexpected error - {e}")
            return False
    
    def show_troubleshooting(self):
        """Show troubleshooting tips"""
        print("\n" + "="*60)
        print("💡 TROUBLESHOOTING TIPS:")
        print("="*60)
        print("1. CLOSE Arduino IDE (especially Serial Monitor)")
        print("2. Close any other programs using the Arduino")
        print("3. Unplug Arduino USB cable and plug it back in")
        print("4. Check Device Manager (Windows) for the correct COM port")
        print("5. Try running Python as Administrator")
        print("6. Restart your computer if the issue persists")
        print("="*60 + "\n")
        
        messagebox.showwarning("Connection Failed",
            "Could not connect to Arduino!\n\n"
            "Common fixes:\n"
            "• Close Arduino IDE Serial Monitor\n"
            "• Unplug and replug USB cable\n"
            "• Run this program as Administrator\n"
            "• Check the console for more details")
    
    def setup_gui(self):
        Label(self.root, text="🤖 DIGITAL TWIN GRIPPER", 
              font=("Arial", 18, "bold"), bg="#2b2b2b", fg="#00ff00").pack(pady=15)
        
        control_frame = Frame(self.root, bg="#3a3a3a", padx=20, pady=20)
        control_frame.pack(side=TOP, fill=X, padx=20)
        
        self.status_label = Label(control_frame, text="● Detecting ports...", 
                                 font=("Arial", 12, "bold"), fg="#FFC107", bg="#3a3a3a")
        self.status_label.pack(pady=5)
        
        # Reconnect button
        Button(control_frame, text="🔄 Reconnect", 
               command=self.reconnect,
               bg="#2196F3", fg="white", font=("Arial", 9),
               padx=10, pady=5).pack(pady=5)
        
        Label(control_frame, text="Gripper Position (0°=Close, 90°=Open)", 
              font=("Arial", 11), bg="#3a3a3a", fg="white").pack(pady=5)
        
        self.position_slider = Scale(control_frame, from_=0, to=90, 
                                    orient=HORIZONTAL, length=500,
                                    command=self.on_slider_change,
                                    bg="#4a4a4a", fg="white", troughcolor="#666")
        self.position_slider.set(90)
        self.position_slider.pack(pady=10)
        
        button_frame = Frame(control_frame, bg="#3a3a3a")
        button_frame.pack(pady=10)
        
        Button(button_frame, text="🟢 OPEN (90°)", 
               command=lambda: self.set_position(90),
               bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
               padx=20, pady=12).pack(side=LEFT, padx=5)
        
        Button(button_frame, text="🟡 HALF (45°)", 
               command=lambda: self.set_position(45),
               bg="#FFC107", fg="white", font=("Arial", 11, "bold"),
               padx=20, pady=12).pack(side=LEFT, padx=5)
        
        Button(button_frame, text="🔴 CLOSE (0°)", 
               command=lambda: self.set_position(0),
               bg="#f44336", fg="white", font=("Arial", 11, "bold"),
               padx=20, pady=12).pack(side=LEFT, padx=5)
        
        self.position_label = Label(control_frame, text="Current: 90°", 
                                   font=("Arial", 16, "bold"), bg="#3a3a3a", fg="#00ff00")
        self.position_label.pack(pady=10)
        
        self.canvas = Canvas(self.root, width=850, height=400, bg="#1a1a1a", 
                           highlightthickness=2, highlightbackground="#00ff00")
        self.canvas.pack(padx=20, pady=10)
        
        self.draw_gripper()
    
    def reconnect(self):
        """Attempt to reconnect to Arduino"""
        self.status_label.config(text="● Reconnecting...", fg="#FFC107")
        self.root.update()
        self.auto_detect_and_connect()
    
    def send_position(self, display_position):
        """Send position to Arduino (converts display angle to servo angle)"""
        if self.serial_port and self.serial_port.is_open:
            try:
                servo_angle = self.display_to_servo(display_position)
                command = f"GRIP:{servo_angle}\n"
                self.serial_port.write(command.encode())
                print(f"📤 Sent: GRIP:{servo_angle} (Display: {display_position}°)")
                return True
            except Exception as e:
                print(f"❌ Send error: {e}")
                self.status_label.config(text="● Connection Lost", fg="#ff4444")
                return False
        else:
            print("⚠️  Not connected to Arduino")
            return False
    
    def on_slider_change(self, value):
        position = int(float(value))
        self.set_position(position)
    
    def set_position(self, display_position):
        """Set gripper position (using display angle 0-60)"""
        self.is_animating = False  # Stop any ongoing animation
        self.current_position = display_position
        self.position_slider.set(display_position)
        self.position_label.config(text=f"Current: {display_position}°")
        self.send_position(display_position)
        self.draw_gripper()
    
    def draw_gripper(self):
        self.canvas.delete("all")
        
        # Calculate visual angle (0° to 90° display range)
        # Make the visual opening more dramatic
        normalized = self.current_position / 90.0  # 0.0 to 1.0
        visual_angle = 2 + 70 * normalized  # 2° at closed, 72° at open
        angle_rad = math.radians(visual_angle)
        
        cx, cy = 425, 200
        
        # Base
        self.canvas.create_rectangle(cx-50, cy+90, cx+50, cy+130, 
                                     fill="#333", outline="#00ff00", width=2)
        
        # Servo
        self.canvas.create_oval(cx-60, cy-25, cx+60, cy+85, 
                               fill="#222", outline="#00ff00", width=3)
        self.canvas.create_text(cx, cy+30, text="SERVO", 
                              font=("Arial", 12, "bold"), fill="#00ff00")
        
        # Jaws
        jaw_length = 130
        jaw_width = 24
        
        x1_left = cx - jaw_width/2
        y1_left = cy
        x2_left = x1_left - jaw_length * math.sin(angle_rad)
        y2_left = y1_left - jaw_length * math.cos(angle_rad)
        
        self.canvas.create_line(x1_left, y1_left, x2_left, y2_left, 
                               fill="#FF6B35", width=jaw_width, capstyle=ROUND)
        
        x1_right = cx + jaw_width/2
        y1_right = cy
        x2_right = x1_right + jaw_length * math.sin(angle_rad)
        y2_right = y1_right - jaw_length * math.cos(angle_rad)
        
        self.canvas.create_line(x1_right, y1_right, x2_right, y2_right, 
                               fill="#FF6B35", width=jaw_width, capstyle=ROUND)
        
        # Tips
        self.canvas.create_oval(x2_left-12, y2_left-12, x2_left+12, y2_left+12,
                               fill="#FFD700", outline="#000", width=2)
        self.canvas.create_oval(x2_right-12, y2_right-12, x2_right+12, y2_right+12,
                               fill="#FFD700", outline="#000", width=2)
        
        # Pivot
        self.canvas.create_oval(cx-18, cy-18, cx+18, cy+18, 
                               fill="#00ff00", outline="#000", width=3)
        
        # Status
        gap = abs(x2_right - x2_left)
        if self.current_position <= 25:
            color, status = "#f44336", "CLOSED"
        elif self.current_position <= 65:
            color, status = "#FFC107", "PARTIAL"
        else:
            color, status = "#4CAF50", "OPEN"
        
        self.canvas.create_rectangle(40, 30, 160, 80, fill=color, outline="#000", width=3)
        self.canvas.create_text(100, 55, text=status, 
                              font=("Arial", 16, "bold"), fill="white")
        
        self.canvas.create_text(cx, 360, 
                               text=f"Angle: {self.current_position}° | Gap: {gap:.0f}px",
                               font=("Courier", 13, "bold"), fill="#00ff00")
    
    def update_position_from_arduino(self, servo_position):
        """Update GUI when Arduino reports its position (converts servo angle to display angle)"""
        display_position = self.servo_to_display(servo_position)
        
        # If already animating, just update target position immediately
        if self.is_animating:
            self.current_position = display_position
            self.position_slider.set(display_position)
            self.position_label.config(text=f"Current: {display_position}°")
            self.draw_gripper()
        else:
            # Smoothly animate to the new position
            self.animate_to_position(display_position)
    
    def animate_to_position(self, target_position):
        """Smoothly animate the digital twin to match physical gripper speed"""
        if self.current_position == target_position or self.is_animating:
            return
        
        self.is_animating = True
        
        # Calculate direction
        step = 1 if target_position > self.current_position else -1
        
        def animate_step():
            if not self.running:  # Allow stopping
                self.is_animating = False
                return
                
            if (step > 0 and self.current_position < target_position) or \
               (step < 0 and self.current_position > target_position):
                self.current_position += step
                self.position_slider.set(self.current_position)
                self.position_label.config(text=f"Current: {self.current_position}°")
                self.draw_gripper()
                # Match Arduino speed: 15ms per degree
                self.root.after(15, animate_step)
            else:
                self.is_animating = False
        
        animate_step()
    
    def update_loop(self):
        while self.running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting:
                        response = self.serial_port.readline().decode().strip()
                        print(f"📥 Received: {response}")
                        
                        # Update GUI when receiving position updates from Arduino
                        if response.startswith("POS:"):
                            try:
                                new_position = int(response.split(":")[1])
                                # Update the GUI (must use after() for thread safety)
                                self.root.after(0, self.update_position_from_arduino, new_position)
                            except:
                                pass
                except:
                    pass
            time.sleep(0.05)
    
    def cleanup(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print("🔌 Disconnected from Arduino")

def main():
    root = Tk()
    app = DigitalTwinGripper(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()