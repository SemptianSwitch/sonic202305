#!/usr/bin/env python
# ------------------------------------------------------------------
# HISTORY:
#    mm/dd/yyyy (A.D.)
#    7/27/2021:  Lkj create for semptian
# ------------------------------------------------------------------

try:
    import getopt
    import os
    import sys
    import logging
    import logging.config
    import logging.handlers
    import subprocess
    import time  # this is only being used as part of the example
    
    import signal
except ImportError as e:
    raise ImportError('%s - required module not found' % str(e))

'''
If you want to disable the watchdog when the program is abnormal, 
please open the code snippet with the comment information: wdt disable
'''

VERSION = '1.0'
SCRIPT_NAME = ""
FUNCTION_NAME = '/usr/local/bin/semptian_monitor_watchdog'

# retry count
RETRY_COUNTS_MAX = 10
# retry interval in second.  The entire retry process takes 5 minutes(10*30 s = 300 s = 5 min) 
RETRY_INTERVALS_SECOND = 30

#watch_dog_base_path = "/sys/class/hwmon/hwmon4"
global log_file
global log_level


# Make a class we can use to capture stdout and sterr in the log
class Watchdog_monitor(object):

    # define a class attribute whose value is independent of the specific Watchdog_monitor class object
    base_cpld_path = None
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

        logging.info("%s  PID: %d", SCRIPT_NAME, os.getpid())
        #logging.debug('SET. logfile:%s / loglevel:%d', log_file, log_level)
    
    # define a class method that can only access class properties and call class methods
    @classmethod
    def generate_base_cpld_path(cls):
        '''
            Generate base_cpld_path path.
        '''
        index = Watchdog_monitor.get_mg_cpld_hwmon_offset()        
        if index is None:
            Watchdog_monitor.base_cpld_path = None
            logging.info("get_mg_cpld_hwmon_offset error")
            return None
        
        path = '/sys/class/hwmon/hwmon{0}/'
        Watchdog_monitor.base_cpld_path = path.format(index)
        return 0
    
    # define a static method that has nothing to do with the 
    # specific Watchdog_monitor class object and class attributes
    @staticmethod
    def get_mg_cpld_hwmon_offset():
        '''
            Get the xc3200an_mg_cpld device node to 
              find the wdt related device node
        '''
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
    
    # Define a class method that can only access class properties and call class methods
    @classmethod
    def watch_dog_enable_set(cls, val):
        '''
            Enable/disable wdt function
        '''
        filename = "%s%s" % (Watchdog_monitor.base_cpld_path, "wdt_enb")
        
        if os.path.exists(filename):
            f = open(filename, 'w')
            f.seek(0,0)
            f.write(str(val))
            f.close()
            return 0
        else:
            logging.info("path %s is no exist", filename)
            return None
    
    def watch_dog_feed_dog(self):
        '''
            wdt dog feeding operation
        '''
        filename = "%s%s" % (Watchdog_monitor.base_cpld_path, "wdt_signal")
        
        if os.path.exists(filename):
            f = open(filename, 'w')
            f.seek(0,0)
            f.write("1")
            f.close()
            return 0
        else:
            logging.info("path %s is no exist", filename)
            return None
    
    def watch_dog_time_get(self):
        '''
            Get the delay for wgt to feed the dog
        '''
        filename = "%s%s" % (Watchdog_monitor.base_cpld_path, "wdt_time")
        
        if os.path.exists(filename):
            f = open(filename, 'r')
            f.seek(0,0)
            ct = f.read()
            f.close()
            ct_list = ct.split()
            return int(ct_list[0])
        else:
            logging.info("path %s is no exist", filename)
            return None
             
    def watch_dog_enb_init(self):
        '''
            enable wdt function 
        '''
        return Watchdog_monitor.watch_dog_enable_set("1")
        
    def manage_wdt(self):
        '''
            wdt main management functions for monitoring and feeding dogs
        '''
        ret = Watchdog_monitor.generate_base_cpld_path()
        if ret is None:
            logging.info("generate_base_cpld_path error")
            return None
    
        feed_dog_time = 6
        
        ret = self.watch_dog_enb_init()
        if ret is None:
            logging.info("watch_dog_enb_init error")
            return None
        
        while True:
            #logging.info("%s is running...", SCRIPT_NAME)
            ret = self.watch_dog_time_get()
            if ret is None:
                logging.info("watch_dog_time_get error")
                return None
            
            feed_dog_time = ret
            feed_dog_time = feed_dog_time/6
            
            ret = self.watch_dog_feed_dog()
            if ret is None:
                logging.info("watch_dog_feed_dog error")
                return None
            
            if feed_dog_time > 0 :
                time.sleep(feed_dog_time)
            else:
                time.sleep(10)
    
    #comment: wdt disable
    #def __del__(self):
    #    '''
    #        Destructor of class object: used to prohibit wdt function 
    #          to prevent system reset caused by not feeding the dog in time
    #    '''
    #    if Watchdog_monitor.base_cpld_path is None:
    #        ret = Watchdog_monitor.generate_base_cpld_path()
    #        if ret is None:
    #            logging.info("__del__() generate_base_cpld_path error")
    #    
    #    
    #    ret = Watchdog_monitor.watch_dog_enable_set("0")
    #    if ret is not None:
    #        logging.info("__del__() disable watchdog success!")
    #        logging.info("If needed, manually turn on the wdt service again.")
    #        logging.info("#" * 80)
        

#comment: wdt disable
#def handler(signum, frame):
#    '''
#        When the program receives an abnormal signal, 
#         it will disable wgt to avoid system reset.
#    '''
#    
#    logging.info("%s: The program catches an exception signal %d, and is about to exit....", SCRIPT_NAME, signum)
#    
#    if Watchdog_monitor.base_cpld_path is None:
#        ret = Watchdog_monitor.generate_base_cpld_path()
#        if ret is None:
#            logging.info("handler generate_base_cpld_path error")
#            
#    ret = Watchdog_monitor.watch_dog_enable_set("0")
#    if ret is not None:
#        logging.info("handler disable watchdog success!")
#        logging.info("If needed, manually turn on the wdt service again.")
#        logging.info("#" * 80)
#    
#    raise OSError("%s has an error occured!", SCRIPT_NAME)


#comment: wdt disable
#def register_signal_handler():
#    '''
#        Register a signal handler to disable wdt function 
#            when the program receives an exception signal.
#    '''
#    signal.signal(signal.SIGHUP, handler)
#    signal.signal(signal.SIGINT, handler)
#    signal.signal(signal.SIGQUIT, handler)
#    signal.signal(signal.SIGILL, handler)
#    signal.signal(signal.SIGTRAP, handler)
#    signal.signal(signal.SIGABRT, handler)
#    signal.signal(signal.SIGBUS, handler)
#    #signal.signal(signal.SIGKILL, handler) # This signal SIGKILL cannot be caught or ignored
#    
#    signal.signal(signal.SIGUSR1, handler)
#    signal.signal(signal.SIGSEGV, handler)
#    signal.signal(signal.SIGUSR2, handler)
#    signal.signal(signal.SIGPIPE, handler)
#    signal.signal(signal.SIGALRM, handler)
#    signal.signal(signal.SIGTERM, handler)

def main(argv):
    log_file = '%s.log' % FUNCTION_NAME
    log_level = logging.INFO
    
    #comment: wdt disable
    #register_signal_handler()
    
    # Parse input parameters
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
    wdt_monitor = Watchdog_monitor(log_file, log_level)
    # Program main loop to deal with wdt function.
    while True:
        wdt_monitor.manage_wdt()
        
        if ret >= RETRY_COUNTS_MAX:
            logging.info("%s failed to execute", SCRIPT_NAME)
            return 0
        
        ret += 1
        logging.info("%s sleep %d sec and wait for next try...", SCRIPT_NAME, RETRY_INTERVALS_SECOND)
        time.sleep(RETRY_INTERVALS_SECOND)
        logging.info("%s try to execute again, remaining times: %d", SCRIPT_NAME, RETRY_COUNTS_MAX - ret)
        logging.info("-" * 80)

    logging.info("%s is exit......", SCRIPT_NAME)
    logging.info("#" * 80)

if __name__ == '__main__':
    SCRIPT_NAME = sys.argv[0]
    main(sys.argv[1:])
