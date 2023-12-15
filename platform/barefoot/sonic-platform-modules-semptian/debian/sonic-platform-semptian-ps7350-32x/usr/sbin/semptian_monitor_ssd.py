#!/usr/bin/env python
# ------------------------------------------------------------------
# HISTORY:
#    mm/dd/yyyy (A.D.)
#    7/27/2021:  Lkj create for semptian
# ------------------------------------------------------------------

try:
    import getopt
    import sys
    import logging
    import logging.config
    import logging.handlers
    import subprocess
    import time  # this is only being used as part of the example
except ImportError as e:
    raise ImportError('%s - required module not found' % str(e))

# Deafults
RECORD_ROW_NUM = 9  # row size of one inspection information 
RECORD_ROW_MAX = RECORD_ROW_NUM * 12  # up to 12 inspection information

VERSION = '1.0'
FUNCTION_NAME = '/usr/local/bin/semptian_monitor_ssd'

global log_file
global log_level


# Make a class we can use to capture stdout and sterr in the log
class ssd_monitor(object):

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
        
    def manage_ssd(self): 
    
        command1 = "sudo show platform ssdhealth --verbose "
        # run command 1
        proc1 = subprocess.Popen(command1, shell=True, universal_newlines=True, stdout=subprocess.PIPE)
        output1 = proc1.stdout.readlines()
        (out, err) = proc1.communicate()
        
        
        if proc1.returncode > 0:
            for line1 in output1:
                print(line1.strip())
            return
        
        for i in range(len(output1)):
            logging.info("%s",output1[i].strip())  # strip() is to remove spaces and newlines
        
        # Save up to 12 inspection information
        log_file_name = '%s.log' % FUNCTION_NAME
        f = open(log_file_name, 'a+')
        f.seek(0,0)
        text_list = f.readlines()
        cut_len = RECORD_ROW_MAX
        if len(text_list) > cut_len:
            new_list = text_list[-cut_len:]
            f.seek(0,0)
            f.truncate(0)
            f.seek(0,0) 
            f.writelines(new_list)
            
        f.close()
        
        return True

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
    
    monitor = ssd_monitor(log_file, log_level)
    # Loop forever, doing something useful hopefully:
    #while True:
    #start_tm = time.perf_counter()
    monitor.manage_ssd()
    #finish_tm = time.perf_counter()
    ##logging.info("%f", finish_tm - start_tm)
    #time.sleep(3-round(finish_tm - start_tm))

if __name__ == '__main__':
    main(sys.argv[1:])
