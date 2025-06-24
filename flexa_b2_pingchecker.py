import threading
import yaml
from ping_addresses import MultiPingChecker, RobotConfig
from ping_gui import PingerGUI

class MultiPingCheckerGUI(MultiPingChecker):
    def __init__(self, dict_of_addresses=None, config_path='config.yaml'):
        # If no addresses provided, load from config
        if dict_of_addresses is None:
            config = RobotConfig.load_config(config_path)
            dict_of_addresses = RobotConfig.get_robot_addresses(config)
            # Add VPN and RM if not in config
            if "VPN" not in dict_of_addresses:
                dict_of_addresses["VPN"] = "192.168.1.1"
            if "RM" not in dict_of_addresses:
                dict_of_addresses["RM"] = "192.168.1.100"
        
        super().__init__(dict_of_addresses, config_path)
        self.ping_gui = PingerGUI(dict_of_addresses, "Flexa Pinger GUI beta")

    def updatePingerTimerThread(self):
        if (self.ping_gui.continue_gui):
            self.updatePingerStatus()
            self.ping_gui.update_ping_status(self.dict_of_ping_status, self.dict_of_robot_status, self.dict_of_cleaning_device_status)
            self.ping_status_thread = threading.Timer(self.update_interval, self.updatePingerTimerThread)
            self.ping_status_thread.start()
        else:
            self.stopAll()

    def startAll(self, blocking=False):
        self.startPing()

        show_gui_thread = threading.Thread(name="gui thread", target = self.ping_gui.main)
        show_gui_thread.start()
        if blocking:
            show_gui_thread.join()

    def stopAll(self):
        self.ping_gui.stopGUI()
        self.stopPing()

if __name__ == "__main__":
    import signal
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Flexa Robot Ping Checker GUI')
    parser.add_argument('--config', default='config.yaml', help='Path to configuration file')
    args = parser.parse_args()
    
    print(f"Loading robot configuration from {args.config}...")
    
    # Create GUI with dynamic configuration
    b2_ping_checker_gui = MultiPingCheckerGUI(config_path=args.config)
    
    # Set up signal handler for clean shutdown
    signal.signal(signal.SIGINT, lambda sig, frame: b2_ping_checker_gui.stopAll())
    
    # Start the GUI
    b2_ping_checker_gui.startAll(True)