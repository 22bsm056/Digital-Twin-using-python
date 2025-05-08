#!/usr/bin/env python3
import serial
import time
import os
import sys

def detect_arduino_port():
    """Auto-detect Arduino port"""
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        # First look for Arduino or USB Serial Device
        for port in ports:
            if "Arduino" in port.description or "USB" in port.description:
                print(f"Found likely Arduino device: {port.device} - {port.description}")
                return port.device
        
        # If no specific Arduino found, return first available port
        if ports:
            print(f"Using first available port: {ports[0].device} - {ports[0].description}")
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
    
    # No valid port found
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
            return True
        else:
            print("No serial ports found.")
            return False
    except ImportError:
        print("Serial port listing requires 'pyserial' module.")
        return False
    except Exception as e:
        print(f"Error listing ports: {e}")
        return False

def connect_to_arduino(port, baud_rate=9600):
    """Connect to Arduino with error handling"""
    try:
        arduino = serial.Serial(
            port=port,
            baudrate=baud_rate,
            timeout=1,
            write_timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        # Wait for connection to establish
        time.sleep(2)
        
        # Clear any startup messages
        arduino.reset_input_buffer()
        
        # Test communication
        arduino.write(b"S:90\n")
        time.sleep(0.5)
        
        response = ""
        start_time = time.time()
        while time.time() - start_time < 1:  # Try reading for up to 1 second
            if arduino.in_waiting > 0:
                response += arduino.readline().decode('utf-8', errors='replace').strip()
                if response.startswith("ACK:") or response.startswith("A:"):
                    print("Communication verified with Arduino.")
                    break
        
        print(f"Connected to Arduino on {port}")
        return arduino
    except Exception as e:
        print(f"Failed to connect to Arduino: {e}")
        return None

def send_command(arduino, angle):
    """Send command to Arduino using the proper protocol"""
    if arduino and arduino.is_open:
        try:
            # Format command according to the Arduino code protocol: S:angle\n
            command = f"S:{angle}\n"
            arduino.write(command.encode())
            
            # Wait for acknowledgment
            time.sleep(0.1)
            if arduino.in_waiting > 0:
                response = arduino.readline().decode('utf-8', errors='replace').strip()
                if response.startswith("ACK:"):
                    return True
            
            return True  # Even if no ACK, assume command was sent
        except Exception as e:
            print(f"Error sending command: {e}")
    return False

def read_status(arduino):
    """Read status updates from Arduino"""
    if arduino and arduino.is_open and arduino.in_waiting > 0:
        try:
            line = arduino.readline().decode('utf-8', errors='replace').strip()
            if line.startswith("A:"):
                try:
                    angle = int(line[2:])
                    return angle
                except ValueError:
                    pass
        except Exception as e:
            print(f"Error reading status: {e}")
    return None

def display_ui(current_position):
    """Display the user interface"""
    os.system('clear' if os.name != 'nt' else 'cls')  # Clear screen
    print("\n=== Servo Motor Controller ===")
    print(f"Current position: {current_position} degrees")
    print("\nChoose an option:")
    print("1: Rotate 5 degrees right")
    print("2: Rotate 5 degrees left")
    print("3: Set specific angle")
    print("4: Show available ports")
    print("q: Quit")

def main():
    """
    Main function to control a servo motor connected to Arduino
    from the terminal. The servo can be rotated by user input.
    """
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Servo Motor Controller')
    parser.add_argument('--port', help='Arduino serial port (e.g., COM3, /dev/ttyUSB0)')
    parser.add_argument('--baud', type=int, default=9600, help='Baud rate (default: 9600)')
    parser.add_argument('--list-ports', action='store_true', help='List available serial ports and exit')
    args = parser.parse_args()
    
    # List ports if requested
    if args.list_ports:
        list_ports()
        return
    
    # Determine the port
    port = args.port if args.port else detect_arduino_port()
    
    if not port:
        print("No Arduino port specified or detected.")
        if list_ports():
            port = input("Enter the port name (e.g., COM3, /dev/ttyACM0): ")
        else:
            return
    
    # Connect to Arduino
    arduino = connect_to_arduino(port, args.baud)
    if not arduino:
        print("Failed to connect to Arduino. Exiting.")
        return
    
    # Initial position value
    current_position = 90
    print(f"Initial position: {current_position} degrees (center)")
    
    # Send initial position to ensure sync
    if not send_command(arduino, current_position):
        print("Warning: Failed to send initial position.")
    
    try:
        while True:
            # Update position from Arduino if available
            status = read_status(arduino)
            if status is not None:
                current_position = status
            
            # Display UI
            display_ui(current_position)
            
            # Get user input
            choice = input("\nEnter your choice: ")
            
            if choice == '1':
                # Rotate right (increase position)
                if current_position < 180:  # Maximum servo position
                    current_position = min(180, current_position + 5)
                    if send_command(arduino, current_position):
                        print(f"Rotating right 5 degrees. New position: {current_position}")
                    else:
                        print("Failed to send command to Arduino.")
                else:
                    print("Cannot rotate further right. Maximum position reached.")
            
            elif choice == '2':
                # Rotate left (decrease position)
                if current_position > 0:  # Minimum servo position
                    current_position = max(0, current_position - 5)
                    if send_command(arduino, current_position):
                        print(f"Rotating left 5 degrees. New position: {current_position}")
                    else:
                        print("Failed to send command to Arduino.")
                else:
                    print("Cannot rotate further left. Minimum position reached.")
            
            elif choice == '3':
                # Set specific angle
                try:
                    angle = int(input("Enter angle (0-180): "))
                    if 0 <= angle <= 180:
                        current_position = angle
                        if send_command(arduino, current_position):
                            print(f"Setting position to {current_position} degrees.")
                        else:
                            print("Failed to send command to Arduino.")
                    else:
                        print("Invalid angle. Must be between 0 and 180.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            elif choice == '4':
                list_ports()
                input("Press Enter to continue...")
                
            elif choice.lower() == 'q':
                print("Exiting the program.")
                break
                
            else:
                print("Invalid choice. Please enter 1, 2, 3, 4, or q.")
                
            # Wait for Arduino to process the command
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    
    finally:
        # Close the serial connection
        if 'arduino' in locals() and arduino and arduino.is_open:
            arduino.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()
