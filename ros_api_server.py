#!/usr/bin/env python3
"""
ROS API Bridge Server
Converts ROS service calls to REST API endpoints
"""

import os
import subprocess
import yaml
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for dashboard access

class MapServiceResponse(Enum):
    SUCCESS = 0
    MAP_DOES_NOT_EXIST = 1
    INVALID_MAP_DATA = 2
    INVALID_MAP_METADATA = 3
    FAILURE = 255

def load_robot_config():
    """Load robot configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def set_ros_master_uri(robot_ip):
    """Set ROS_MASTER_URI for the target robot"""
    ros_uri = f"http://{robot_ip}:11311"
    os.environ["ROS_MASTER_URI"] = ros_uri
    logger.info(f"ROS_MASTER_URI set to {ros_uri}")
    return ros_uri

def get_robot_ip(robot_name):
    """Get robot IP from config"""
    config = load_robot_config()
    fleet = list(config.values())[0]
    
    for robot_info in fleet.values():
        if robot_info["name"] == robot_name:
            return robot_info["ip"]
    
    raise ValueError(f"Robot {robot_name} not found in config")

# ROS Service API Endpoints

@app.route('/api/ros/manage_goals', methods=['POST'])
def manage_goals():
    """
    Manage robot goals (pause/resume/finish)
    Expected payload: {
        "robot_name": "base1",
        "exec_code": 0  # 0=resume, 1=pause, 2=finish
    }
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        exec_code = data.get('exec_code', 0)
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        # Set ROS master URI
        robot_ip = get_robot_ip(robot_name)
        set_ros_master_uri(robot_ip)
        
        # Execute ROS service call
        cmd = f"rosservice call /goal_manager/manage_goals {exec_code} ''"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "robot_name": robot_name,
                "exec_code": exec_code,
                "message": f"Goal management command {exec_code} executed successfully"
            })
        else:
            return jsonify({
                "error": "ROS service call failed",
                "details": result.stderr
            }), 500
            
    except Exception as e:
        logger.error(f"Error in manage_goals: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ros/change_state', methods=['POST'])
def change_state():
    """
    Change robot state/mode
    Expected payload: {
        "robot_name": "base1",
        "target_mode": 0,
        "target_state": 1  # 0=base, 1=navigation, 2=mapping, 3=cleaning, 4=manual
    }
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        target_mode = data.get('target_mode', 0)
        target_state = data.get('target_state', 0)
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        # Set ROS master URI
        robot_ip = get_robot_ip(robot_name)
        set_ros_master_uri(robot_ip)
        
        # Execute ROS service call
        cmd = f"rosservice call /state_supervisor/change_state {target_mode} {target_state}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            state_names = ["base", "navigation", "mapping", "cleaning", "manual"]
            state_name = state_names[target_state] if target_state < len(state_names) else "unknown"
            
            return jsonify({
                "success": True,
                "robot_name": robot_name,
                "new_state": state_name,
                "message": f"Robot state changed to {state_name}"
            })
        else:
            return jsonify({
                "error": "ROS service call failed",
                "details": result.stderr
            }), 500
            
    except Exception as e:
        logger.error(f"Error in change_state: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ros/reset_soft_estop', methods=['POST'])
def reset_soft_estop():
    """
    Reset software E-stop
    Expected payload: {
        "robot_name": "base1"
    }
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        # Set ROS master URI
        robot_ip = get_robot_ip(robot_name)
        set_ros_master_uri(robot_ip)
        
        # Execute ROS service call
        cmd = "rosservice call /device_handler/reset_soft_estop"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "robot_name": robot_name,
                "message": "Software E-stop reset successfully"
            })
        else:
            return jsonify({
                "error": "ROS service call failed",
                "details": result.stderr
            }), 500
            
    except Exception as e:
        logger.error(f"Error in reset_soft_estop: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ros/enable_motor', methods=['POST'])
def enable_motor():
    """
    Enable motor controller
    Expected payload: {
        "robot_name": "base1"
    }
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        # Set ROS master URI
        robot_ip = get_robot_ip(robot_name)
        set_ros_master_uri(robot_ip)
        
        # Execute ROS service call
        cmd = "rosservice call /flexa_motor_controller/enable"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "robot_name": robot_name,
                "message": "Motor controller enabled successfully"
            })
        else:
            return jsonify({
                "error": "ROS service call failed",
                "details": result.stderr
            }), 500
            
    except Exception as e:
        logger.error(f"Error in enable_motor: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ros/change_map', methods=['POST'])
def change_map():
    """
    Change robot map
    Expected payload: {
        "robot_name": "base1",
        "map_name": "warehouse_floor_1"
    }
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        map_name = data.get('map_name')
        
        if not robot_name or not map_name:
            return jsonify({"error": "robot_name and map_name are required"}), 400
        
        # Set ROS master URI
        robot_ip = get_robot_ip(robot_name)
        set_ros_master_uri(robot_ip)
        
        # Execute ROS service call for main map
        cmd = f"rosservice call /change_map {map_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse result
            try:
                service_result = yaml.safe_load(result.stdout)['result']
                status = MapServiceResponse(service_result).name
            except:
                status = "UNKNOWN"
            
            # Also change prohibited map
            cmd_prohibited = f"rosservice call /prohibited_map/change_map {map_name}_prohibited"
            result_prohibited = subprocess.run(cmd_prohibited, shell=True, capture_output=True, text=True)
            
            # If prohibited map with suffix fails, try without suffix
            if result_prohibited.returncode != 0:
                cmd_prohibited = f"rosservice call /prohibited_map/change_map {map_name}"
                result_prohibited = subprocess.run(cmd_prohibited, shell=True, capture_output=True, text=True)
            
            return jsonify({
                "success": True,
                "robot_name": robot_name,
                "map_name": map_name,
                "status": status,
                "message": f"Map changed to {map_name}"
            })
        else:
            return jsonify({
                "error": "ROS service call failed",
                "details": result.stderr
            }), 500
            
    except Exception as e:
        logger.error(f"Error in change_map: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ros/teleop', methods=['POST'])
def start_teleop():
    """
    Start teleop mode for a robot
    Expected payload: {
        "robot_name": "base1"
    }
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        # Set ROS master URI
        robot_ip = get_robot_ip(robot_name)
        set_ros_master_uri(robot_ip)
        
        # Note: This launches a terminal process, so it's more of a trigger
        # In production, you might want to handle this differently
        cmd = 'gnome-terminal -- /bin/bash -c "rosrun teleop_twist_keyboard teleop_twist_keyboard.py cmd_vel:=cmd_vel_rm; exec bash;"'
        os.system(cmd)
        
        return jsonify({
            "success": True,
            "robot_name": robot_name,
            "message": "Teleop terminal launched"
        })
            
    except Exception as e:
        logger.error(f"Error in start_teleop: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ros/batch', methods=['POST'])
def batch_commands():
    """
    Execute multiple ROS commands in sequence
    Expected payload: {
        "robot_name": "base1",
        "commands": [
            {"service": "reset_soft_estop", "params": {}},
            {"service": "enable_motor", "params": {}}
        ]
    }
    """
    try:
        data = request.get_json()
        robot_name = data.get('robot_name')
        commands = data.get('commands', [])
        
        if not robot_name:
            return jsonify({"error": "robot_name is required"}), 400
        
        # Set ROS master URI once
        robot_ip = get_robot_ip(robot_name)
        set_ros_master_uri(robot_ip)
        
        results = []
        all_success = True
        
        for cmd_info in commands:
            service = cmd_info.get('service')
            params = cmd_info.get('params', {})
            
            # Map service names to actual ROS commands
            service_map = {
                'reset_soft_estop': 'rosservice call /device_handler/reset_soft_estop',
                'enable_motor': 'rosservice call /flexa_motor_controller/enable',
                'pause': 'rosservice call /goal_manager/manage_goals 1 ""',
                'resume': 'rosservice call /goal_manager/manage_goals 0 ""',
                'finish': 'rosservice call /goal_manager/manage_goals 2 ""'
            }
            
            if service not in service_map:
                results.append({
                    "service": service,
                    "success": False,
                    "error": "Unknown service"
                })
                all_success = False
                continue
            
            cmd = service_map[service]
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            results.append({
                "service": service,
                "success": result.returncode == 0,
                "output": result.stdout if result.returncode == 0 else result.stderr
            })
            
            if result.returncode != 0:
                all_success = False
                if data.get('stop_on_error', True):
                    break
        
        return jsonify({
            "success": all_success,
            "robot_name": robot_name,
            "results": results
        })
            
    except Exception as e:
        logger.error(f"Error in batch_commands: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "ros_api_bridge"})

if __name__ == '__main__':
    port = 8091  # Different port from main dashboard
    logger.info(f"Starting ROS API Bridge Server on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port)