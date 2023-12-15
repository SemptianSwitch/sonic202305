#!/usr/bin/env python
# ------------------------------------------------------------------
# HISTORY:
#    mm/dd/yyyy (A.D.)
#    7/27/2021:  Lkj create for semptian
# ------------------------------------------------------------------

try:
    import getopt
    import os
    import logging
    import sys
    import logging.config
    import logging.handlers
    import subprocess
    import time  # this is only being used as part of the example
    from enum import Enum
except ImportError as e:
    raise ImportError('%s - required module not found' % str(e))


VERSION = '1.0'
SCRIPT_NAME = ""
FUNCTION_NAME = '/usr/local/bin/semptian_monitor_usbnet'

RETRY_COUNTS_MAX = 10       
RETRY_INTERVALS_SECOND = 30 

global log_file
global log_level

IFCONFIG_USB0 = "ifconfig usb0"
USB_NAME = "usb0"

class Bdd_platform_type_enum(Enum):
    PLTFM_TYPE_PS8550 = 1
    PLTFM_TYPE_PS8560 = 2
    PLTFM_TYPE_PS7350 = 3
    PLTFM_TYPE_MAX    = 4


# Make a class we can use to capture stdout and sterr in the log
class usb_monitor(object):

    def __init__(self, log_file, log_level):
    
        """Needs a logger and a logger level."""
        # set up logging to file
        logging.basicConfig(
            filename=log_file,
            filemode='a',   # filemode='a' will append context into logfile, filemode='w' will truncated logfile 
            level=log_level,
            format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        # set up logging to console
        if log_level == logging.DEBUG:
            console = logging.StreamHandler()
            console.setLevel(log_level)
            formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

        sys_handler = logging.handlers.SysLogHandler(address = '/dev/log')
        #sys_handler.setLevel(logging.WARNING)       
        sys_handler.setLevel(logging.INFO)       
        logging.getLogger('').addHandler(sys_handler)

        #logging.debug('SET. logfile:%s / loglevel:%d', log_file, log_level)
    def bmc_usb_status_check(self):
        usb_up = 0
        
        proc1 = subprocess.Popen(IFCONFIG_USB0, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        output = proc1.stdout.readlines()
        errput = proc1.stderr.readlines()
        (out, err) = proc1.communicate()
        
        if proc1.returncode > 0:
            for line1 in errput:
                logging.info("%s: %s", IFCONFIG_USB0, line1.strip())
            return None
        
        for i in range(len(output)):
            #logging.info("%s",output[i].strip())  # strip() is to remove spaces and newlines
            str_list = output[i].strip().split(":")

            str_first = str_list[-1].strip()
            if str_first.find("UP") >= 0:
                usb_up = 1
                break
            
        return  usb_up
    
    def bmc_usb_check(self):
        usb_ready = 0
        
        proc1 = subprocess.Popen(IFCONFIG_USB0, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        output = proc1.stdout.readlines()
        errput = proc1.stderr.readlines()
        (out, err) = proc1.communicate()
        
        if proc1.returncode > 0:
            for line1 in errput:
                logging.info("%s: %s", IFCONFIG_USB0, line1.strip())
            return None
        
        for i in range(len(output)):
            #logging.info("%s",output[i].strip())  # strip() is to remove spaces and newlines
            str_list = output[i].strip().split(":")

            str_first = str_list[0].strip()
            if str_first.find(USB_NAME) >= 0:
                usb_ready = 1
                break
            
        return  usb_ready
        
    def manage_usb(self): 
        alarm_num = 0
        pltfm_type = Bdd_platform_type_enum.PLTFM_TYPE_PS7350
        # 1. check usb if exsit
        # 2. check usb if down
        # 3. usb up

        while True:
            #logging.info("%s is running...", SCRIPT_NAME)
            ret = self.bmc_usb_check()
            if ret is None:
                logging.warn("bmc usb not ready")
                return None
            
            if ret == 1:
                status = self.bmc_usb_status_check()
                if status == 0:
                    logging.warn("usb if down");
                    cmd =  IFCONFIG_USB0 + ' up'
                    rv = os.popen(cmd)
                    rv.close()
            else:
                logging.warn("bmc usb not ready")
            time.sleep(10)
        
        return 0

def main(argv):
    log_file = '%s.log' % FUNCTION_NAME
    log_level = logging.INFO
     
    if len(sys.argv) != 1:
        try:
            opts, args = getopt.getopt(argv,'hdl:',['lfile='])
        except getopt.GetoptError:
            print('Usage: %s [-d] [-l <log_file>]' % sys.argv[0])
            print('       -d: debug mode')
            print('       -l: log_file name')
            return 0
        for opt, arg in opts:
            if opt == '-h':
                print('Usage: %s [-d] [-l <log_file>]' % sys.argv[0])
                return 0
            elif opt in ('-d', '--debug'):
                log_level = logging.DEBUG
            elif opt in ('-l', '--lfile'):
                log_file = arg

    ret = 0    
    monitor = usb_monitor(log_file, log_level)
    while True:
        monitor.manage_usb()
        if ret >= RETRY_COUNTS_MAX:
            logging.info("%s failed to execute", SCRIPT_NAME)
            return 0

        ret += 1
        logging.info("%s sleep %d sec and wait for next try...", SCRIPT_NAME, RETRY_INTERVALS_SECOND)
        time.sleep(RETRY_INTERVALS_SECOND)
        logging.info("%s try to execute again, remaining times: %d", SCRIPT_NAME, RETRY_COUNTS_MAX - ret)



if __name__ == '__main__':
    SCRIPT_NAME = sys.argv[0]
    main(sys.argv[1:])
