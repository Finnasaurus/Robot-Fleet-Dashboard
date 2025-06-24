from flask import Flask, render_template, jsonify, request
from datetime import datetime
import traceback
import yaml
import os
import logging
import signal
import sys
import atexit

from ping_addresses import MultiPingChecker, RobotConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dashboard.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def load_robot_config():
    """Load robot configuration from config.yaml"""
    try:
        config = RobotConfig.load_config('config.yaml')
        return config
    except Exception as e:
        logger.error(f"Error loading robot config: {e}")
        return None

# Initialize with dynamic configuration
config = load_robot_config()

# Initialize components using the configuration
b2_ping_checker = None
rm_helper = None
motor_controller = None

def cleanup_resources():
    """Clean up all resources before shutdown"""
    global b2_ping_checker, rm_helper, motor_controller
    
    logger.info("Starting graceful shutdown...")
    
    # Stop ping checker
    if b2_ping_checker:
        try:
            logger.info("Stopping ping checker...")
            b2_ping_checker.stopPing()
            logger.info("Ping checker stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping ping checker: {e}")
    
    # Clean up motor controller
    if motor_controller:
        try:
            logger.info("Cleaning up motor controller...")
            # Add any specific cleanup for motor controller if needed
            motor_controller = None
        except Exception as e:
            logger.error(f"Error cleaning up motor controller: {e}")
    
    # Clean up rm_helper
    if rm_helper:
        try:
            logger.info("Cleaning up RM helper...")
            # Add any specific cleanup for rm_helper if needed
            rm_helper = None
        except Exception as e:
            logger.error(f"Error cleaning up RM helper: {e}")
    
    logger.info("Graceful shutdown completed")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    signal_names = {
        signal.SIGINT: 'SIGINT (Ctrl+C)',
        signal.SIGTERM: 'SIGTERM'
    }
    
    signal_name = signal_names.get(signum, f'Signal {signum}')
    logger.info(f"Received {signal_name}, shutting down gracefully...")
    
    cleanup_resources()
    
    logger.info("Exiting...")
    sys.exit(0)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/config')
def get_config():
    """API endpoint to get robot configuration for frontend"""
    try:
        config = load_robot_config()
        if not config or 'flexa' not in config:
            return jsonify({"error": "No robot configuration found"}), 500
        
        # Extract robot names and motor capabilities
        robots = []
        for robot_id, robot_data in config['flexa'].items():
            robots.append({
                'name': robot_data['name'],
                'ip': robot_data['ip'],
                'has_motors': robot_data.get('has_motors', False)
            })
        
        return jsonify({
            'robots': robots,
            'system': config.get('system', {})
        })
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/logs')
def get_logs():
    try:
        robot_name = request.args.get('robot_name', 'base1')
        if rm_helper:
            return jsonify(rm_helper.getLogs())
        else:
            return jsonify({"error": "RmHelper not initialized"}), 500
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def get_status():
    try:
        robot_name = request.args.get('robot_name', 'base1')
        if rm_helper:
            return jsonify({'status': rm_helper.getWorkingStatus(robot_name)})
        else:
            return jsonify({"error": "RmHelper not initialized"}), 500
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/robot-status')
def get_robot_status():
    try:
        if not b2_ping_checker:
            logger.warning("b2_ping_checker not initialized, returning empty data")
            return jsonify({
                'ping_status': {},
                'robot_status': {},
                'cleaning_device_status': {},
                'motor_data': {}
            })
            
        # Check request type to optimize response
        request_type = request.args.get('type', 'full')
        
        # Get data with safe fallbacks
        ping_status = getattr(b2_ping_checker, 'dict_of_ping_status', {})
        
        # Motor data only response (optimized for 1Hz polling)
        if request_type == 'motor':
            motor_data = {}
            if hasattr(b2_ping_checker, 'dict_of_motor_data'):
                motor_data = b2_ping_checker.dict_of_motor_data
                
                # Debug the motor data that's being returned
                logger.info(f"Motor data response contains {len(motor_data)} robots")
                
                # Make sure we're returning the correctly structured data for display
                for robot_name, robot_data in motor_data.items():
                    # Ensure each robot has motor1 and motor2
                    if 'motor1' not in robot_data:
                        logger.warning(f"Adding missing motor1 structure for {robot_name}")
                        motor_data[robot_name]['motor1'] = {
                            "pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, 
                            "vel_rad": 0.0, "current": 0.0
                        }
                    
                    if 'motor2' not in robot_data:
                        logger.warning(f"Adding missing motor2 structure for {robot_name}")
                        motor_data[robot_name]['motor2'] = {
                            "pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, 
                            "vel_rad": 0.0, "current": 0.0
                        }
                
                # For each online robot that doesn't have motor data, add placeholder structure
                # This will allow the UI to at least show the pending state
                for robot_name, is_online in ping_status.items():
                    if is_online and robot_name not in motor_data:
                        logger.info(f"Adding placeholder motor data for online robot {robot_name}")
                        motor_data[robot_name] = {
                            "motor1": {"pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, "vel_rad": 0.0, "current": 0.0},
                            "motor2": {"pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, "vel_rad": 0.0, "current": 0.0}
                        }
                
            # Return minimal response for motor data
            return jsonify({
                'ping_status': ping_status,
                'motor_data': motor_data
            })
            
        # General data response (excluding motor data)
        elif request_type == 'general':
            robot_status = getattr(b2_ping_checker, 'dict_of_robot_status', {})
            cleaning_device_status = getattr(b2_ping_checker, 'dict_of_cleaning_device_status', {})
            
            # Return everything except motor data
            return jsonify({
                'ping_status': ping_status,
                'robot_status': robot_status,
                'cleaning_device_status': cleaning_device_status
            })
            
        # Full response (default)
        else:
            robot_status = getattr(b2_ping_checker, 'dict_of_robot_status', {})
            cleaning_device_status = getattr(b2_ping_checker, 'dict_of_cleaning_device_status', {})
            
            # Check if motor_data attribute exists
            motor_data = {}
            if hasattr(b2_ping_checker, 'dict_of_motor_data'):
                motor_data = b2_ping_checker.dict_of_motor_data
            
            response_data = {
                'ping_status': ping_status,
                'robot_status': robot_status,
                'cleaning_device_status': cleaning_device_status,
                'motor_data': motor_data
            }
            
            return jsonify(response_data)
            
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in get_robot_status: {e}\n{error_details}")
        return jsonify({
            'error': str(e),
            'ping_status': {},
            'robot_status': {},
            'cleaning_device_status': {},
            'motor_data': {}
        }), 500
    
def safe_init_motor_controller():
    """Safely initialize the MotorController with fallback to None"""
    try:
        from motorReader import MotorController
        logger.info("Initializing MotorController...")
        return MotorController()
    except Exception as e:
        logger.error(f"Failed to initialize MotorController: {e}")
        return None

def safe_init_ping_checker():
    """Safely initialize MultiPingChecker using configuration"""
    try:
        from ping_addresses import MultiPingChecker
        logger.info("Initializing MultiPingChecker...")
        # No need to pass address book - it will load from config
        checker = MultiPingChecker()
        
        # Make sure dict_of_motor_data exists
        if not hasattr(checker, 'dict_of_motor_data'):
            checker.dict_of_motor_data = {}
            
        return checker
    except Exception as e:
        logger.error(f"Failed to initialize MultiPingChecker: {e}")
        return None

def safe_init_rm_helper():
    """Safely initialize RmHelper"""
    try:
        from rmHelper import RmHelper
        logger.info("Initializing RmHelper...")
        return RmHelper()
    except Exception as e:
        logger.error(f"Failed to initialize RmHelper: {e}")
        return None

@app.route('/api/motor-data')
def get_motor_data_only():
    """
    Lightweight API endpoint that only returns motor data
    This allows for faster refresh of motor visualizations (1Hz)
    while keeping full data refresh at a slower rate
    """
    try:
        if not b2_ping_checker:
            logger.warning("b2_ping_checker not initialized, returning empty data")
            return jsonify({
                'motor_data': {}
            })
            
        # Get only motor data with safe fallbacks
        motor_data = {}
        if hasattr(b2_ping_checker, 'dict_of_motor_data'):
            motor_data = b2_ping_checker.dict_of_motor_data
        
        return jsonify({
            'motor_data': motor_data
        })
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in get_motor_data_only: {e}\n{error_details}")
        return jsonify({
            'error': str(e),
            'motor_data': {}
        }), 500

@app.route('/api/direct_motor_data', methods=['POST'])
def direct_motor_data():
    try:
        data = request.json
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid data format"}), 400
            
        # Store the injected motor data
        if hasattr(b2_ping_checker, 'dict_of_motor_data') and data.get('motor_data'):
            b2_ping_checker.dict_of_motor_data = data['motor_data']
            logger.info(f"Injected motor data for {len(data['motor_data'])} robots")
            
        # Update online status for robots
        if hasattr(b2_ping_checker, 'dict_of_ping_status') and data.get('online_robots'):
            for robot in b2_ping_checker.dict_of_ping_status:
                b2_ping_checker.dict_of_ping_status[robot] = robot in data['online_robots']
            logger.info(f"Updated online status for {len(data['online_robots'])} robots")
            
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in direct_motor_data endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/robots', methods=['GET'])
def get_robots():
    """Get list of all configured robots"""
    try:
        config = load_robot_config()
        if not config or 'flexa' not in config:
            return jsonify({"error": "No robot configuration found"}), 500
        
        robots = []
        for robot_id, robot_data in config['flexa'].items():
            robots.append({
                'id': robot_id,
                'name': robot_data['name'],
                'ip': robot_data['ip'],
                'has_motors': robot_data.get('has_motors', False)
            })
        
        return jsonify({'robots': robots})
    except Exception as e:
        logger.error(f"Error getting robots: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/robots', methods=['POST'])
def add_robot():
    """Add a new robot via API"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['id', 'name', 'ip']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        robot_id = data['id'].strip().lower()
        name = data['name'].strip()
        ip = data['ip'].strip()
        has_motors = data.get('has_motors', False)
        
        # Validate IP
        try:
            import ipaddress
            ipaddress.ip_address(ip)
        except ValueError:
            return jsonify({"error": "Invalid IP address"}), 400
        
        # Load current config
        config = load_robot_config()
        if not config:
            config = {'flexa': {}, 'system': {}}
        
        # Check if robot already exists
        if robot_id in config['flexa']:
            return jsonify({"error": f"Robot '{robot_id}' already exists"}), 409
        
        # Add robot
        config['flexa'][robot_id] = {
            'name': name,
            'ip': ip,
            'has_motors': has_motors
        }
        
        # Save config
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Added robot '{robot_id}' via API")
        
        # Note: The ping checker would need to be restarted to pick up the new robot
        return jsonify({
            "success": True, 
            "message": "Robot added successfully. Restart required for changes to take effect.",
            "robot": {
                'id': robot_id,
                'name': name,
                'ip': ip,
                'has_motors': has_motors
            }
        })
        
    except Exception as e:
        logger.error(f"Error adding robot: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/robots/<robot_id>', methods=['DELETE'])
def remove_robot(robot_id):
    """Remove a robot via API"""
    try:
        # Load current config
        config = load_robot_config()
        if not config or 'flexa' not in config:
            return jsonify({"error": "No robot configuration found"}), 500
        
        # Check if robot exists
        if robot_id not in config['flexa']:
            return jsonify({"error": f"Robot '{robot_id}' not found"}), 404
        
        # Remove robot
        removed_robot = config['flexa'].pop(robot_id)
        
        # Save config
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Removed robot '{robot_id}' via API")
        
        return jsonify({
            "success": True,
            "message": "Robot removed successfully. Restart required for changes to take effect.",
            "removed_robot": {
                'id': robot_id,
                'name': removed_robot['name'],
                'ip': removed_robot['ip']
            }
        })
        
    except Exception as e:
        logger.error(f"Error removing robot: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/robots/<robot_id>', methods=['PUT'])
def update_robot(robot_id):
    """Update a robot's configuration via API"""
    try:
        data = request.json
        
        # Load current config
        config = load_robot_config()
        if not config or 'flexa' not in config:
            return jsonify({"error": "No robot configuration found"}), 500
        
        # Check if robot exists
        if robot_id not in config['flexa']:
            return jsonify({"error": f"Robot '{robot_id}' not found"}), 404
        
        # Update fields
        robot = config['flexa'][robot_id]
        if 'name' in data:
            robot['name'] = data['name'].strip()
        if 'ip' in data:
            ip = data['ip'].strip()
            # Validate IP
            try:
                import ipaddress
                ipaddress.ip_address(ip)
                robot['ip'] = ip
            except ValueError:
                return jsonify({"error": "Invalid IP address"}), 400
        if 'has_motors' in data:
            robot['has_motors'] = bool(data['has_motors'])
        
        # Save config
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Updated robot '{robot_id}' via API")
        
        return jsonify({
            "success": True,
            "message": "Robot updated successfully. Restart required for changes to take effect.",
            "robot": {
                'id': robot_id,
                'name': robot['name'],
                'ip': robot['ip'],
                'has_motors': robot.get('has_motors', False)
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating robot: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    try:
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Register cleanup function to run at exit
        atexit.register(cleanup_resources)
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Create .env file with default values if it doesn't exist
        env_file = '.env'
        if not os.path.exists(env_file):
            logger.warning(f"{env_file} not found, creating with default values")
            with open(env_file, 'w') as f:
                f.write("ROS_MASTER_URI=http://192.168.1.100:11311\n")
                f.write("ROS_MASTER_USER=admin\n")
                f.write("ROS_MASTER_PASSWD=password\n")
            logger.info(f"Created {env_file} with default values - UPDATE WITH REAL CREDENTIALS")
            
        # Initialize components in correct order
        logger.info("Loading robot configuration...")
        config = load_robot_config()
        
        if not config:
            logger.critical("Failed to load robot configuration")
            sys.exit(1)
            
        # Initialize the ping checker
        b2_ping_checker = safe_init_ping_checker()

        if b2_ping_checker:
            logger.info("Starting ping checker...")
            b2_ping_checker.startPing()
        else:
            logger.error("Failed to initialize ping checker, dashboard will have limited functionality")
        
        logger.info("Initializing RmHelper")
        rm_helper = safe_init_rm_helper()
        
        port = 8000
        logger.info(f"Starting Flask server on port {port}...")
        logger.info("Press Ctrl+C to shutdown gracefully")
        
        try:
            app.run(debug=True, host='0.0.0.0', port=port)
        except KeyboardInterrupt:
            # This handles the case where Ctrl+C is pressed during app.run()
            logger.info("KeyboardInterrupt received during Flask startup")
            signal_handler(signal.SIGINT, None)
            
    except Exception as e:
        logger.critical(f"Failed to start server: {e}")
        traceback.print_exc()
        cleanup_resources()
        sys.exit(1)