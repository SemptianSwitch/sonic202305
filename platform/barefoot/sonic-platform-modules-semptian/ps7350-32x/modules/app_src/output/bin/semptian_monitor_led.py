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
FUNCTION_NAME = '/usr/local/bin/semptian_monitor_led'

RETRY_COUNTS_MAX = 10       
RETRY_INTERVALS_SECOND = 30 

global log_file
global log_level

SYS_LED_STR_ON          = "0"
SYS_LED_STR_BLINK_1S    = "1" 
SYS_LED_STR_BLINK_500MS = "2"
SYS_LED_STR_BLINK_125MS = "3"
SYS_LED_STR_OFF         = "4"


class Sys_led_type_enum(Enum):
    SYS_LED_TYPE_STATE = 1
    SYS_LED_TYPE_ALARM = 2
    SYS_LED_TYPE_MAX   = 3

class Sys_led_action_enum(Enum):
    SYS_LED_ON          = 1
    SYS_LED_OFF         = 2
    SYS_LED_BLINK_1S    = 3
    SYS_LED_BLINK_125MS = 4
    SYS_LED_BLINK_500MS = 5
    SYS_LED_MAX         = 6

class Bdd_platform_type_enum(Enum):
    PLTFM_TYPE_PS8550 = 1
    PLTFM_TYPE_PS8560 = 2
    PLTFM_TYPE_PS7350 = 3
    PLTFM_TYPE_MAX    = 4


# Make a class we can use to capture stdout and sterr in the log
class led_monitor(object):

    alarm = 0
    base_cpld_path = ""
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
        
    
    def get_mg_cpld_hwmon_offset(self):
        sysfs = '/sys/class/hwmon/hwmon{0}/name'
        
        offset = -1
        cpld_name = 'xc3200an_mg_cpld'
        for index in range(0, 10):
            filename=sysfs.format(index)
            
            if os.path.exists(filename) and os.path.isfile(filename):
                cmd = "cat " + filename
                proc1 = subprocess.Popen(cmd, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
                output = proc1.stdout.readlines()
                errput = proc1.stderr.readlines()
                (out, err) = proc1.communicate()
                
                if proc1.returncode > 0:
                    for line1 in errput:
                        logging.info("ipmitool sdr Error: %s", line1.strip())
                    return None
                
                
                #print("filename:%s  adaptername:%s find result:%s" % (filename, adaptername, adaptername.find(cpld_name)))
                for i in range(len(output)):
                    if output[0].find(cpld_name) >= 0:
                        offset = index       
                        break
                
        return  offset 
        
    def bf_pltfm_sys_led_init(self):
        return self.bf_pltfm_ps7350_sys_led_set(Sys_led_type_enum.SYS_LED_TYPE_STATE, Sys_led_action_enum.SYS_LED_BLINK_1S)
    
    def bf_pltfm_ps7350_sys_led_set(self, led_type, led_action):
        if led_type is Sys_led_type_enum.SYS_LED_TYPE_STATE:
            filename = "%s%s" % (self.base_cpld_path, "system_led")
            
        elif led_type is Sys_led_type_enum.SYS_LED_TYPE_ALARM:
            filename = "%s%s" % (self.base_cpld_path, "alarm_led")
        
        if os.path.exists(filename) and os.path.isfile(filename):
            f = open(filename, 'w')
            f.seek(0,0)
            
            if led_action is Sys_led_action_enum.SYS_LED_ON:
                f.write(SYS_LED_STR_ON)
            elif led_action is Sys_led_action_enum.SYS_LED_BLINK_1S:
                f.write(SYS_LED_STR_BLINK_1S)
            elif led_action is Sys_led_action_enum.SYS_LED_BLINK_125MS:
                f.write(SYS_LED_STR_BLINK_125MS)
            elif led_action is Sys_led_action_enum.SYS_LED_BLINK_500MS:
                f.write(SYS_LED_STR_BLINK_500MS)
            elif led_action is Sys_led_action_enum.SYS_LED_OFF:
                f.write(SYS_LED_STR_OFF)
            
            f.close()
            return 0
        else:
            logging.info("path %s is no exist", filename)
            return None
    
    def bf_pltfm_sys_led_set(self, led_type, led_action):
        return self.bf_pltfm_ps7350_sys_led_set(led_type, led_action)
    
    def bmc_alarm_info_check(self):
        alarm_state = 0
        
        proc1 = subprocess.Popen("ipmitool sdr", shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        output = proc1.stdout.readlines()
        errput = proc1.stderr.readlines()
        (out, err) = proc1.communicate()
        
        if proc1.returncode > 0:
            for line1 in errput:
                logging.info("ipmitool sdr Error: %s", line1.strip())
            return None
        
        for i in range(len(output)):
            #logging.info("%s",output[i].strip())  # strip() is to remove spaces and newlines
            str_list = output[i].strip().split("|")
            str_middle = str_list[1].strip()
            
            #if str_middle == "disable":
            #    continue
            
            str_last = str_list[-1].strip()
            if str_last == "nr" or str_last == "sr" or str_middle.find("disable") >= 0:
                alarm_state += 1
            
        return  alarm_state
        
    def manage_led(self): 
        alarm_num = 0
        pltfm_type = Bdd_platform_type_enum.PLTFM_TYPE_PS7350

        index = self.get_mg_cpld_hwmon_offset()        
        if index is None:
            logging.info("get_mg_cpld_hwmon_offset error")
            return None
        
        path = '/sys/class/hwmon/hwmon{0}/'
        self.base_cpld_path = path.format(index)
        
        ret = self.bf_pltfm_sys_led_init()
        time.sleep(1)
        if ret is None:
            logging.info("bf_pltfm_sys_led_init error")
            return None
        
        while True:
            #logging.info("%s is running...", SCRIPT_NAME)
            ret = self.bmc_alarm_info_check()
            if ret is None:
                logging.info("bmc_alarm_info_check error")
                return None
            
            alarm_num = ret
            
            if self.alarm != alarm_num:
                logging.info("warning  self.alarm:%d changed to alarm_num:%d !!!!!!!!!!!!!!!!", self.alarm, alarm_num)
                
                self.alarm = alarm_num
                
                if alarm_num > 4:
                    logging.info("warning  alarm_num:%d !!!!!!!!!!!!!!!!\r\n", alarm_num);
                    ret = self.bf_pltfm_sys_led_set(Sys_led_type_enum.SYS_LED_TYPE_ALARM, Sys_led_action_enum.SYS_LED_BLINK_125MS)
                    
                elif alarm_num > 2:
                    logging.info("warning  alarm_num:%d !!!!!!!!!!!!!!!!\r\n", alarm_num);
                    ret = self.bf_pltfm_sys_led_set(Sys_led_type_enum.SYS_LED_TYPE_ALARM, Sys_led_action_enum.SYS_LED_BLINK_500MS)
                    
                elif alarm_num > 0:
                    logging.info("warning  alarm_num:%d !!!!!!!!!!!!!!!!\r\n", alarm_num);
                    ret = self.bf_pltfm_sys_led_set(Sys_led_type_enum.SYS_LED_TYPE_ALARM, Sys_led_action_enum.SYS_LED_BLINK_1S)
                
                elif alarm_num == 0:
                    ret = self.bf_pltfm_sys_led_set(Sys_led_type_enum.SYS_LED_TYPE_ALARM, Sys_led_action_enum.SYS_LED_OFF)
                
                if ret < 0 or ret is None:
                    self.alarm = 0
                    logging.info("[monitor] pltfm_type:%s set sys led err", pltfm_type.name)

            
            time.sleep(5)
        
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
    monitor = led_monitor(log_file, log_level)
    while True:
        monitor.manage_led()
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
