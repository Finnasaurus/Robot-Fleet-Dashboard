#!/usr/bin/env python3
import time
import threading
import logging
import traceback
import concurrent.futures
import yaml
import os

from ping_address import PeriodicAddressPinger
from motorReader import MotorController

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(),
              logging.FileHandler('ping_checker.log')]
)
logger = logging.getLogger(__name__)

class RobotConfig:
    """Centralized robot configuration loader"""
    
    @staticmethod
    def load_config(config_path='config.yaml'):
        """Load robot configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return None
    
    @staticmethod
    def get_robot_addresses(config):
        """Extract robot addresses from config"""
        addresses = {}
        if config and 'flexa' in config:
            for robot_id, robot_data in config['flexa'].items():
                if robot_data.get('ip') and robot_data['ip'] != '127.0.0.1':
                    addresses[robot_data['name']] = robot_data['ip']
        return addresses
    
    @staticmethod
    def get_motor_enabled_robots(config):
        """Get list of robots with motor capabilities"""
        motor_robots = []
        if config and 'flexa' in config:
            for robot_id, robot_data in config['flexa'].items():
                if robot_data.get('has_motors', False):
                    motor_robots.append(robot_data['name'])
        return motor_robots
    
    @staticmethod
    def get_all_robot_names(config):
        """Get list of all robot names"""
        names = []
        if config and 'flexa' in config:
            for robot_id, robot_data in config['flexa'].items():
                names.append(robot_data['name'])
        return names

class MultiPingChecker:
    def __init__(self, address_book=None, config_path='config.yaml'):
        # Load configuration
        self.config = RobotConfig.load_config(config_path)
        
        # If no address book provided, load from config
        if address_book is None:
            address_book = RobotConfig.get_robot_addresses(self.config)
            logger.info(f"Loaded {len(address_book)} robots from config")
        
        # Get system settings from config
        system_config = self.config.get('system', {}) if self.config else {}
        self.update_interval = system_config.get('update_interval', 1.0)
        self.motor_update_interval = system_config.get('motor_update_interval', 1.0)
        
        # Get motor-enabled robots from config
        self.motor_primary_robots = RobotConfig.get_motor_enabled_robots(self.config)
        logger.info(f"Motor-enabled robots: {self.motor_primary_robots}")

        # State, keyed by lowercase robot names
        self.dict_of_pingers = {}
        self.dict_of_ping_status = {}
        self.dict_of_robot_status = {}
        self.dict_of_cleaning_device_status = {}
        self.dict_of_motor_data = {}
        self.motor_controllers = {}

        # Seed structures and instantiate controllers/pingers
        for name, ip in address_book.items():
            key = name.lower()

            # 1) Default-zero motor data
            self.dict_of_motor_data[key] = {
                "motor1": {"pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, "vel_rad": 0.0, "current": 0.0},
                "motor2": {"pos_rad": 0.0, "pos_offset": 0.0, "vel_rpm": 0.0, "vel_rad": 0.0, "current": 0.0},
            }

            # 2) Default ping/status slots
            self.dict_of_ping_status[key] = False
            self.dict_of_robot_status[key] = {}
            self.dict_of_cleaning_device_status[key] = {}

            # 3) MotorController - ONLY for motor-enabled robots
            if key in self.motor_primary_robots:
                try:
                    mc = MotorController(ssh_host=ip)
                    self.motor_controllers[key] = mc
                    logger.info(f"MotorController initialized for {key}@{ip}")
                except Exception as e:
                    logger.error(f"Failed MotorController init for {key}@{ip}: {e}")
            else:
                logger.debug(f"Skipping MotorController for {key} - not motor-enabled")

            # 4) Pinger (for all robots)
            try:
                p = PeriodicAddressPinger(ip)
                self.dict_of_pingers[key] = p
            except Exception as e:
                logger.error(f"Failed pinger init for {key}@{ip}: {e}")

        # Thread control
        self.running = True
        self.ping_status_thread = None
        self.motor_update_thread = None

    def updatePingerStatus(self):
        """Refresh ping, robot status, and cleaning-device status."""
        for key, p in self.dict_of_pingers.items():
            try:
                self.dict_of_ping_status[key] = getattr(p, 'is_address_reachable', False)
                if hasattr(p, 'assistant') and p.assistant:
                    self.dict_of_robot_status[key] = p.assistant.robotStatus(key)
                    self.dict_of_cleaning_device_status[key] = p.assistant.brushStatus(key) or {}
            except Exception as e:
                logger.error(f"Error in updatePingerStatus for {key}: {e}")
                self.dict_of_ping_status[key] = False

    def updateMotorDataParallel(self):
        """Update motor data for motor-enabled robots in parallel"""
        robots_to_update = []
        
        # Collect only motor-enabled robots that are online
        for k in self.motor_primary_robots:
            if self.dict_of_ping_status.get(k, False):
                motor_controller = self.motor_controllers.get(k)
                if motor_controller:
                    robots_to_update.append((k, k, motor_controller))
        
        if not robots_to_update:
            logger.debug("No motor-enabled robots online")
            return
        
        logger.info(f"Updating motor data for {len(robots_to_update)} robots: {[r[0] for r in robots_to_update]}")
        
        # Use ThreadPoolExecutor for parallel SSH connections
        max_workers = min(3, len(robots_to_update))

        def update_single_robot(robot_data):
            k, robot_key, motor_controller = robot_data
            try:
                start_time = time.time()
                motor_data = motor_controller.read_motor_data()
                elapsed = time.time() - start_time
                
                if motor_data:
                    self.dict_of_motor_data[k] = motor_data
                    logger.debug(f"Updated motor data for {k} in {elapsed:.2f}s")
                    return True
                else:
                    logger.warning(f"No motor data returned for {k} after {elapsed:.2f}s")
                    return False
            except Exception as e:
                logger.error(f"Error reading motor data for {k}: {e}")
                return False
        
        # Execute updates in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            start_time = time.time()
            futures = [executor.submit(update_single_robot, robot_data) 
                      for robot_data in robots_to_update]
            
            # Wait for all to complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Future exception: {e}")
                    results.append(False)
            
            elapsed = time.time() - start_time
            successful = sum(1 for r in results if r)
            logger.info(f"Updated {successful}/{len(robots_to_update)} robots in {elapsed:.2f}s")

    def _schedule_ping_status(self):
        """Thread function for periodic ping-status refresh."""
        if not self.running:
            return
        try:
            self.updatePingerStatus()
            online = [k for k, v in self.dict_of_ping_status.items() if v]
            logger.info(f"Online robots: {online}")
        except Exception as e:
            logger.error(f"Error in _schedule_ping_status: {e}")
        
        if self.running:
            self.ping_status_thread = threading.Timer(self.update_interval, self._schedule_ping_status)
            self.ping_status_thread.daemon = True
            self.ping_status_thread.start()

    def _schedule_motor_update(self):
        """Thread function for periodic motor-data refresh."""
        if not self.running:
            return
        try:
            self.updateMotorDataParallel()
        except Exception as e:
            logger.error(f"Error in _schedule_motor_update: {e}")
        
        if self.running:
            self.motor_update_thread = threading.Timer(self.motor_update_interval, self._schedule_motor_update)
            self.motor_update_thread.daemon = True
            self.motor_update_thread.start()

    def startPing(self, blocking=False):
        """Kick off both ping-status and motor-data timers."""
        self.running = True
        
        # Start all pingers
        for p in self.dict_of_pingers.values():
            try:
                p.startPing()
            except Exception as e:
                logger.error(f"Error starting pinger: {e}")

        # Start update threads
        threading.Thread(target=self._schedule_ping_status, daemon=True).start()
        threading.Thread(target=self._schedule_motor_update, daemon=True).start()

        if blocking and self.ping_status_thread:
            self.ping_status_thread.join()

    def stopPing(self):
        """Cancel timers and stop pingers."""
        logger.info("Stopping MultiPingChecker")
        self.running = False
        
        # Stop all pingers
        for p in self.dict_of_pingers.values():
            try:
                p.stopPing()
            except:
                pass

        # Cancel timers
        if self.ping_status_thread:
            self.ping_status_thread.cancel()
        if self.motor_update_thread:
            self.motor_update_thread.cancel()

if __name__ == "__main__":
    import signal

    logger.info("Starting MultiPingChecker demo")
    
    # No need to provide address book - it will load from config.yaml
    checker = MultiPingChecker()
    signal.signal(signal.SIGINT, lambda s, f: checker.stopPing())
    checker.startPing(blocking=True)