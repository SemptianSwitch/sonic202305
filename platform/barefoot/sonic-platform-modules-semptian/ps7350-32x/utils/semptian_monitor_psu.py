#!/usr/bin/env python3

import signal
import sys
import threading
from datetime import datetime

from sonic_platform.psu import Psu
from sonic_py_common import daemon_base, logger
from swsscommon import swsscommon


#
# Constants ====================================================================
#

# TODO: Once we no longer support Python 2, we can eliminate this and get the
# name using the 'name' field (e.g., `signal.SIGINT.name`) starting with Python 3.5
SIGNALS_TO_NAMES_DICT = dict((getattr(signal, n), n)
                             for n in dir(signal) if n.startswith('SIG') and '_' not in n)

SYSLOG_IDENTIFIER = "psu_monitor"

PLATFORM_SPECIFIC_MODULE_NAME = "psuutil"
PLATFORM_SPECIFIC_CLASS_NAME = "PsuUtil"

CHASSIS_INFO_TABLE = 'CHASSIS_INFO'
CHASSIS_INFO_KEY = 'chassis 1'
CHASSIS_INFO_PSU_NUM_FIELD = 'psu_num'

CHASSIS_INFO_POWER_CONSUMER_FIELD = 'Consumed Power {}'
CHASSIS_INFO_POWER_SUPPLIER_FIELD = 'Supplied Power {}'
CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD = 'Total Consumed Power'
CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD = 'Total Supplied Power'
CHASSIS_INFO_POWER_KEY_TEMPLATE = 'chassis_power_budget {}'

PSU_INFO_TABLE = 'PSU_INFO'
PSU_INFO_KEY_TEMPLATE = 'PSU {}'
PSU_INFO_PRESENCE_FIELD = 'presence'
PSU_INFO_MODEL_FIELD = 'model'
PSU_INFO_SERIAL_FIELD = 'serial'
PSU_INFO_REV_FIELD = 'revision'
PSU_INFO_STATUS_FIELD = 'status'
PSU_INFO_TEMP_FIELD = 'temp'
PSU_INFO_TEMP_TH_FIELD = 'temp_threshold'
PSU_INFO_VOLTAGE_FIELD = 'voltage'
PSU_INFO_VOLTAGE_MAX_TH_FIELD = 'voltage_max_threshold'
PSU_INFO_VOLTAGE_MIN_TH_FIELD = 'voltage_min_threshold'
PSU_INFO_CURRENT_FIELD = 'current'
PSU_INFO_POWER_FIELD = 'power'
PSU_INFO_FRU_FIELD = 'is_replaceable'
PSU_INFO_FAN_SPEED_FIELD = 'fan_speed'

PHYSICAL_ENTITY_INFO_TABLE = 'PHYSICAL_ENTITY_INFO'

FAN_INFO_TABLE = 'FAN_INFO'
FAN_INFO_PRESENCE_FIELD = 'presence'
FAN_INFO_STATUS_FIELD = 'status'
FAN_INFO_DIRECTION_FIELD = 'direction'
FAN_INFO_SPEED_FIELD = 'speed'
FAN_INFO_LED_STATUS_FIELD = 'led_status'
FAN_INFO_TIMESTAMP_FIELD = 'timestamp'

NOT_AVAILABLE = 'N/A'
UPDATING_STATUS = 'Updating'

PSU_INFO_UPDATE_PERIOD_SECS = 10

PSUUTIL_LOAD_ERROR = 1

platform_psuutil = None
platform_chassis = None

exit_code = 0

# temporary wrappers that are compliable with both new platform api and old-style plugin mode


def _wrapper_get_num_psus():
    if platform_chassis is not None:
        try:
            return platform_chassis.get_num_psus()
        except NotImplementedError:
            pass
    return platform_psuutil.get_num_psus()


def _wrapper_get_psu_presence(psu_index):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_psu(psu_index - 1).check_power_presence_err() #return platform_chassis.get_psu(psu_index - 1).get_presence()
        except NotImplementedError:
            pass
    return platform_psuutil.get_psu_presence(psu_index)


def _wrapper_get_psu_status(psu_index):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_psu(psu_index - 1).check_pg_signal_err() # return platform_chassis.get_psu(psu_index - 1).get_powergood_status()
        except NotImplementedError:
            pass
    return platform_psuutil.get_psu_status(psu_index)


#
# Helper functions =============================================================
#

def get_psu_key(psu_index):
    return PSU_INFO_KEY_TEMPLATE.format(psu_index)


def psu_db_update(psu_tbl, psu_num):
    for psu_index in range(1, psu_num + 1):
        fvs = swsscommon.FieldValuePairs([(PSU_INFO_PRESENCE_FIELD,
                                           'true' if _wrapper_get_psu_presence(psu_index) else 'false'),
                                          (PSU_INFO_STATUS_FIELD,
                                           'true' if _wrapper_get_psu_status(psu_index) else 'false')])
        psu_tbl.set(get_psu_key(psu_index), fvs)


# try get information from platform API and return a default value if we catch NotImplementedError
def try_get(callback, default=None):
    """
    Handy function to invoke the callback and catch NotImplementedError
    :param callback: Callback to be invoked
    :param default: Default return value if exception occur
    :return: Default return value if exception occur else return value of the callback
    """
    try:
        ret = callback()
        if ret is None:
            ret = default
    except NotImplementedError:
        ret = default

    return ret


def log_on_status_changed(logger, normal_status, normal_log, abnormal_log):
    """
    Log when any status changed
    :param logger: Logger object.
    :param normal_status: Expected status.
    :param normal_log: Log string for expected status.
    :param abnormal_log: Log string for unexpected status
    :return:
    """
    if normal_status:
        logger.log_notice(normal_log)
    else:
        logger.log_warning(abnormal_log)

#
# PSU Chassis Info ==========================================================
#


class PsuChassisInfo(logger.Logger):

    def __init__(self, log_identifier, chassis):
        """
        Constructor for PsuChassisInfo
        :param chassis: Object representing a platform chassis
        """
        super(PsuChassisInfo, self).__init__(log_identifier)

        self.chassis = chassis
        self.first_run = True
        self.master_status_good = True
        self.total_consumed_power = 0.0
        self.total_supplied_power = 0.0

    def run_power_budget(self, chassis_tbl):
        self.total_supplied_power = 0.0
        self.total_consumed_power = 0.0
        total_supplied_power = 0.0
        total_fan_consumed_power = 0.0
        total_module_consumed_power = 0.0

        dict_index = 0
        total_entries_len = 2  # For total supplied and consumed
        dict_len = self.chassis.get_num_psus() +\
            self.chassis.get_num_fan_drawers() +\
            self.chassis.get_num_modules() + \
            total_entries_len

        fvs = swsscommon.FieldValuePairs(dict_len)

        for index, psu in enumerate(self.chassis.get_all_psus()):
            presence = try_get(psu.get_presence)
            if not presence:
                continue

            power_good = try_get(psu.get_powergood_status)
            if not power_good:
                continue

            name = try_get(psu.get_name, 'PSU {}'.format(index + 1))
            supplied_power = try_get(psu.get_maximum_supplied_power, 0.0)
            total_supplied_power = total_supplied_power + supplied_power
            fvs[dict_index] = (CHASSIS_INFO_POWER_SUPPLIER_FIELD.format(name), str(supplied_power))
            dict_index += 1

        for index, power_consumer in enumerate(self.chassis.get_all_fan_drawers()):
            presence = try_get(power_consumer.get_presence)
            if not presence:
                continue

            name = try_get(power_consumer.get_name, 'FAN-DRAWER {}'.format(index))
            fan_drawer_power = try_get(power_consumer.get_maximum_consumed_power, 0.0)
            total_fan_consumed_power = total_fan_consumed_power + fan_drawer_power
            fvs[dict_index] = (CHASSIS_INFO_POWER_CONSUMER_FIELD.format(name), str(fan_drawer_power))
            dict_index += 1

        for index, power_consumer in enumerate(self.chassis.get_all_modules()):
            presence = try_get(power_consumer.get_presence)
            if not presence:
                continue

            name = try_get(power_consumer.get_name, 'MODULE {}'.format(index))
            module_power = try_get(power_consumer.get_maximum_consumed_power, 0.0)
            total_module_consumed_power = total_module_consumed_power + module_power
            fvs[dict_index] = (CHASSIS_INFO_POWER_CONSUMER_FIELD.format(name), str(module_power))
            dict_index += 1

        # Record total supplied and consumed power
        self.total_supplied_power = total_supplied_power
        self.total_consumed_power = total_fan_consumed_power + total_module_consumed_power

        # Record in state DB in chassis table
        fvs[dict_index] = (CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD, str(self.total_supplied_power))
        fvs[dict_index + 1] = (CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD, str(self.total_consumed_power))
        chassis_tbl.set(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1), fvs)

    def update_master_status(self):
        set_led = self.first_run
        master_status_good = False

        if self.total_supplied_power != 0.0 and self.total_consumed_power != 0.0:
            master_status_good = (self.total_consumed_power < self.total_supplied_power)
            if master_status_good != self.master_status_good:
                set_led = True

            self.master_status_good = master_status_good

        if set_led:
            # Update the PSU master status LED
            # set_status_master_led() is a class method implemented in PsuBase
            # so we do not need to catch NotImplementedError here
            color = Psu.STATUS_LED_COLOR_GREEN if master_status_good else Psu.STATUS_LED_COLOR_RED
            Psu.set_status_master_led(color)

            log_on_status_changed(self, self.master_status_good,
                                  'PSU supplied power warning cleared: supplied power is back to normal.',
                                  'PSU supplied power warning: {}W supplied-power less than {}W consumed-power'.format(
                                      self.total_supplied_power, self.total_consumed_power)
                                  )

        return set_led

# PSU status ===================================================================
#


class PsuStatus(object):
    def __init__(self, logger, psu, psu_index):
        self.psu = psu
        self.psu_index = psu_index
        self.presence = True
        self.power_good = True
        self.voltage_good = True
        self.temperature_good = True
        self.logger = logger
        
        self.over_temp         = True
        self.over_volt_input   = True
        self.under_volt_input  = True
        self.over_curr_input   = True
        self.over_volt_output  = True
        self.under_volt_output = True
        self.over_curr_output  = True
        
        self.device_match_res = True
        self.alarm_err = True
        self.pg_signal_err = True
        
    def set_presence(self, presence):
        """
        Set and cache PSU presence status
        :param presence: PSU presence status
        :return: True if status changed else False
        """
        if presence == self.presence:
            return False

        self.presence = presence
        return True

    def set_power_good(self, power_good):
        """
        Set and cache PSU power good status
        :param power_good: PSU power good status
        :return: True if status changed else False
        """
        if power_good == self.power_good:
            return False

        self.power_good = power_good
        return True

    def set_voltage(self, voltage, high_threshold, low_threshold):
        if voltage == NOT_AVAILABLE or high_threshold == NOT_AVAILABLE or low_threshold == NOT_AVAILABLE:
            if self.voltage_good is not True:
                self.logger.log_warning('PSU {} voltage or high_threshold or low_threshold become unavailable, '
                                        'voltage={}, high_threshold={}, low_threshold={}'.format(self.psu_index, voltage, high_threshold, low_threshold))
                self.voltage_good = True
            return False

        voltage_good = (low_threshold <= voltage <= high_threshold)
        if voltage_good == self.voltage_good:
            return False

        self.voltage_good = voltage_good
        return True

    def set_temperature(self, temperature, high_threshold):
        if temperature == NOT_AVAILABLE or high_threshold == NOT_AVAILABLE:
            if self.temperature_good is not True:
                self.logger.log_warning('PSU {} temperature or high_threshold become unavailable, '
                                        'temperature={}, high_threshold={}'.format(self.psu_index, temperature, high_threshold))
                self.temperature_good = True
            return False

        temperature_good = (temperature < high_threshold)
        if temperature_good == self.temperature_good:
            return False

        self.temperature_good = temperature_good
        return True
    
    def set_device_match_res(self, device_match_res):
        if device_match_res == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} device match res become unavailable'.format(self.psu_index))
            return False
            
        if device_match_res == self.device_match_res:
            return False

        self.device_match_res = device_match_res
        return True
    
    def set_alarm_err(self, alarm_err):
        if alarm_err == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} alarm become unavailable'.format(self.psu_index))
            return False
            
        if alarm_err == self.alarm_err:
            return False

        self.alarm_err = alarm_err
        return True
    
    def set_pg_signal_err(self, pg_signal_err):
        if pg_signal_err == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} pg signal become unavailable'.format(self.psu_index))
            return False
            
        if pg_signal_err == self.pg_signal_err:
            return False

        self.pg_signal_err = pg_signal_err
        return True
    
    def set_over_volt_input(self, over_volt_input):
        if over_volt_input == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} over volt input become unavailable'.format(self.psu_index))
            return False
            
        if over_volt_input == self.over_volt_input:
            return False

        self.over_volt_input = over_volt_input
        return True
    
    def set_under_volt_input(self, under_volt_input):
        if under_volt_input == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} under volt input become unavailable'.format(self.psu_index))
            return False
        
        if under_volt_input == self.under_volt_input:
            return False

        self.under_volt_input = under_volt_input
        return True
    
    def set_over_curr_input(self, over_curr_input):
        if over_curr_input == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} over curr input become unavailable'.format(self.psu_index))
            return False
        
        if over_curr_input == self.over_curr_input:
            return False

        self.over_curr_input = over_curr_input
        return True
    
    def set_over_volt_output(self, over_volt_output):
        if over_volt_output == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} over volt output become unavailable'.format(self.psu_index))
            return False
        
        if over_volt_output == self.over_volt_output:
            return False

        self.over_volt_output = over_volt_output
        return True
    
    def set_under_volt_output(self, under_volt_output):
        if under_volt_output == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} under volt output become unavailable'.format(self.psu_index))
            return False
        
        if under_volt_output == self.under_volt_output:
            return False

        self.under_volt_output = under_volt_output
        return True
    
    def set_over_curr_output(self, over_curr_output):
        if over_curr_output == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} over curr output become unavailable'.format(self.psu_index))
            return False
        
        if over_curr_output == self.over_curr_output:
            return False

        self.over_curr_output = over_curr_output
        return True
    
    def set_over_temp(self, over_temp):
        if over_temp == NOT_AVAILABLE:
            self.logger.log_warning('PSU {} over temp become unavailable'.format(self.psu_index))
            return False
        
        if over_temp == self.over_temp:
            return False

        self.over_temp = over_temp
        return True

    def is_ok(self):
        return self.presence and self.power_good and self.voltage_good and self.temperature_good


#
# Daemon =======================================================================
#

class Psu_monitor(daemon_base.DaemonBase):
    def __init__(self, log_identifier):
        super(Psu_monitor, self).__init__(log_identifier)

        # Set minimum logging level to INFO
        self.set_min_log_priority_info()

        self.stop_event = threading.Event()
        self.num_psus = 0
        self.psu_status_dict = {}
        self.chassis_tbl = None
        self.fan_tbl = None
        self.psu_tbl = None
        self.psu_chassis_info = None
        self.first_run = True

        global platform_psuutil
        global platform_chassis

        # Load new platform api class
        try:
            import sonic_platform.platform
            platform_chassis = sonic_platform.platform.Platform().get_chassis()
        except Exception as e:
            self.log_warning("Failed to load chassis due to {}".format(repr(e)))

        # Load platform-specific psuutil class
        if platform_chassis is None:
            try:
                platform_psuutil = self.load_platform_util(PLATFORM_SPECIFIC_MODULE_NAME, PLATFORM_SPECIFIC_CLASS_NAME)
            except Exception as e:
                self.log_error("Failed to load psuutil: %s" % (str(e)), True)
                sys.exit(PSUUTIL_LOAD_ERROR)

        # Connect to STATE_DB and create psu/chassis info tables
        state_db = daemon_base.db_connect("STATE_DB")
        self.chassis_tbl = swsscommon.Table(state_db, CHASSIS_INFO_TABLE)
        self.psu_tbl = swsscommon.Table(state_db, PSU_INFO_TABLE)
        self.fan_tbl = swsscommon.Table(state_db, FAN_INFO_TABLE)
        self.phy_entity_tbl = swsscommon.Table(state_db, PHYSICAL_ENTITY_INFO_TABLE)

        # Post psu number info to STATE_DB
        self.num_psus = _wrapper_get_num_psus()
        fvs = swsscommon.FieldValuePairs([(CHASSIS_INFO_PSU_NUM_FIELD, str(self.num_psus))])
        self.chassis_tbl.set(CHASSIS_INFO_KEY, fvs)

    def __del__(self):
        # Delete all the information from DB and then exit
        for psu_index in range(1, self.num_psus + 1):
            self.psu_tbl._del(get_psu_key(psu_index))

        self.chassis_tbl._del(CHASSIS_INFO_KEY)
        self.chassis_tbl._del(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

    # Override signal handler from DaemonBase
    def signal_handler(self, sig, frame):
        FATAL_SIGNALS = [signal.SIGINT, signal.SIGTERM]
        NONFATAL_SIGNALS = [signal.SIGHUP]

        global exit_code

        if sig in FATAL_SIGNALS:
            self.log_info("Caught signal '{}' - exiting...".format(SIGNALS_TO_NAMES_DICT[sig]))
            exit_code = 128 + sig  # Make sure we exit with a non-zero code so that supervisor will try to restart us
            self.stop_event.set()
        elif sig in NONFATAL_SIGNALS:
            self.log_info("Caught signal '{}' - ignoring...".format(SIGNALS_TO_NAMES_DICT[sig]))
        else:
            self.log_warning("Caught unhandled signal '{}' - ignoring...".format(SIGNALS_TO_NAMES_DICT[sig]))

    # Main daemon logic
    def run(self):
        if self.stop_event.wait(PSU_INFO_UPDATE_PERIOD_SECS):
            # We received a fatal signal
            return False

        self._update_psu_entity_info()
        psu_db_update(self.psu_tbl, self.num_psus)
        self.update_psu_data()
        self._update_led_color()

        if platform_chassis and platform_chassis.is_modular_chassis():
            self.update_psu_chassis_info()  # 没进来

        if self.first_run:
            self.first_run = False

        return True

    def update_psu_data(self):
        if not platform_chassis:
            return

        for index, psu in enumerate(platform_chassis.get_all_psus()):
            try:
                self._update_single_psu_data(index + 1, psu)
                #err_code_str_list = psu.err_map_retrieve()  ## added
                #for err_str in err_code_str_list:
                #    print(err_str)
                #    self.log_warning(err_str) 
            except Exception as e:
                self.log_warning("Failed to update PSU data - {}".format(e))

    def _update_single_psu_data(self, index, psu):
        name = get_psu_key(index)
        psu.reset_err_map()  ## added
        presence = _wrapper_get_psu_presence(index)             # step in
        power_good = False
        voltage = NOT_AVAILABLE
        voltage_high_threshold = NOT_AVAILABLE
        voltage_low_threshold = NOT_AVAILABLE
        temperature = NOT_AVAILABLE
        temperature_threshold = NOT_AVAILABLE
        current = NOT_AVAILABLE
        power = NOT_AVAILABLE
        
        fan_speed = NOT_AVAILABLE
        
        device_match_res = NOT_AVAILABLE
        alarm_err = NOT_AVAILABLE
        pg_signal_err = NOT_AVAILABLE
        over_temp_res = NOT_AVAILABLE
        over_volt_input_res = NOT_AVAILABLE
        under_volt_input_res = NOT_AVAILABLE
        over_curr_input_res = NOT_AVAILABLE
        over_volt_output_res = NOT_AVAILABLE
        under_volt_output_res = NOT_AVAILABLE
        over_curr_output_res = NOT_AVAILABLE
        
        is_replaceable = try_get(psu.is_replaceable, False)
        if presence:
            loop = True
            while loop:
                if psu.get_is_first_reg():
                    device_match_res = psu.check_device_match_err()
                    if device_match_res:
                        psu.set_is_first_reg(False)
                    else:
                        break
                
                alarm_err = psu.check_alarm_err()
                if not alarm_err:
                    break
                
                pg_signal_err = psu.check_pg_signal_err()
                if not pg_signal_err:
                    break
                
                retry = 5
                while retry:
                    if not psu.check_ID_register_err():
                        retry -= 1
                        psu.reset_slave_mach()
                    else:
                        break
                        
                if retry == 0 :
                    return False
                loop = False
            
            
            if not loop:
                over_temp_res = psu.check_over_temperature()
                
                over_volt_input_res = psu.check_over_volt_input()
                under_volt_input_res = psu.check_under_volt_input()
                over_curr_input_res = psu.check_over_curr_input()
                over_volt_output_res = psu.check_over_volt_output()
                under_volt_output_res = psu.check_under_volt_output()
                over_curr_output_res = psu.check_over_curr_output()
                
                power_good = _wrapper_get_psu_status(index)          # step in
                voltage = try_get(psu.get_voltage, NOT_AVAILABLE)
                voltage_high_threshold = try_get(psu.get_voltage_high_threshold, NOT_AVAILABLE)
                voltage_low_threshold = try_get(psu.get_voltage_low_threshold, NOT_AVAILABLE)
                temperature = try_get(psu.get_temperature, NOT_AVAILABLE)
                temperature_threshold = try_get(psu.get_temperature_high_threshold, NOT_AVAILABLE)
                current = try_get(psu.get_current, NOT_AVAILABLE)
                power = try_get(psu.get_power, NOT_AVAILABLE)
                
                fan_speed = psu.get_fan_speed()
            

        if index not in self.psu_status_dict:
            self.psu_status_dict[index] = PsuStatus(self, psu, index)

        psu_status = self.psu_status_dict[index]
        set_led = self.first_run
        presence_changed = psu_status.set_presence(presence)
        if presence_changed:
            set_led = True
            log_on_status_changed(self, psu_status.presence,
                                  'PSU absence warning cleared: {} is inserted back.'.format(name),
                                  'PSU absence warning: {} is not present.'.format(name)
                                  )

        if presence_changed or self.first_run:
            # Have to update PSU fan data here because PSU presence status changed. If we don't
            # update PSU fan data here, there might be an inconsistent output between "show platform psustatus"
            # and "show platform fan". For example, say PSU 1 is removed, and psud query PSU status every 3 seconds,
            # it will update PSU state to "Not OK" and PSU LED to "red"; but thermalctld query PSU fan status
            # every 60 seconds, it may still treat PSU state to "OK" and PSU LED to "red".
            self._update_psu_fan_data(psu, index)

        if presence and psu_status.set_power_good(power_good):
            set_led = True
            log_on_status_changed(self, psu_status.power_good,
                                  'Power absence warning cleared: {} power is back to normal.'.format(name),
                                  'Power absence warning: {} is out of power.'.format(name)
                                  )

        if presence and psu_status.set_voltage(voltage, voltage_high_threshold, voltage_low_threshold):
            set_led = True
            log_on_status_changed(self, psu_status.voltage_good,
                                  'PSU voltage warning cleared: {} voltage is back to normal.'.format(name),
                                  'PSU voltage warning: {} voltage out of range, current voltage={}, valid range=[{}, {}].'.format(
                                      name, voltage, voltage_high_threshold, voltage_low_threshold)
                                  )

        if presence and psu_status.set_temperature(temperature, temperature_threshold):
            set_led = True
            log_on_status_changed(self, psu_status.temperature_good,
                                  'PSU temperature warning cleared: {} temperature is back to normal.'.format(name),
                                  'PSU temperature warning: {} temperature too hot, temperature={}, threshold={}.'.format(
                                      name, temperature, temperature_threshold)
                                  )
        
        if presence and psu_status.set_device_match_res(device_match_res):
            set_led = True
            log_on_status_changed(self, psu_status.device_match_res,
                                  'PSU device match warning cleared: {} device match is back to normal.'.format(name),
                                  'PSU device match warning: {} device match err.'.format(name)
                                  )
        
        if presence and psu_status.set_alarm_err(alarm_err):
            set_led = True
            log_on_status_changed(self, psu_status.alarm_err,
                                  'PSU alarm warning cleared: {} alarm is back to normal.'.format(name),
                                  'PSU alarm warning: {} alarm err.'.format(name)
                                  )
        
        if presence and psu_status.set_pg_signal_err(pg_signal_err):
            set_led = True
            log_on_status_changed(self, psu_status.pg_signal_err,
                                  'PSU pg signal warning cleared: {} pg signal is back to normal.'.format(name),
                                  'PSU pg signal warning: {} pg signal err.'.format(name)
                                  )
        
        if presence and psu_status.set_over_temp(over_temp_res):
            set_led = True
            log_on_status_changed(self, psu_status.over_temp,
                                  'PSU temperature warning cleared: {} temperature is back to normal.'.format(name),
                                  'PSU temperature warning: {} temperature too hot.'.format(name)
                                  )
        
        if presence and psu_status.set_over_curr_input(over_curr_input_res):
            set_led = True
            log_on_status_changed(self, psu_status.over_curr_input,
                                  'PSU over current input warning cleared: {} current input is back to normal.'.format(name),
                                  'PSU over current input warning: {} current input is over.'.format(name)
                                  )
        
        if presence and psu_status.set_over_volt_input(over_volt_input_res):
            set_led = True
            log_on_status_changed(self, psu_status.over_volt_input,
                                  'PSU over volt input warning cleared: {} volt input is back to normal.'.format(name),
                                  'PSU over volt input warning: {} volt input is over.'.format(name)
                                  )
        
        if presence and psu_status.set_under_volt_input(under_volt_input_res):
            set_led = True
            log_on_status_changed(self, psu_status.under_volt_input,
                                  'PSU under volt input warning cleared: {} volt input is back to normal.'.format(name),
                                  'PSU under volt input warning: {} volt input is under.'.format(name)
                                  )
        
        if presence and psu_status.set_over_curr_output(over_curr_output_res):
            set_led = True
            log_on_status_changed(self, psu_status.over_curr_output,
                                  'PSU over current output warning cleared: {} current output is back to normal.'.format(name),
                                  'PSU over current output warning: {} current output is over.'.format(name)
                                  )
        
        if presence and psu_status.set_over_volt_output(over_volt_output_res):
            set_led = True
            log_on_status_changed(self, psu_status.over_volt_output,
                                  'PSU over volt output warning cleared: {} volt output is back to normal.'.format(name),
                                  'PSU over volt output warning: {} volt output is over.'.format(name)
                                  )
        
        if presence and psu_status.set_under_volt_output(under_volt_output_res):
            set_led = True
            log_on_status_changed(self, psu_status.under_volt_output,
                                  'PSU under volt output warning cleared: {} volt output is back to normal.'.format(name),
                                  'PSU under volt output warning: {} volt output is under.'.format(name)
                                  )

        if set_led:
            self._set_psu_led(psu, psu_status)

        fvs = swsscommon.FieldValuePairs(
            [(PSU_INFO_MODEL_FIELD, str(try_get(psu.get_model, NOT_AVAILABLE))),
             (PSU_INFO_SERIAL_FIELD, str(try_get(psu.get_serial, NOT_AVAILABLE))),
             (PSU_INFO_REV_FIELD, str(try_get(psu.get_revision, NOT_AVAILABLE))),
             (PSU_INFO_TEMP_FIELD, str(temperature)),
             (PSU_INFO_TEMP_TH_FIELD, str(temperature_threshold)),
             (PSU_INFO_VOLTAGE_FIELD, str(voltage)),
             (PSU_INFO_VOLTAGE_MIN_TH_FIELD, str(voltage_low_threshold)),
             (PSU_INFO_VOLTAGE_MAX_TH_FIELD, str(voltage_high_threshold)),
             (PSU_INFO_CURRENT_FIELD, str(current)),
             (PSU_INFO_POWER_FIELD, str(power)),
             (PSU_INFO_FRU_FIELD, str(is_replaceable)),
             (PSU_INFO_FAN_SPEED_FIELD, str(fan_speed)), ##added
             ])
        self.psu_tbl.set(name, fvs)

    def _update_psu_entity_info(self):
        if not platform_chassis:
            return

        for index, psu in enumerate(platform_chassis.get_all_psus()):
            try:
                self._update_single_psu_entity_info(index + 1, psu)
            except Exception as e:
                self.log_warning("Failed to update PSU data - {}".format(e))

    def _update_single_psu_entity_info(self, psu_index, psu):
        position = try_get(psu.get_position_in_parent, psu_index)
        fvs = swsscommon.FieldValuePairs(
            [('position_in_parent', str(position)),
             ('parent_name', CHASSIS_INFO_KEY),
             ])
        self.phy_entity_tbl.set(get_psu_key(psu_index), fvs)

    def _update_psu_fan_data(self, psu, psu_index):
        """
        :param psu:
        :param psu_index:
        :return:
        """
        psu_name = get_psu_key(psu_index)
        presence = _wrapper_get_psu_presence(psu_index)
        fan_list = psu.get_all_fans()
        for index, fan in enumerate(fan_list):
            fan_name = try_get(fan.get_name, '{} FAN {}'.format(psu_name, index + 1))
            direction = try_get(fan.get_direction, NOT_AVAILABLE) if presence else NOT_AVAILABLE
            speed = try_get(fan.get_speed, NOT_AVAILABLE) if presence else NOT_AVAILABLE
            status = "True" if presence else "False"
            fvs = swsscommon.FieldValuePairs(
                [(FAN_INFO_PRESENCE_FIELD, str(presence)),
                 (FAN_INFO_STATUS_FIELD, status),
                 (FAN_INFO_DIRECTION_FIELD, direction),
                 (FAN_INFO_SPEED_FIELD, str(speed)),
                 (FAN_INFO_TIMESTAMP_FIELD, datetime.now().strftime('%Y%m%d %H:%M:%S'))
                 ])
            self.fan_tbl.set(fan_name, fvs)

    def _set_psu_led(self, psu, psu_status):
        try:
            color = psu.STATUS_LED_COLOR_GREEN if psu_status.is_ok() else psu.STATUS_LED_COLOR_RED
            psu.set_status_led(color)
        except NotImplementedError:
            self.log_warning("set_status_led() not implemented")

    def _update_led_color(self):
        if not platform_chassis:
            return

        for index, psu_status in self.psu_status_dict.items():
            fvs = swsscommon.FieldValuePairs([
                ('led_status', str(try_get(psu_status.psu.get_status_led, NOT_AVAILABLE)))
            ])
            self.psu_tbl.set(get_psu_key(index), fvs)
            self._update_psu_fan_led_status(psu_status.psu, index)

    def _update_psu_fan_led_status(self, psu, psu_index):
        psu_name = get_psu_key(psu_index)
        fan_list = psu.get_all_fans()
        for index, fan in enumerate(fan_list):
            fan_name = try_get(fan.get_name, '{} FAN {}'.format(psu_name, index + 1))
            fvs = swsscommon.FieldValuePairs([
                (FAN_INFO_LED_STATUS_FIELD, str(try_get(fan.get_status_led, NOT_AVAILABLE)))
            ])
            self.fan_tbl.set(fan_name, fvs)

    def update_psu_chassis_info(self):
        if not platform_chassis:
            return

        if not self.psu_chassis_info:
            self.psu_chassis_info = PsuChassisInfo(SYSLOG_IDENTIFIER, platform_chassis)

        self.psu_chassis_info.run_power_budget(self.chassis_tbl)
        self.psu_chassis_info.update_master_status()

        if self.first_run:
            self.first_run = False


#
# Main =========================================================================
#


def main():
    psu_moni = Psu_monitor(SYSLOG_IDENTIFIER)

    psu_moni.log_info("Starting up...")

    while psu_moni.run():
        pass

    psu_moni.log_info("Shutting down...")

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
