import json
import requests
from datetime import datetime
import yaml
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8090/")
AUTHKEY = {"Authorization": os.environ.get("API_AUTH_KEY", "enter-your-api-key")}
CONFIGPATH = 'config.yaml'

class RmHelper():
    def __init__(self) -> None:
        """
        RM Helper will help to automate some of the tasks for the RM

        1. Auto-release estop
        2. ...

        Helper is built on top of the flexa API, all functions here are API calls

        There are 2 methods defined in this class to execute API calls, self.generalAPI() and self.apiCall().
        self.generalAPI() is a wrapper for self.apiCall() to prevent calling invalid API routes, thus the recommended method is to use self.generalAPI() for most cases
        More details in the self.generalAPI() docstring

        Logs are stored in the same file as the API error logs, structured as such:

        Logs
        {
            API Errors: 
            {
                Error 502: <time of occurences>
                ...
            }

            Robot Errors: 
            {
                base1:
                [
                    Error: <time of occurences>
                ]
                base2: 
                [
                    Error: <time of occurences>
                ]
                ...
                base-b3:
                [
                    Error: <time of occurences>
                ]
            }
        }
        """
        ## Load robot configuration
        self._loadRobotConfig()
        
        ## Initialise all private attributes
        self.__logpath = ""
        self.__logs = {}

        ## Initialise by getting a copy of the logs
        self._refreshLogs()
        self.estopTracker = {} #dict of number of times robot estop was released

        ## 1201 is motor error, the rest is overcurrent for the diff components, 1416 and 1417 are overtemp
        ## This list contains all auto-release estops
        self.estopErrors = ['1201', '1412', '1413', '1414', '1415', '1416', '1417']
        ## List of commands and their corresponding api routes
        self.routeDict = {
            "start charge":"start_charging",
            "is online":"Online",
            "release estop":"reset_soft_estop",
            "device status":"cleaning_device_status",
            "back to dock":"navigate_back_to_dock",
            "remaining goals":"goal_queue_size",
            "rm info":"get_robot_info_rm",
            "battery":"battery_soc",
            "cleaning stats":"cleaning_stats",
            "current map":"current_map"
        }

    def _loadRobotConfig(self):
        """Load robot names from config.yaml"""
        try:
            with open(CONFIGPATH, 'r') as f:
                config = yaml.safe_load(f)
                self.robot_names = []
                if 'flexa' in config:
                    for robot_id, robot_data in config['flexa'].items():
                        self.robot_names.append(robot_data['name'])
                print(f"Loaded {len(self.robot_names)} robots from config")
        except Exception as e:
            print(f"Error loading robot config: {e}")
            # Fallback to default robots if config fails
            self.robot_names = ["base1", "base2", "base3", "base4", "base5", "base6",
                               "base7", "base8", "base9", "base10", "base11", "base12",
                               "base-b2", "base-b3"]

    def _generateLogTemplate(self):
        """Generate log template based on configured robots"""
        template = {
            "API Errors": {"502": []},
            "Robot Errors": {}
        }
        
        # Add each robot to the template
        for robot_name in self.robot_names:
            template["Robot Errors"][robot_name] = []
            
        return template

    ## File handling
    def _loadJson(self, filepath, template = None) -> dict:
        ## If file exists, load the file
        try:
            file = open(filepath, 'r')
            data = json.load(file)
            file.close()
            
            # Ensure all configured robots exist in the log file
            if "Robot Errors" in data:
                for robot_name in self.robot_names:
                    if robot_name not in data["Robot Errors"]:
                        data["Robot Errors"][robot_name] = []
            
            return data

        ## If file does not exist, make a new file
        except FileNotFoundError:
            data = self._makeJson(filepath, template)

            ## File made, reload json
            return self._loadJson(filepath)
        
        except json.decoder.JSONDecodeError as e:
            #print("Error loading json file:", e)
            
            ## if there's an error with the file, use fallback to make sure logs still get recorded, then RM can remedy
            ## until a permanent fix has been implemented (see top of this file)
            return self._loadJson('logs/fallbackLog.json')
    
    def _dumpJson(self, filepath, data) -> None:
        file = open(filepath, 'r+')
        json.dump(data, file)
        file.close

    def _makeJson(self, filepath, template = None) -> None:
        file = open(filepath, 'w')
        if not template:
            ## Generate template dynamically based on configured robots
            template = self._generateLogTemplate()
        
        json.dump(template, file)
        file.close()

    ## Logging
    def getLogPath(self) -> str:
        return self.__logpath
    
    def setLogPath(self, logpath) -> str:
        self.__logpath = logpath

    def getLogs(self) -> dict:
        ## Use this method for getting updated logs
        ## Refresh the logs before returning so that it is always updated to the latest ver.
        self._refreshLogs()
        return self.__logs
    
    def _refreshLogs(self) -> None:
        ## Sets the logpath and loads the logs into self.__logs
        self.setLogPath("logs/log" + str(datetime.now())[:10] + ".json")
        self.__logs = self._loadJson(self.getLogPath())
    
    def updateLogs(self) -> bool:
        """
        Updates the object self.__logs, then dumps the logs into the log.json file

        Returns True if successfully dumps, False if unable to dump

        Since python passes by reference, any time self.__logs is passed to another variable, its values will be modified as well
        """
        ## One more layer before changing the actual values on the file
        print(self.getLogPath())
        try:
            self._dumpJson(self.getLogPath(), self.__logs)
            return True
        
        except Exception as e:
            print(f"rmHelper.py failed to dump JSON!\nException: {e}")
            ## Failed to dump json
            return False

    ## API handler
    def apiCall(self, cmd, content) -> str:
        """
        Robot name should be included in the content as part of the params for API cmd
        
        self.apiCall() will handle any exceptions from requests, no need to do handling above this
        """
        logs = self.getLogs()
        try:
            url = URL + cmd
            response = requests.post(url, headers = AUTHKEY, json = content)

            ## Logs API errors with status code 502
            if (response.status_code == 502):
                now = datetime.now()
                ## Times is an array of the number of times Error 502 was thrown
                times = logs["API Errors"]["502"]
                times.append(now)
                ## Update temp logs with the new time
                logs["API Errors"] = times
                ## Commit changes on the file
                self.updateLogs()

            return response.text
        
        except requests.exceptions.ReadTimeout:
            ## Unable to get a response from API server
            return "Failed to connect to API"
        
    def unpackDoggo(self, doggoError) -> list:
        ## Returns an array error codes from doggo error
        codes = []
        for i in range(len(doggoError)):
            codes.append(doggoError[i]['error_code'])

        return codes

    ## Specific API calls
    ## API calls with no additional params (apart from robot name), wrapper for self.apiCall()
    def generalAPI(self, cmd:str, robotName:str) -> dict:
        """
        ONLY USE FOR COMMANDS THAT ONLY REQUIRE ROBOTNAME

        generalAPI() returns a dict of the response message, no need for json.loads to make the response a usable format

        self.generalAPI() is a wrapper for self.apiCall() to prevent calling unavailable API routes, adds a layer of abstraction and removes the 
        need to format request and response content
        e.g. self.apiCall("navigate_back_to_dock", {"robot_name":robotName}) vs self.generalAPI("back to dock", robotName)

        cmd is mapped in attribute self.routeDict, initialised on instantiation
        """
        try:
            response = json.loads(self.apiCall(self.routeDict[cmd], {"robot_name":robotName}))
            return response
        
        except KeyError:
            ## Invalid route
            raise KeyError
        
    ## Get Cleaning Brush Status
    def brushStatus(self, robotName:str) -> dict:
        try:
            ## Get robot device status
            result = self.generalAPI("device status", robotName)
            response = {}

            response["rear"] = result["result"]["roller_rear_brush_current"]
            response["front"] = result["result"]["roller_front_brush_current"]
            return response

        except Exception as e:
            #print(e)
            pass
    
    ## Get robot status
    def robotStatus(self, robotName:str) -> dict:
        """
        Param robotName should be given as such: base2 or base-b3 etc.
        """
        response = {"isOnline": "NA"}
        
        try:
            ## Check robot status using get_robot_info_rm
            result = self.generalAPI("rm info", robotName)
            response = result["result"]
            
            ## Get robot device status
            result = self.generalAPI("device status", robotName)

            ## Replaces estop message with appropriate specificity, eg: button pressed or bumper hit
            if result["result"]["base_estop_engaged"]:
                response["soft_estop_engaged"] = "Button pressed"

            elif result["result"]["base_bumper_engaged"]:
                response["soft_estop_engaged"] = "Front bumper hit"

            else:
                ## Do not change the message, leave as boolean
                pass
            
            if response["soft_estop_engaged"]:
                ## If estop is engaged, call auto RM
                self.listEstop(response, robotName)

            else:
                ## If estop is not engaged, do nothing
                pass
        
        except:
            ## If json error, check if robot is online
            online = self.generalAPI("is online", robotName)
            response["isOnline"] = online["message"]

        return response
    
    def getWorkingStatus(self, robotName: str) -> str:
        """
        Returns the working status of the robot. 
        Status could be one of: 'cleaning', 'idle', 'charging', or 'navigation'.
        """
        try:
            # Call API to get the robot status
            status = self.robotStatus(robotName)  # This fetches robot status
            # Depending on the robot's status, return the appropriate working status
            if status.get('isOnline') == 'NA':
                return 'Offline'

            if status.get('soft_estop_engaged'):
                return 'E-Stop Engaged'

            if status.get('is_charging', False):
                return 'Charging'

            if status.get('is_cleaning', False):
                return 'Cleaning'

            if status.get('is_navigating', False):
                return 'Navigation'

            return 'Idle'  # Default fallback if no other condition is met

        except Exception as e:
            return f"Error: {str(e)}"
    

    def listEstop(self, response:dict, robotName:str) -> None:
        ## Checks if robot is being tracked for auto estop release
        ## Robot is being tracked
        if robotName in self.estopTracker:
            ## Do nothing
            pass

        else:
            ## Robot is not being tracked, add to tracker
            self.estopTracker[robotName] = 0
        
        print("The dictionary is now", self.estopTracker)
        estopCount = self.estopTracker[robotName]
        autoResponse = self.autoRM(response, robotName)


    ## Auto RM
    def autoRM(self, response:dict, robotName:str) -> None:
        """
        Automatically releases estops for the specified errors in self.estopErrors

        Does not release estop for overtemp errors 1416 and 1417
        self.autoRM() auto logs when an error occurs and logs it in the log.json file

        Variables:
        (var) times     :   is an array of all the times an error occured for the robotName
        (var) errorLog  :   is an array containing the error code and time of occurence, if auto released, will specify as such
        (var) logs      :   gets updated logs from self.getLogs(), which returns self.__logs
        (var) codes     :   array of all the error codes, retrieved from self.unpackDoggo()

        AutoRM actions:
        If the error code is in the list of release-able error codes, auto rm will automatically release estop and log that it was done by autoRM. 
        Error logs are saved as a python list to allow for more mutability and because json is not able to store tuples

        **Auto rm will not release estop for overtemp estops**

        Logging:
        Every error code and the time of occurence will be added to (var)times
        Then (var)logs will be updated to match (var)times
        Once all error codes have been recorded in (var)logs, call self.updateLogs() to push the changes onto the log file

        Limitations and bugs:
        1. There is a known loophole where autoRM could release estop when there are errors that weren't listed
        e.g. if robot overtemps and overcurrents, there would be error codes 1416 and 1414
        autoRM sees error code 1416 and skips to the next iteration
        autoRM sees error code 1414 and releases estop (even though there was an overtemp error)

        an attempted fix was to break the loop when there is an "illegal" code, but it resulted in broken logs

        2. Logs record on a time basis instead of an event basis
        e.g. if robot estops due to mcu issue, there will be multiple log entries on the same issue

        This is not a big issue as it could be used as an indicator for how long the error has been ongoing, however it is still good to note
        that there will be multiple entries of the same issue.
        """

        print("\nAutoRM engaged")
        codes = self.unpackDoggo(response['watch_doggo_error_rm'])
        logs = self.getLogs()

        for code in codes:
            now = datetime.now()
            
            # Ensure the robot exists in the logs
            if robotName not in logs["Robot Errors"]:
                logs["Robot Errors"][robotName] = []
                
            times = logs["Robot Errors"][robotName]
            errorLog = ["[NOT RELEASED] Error " + code, now.strftime("%d/%m/%y %H:%M:%S")]
            ## Only auto release estops for specified error codes
            if code in self.estopErrors:
                ## Codes 1416 and 1417 are overtemp errors, do not auto-release
                if code in ['1416', '1417']:
                    print(robotName, "roller over temperature, release estop manually")

                elif self.estopTracker[robotName] >= 3:
                    ## Do nothing, continue to next loop
                    continue

                else:
                    releaseResponse = self.generalAPI('release estop', robotName)
                    self.estopTracker[robotName] += 1
                    errorLog = ["[AUTO RELEASED] Error " + code, now.strftime("%d/%m/%y %H:%M:%S")]

            else:
                ## Error is not specified, do not auto release
                pass

            ## Finally, add the error msg to the times array and update temp logs to match
            print(errorLog)
            times.append(errorLog)
            logs["Robot Errors"][robotName] = times

        ## Update logfile to match temp logs after all changes have been made
        logUpdated = self.updateLogs()
        print(robotName, str(now), "\nLog updated: ", logUpdated)