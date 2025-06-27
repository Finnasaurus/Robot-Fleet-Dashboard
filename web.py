from flask import Flask, render_template, jsonify, request
from datetime import datetime
import traceback
import yaml
import os
import logging
import signal
import sys
import atexit
import requests
import json
from dotenv import load_dotenv

from ping_addresses import MultiPingChecker, RobotConfig

from version import get_version_info, __development_note__

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

load_dotenv()
# Robot API configuration
ROS_API_URL = "http://localhost:8091"  # ROS API Bridge server
ROBOT_API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8090/")
AUTHKEY = {"Authorization": os.environ.get("API_AUTH_KEY", "enter-your-api-key")}

app = Flask(__name__)

# Define which commands should go to ROS bridge vs existing API
ROS_COMMANDS = {
    'pause', 'resume', 'stop', 'reset_soft_estop', 'enable_motor', 
    'change_map', 'change_state', 'teleop', 'manage_goals'
}

EXISTING_API_COMMANDS = {
    'start_charging', 'stop_charging', 'navigate_back_to_dock', 'docking',
    'battery_soc', 'is_charging', 'goal_queue_size', 'cleaning_stats',
    'set_cleaning_mode', 'navigation', 'start_process'
}

def load_robot_config():
    """Load robot configuration from config.yaml"""
    try:
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
            
            robots = []
            system_config = {
                'update_interval': 5,
                'motor_update_interval': 1
            }
            
            # Parse fleet configuration
            for fleet_name, fleet_data in config.items():
                for robot_id, robot_info in fleet_data.items():
                    robot_entry = {
                        'id': robot_id,
                        'name': robot_info.get('name', robot_id),
                        'ip': robot_info.get('ip', '127.0.0.1'),
                        'has_motors': robot_info.get('has_motors', False)
                    }
                    robots.append(robot_entry)
            
            return {
                'robots': robots,
                'system': system_config
            }
    except Exception as e:
        logger.error(f"Error loading robot config: {e}")
        return {
            'robots': [],
            'system': {'update_interval': 5, 'motor_update_interval': 1}
        }

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
    
@app.route('/api/about')
def get_about_info():
    """API endpoint to get project information including development story"""
    try:
        info = get_version_info()
        info['development_story'] = __development_note__
        info['features'] = [
            "Real-time robot monitoring",
            "Motor data visualization", 
            "Dynamic configuration",
            "Modern web interface",
            "RESTful API",
            "Built entirely with Claude"
        ]
        return jsonify(info)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "app_name": "Robot Fleet Dashboard",
            "note": "Built as a human-AI collaboration experiment"
        })

@app.route('/about')
def about_page():
    """About page showing development story"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>About - Robot Fleet Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <div class="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-8">
                <h1 class="text-3xl font-bold text-gray-800 mb-6">🤖 Robot Fleet Dashboard</h1>
                
                <div class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
                    <h2 class="text-xl font-semibold text-blue-800 mb-2">Development Story</h2>
                    <p class="text-blue-700">
                        This entire project was built as a personal experiment to test Claude's capabilities 
                        while creating something practical for my company. Every line of code, architecture 
                        decision, and feature was developed through human-AI collaboration.
                    </p>
                </div>
                
                <div class="grid md:grid-cols-2 gap-6 mb-6">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-800 mb-3">🏗️ What We Built Together</h3>
                        <ul class="list-disc list-inside text-gray-600 space-y-1">
                            <li>Full-stack web application</li>
                            <li>Real-time robot monitoring</li>
                            <li>Motor data visualization</li>
                            <li>Dynamic configuration system</li>
                            <li>RESTful API</li>
                            <li>Security implementation</li>
                            <li>Complete documentation</li>
                        </ul>
                    </div>
                    
                    <div>
                        <h3 class="text-lg font-semibold text-gray-800 mb-3">🚀 Technologies Used</h3>
                        <ul class="list-disc list-inside text-gray-600 space-y-1">
                            <li>Python Flask backend</li>
                            <li>Modern JavaScript frontend</li>
                            <li>ROS integration</li>
                            <li>YAML configuration</li>
                            <li>Real-time data streaming</li>
                            <li>Responsive web design</li>
                        </ul>
                    </div>
                </div>
                
                <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
                    <h3 class="text-lg font-semibold text-green-800 mb-2">💡 The Result</h3>
                    <p class="text-green-700">
                        A production-ready robot fleet monitoring dashboard that evolved from a simple 
                        ping checker into a comprehensive management system. This showcases what's 
                        possible when human creativity meets AI capabilities.
                    </p>
                </div>
                
                <div class="text-center">
                    <a href="/" class="bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded">
                        Back to Dashboard
                    </a>
                </div>
                
                <div class="mt-8 text-center text-gray-500 text-sm">
                    <p>Built through human-AI collaboration 🤖❤️👨‍💻</p>
                    <div id="version-info" class="mt-2"></div>
                </div>
            </div>
        </div>
        
        <script>
            fetch('/api/about')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('version-info').innerHTML = 
                        `Version ${data.version} | Built ${new Date(data.build_date).toLocaleDateString()}`;
                })
                .catch(error => console.log('Version info not available'));
        </script>
    </body>
    </html>
    '''

@app.route('/api/robot-control/<command>', methods=['POST'])
def robot_control_proxy(command):
    """
    Hybrid robot control proxy - routes to ROS bridge or existing API based on command
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        robot_name = data.get('robot_name')
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400

        # Route to ROS Bridge for ROS commands
        if command in ROS_COMMANDS:
            logger.info(f"Routing {command} to ROS bridge for {robot_name}")
            
            # Map dashboard commands to ROS bridge endpoints
            ros_endpoint_map = {
                'pause': 'manage_goals',
                'resume': 'manage_goals',
                'stop': 'manage_goals',
                'reset_soft_estop': 'reset_soft_estop',
                'enable_motor': 'enable_motor',
                'change_map': 'change_map',
                'change_state': 'change_state',
                'teleop': 'teleop',
                'manage_goals': 'manage_goals'
            }
            
            ros_endpoint = ros_endpoint_map.get(command, command)
            ros_url = f"{ROS_API_URL}/api/ros/{ros_endpoint}"
            
            # Build payload for ROS bridge
            ros_payload = {"robot_name": robot_name}
            
            # Add command-specific parameters
            if command == 'pause':
                ros_payload['exec_code'] = 1
            elif command == 'resume':
                ros_payload['exec_code'] = 0
            elif command == 'stop':
                ros_payload['exec_code'] = 2
            elif command == 'change_map':
                ros_payload['map_name'] = data.get('map_name', '')
            elif command == 'change_state':
                ros_payload['target_mode'] = data.get('target_mode', 0)
                ros_payload['target_state'] = data.get('target_state', 0)
            elif command == 'manage_goals':
                ros_payload['exec_code'] = data.get('exec_code', 0)
            
            # Make request to ROS bridge
            response = requests.post(
                ros_url,
                json=ros_payload,
                timeout=30
            )
            
            if response.ok:
                result = response.json()
                logger.info(f"ROS bridge success: {robot_name} -> {command}")
                return jsonify(result)
            else:
                logger.error(f"ROS bridge failed: {robot_name} -> {command} -> {response.status_code}")
                return jsonify({
                    "error": f"ROS bridge returned status {response.status_code}",
                    "details": response.text
                }), response.status_code
                
        # Route to existing API for non-ROS commands
        else:
            logger.info(f"Routing {command} to existing API for {robot_name}")
            
            # Use the same API configuration as rmHelper/remotecontroller
            API_URL = ROBOT_API_BASE_URL
            API_HEADERS = AUTHKEY
            
            # Build the request URL and payload
            endpoint_url = API_URL.rstrip('/') + '/' + command
            
            # Base payload - always include robot_name
            payload = {"robot_name": robot_name}
            
            # Add command-specific parameters
            if command == 'docking':
                payload['action'] = data.get('action', 'dock')
            elif command == 'set_cleaning_mode':
                payload.update({
                    'vacuum': data.get('vacuum', 0),
                    'roller': data.get('roller', 0), 
                    'gutter': data.get('gutter', False)
                })
            elif command == 'navigation':
                payload['pose2d'] = data.get('pose2d', [0, 0, 0])
            elif command == 'start_process':
                payload.update({
                    'process': data.get('process'),
                    'order': data.get('order', 'ASCENDING')
                })
                if data.get('type'):
                    payload['type'] = data.get('type')
                if data.get('selection'):
                    payload['selection'] = data.get('selection')
            elif command == 'manage_goals':
                payload.update({
                    'exec_code': data.get('exec_code', 5),
                    'argument': data.get('argument', '100')
                })
            
            # Make the API call
            logger.info(f"Robot control: {robot_name} -> {command} -> {endpoint_url}")
            
            response = requests.post(
                endpoint_url,
                headers=API_HEADERS,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    result = response.json()
                except:
                    result = {"message": response.text}
                
                logger.info(f"Robot control success: {robot_name} -> {command}")
                return jsonify({
                    "success": True,
                    "command": command,
                    "robot_name": robot_name,
                    "result": result
                })
            else:
                logger.error(f"Robot control failed: {robot_name} -> {command} -> {response.status_code}")
                return jsonify({
                    "error": f"Robot API returned status {response.status_code}",
                    "details": response.text
                }), response.status_code
            
    except requests.exceptions.Timeout:
        logger.error(f"Robot control timeout: {robot_name} -> {command}")
        return jsonify({"error": "Command timed out"}), 408
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Robot control connection error: {robot_name} -> {command}")
        return jsonify({"error": "Cannot connect to robot API"}), 503
        
    except Exception as e:
        logger.error(f"Robot control error: {robot_name} -> {command} -> {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/robot-control/batch', methods=['POST'])
def robot_control_batch():
    """
    Execute multiple robot control commands in sequence.
    Now supports both ROS and existing API commands.
    """
    try:
        data = request.get_json()
        if not data or 'commands' not in data:
            return jsonify({"error": "No commands provided"}), 400
        
        commands = data['commands']
        robot_name = data.get('robot_name')
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        results = []
        
        for cmd in commands:
            command = cmd.get('command')
            params = cmd.get('params', {})
            
            # Add robot_name to params
            params['robot_name'] = robot_name
            
            # Check if this is a ROS command that should use the bridge
            if command in ROS_COMMANDS:
                logger.info(f"Batch: Routing {command} to ROS bridge")
                
                # Use the ROS batch endpoint
                try:
                    ros_response = requests.post(
                        f"{ROS_API_URL}/api/ros/batch",
                        json={
                            "robot_name": robot_name,
                            "commands": [{
                                "service": command,
                                "params": params
                            }],
                            "stop_on_error": False
                        },
                        timeout=30
                    )
                    
                    if ros_response.ok:
                        ros_result = ros_response.json()
                        if ros_result.get('results') and len(ros_result['results']) > 0:
                            result = {
                                "command": command,
                                "success": ros_result['results'][0].get('success', False),
                                "result": ros_result['results'][0]
                            }
                        else:
                            result = {
                                "command": command,
                                "success": False,
                                "error": "No result from ROS bridge"
                            }
                    else:
                        result = {
                            "command": command,
                            "success": False,
                            "error": f"ROS bridge error: {ros_response.status_code}"
                        }
                        
                except Exception as e:
                    result = {
                        "command": command,
                        "success": False,
                        "error": str(e)
                    }
            else:
                # Use existing API
                logger.info(f"Batch: Routing {command} to existing API")
                
                try:
                    # Make internal request to our own API
                    internal_response = requests.post(
                        f"http://localhost:{request.environ.get('SERVER_PORT', '8000')}/api/robot-control/{command}",
                        json=params,
                        timeout=30
                    )
                    
                    result = {
                        "command": command,
                        "success": internal_response.status_code == 200,
                        "result": internal_response.json()
                    }
                    
                except Exception as e:
                    result = {
                        "command": command,
                        "success": False,
                        "error": str(e)
                    }
            
            results.append(result)
            
            # If command failed and stop_on_error is True, break
            if not result['success'] and data.get('stop_on_error', True):
                break
        
        return jsonify({
            "success": all(r['success'] for r in results),
            "robot_name": robot_name,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Batch robot control error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/robot-presets', methods=['GET'])
def get_robot_presets():
    """
    Get predefined robot operation presets.
    Updated to include ROS commands.
    """
    presets = {
        "dock_and_charge": {
            "name": "Dock and Charge",
            "description": "Navigate to dock and start charging",
            "commands": [
                {"command": "navigate_back_to_dock", "params": {}},
                {"command": "docking", "params": {"action": "dock"}},
                {"command": "start_charging", "params": {}}
            ]
        },
        "emergency_stop": {
            "name": "Emergency Stop",
            "description": "Immediately stop all operations",
            "commands": [
                {"command": "stop", "params": {}}  # This will use ROS bridge
            ]
        },
        "start_cleaning_cycle": {
            "name": "Start Full Cleaning",
            "description": "Configure cleaning devices and start cleaning",
            "commands": [
                {"command": "set_cleaning_mode", "params": {"vacuum": 2, "roller": 1, "gutter": True}},
                {"command": "start_process", "params": {"process": "default_cleaning", "order": "ASCENDING"}}
            ]
        },
        "reset_and_resume": {
            "name": "Reset E-Stop and Resume",
            "description": "Reset e-stop, enable motor, and resume operations",
            "commands": [
                {"command": "reset_soft_estop", "params": {}},  # ROS bridge
                {"command": "enable_motor", "params": {}},      # ROS bridge
                {"command": "resume", "params": {}}              # ROS bridge
            ]
        },
        "pause_and_dock": {
            "name": "Pause and Dock",
            "description": "Pause current operation and return to dock",
            "commands": [
                {"command": "pause", "params": {}},              # ROS bridge
                {"command": "navigate_back_to_dock", "params": {}},
                {"command": "docking", "params": {"action": "dock"}}
            ]
        }
    }
    
    return jsonify(presets)

@app.route('/api/robot-presets/<preset_name>', methods=['POST'])
def execute_robot_preset(preset_name):
    """
    Execute a predefined robot preset.
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        # Get presets
        presets_response = get_robot_presets()
        presets = presets_response.get_json()
        
        if preset_name not in presets:
            return jsonify({"error": f"Unknown preset: {preset_name}"}), 400
        
        preset = presets[preset_name]
        
        # Execute preset as batch command
        batch_data = {
            "robot_name": robot_name,
            "commands": preset["commands"],
            "stop_on_error": data.get("stop_on_error", True)
        }
        
        # Use internal batch endpoint
        batch_response = robot_control_batch()
        
        return jsonify({
            "preset": preset_name,
            "preset_description": preset["description"],
            "batch_result": batch_response.get_json()
        })
        
    except Exception as e:
        logger.error(f"Preset execution error: {preset_name} -> {str(e)}")
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
                f.write("API_BASE_URL=http://127.0.0.1:8090/\n")
                f.write("API_AUTH_KEY=enter-your-api-key\n")
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
        
        # Check if ROS API bridge is running
        try:
            health_check = requests.get(f"{ROS_API_URL}/health", timeout=2)
            if health_check.ok:
                logger.info("ROS API Bridge is running")
            else:
                logger.warning("ROS API Bridge is not responding properly")
        except:
            logger.warning("ROS API Bridge is not running - ROS commands will fail")
            logger.info("Start it with: python ros_api_server.py")
        
        port = 8000
        logger.info(f"Starting Flask server on port {port}...")
        logger.info("Press Ctrl+C to shutdown gracefully")
        logger.info(f"ROS API Bridge expected at: {ROS_API_URL}")
        logger.info(f"Robot API expected at: {ROBOT_API_BASE_URL}")
        
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