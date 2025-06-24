import cv2 # version 4.3.0.38
import numpy as np
import math
import json
from datetime import datetime

class PingerGUI():
    ## dict_color is deprecated, use color_dict
    dict_color = {
                  "on": (0, 128, 0),
                  "off": (0, 0, 255),
                  "unknown": (128, 128, 128),
                 }

    def __init__(self, dict_of_addresses, image_window_name):
        self.dict_of_addresses = dict_of_addresses
        self.dict_of_ping_status = {k: "unknown" for k in dict_of_addresses}
        ## Match the robot ip address to the status of the robot
        self.dict_of_robot_status = {k: {"isOnline":"No Connection"} for k in dict_of_addresses}
        self.dict_of_cleaning_devices = {k: {"Brush":"No Connection"} for k in dict_of_addresses}
        self.padding = 5
        self.rectangle_length = 750
        ## square length is also rectangle height
        self.square_length = 60
        self.num_in_height = len(dict_of_addresses)
        self.num_in_width = 1
        self.window_height = (self.square_length + self.padding)*self.num_in_height
        self.window_width = self.padding + self.num_in_width*(self.rectangle_length + self.square_length + 2*self.padding)
        self.img = 255*np.ones((self.window_height, self.window_width,3), np.uint8)
        self.image_window_name = image_window_name
        self.continue_gui = True
        ## Defines all colour names with their associated BGR
        self.color_dict = {"green": (112, 173, 115),
                           "red": (0, 0, 255),
                           "orange":(128, 180, 250),
                           "yellow":(0, 229, 229),
                           "lightBlue":(255, 154, 100),
                           "navy":(72, 45, 27),
                           "blank":(100, 100, 100),
                           "white":(255, 255, 255),
                           "darkGreen": (32, 50, 1),
                           "darkRed": (0, 20, 255),
                           "darkOrange": (38, 93, 214),
                           "black":(0,0,0)
                           }
    
    def determine_color(self, base):
        '''
        Returns 4 values, baseColour(str), statusColour(str), textColour(str), robot_status(dict)

        self.determine_color(base) Determines the colour based on the robot status. 
        Need to pass in base as parameter, need base to check ping status

        baseColour refers to block on the left
        statusColour refers to the block on the right
        textColour refers to the text on the right, text on the left is a constant white       
        '''
        ## Default colours (when offline)
        baseColour = "blank"
        textColour = 'white'
        statusColour = 'blank'
        robot_status = {}
        cleaning_device_status = {}
        try:
            robot_status = self.dict_of_robot_status[base]
            cleaning_device_status = self.dict_of_cleaning_devices[base]
            if len(robot_status) <= 1:
                ## Unable to connect to robot
                ## Check ping status, in case target is not available on API (local)
                if self.dict_of_ping_status[base] == "on":
                    ## Ping robot to check if online (robot might not be on API, but could be online)
                    baseColour = "navy"

                else:
                    ## Robot offline and not on API, maintain as blank
                    baseColour = "blank"

            else:
                ## Able to connect to robot / Online
                battery = robot_status['battery_soc']
                estop = robot_status['soft_estop_engaged']
                workingStatus = robot_status['working_status']
                good = ['Cleaning', 'Navigation', 'Mapping', 'Manual']

                try:
                    rearCurrent = cleaning_device_status['rear']
                    frontCurrent = cleaning_device_status['front']
                
                except TypeError as e:
                    rearCurrent = "None"
                    frontCurrent = "None"
                    print("Var: ", rearCurrent, frontCurrent)
                    print(e)
                    pass

                ## Check estop, set status colour
                if estop or "error" in workingStatus.lower():
                    ## Red if any error
                    statusColour = "red"

                elif workingStatus in good:
                    ## Green if good
                    statusColour = "green"

                else:
                    ## For anything else
                    statusColour = "navy"
                
                ## Check cleaning devices
                if base == 'Base-B2':
                    if (type(rearCurrent) == float) and (rearCurrent > 0.6):
                        ## rearCurrent has a valid type and more than 0.6
                        baseColour = "green"
                    else:
                        baseColour = "navy"

                else:
                    if (type(frontCurrent) == float) and (frontCurrent > 0.3):
                        ## frontCurrent has a valid type and more than 0.3
                        baseColour = "green"

                    else:
                        baseColour = "navy"


        except KeyError:
            ## Prevents GUI from dying when connection dies midway
            robot_status["isOnline"] = "unknown"
            baseColour = "blank"
            statusColour = "blank"
            textColour = "white"

        return baseColour, statusColour, textColour, robot_status

    def redraw(self):
        for i, base in enumerate(self.dict_of_addresses):
            baseColour, statusColour, textColour, robot_status = self.determine_color(base)

            ## Start here to change the layout of the GUI
            # Square top left and bottom right, panel refers to the entire line

            ## To make the robot name fit in the square
            if base == "Base-B2":
                base = "B2"
            
            elif base == "Base-B3":
                base = "B3"

            else:
                pass

            panel_top_pad = (self.padding + i*(self.padding + self.square_length))
            sqtl = (self.padding, panel_top_pad)
            sqbr = (self.padding + self.square_length, panel_top_pad + self.square_length)
            textCoord = (self.padding + 1, panel_top_pad + 77*self.square_length//128)
            cv2.rectangle(self.img, sqtl, sqbr, self.color_dict[baseColour], -1)
            self.img = cv2.putText(self.img, base, textCoord, cv2.FONT_HERSHEY_TRIPLEX ,
                                   0.5, self.color_dict['white'], 1, cv2.LINE_AA)

            ## Rectangle top left and bottom right
            try:
                statusMessage = "Batt: {0:>3}% | Estop: {1:<7} | Working Status: {2:<11}".format(robot_status['battery_soc'], str(robot_status['soft_estop_engaged']), robot_status['working_status'])

                ## Terminal output as backup in case GUI does not update
                #print(f"{datetime.now().time()} {base:<6} {statusMessage}")
                
            except:
                statusMessage = robot_status["isOnline"]

            try:
                doggoMessage = "Error {0}".format(self.unpack_doggo_error(robot_status['watch_doggo_error_rm']))
                if statusColour == "yellow":
                    ## To make text readable
                    doggoColour = "black"
                else:
                    doggoColour = "yellow"

                ## Terminal output as a backup in case GUI does not update
                #print(doggoMessage)

            except:
                doggoMessage = 'No errors'
                ## Doggo colour defaults to standard colour
                doggoColour = textColour

            tl = (self.square_length + 2*self.padding, panel_top_pad)
            br = (self.square_length + self.padding + self.rectangle_length, panel_top_pad + self.square_length)
            textCoord = (self.square_length + 2*self.padding + 1, panel_top_pad + 3*self.square_length//8)
            doggoCoord = (self.square_length + 2*self.padding + 1, panel_top_pad + 7*self.square_length//8)
            cv2.rectangle(self.img, tl, br, self.color_dict[statusColour], -1)
            self.img = cv2.putText(self.img, statusMessage, textCoord, cv2.FONT_HERSHEY_TRIPLEX ,
                                   0.6, self.color_dict[textColour], 1, cv2.LINE_AA)
            self.img = cv2.putText(self.img, doggoMessage, doggoCoord, cv2.FONT_HERSHEY_TRIPLEX,
                                    0.6, self.color_dict[doggoColour], 1, cv2.LINE_AA)

    def unpack_doggo_error(self, errorRm:list) -> str:
        ## Unpacks rm_message in watch_doggo_error_rm
        ## Low error refers to lower priority errors, add to the array
        lowError = ['1201']
        ## Truncated errors, for when the message is too long
        truncError = {'3605':"Module MCU disconnected"}
        i = 0
        #print(errorRm)
        while (errorRm[i]['error_code'] in lowError):
            ## Get next error
            if i < len(errorRm):
                i += 1
            
            else:
                i -= 1
                break
        
        rmMessage = errorRm[i]['rm_message']
        errorCode = errorRm[i]['error_code']
        if errorCode in truncError.keys():
            rmMessage = truncError[errorCode]
        
        message = "{0}: {1}".format(errorCode, rmMessage)
        return message

    def redraw_and_show(self):
        self.redraw()
        cv2.imshow(self.image_window_name, self.img)

    def update_ping_status(self, new_dict_of_ping_status, new_dict_of_robot_status, new_dict_of_cleaning_device_status):
        for k in self.dict_of_ping_status:
            ping_status = new_dict_of_ping_status.get(k, None)
            self.dict_of_robot_status = new_dict_of_robot_status
            self.dict_of_cleaning_devices = new_dict_of_cleaning_device_status
            if ping_status is None:
                self.dict_of_ping_status[k] = "unknown"
            else:
                self.dict_of_ping_status[k] = "on" if ping_status else "off"
            

    def update_and_redraw_and_show(self, new_dict_of_ping_status):
        self.update_ping_status(new_dict_of_ping_status)
        self.redraw_and_show()

    def stopGUI(self):
        self.continue_gui = False

    def main(self):
        cv2.namedWindow(self.image_window_name, cv2.WINDOW_NORMAL)

        while self.continue_gui:
            self.redraw_and_show()
            # close if window closes with [x], or if 'q' is pressed on keyboard
            if ((cv2.waitKey(1000) == ord('q')) or (cv2.getWindowProperty(self.image_window_name, cv2.WND_PROP_VISIBLE) < 1)):
                self.continue_gui = False
                break

        cv2.destroyAllWindows()




if __name__=="__main__":
    address_book = {"VPN": "192.168.1.1", "SLAVE": "192.168.1.100", "MASTER": "192.168.1.102"}
    gui = PingerGUI(address_book, "test page")
    gui.main()

