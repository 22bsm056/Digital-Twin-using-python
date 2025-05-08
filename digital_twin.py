#!/usr/bin/env python3
import serial
import time
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import threading
import math
import sys
import os

# Initialize GLUT if available, but provide fallback
try:
    from OpenGL.GLUT import *
    glutInit()  # Initialize GLUT
    GLUT_AVAILABLE = True
except Exception:
    GLUT_AVAILABLE = False

# Servo Digital Twin Class
class ServoDigitalTwin:
    def __init__(self, port=None, baud_rate=9600):
        self.angle = 90  # Initial angle
        self.target_angle = 90  # Target angle for smooth transitions
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connected = False
        self.running = True
        self.lock = threading.Lock()
        self.arduino = None
        self.step_size = 10  # Changed from 5 to 10 degrees
        
        # Setup PyGame and OpenGL
        pygame.init()
        display = (800, 600)
        pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
        pygame.display.set_caption('Servo Motor Digital Twin')
        
        # Initialize default font for text rendering
        pygame.font.init()
        if not pygame.font.get_init():
            print("Warning: Font initialization failed")
        
        # OpenGL initialization
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)
        glTranslatef(0.0, 0.0, -5)
        glEnable(GL_DEPTH_TEST)
        
        # Lighting (optional but makes the model look better)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [1, 1, 1, 0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1])
        
        # Connect to Arduino if port is specified
        if self.port:
            self.connect_to_arduino()
        else:
            print("No port specified. Running in simulation mode.")
        
        # Start serial reading thread if connected
        if self.serial_connected:
            self.serial_thread = threading.Thread(target=self.read_from_arduino)
            self.serial_thread.daemon = True
            self.serial_thread.start()
    
    def connect_to_arduino(self):
        """Attempt to connect to the Arduino"""
        try:
            # Try to close any existing connection first
            if self.arduino:
                try:
                    self.arduino.close()
                except:
                    pass
            
            # Connect to the serial port with more robust settings
            self.arduino = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=1,
                write_timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Wait for connection to establish
            time.sleep(2)
            
            # Check if connection is actually working
            if self.arduino.is_open:
                self.serial_connected = True
                print(f"Connected to Arduino on {self.port}")
                
                # Try to send a test message and read response
                try:
                    self.arduino.write(b"S:90\n")
                    time.sleep(0.5)
                    if self.arduino.in_waiting > 0:
                        response = self.arduino.readline()
                        print(f"Arduino response: {response.decode('utf-8', errors='replace').strip()}")
                except Exception as e:
                    print(f"Warning: Test message failed but continuing: {e}")
            else:
                raise Exception("Port could not be opened")
                
        except Exception as e:
            print(f"Failed to connect to Arduino: {e}")
            print("Running in simulation mode")
            self.arduino = None
            self.serial_connected = False
    
    def read_from_arduino(self):
        """Thread function to read data from Arduino"""
        if not self.serial_connected:
            return
        
        while self.running:
            try:
                if self.arduino and self.arduino.is_open and self.arduino.in_waiting > 0:
                    line = self.arduino.readline().decode('utf-8', errors='replace').strip()
                    if line.startswith("A:"):
                        # Update angle from physical servo
                        with self.lock:
                            try:
                                new_angle = int(line[2:])
                                if 0 <= new_angle <= 180:
                                    self.angle = new_angle
                                    self.target_angle = new_angle
                                    print(f"Servo angle: {self.angle}°")
                            except ValueError:
                                pass
                time.sleep(0.05)  # Small delay to prevent CPU hogging
            except Exception as e:
                print(f"Serial reading error: {e}")
                # Don't break the loop - try to recover
                try:
                    if self.arduino and self.arduino.is_open:
                        self.arduino.close()
                    time.sleep(1)  # Wait before attempting reconnection
                    self.connect_to_arduino()  # Try to reconnect
                except Exception:
                    time.sleep(2)  # Wait longer before next attempt
    
    def send_to_arduino(self, angle):
        """Send angle command to Arduino"""
        if self.serial_connected and self.arduino and self.arduino.is_open:
            try:
                # Format: S:angle\n
                command = f"S:{angle}\n"
                self.arduino.write(command.encode())
                print(f"Sent to Arduino: {angle}°")
            except Exception as e:
                print(f"Error sending to Arduino: {e}")
                # Try to reconnect if there's an error
                try:
                    self.arduino.close()
                    self.connect_to_arduino()
                except:
                    pass
    
    def update_angle(self, new_angle):
        """Update the servo angle and send to Arduino"""
        with self.lock:
            if 0 <= new_angle <= 180:
                self.target_angle = new_angle
                if self.serial_connected:
                    self.send_to_arduino(new_angle)
    
    def draw_servo(self):
        """Draw the 3D servo model"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        try:
            # Draw base (cylinder)
            glPushMatrix()
            glColor3f(0.2, 0.2, 0.2)  # Dark gray
            self.draw_cylinder(0.5, 0.5, 0.3, 20)
            glPopMatrix()
            
            # Draw servo body (box)
            glPushMatrix()
            glTranslatef(0, 0, 0.3)
            glColor3f(0.0, 0.3, 0.7)  # Blue
            self.draw_cube(1.0, 1.0, 0.5)
            glPopMatrix()
            
            # Draw rotating shaft with current angle
            glPushMatrix()
            glTranslatef(0, 0, 0.8)
            glRotatef(self.angle, 0, 0, 1)  # Apply rotation around z-axis
            
            # Draw shaft
            glColor3f(0.7, 0.7, 0.7)  # Light gray
            self.draw_cylinder(0.1, 0.1, 0.2, 10)
            
            # Draw horn
            glPushMatrix()
            glTranslatef(0, 0, 0.2)
            glColor3f(1.0, 0.5, 0.0)  # Orange
            self.draw_horn()
            glPopMatrix()
            
            glPopMatrix()
            
            # Draw angle text (position moved to make it more visible)
            self.render_text(f"Angle: {int(self.angle)}°", -1.5, -1.5, -3)
            
            # Add connection status
            status = "Connected" if (self.arduino and self.arduino.is_open) else "Disconnected"
            color = "green" if (self.arduino and self.arduino.is_open) else "red"
            status_text = f"Arduino: {status}"
            self.render_text(status_text, -1.5, -1.7, -3)
            
            pygame.display.flip()
            
        except Exception as e:
            print(f"Error in draw_servo: {e}")
            # Attempt to recover from rendering errors
            try:
                pygame.display.flip()
            except:
                pass
    
    def render_text(self, text, x, y, z):
        """Simple method to render text in OpenGL (using Pygame instead of GLUT for compatibility)"""
        # Skip text rendering if no text to display
        if not text:
            return
            
        # Disable lighting for text rendering
        glDisable(GL_LIGHTING)
        
        # Create a Pygame surface with the text
        font = pygame.font.SysFont('Arial', 24)
        text_surface = font.render(text, True, (255, 255, 255))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        
        # Enable texture for text rendering
        glEnable(GL_TEXTURE_2D)
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        
        # Set texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(), 
                    0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
        # Position and draw the text as a textured quad
        glColor3f(1.0, 1.0, 1.0)  # White
        width, height = text_surface.get_width() / 250, text_surface.get_height() / 250
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(x, y, z)
        glTexCoord2f(1, 0); glVertex3f(x + width, y, z)
        glTexCoord2f(1, 1); glVertex3f(x + width, y + height, z)
        glTexCoord2f(0, 1); glVertex3f(x, y + height, z)
        glEnd()
        
        # Clean up
        glDeleteTextures(1, [texture_id])
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
    
    def draw_cube(self, width, height, depth):
        """Draw a simple cube"""
        w, h, d = width/2, height/2, depth/2
        vertices = [
            [w, h, d], [-w, h, d], [-w, -h, d], [w, -h, d],
            [w, h, -d], [-w, h, -d], [-w, -h, -d], [w, -h, -d]
        ]
        
        glBegin(GL_QUADS)
        # Front face
        glNormal3f(0, 0, 1)
        glVertex3fv(vertices[0])
        glVertex3fv(vertices[1])
        glVertex3fv(vertices[2])
        glVertex3fv(vertices[3])
        
        # Back face
        glNormal3f(0, 0, -1)
        glVertex3fv(vertices[4])
        glVertex3fv(vertices[7])
        glVertex3fv(vertices[6])
        glVertex3fv(vertices[5])
        
        # Top face
        glNormal3f(0, 1, 0)
        glVertex3fv(vertices[0])
        glVertex3fv(vertices[4])
        glVertex3fv(vertices[5])
        glVertex3fv(vertices[1])
        
        # Bottom face
        glNormal3f(0, -1, 0)
        glVertex3fv(vertices[3])
        glVertex3fv(vertices[2])
        glVertex3fv(vertices[6])
        glVertex3fv(vertices[7])
        
        # Right face
        glNormal3f(1, 0, 0)
        glVertex3fv(vertices[0])
        glVertex3fv(vertices[3])
        glVertex3fv(vertices[7])
        glVertex3fv(vertices[4])
        
        # Left face
        glNormal3f(-1, 0, 0)
        glVertex3fv(vertices[1])
        glVertex3fv(vertices[5])
        glVertex3fv(vertices[6])
        glVertex3fv(vertices[2])
        glEnd()
    
    def draw_cylinder(self, base_radius, top_radius, height, slices):
        """Draw a cylinder"""
        glBegin(GL_QUAD_STRIP)
        for i in range(slices + 1):
            angle = 2.0 * math.pi * i / slices
            x = math.cos(angle)
            y = math.sin(angle)
            
            # Calculate normals
            nx, ny = x, y
            norm = math.sqrt(nx*nx + ny*ny)
            if norm > 0:
                nx, ny = nx/norm, ny/norm
            
            glNormal3f(nx, ny, 0)
            glVertex3f(base_radius * x, base_radius * y, 0)
            glVertex3f(top_radius * x, top_radius * y, height)
        glEnd()
        
        # Draw top and bottom circles
        self.draw_circle(0, 0, 0, base_radius, slices, False)
        self.draw_circle(0, 0, height, top_radius, slices, True)
    
    def draw_circle(self, x, y, z, radius, slices, facing_up=True):
        """Draw a circle at given position"""
        glBegin(GL_TRIANGLE_FAN)
        if facing_up:
            glNormal3f(0, 0, 1)
        else:
            glNormal3f(0, 0, -1)
            
        glVertex3f(x, y, z)  # Center
        for i in range(slices + 1):
            angle = 2.0 * math.pi * i / slices
            cx = x + radius * math.cos(angle)
            cy = y + radius * math.sin(angle)
            glVertex3f(cx, cy, z)
        glEnd()
    
    def draw_horn(self):
        """Draw a servo horn (cross shape)"""
        # Main arm of the horn
        glPushMatrix()
        glScalef(0.8, 0.2, 0.1)
        self.draw_cube(1.0, 1.0, 1.0)
        glPopMatrix()
        
        # Cross arm of the horn
        glPushMatrix()
        glScalef(0.2, 0.8, 0.1)
        self.draw_cube(1.0, 1.0, 1.0)
        glPopMatrix()
    
    def handle_events(self):
        """Handle PyGame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False
                
            # Mouse wheel for rotation
            elif event.type == pygame.MOUSEWHEEL:
                # Calculate new angle based on scroll direction
                delta = event.y * self.step_size  # Using step_size with mouse wheel
                new_angle = max(0, min(180, self.target_angle + delta))
                self.update_angle(new_angle)
                
            # Arrow keys for rotation
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT or event.key == pygame.K_DOWN:
                    new_angle = max(0, self.target_angle - self.step_size)  # Using step_size for arrow keys
                    self.update_angle(new_angle)
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_UP:
                    new_angle = min(180, self.target_angle + self.step_size)  # Using step_size for arrow keys
                    self.update_angle(new_angle)
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                    return False
        return True
    
    def smooth_angle_update(self):
        """Smoothly update the angle towards the target for visual effect"""
        if abs(self.angle - self.target_angle) > 0.5:
            direction = 1 if self.target_angle > self.angle else -1
            self.angle += direction * 1.5  # Speed of animation
            
            # Ensure we don't overshoot
            if direction > 0 and self.angle > self.target_angle:
                self.angle = self.target_angle
            elif direction < 0 and self.angle < self.target_angle:
                self.angle = self.target_angle
    
    def run(self):
        """Main application loop"""
        clock = pygame.time.Clock()
        
        try:
            while self.running:
                if not self.handle_events():
                    break
                    
                self.smooth_angle_update()
                self.draw_servo()
                clock.tick(60)  # 60 FPS
                
        except KeyboardInterrupt:
            print("Received keyboard interrupt, shutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.serial_connected and self.arduino and self.arduino.is_open:
            try:
                self.arduino.close()
            except Exception as e:
                print(f"Error closing serial port: {e}")
        pygame.quit()
        print("Digital Twin terminated")


def detect_arduino_port():
    """Auto-detect Arduino port"""
    ports = []
    
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        # First look for Arduino or USB Serial Device
        for port in ports:
            if "Arduino" in port.description or "USB" in port.description:
                print(f"Found likely Arduino device: {port.device} - {port.description}")
                return port.device
        
        # If no specific Arduino found, print available ports
        if ports:
            print("Available serial ports:")
            for i, port in enumerate(ports):
                print(f"  {i+1}. {port.device} - {port.description}")
            
            # Return first available port if any exist
            return ports[0].device
        else:
            print("No serial ports found.")
            
    except ImportError:
        print("Serial port detection requires 'pyserial' module.")
    except Exception as e:
        print(f"Error detecting ports: {e}")
    
    # Default fallbacks based on OS
    if sys.platform.startswith('win'):
        return 'COM3'  # Common Windows Arduino port
    elif sys.platform.startswith('linux'):
        # Check common Linux Arduino ports
        for device in ['/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyS0']:
            if os.path.exists(device):
                return device
    elif sys.platform.startswith('darwin'):  # macOS
        return '/dev/cu.usbmodem1101'  # Common macOS Arduino port
    
    # No valid port found - return None to run in simulation mode
    return None


def list_ports():
    """List all available serial ports"""
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if ports:
            print("Available serial ports:")
            for i, port in enumerate(ports):
                print(f"  {i+1}. {port.device} - {port.description}")
        else:
            print("No serial ports found.")
    except ImportError:
        print("Serial port listing requires 'pyserial' module.")
    except Exception as e:
        print(f"Error listing ports: {e}")


def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Servo Motor Digital Twin')
    parser.add_argument('--port', help='Arduino serial port (e.g., COM3, /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=9600, help='Baud rate (default: 9600)')
    parser.add_argument('--list-ports', action='store_true', help='List available serial ports and exit')
    parser.add_argument('--sim', action='store_true', help='Run in simulation mode (no Arduino)')
    args = parser.parse_args()
    
    # List ports if requested
    if args.list_ports:
        list_ports()
        return
        
    # Print welcome message
    print("Starting Servo Digital Twin")
    print("Controls: Arrow keys or mouse wheel to rotate servo")
    print("Press ESC to exit")
    
    # Determine the port
    port = None
    if not args.sim:  # Skip port detection if simulation mode is requested
        if args.port:
            port = args.port
        else:
            port = detect_arduino_port()
            
    # Create the digital twin instance
    try:
        if port:
            print(f"Using port: {port}")
        else:
            print("Running in simulation mode (no Arduino connection)")
            
        digital_twin = ServoDigitalTwin(port=port, baud_rate=args.baud)
        digital_twin.run()
    except Exception as e:
        print(f"Error running digital twin: {e}")
        
        # Keep window open for error viewing
        import traceback
        traceback.print_exc()
        try:
            print("\nPress Enter to exit...")
            input()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
