#!/usr/bin/env python3
import rospy
import os
from os.path import join, dirname
import subprocess
import logging
import time
import json

# Configure logging with more details
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('motor_reader.log')
    ]
)
logger = logging.getLogger(__name__)

# Try to load environment variables, but provide defaults if .env file is missing
try:
    from dotenv import load_dotenv
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    logger.info(f"Loaded environment from {dotenv_path}")
except ImportError:
    logger.warning("python-dotenv not installed, using default environment variables")
except Exception as e:
    logger.warning(f"Failed to load .env file: {e}")

# Get environment variables with defaults
ROS_MASTER_URI = os.environ.get("ROS_MASTER_URI")
ROS_MASTER_USER = os.environ.get("ROS_MASTER_USER")
ROS_MASTER_PASSWD = os.environ.get("ROS_MASTER_PASSWD")

if not ROS_MASTER_PASSWD:
    logger.warning("ROS_MASTER_PASSWD environment variable not set, SSH connections may fail")

class MotorController:
    def __init__(self, ssh_host: str="192.168.1.100", ssh_user: str=None, ssh_passwd:str=None, rate: int=120):
        """
        Initialize a motor controller for a specific robot.
        
        Parameters:
            ssh_host (str): IP address of the target robot (defaults to base8 IP)
            ssh_user (str): SSH username (defaults to environment variable)
            ssh_passwd (str): SSH password (defaults to environment variable)
            rate (int): Rate for ROS node (Hz)
        """
        self.ROS_MASTER_URI = f"http://{ssh_host}:11311"
        self.ssh_host = ssh_host
        self.ssh_user = ROS_MASTER_USER
        self.ssh_passwd = ROS_MASTER_PASSWD
        self.connection_attempts = 0
        self.max_connection_attempts = 10
        self.connection_timeout = 15
        self.cmd_timeout = 20
        self.topic_verified = False
        
        logger.info(f"Initializing MotorController for {ssh_host}")

        
        os.environ["ROS_MASTER_URI"] = self.ROS_MASTER_URI
        try:
            rospy.init_node(f'motor_data_reader_{ssh_host.replace(".", "_")}', anonymous=True)
            self.rate = rospy.Rate(rate)
            logger.info(f"Initialized ROS node for {ssh_host}")
        except Exception as e:
            logger.error(f"Failed to initialize ROS node for {ssh_host}: {e}")
            self.rate = None

    def verify_motor_topic(self) -> bool:
        """
        Verify if the motor topic exists on the robot
        
        Returns:
            bool: True if topic exists, False otherwise
        """
        if self.topic_verified:
            return True
            
        try:
            # Check if the topic exists
            cmd = (
                f"sshpass -p '{self.ssh_passwd}' ssh "
                f"-o ConnectTimeout={self.connection_timeout} "
                f"-o StrictHostKeyChecking=no "
                f"{self.ssh_user}@{self.ssh_host} "
                f"'source /opt/ros/noetic/setup.bash && "
                f"source ~/catkin_ws/devel/setup.bash && "
                f"rostopic list | grep flexa_motor_controller'"
            )
            
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate(timeout=10)
            
            if output:
                logger.info(f"Verified motor topic on {self.ssh_host}: {output.decode().strip()}")
                self.topic_verified = True
                return True
            else:
                logger.warning(f"Motor topic not found on {self.ssh_host}")
                # List all available topics for diagnosis
                self.list_available_topics()
                return False
                
        except Exception as e:
            logger.error(f"Error verifying motor topic: {e}")
            return False
    
    def list_available_topics(self):
        """List all available topics on the robot for diagnosis"""
        try:
            cmd = (
                f"sshpass -p '{self.ssh_passwd}' ssh "
                f"-o ConnectTimeout={self.connection_timeout} "
                f"-o StrictHostKeyChecking=no "
                f"-o BatchMode=no "
                f"{self.ssh_user}@{self.ssh_host} "
                f"'source /opt/ros/noetic/setup.bash && "
                f"source ~/catkin_ws/devel/setup.bash && "
                f"rostopic list'"
            )

            
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate(timeout=10)
            
            if output:
                topics = output.decode().strip().split("\n")
                logger.info(f"Available topics on {self.ssh_host} ({len(topics)} topics):")
                for topic in topics:
                    if 'motor' in topic or 'joint' in topic or 'state' in topic:
                        logger.info(f"  Relevant topic: {topic}")
            else:
                logger.warning(f"No topics found on {self.ssh_host}")
                
        except Exception as e:
            logger.error(f"Error listing topics: {e}")

    def read_motor_data(self) -> dict:
        """
        Read motor data and parse it into a dictionary with error handling and validation.
        """
        print("? DEBUG: read_motor_data called for " + self.ssh_host)

        print(f"{self.ssh_user}@{self.ssh_host} w/ {self.ssh_passwd}")
        
        # Don't keep trying if we've exceeded max attempts
        if self.connection_attempts >= self.max_connection_attempts:
            print("? DEBUG: Max connection attempts reached, skipping")
            self.connection_attempts = 0
            return None
            
        try:
            # Enhanced SSH command with longer timeouts and retries
            print("? DEBUG: Preparing to execute SSH command")
            cmd = (
                f"sshpass -p '{self.ssh_passwd}' ssh "
                f"-o ConnectTimeout={self.connection_timeout} "
                f"-o StrictHostKeyChecking=no "
                f"-o ServerAliveInterval=5 "
                f"-o ServerAliveCountMax=3 "
                f"-o BatchMode=no "
                f"-o LogLevel=ERROR "
                f"{self.ssh_user}@{self.ssh_host} "
                f"'source /opt/ros/noetic/setup.bash && "
                f"source ~/catkin_ws/devel/setup.bash && "
                f"rostopic echo -n 1 /flexa_motor_controller/motor_agg_info'"
            )
            
            print("? DEBUG: Executing SSH command for " + self.ssh_host)
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, error = process.communicate(timeout=self.cmd_timeout)
            
            print("? DEBUG: SSH command completed with return code " + str(process.returncode))
            
            if error:
                error_text = error.decode()
                print(f"? DEBUG: SSH error: {error_text[:100]}")
                if "Connection refused" in error_text or "Connection timed out" in error_text:
                    self.connection_attempts += 1
                    logger.error(f"Connection error ({self.connection_attempts}/{self.max_connection_attempts}) for {self.ssh_host}: {error_text}")
                else:
                    logger.error(f"Command error for {self.ssh_host}: {error_text}")
                return None
                
            if not output:
                self.connection_attempts += 1
                logger.error(f"No data received from motors on {self.ssh_host} (attempt {self.connection_attempts}/{self.max_connection_attempts})")
                return None
                
            # Parse the output
            output_str = output.decode()
            logger.debug(f"Raw output from {self.ssh_host}: {output_str[:100]}")

            # Parse the real data first
            motor_data = self._parse_motor_data(output_str)

            # For debugging only - parse test data to check parser works, but don't use the result
            test_data = self._parse_motor_data("motor1: \n  pos_rad: 96853.57659399601\n  pos_offset: -0.0007363080000000001\n  vel_rpm: 0.0\n  vel_rad: 0.0\n  current: 0.338\nmotor2: \n  pos_rad: 97109.83687382701\n  pos_offset: -0.0007976670000000001\n  vel_rpm: -0.20000053920000002\n  vel_rad: -0.020944\n  current: 0.605")
            print(f"? DEBUG: Test parsing works: {test_data is not None and len(test_data) > 0}")

            # Log the real data results
            if motor_data:
                self._log_motor_data(motor_data)
                self.connection_attempts = 0
                logger.info(f"Successfully parsed motor data from {self.ssh_host}")
                return motor_data
            else:
                self.connection_attempts += 1
                logger.warning(f"Failed to parse valid motor data from {self.ssh_host}")
                return None

        except subprocess.TimeoutExpired:
            self.connection_attempts += 1
            logger.error(f"Timeout ({self.connection_attempts}/{self.max_connection_attempts}) connecting to {self.ssh_host} for motor data")
            return None
        except Exception as e:
            self.connection_attempts += 1
            logger.error(f"Unexpected error ({self.connection_attempts}/{self.max_connection_attempts}) reading motor data from {self.ssh_host}: {e}")
            return None
        
        
    
    def _parse_motor_data(self, output_str) -> dict:
        """Internal method to parse motor data output with fixed robust parsing"""
        print("\n\n??? MOTOR DEBUG ???")
        print("? DEBUG: Starting motor parsing for " + self.ssh_host)
        try:
            # Expected fields and motors
            EXPECTED_FIELDS = {'pos_rad', 'pos_offset', 'vel_rpm', 'vel_rad', 'current'}
            EXPECTED_MOTORS = {'motor1', 'motor2'}
                
            # Parse the output into a dictionary
            motor_data = {}
            current_motor = None
            
            # First, try to parse line by line
            for line in output_str.split('\n'):
                line = line.strip()
                if not line or line.startswith('[INFO]'):
                    continue
                    
                # Handle motor header lines (with or without colon)
                if line.lower().startswith('motor'):
                    # Extract motor name
                    if ':' in line:
                        current_motor = line.split(':')[0].strip().lower()
                    else:
                        current_motor = line.strip().lower()
                    
                    print(f"? DEBUG: Found motor header: '{current_motor}'")
                    
                    if current_motor not in EXPECTED_MOTORS:
                        print(f"? DEBUG: Unexpected motor identifier: {current_motor}")
                    
                    motor_data[current_motor] = {}
                    
                # Handle data lines that have a colon
                elif current_motor and ':' in line:
                    try:
                        key, value = line.split(':', 1)  # Split on first colon only
                        key = key.strip().lower()
                        
                        if key not in EXPECTED_FIELDS:
                            print(f"? DEBUG: Unexpected field {key} for {current_motor}")
                            continue
                            
                        try:
                            value_str = value.strip()
                            value = float(value_str)
                            motor_data[current_motor][key] = value
                            print(f"? DEBUG: {current_motor}.{key} = {value}")
                        except ValueError:
                            print(f"? DEBUG: Failed to convert value to float: '{value_str}' for {key}")
                            motor_data[current_motor][key] = 0.0  # Default value on error
                            
                    except ValueError:
                        print(f"? DEBUG: Malformed line: '{line}'")
                        continue
            
            print("? DEBUG: PARSING RESULT:")
            print(f"? motor1: {motor_data.get('motor1', {})}")
            print(f"? motor2: {motor_data.get('motor2', {})}")
            print("??? END MOTOR DEBUG ???\n")
            return motor_data
            
        except Exception as e:
            print(f"? ERROR in parsing: {str(e)}")
            return {"motor1": {}, "motor2": {}}
    
    def _log_motor_data(self, motor_data: dict):
        """Log motor data values for debugging"""
        try:
            # Check for non-zero values
            motor1_values = motor_data.get('motor1', {})
            motor2_values = motor_data.get('motor2', {})
            non_zero_fields = []
            
            if motor1_values.get('pos_rad', 0) != 0 or motor2_values.get('pos_rad', 0) != 0:
                non_zero_fields.append('pos_rad')
            if motor1_values.get('vel_rpm', 0) != 0 or motor2_values.get('vel_rpm', 0) != 0:
                non_zero_fields.append('vel_rpm')
            if motor1_values.get('current', 0) != 0 or motor2_values.get('current', 0) != 0:
                non_zero_fields.append('current')
                
            if non_zero_fields:
                logger.info(f"Robot {self.ssh_host} has non-zero motor values for: {', '.join(non_zero_fields)}")
            else:
                logger.warning(f"Robot {self.ssh_host} returned ALL ZEROS for motor values")
                
            # For debugging, show a compact representation of the data
            compact_data = {
                'motor1': {k: f"{v:.2f}" for k, v in motor1_values.items()},
                'motor2': {k: f"{v:.2f}" for k, v in motor2_values.items()}
            }
            logger.debug(f"Motor data summary: {json.dumps(compact_data)}")
            
        except Exception as e:
            logger.error(f"Error logging motor data: {e}")
    
    def generate_test_data(self) -> dict:
        """
        Generate test motor data when real data isn't available
        
        Returns:
            dict: Simulated motor data with the expected structure
        """
        # Only generate test data after multiple failed attempts
        if self.connection_attempts < 5:
            return None
            
        logger.warning(f"Generating test data for {self.ssh_host} after {self.connection_attempts} failed attempts")
        
        # Create simulated data with non-zero values
        return {
            "motor1": {
                "pos_rad": 1.57, 
                "pos_offset": 0.05, 
                "vel_rpm": 120.5, 
                "vel_rad": 12.6, 
                "current": 2.3
            },
            "motor2": {
                "pos_rad": 2.14, 
                "pos_offset": 0.02, 
                "vel_rpm": 135.2, 
                "vel_rad": 14.1, 
                "current": 2.7
            }
        }
    
    def get_motor_data(self, allow_test_data=False) -> dict:
        """
        Get motor data with fallback to test data if needed
        
        Parameters:
            allow_test_data (bool): Whether to allow test data generation
        
        Returns:
            dict: Motor data, either real or simulated
        """
        # Try to get real data first
        motor_data = self.read_motor_data()
        
        # If real data not available and test data allowed, generate test data
        if motor_data is None and allow_test_data:
            motor_data = self.generate_test_data()
            
        # If we still have no data, create an empty structure
        if motor_data is None:
            motor_data = {
                "motor1": {"pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, "vel_rad": 0.0, "current": 0.0},
                "motor2": {"pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, "vel_rad": 0.0, "current": 0.0}
            }
            
        return motor_data

    def set_rate(self, new_rate):
        self.rate = rospy.Rate(new_rate)

if __name__ == '__main__':
    try:
        controller = MotorController(rate=5)  # Example: 0.5 Hz = every 2 seconds
        while not rospy.is_shutdown():
            motor_data = controller.get_motor_data(allow_test_data=True)
            logger.info(f"Got motor data: {motor_data is not None}")
            controller.rate.sleep()
    except rospy.ROSInterruptException:
        pass