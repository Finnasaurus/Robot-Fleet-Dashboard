import datetime
import threading
import subprocess
import yaml
import json
from rmHelper import RmHelper
from motorReader import MotorController

CONFIGPATH = "config.yaml"

class PeriodicAddressPinger():
    def __init__(self, address_to_ping, ping_interval_in_seconds = 1):
        self.address_to_ping = address_to_ping
        self.ping_interval_in_seconds = ping_interval_in_seconds
        self.is_address_reachable = None
        self.continue_pinging = True
        self.subprocess_p = None
        self.ping_timer_thread = None
        self.robots = self._loadYaml()
        self.robot_status = {}
        self.cleaning_device_status = {}
        self.motor_data = {}
        self.motor_controller = MotorController()

        ## Make an instance of Rm helper
        self.assistant = RmHelper()

    def _loadYaml(self):
        data = open(CONFIGPATH)
        robots = yaml.safe_load(data)
        data.close()
        return robots["flexa"]
       
    def _getRobotName(self):
        for k in self.robots:
            if self.robots[k]["ip"] == self.address_to_ping:
                return self.robots[k]['name']

 
    def pingAnAddress(self):
        # Not 0: not available
        # 0: available
        self.subprocess_p = subprocess.Popen(["ping","-c", "1", "-W", "5", self.address_to_ping], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        res = self.subprocess_p.wait() # or .poll() after .wait()
        self.is_address_reachable = not res
        self.robot_status = self.assistant.robotStatus(self._getRobotName())
        self.cleaning_device_status = self.assistant.brushStatus(self._getRobotName())
        # print("[{}] {}: {}".format(time.ctime(), self.address_to_ping, self.is_address_reachable))

    def pingTimerThread(self):
        self.pingAnAddress()
        if (self.continue_pinging):
            self.ping_timer_thread = threading.Timer(self.ping_interval_in_seconds, self.pingTimerThread)
            self.ping_timer_thread.start()

    def startPing(self, blocking=False):
        pinging_thread = threading.Thread(name="ping thread", target = self.pingTimerThread)
        pinging_thread.start()
        if blocking:
            pinging_thread.join()

    def stopPing(self):
        if self.ping_timer_thread is not None:
            self.ping_timer_thread.cancel()
        if self.subprocess_p is not None:
            self.subprocess_p.terminate()
        self.continue_pinging = False

if __name__ == "__main__":
    import signal

    pinger = PeriodicAddressPinger("192.168.1.100")
    signal.signal(signal.SIGINT, lambda sig, frame: pinger.stopPing())
    pinger.startPing(True)
    print('hi')

