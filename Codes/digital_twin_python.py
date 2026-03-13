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
        self.is_animating = False
        self.manual_mode = False   # <<< SENSOR MODE FLAG
        
        print("="*60)
        print(" DIGITAL TWIN GRIPPER")
        print("="*60)
        
        self.setup_gui()
        self.auto_detect_and_connect()
        
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()
    
    # ================= MAPPING =================
    def display_to_servo(self, display_angle):
        # Display 0° → Servo 30°, Display 90° → Servo 90°
        return 30 + int(display_angle * 2 / 3)
    
    def servo_to_display(self, servo_angle):
        # Servo 30° → Display 0°, Servo 90° → Display 90°
        return int((servo_angle - 30) * 1.5)
        
    # ================= SERIAL =================
    def list_available_ports(self):
        ports = serial.tools.list_ports.comports()
        available = []
        print("\n📡 Available COM Ports:")
        if not ports:
            print(" No COM ports found!")
        for port in ports:
            print(f"   • {port.device} - {port.description}")
            available.append(port.device)
        print()
        return available
    
    def auto_detect_and_connect(self):
        available_ports = self.list_available_ports()
        
        if not available_ports:
            self.status_label.config(text=" Error: No COM ports found", fg="#ff4444")
            messagebox.showerror("No Ports", "No COM ports detected!")
            return False
        
        if 'COM7' in available_ports:
            if self.connect_to_port('COM7'):
                return True
        
        for port in available_ports:
            if self.connect_to_port(port):
                return True
        
        self.status_label.config(text=" Connection Failed", fg="#ff4444")
        self.show_troubleshooting()
        return False
    
    def connect_to_port(self, port_name):
        print(f"🔌 Attempting connection to {port_name}...")
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            
            self.serial_port = serial.Serial(port_name, 9600, timeout=2)
            time.sleep(2.5)
            
            self.port_name = port_name
            self.status_label.config(text=f" Connected: {port_name}", fg="#00ff00")
            self.root.title(f"Digital Twin Gripper - {port_name}")
            print(f" Successfully connected to {port_name}!\n")
            return True
            
        except Exception as e:
            print(f" {port_name}: {e}")
            return False
    
    def show_troubleshooting(self):
        messagebox.showwarning("Connection Failed",
            "Could not connect to Arduino!\n\n"
            "• Close Arduino IDE Serial Monitor\n"
            "• Unplug and replug USB cable\n"
            "• Run as Administrator")
    
    # ================= GUI =================
    def setup_gui(self):
        Label(self.root, text=" DIGITAL TWIN GRIPPER", 
              font=("Arial", 18, "bold"), bg="#2b2b2b", fg="#00ff00").pack(pady=15)
        
        control_frame = Frame(self.root, bg="#3a3a3a", padx=20, pady=20)
        control_frame.pack(side=TOP, fill=X, padx=20)
        
        self.status_label = Label(control_frame, text=" Detecting ports...", 
                                 font=("Arial", 12, "bold"), fg="#FFC107", bg="#3a3a3a")
        self.status_label.pack(pady=5)
        
        Button(control_frame, text=" Reconnect", 
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
        
        Button(button_frame, text=" OPEN (90°)", 
               command=lambda: self.set_position(90),
               bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
               padx=20, pady=12).pack(side=LEFT, padx=5)
        
        Button(button_frame, text=" HALF (45°)", 
               command=lambda: self.set_position(45),
               bg="#FFC107", fg="white", font=("Arial", 11, "bold"),
               padx=20, pady=12).pack(side=LEFT, padx=5)
        
        Button(button_frame, text=" CLOSE (0°)", 
               command=lambda: self.set_position(0),
               bg="#f44336", fg="white", font=("Arial", 11, "bold"),
               padx=20, pady=12).pack(side=LEFT, padx=5)

        # >>> SENSOR MODE TOGGLE BUTTON <<<
        self.sensor_btn = Button(control_frame, text="Sensor: OFF", 
                                 command=self.toggle_sensor_mode,
                                 bg="#555", fg="white", font=("Arial", 11, "bold"),
                                 padx=20, pady=10)
        self.sensor_btn.pack(pady=10)
        
        self.position_label = Label(control_frame, text="Current: 90°", 
                                   font=("Arial", 16, "bold"), bg="#3a3a3a", fg="#00ff00")
        self.position_label.pack(pady=10)
        
        self.canvas = Canvas(self.root, width=850, height=400, bg="#1a1a1a", 
                           highlightthickness=2, highlightbackground="#00ff00")
        self.canvas.pack(padx=20, pady=10)
        
        self.draw_gripper()
    
    # ================= SENSOR MODE =================
    def toggle_sensor_mode(self):
        self.manual_mode = not self.manual_mode
        
        if self.manual_mode:
            self.sensor_btn.config(text="Sensor: ON", bg="#4CAF50")
            if self.serial_port:
                self.serial_port.write(b"MODE:MANUAL\n")
            print(" Sensor mode ENABLED")
        else:
            self.sensor_btn.config(text="Sensor: OFF", bg="#555")
            if self.serial_port:
                self.serial_port.write(b"MODE:DIGITAL\n")
            print(" Digital mode ENABLED")
    
    def reconnect(self):
        self.status_label.config(text=" Reconnecting...", fg="#FFC107")
        self.root.update()
        self.auto_detect_and_connect()
    
    # ================= SEND TO ARDUINO =================
    def send_position(self, display_position):
        if self.serial_port and self.serial_port.is_open and not self.manual_mode:
            try:
                servo_angle = self.display_to_servo(display_position)
                self.serial_port.write(b"MODE:DIGITAL\n")
                time.sleep(0.05)
                command = f"GRIP:{servo_angle}\n"
                self.serial_port.write(command.encode())
                print(f" Sent: GRIP:{servo_angle} (Display: {display_position}°)")
                return True
            except Exception as e:
                print(f" Send error: {e}")
                return False
        return False
    
    def on_slider_change(self, value):
        position = int(float(value))
        self.set_position(position)
    
    def set_position(self, display_position):
        if self.manual_mode:
            return   # Ignore UI control in sensor mode
        
        self.is_animating = False
        self.current_position = display_position
        self.position_slider.set(display_position)
        self.position_label.config(text=f"Current: {display_position}°")
        self.send_position(display_position)
        self.draw_gripper()
    
    # ================= DRAW =================
    def draw_gripper(self):
        self.canvas.delete("all")
        
        normalized = self.current_position / 90.0
        visual_angle = 2 + 70 * normalized
        angle_rad = math.radians(visual_angle)
        
        cx, cy = 425, 200
        
        self.canvas.create_rectangle(cx-50, cy+90, cx+50, cy+130, 
                                     fill="#333", outline="#00ff00", width=2)
        
        self.canvas.create_oval(cx-60, cy-25, cx+60, cy+85, 
                               fill="#222", outline="#00ff00", width=3)
        
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
        
        self.canvas.create_text(cx, 360, 
                               text=f"Angle: {self.current_position}°",
                               font=("Courier", 13, "bold"), fill="#00ff00")
    
    # ================= UPDATE FROM ARDUINO =================
    def update_position_from_arduino(self, servo_position):
        display_position = self.servo_to_display(servo_position)
        self.current_position = display_position
        self.position_slider.set(display_position)
        self.position_label.config(text=f"Current: {display_position}°")
        self.draw_gripper()
    
    # ================= SERIAL READ LOOP =================
    def update_loop(self):
        while self.running:
            if self.serial_port and self.serial_port.is_open:
                try:
                    if self.serial_port.in_waiting:
                        response = self.serial_port.readline().decode().strip()
                        print(f" Received: {response}")
                        
                        # DIGITAL MODE FEEDBACK
                        if response.startswith("POS:"):
                            new_position = int(response.split(":")[1])
                            self.root.after(0, self.update_position_from_arduino, new_position)
                        
                        # MANUAL MODE FEEDBACK (SENSOR)
                        elif response.startswith("SENSOR:"):
                            data = response.replace("SENSOR:", "")
                            angle_str, dist_str = data.split(",")
                            servo_angle = int(float(angle_str))
                            
                            # Update digital twin only (NO GRIP back!)
                            self.root.after(0, self.update_position_from_arduino, servo_angle)
                
                except Exception as e:
                    print("Serial read error:", e)
            time.sleep(0.05)
    
    def cleanup(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print(" Disconnected from Arduino")

def main():
    root = Tk()
    app = DigitalTwinGripper(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
