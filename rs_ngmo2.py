# -*- coding: utf-8 -*-

import pyvisa
import numpy as np


class Device:
    def __init__(self, visa_addr='GPIB0::4::INSTR'):
        self._address = str(visa_addr)
        self._visa_driver = pyvisa.ResourceManager()
        self._bus = self._visa_driver.open_resource(self._address)
        self._command = Command(self._bus)
        self._bus.read_termination = '\n'
        self._bus.write_termination = '\n'

        # Device class shortcuts
        self.display = Display(self._bus)
        self.format = Format(self._bus, 'ASC')
        self.cha = Channel(self._bus, 'A')
        self.chb = Channel(self._bus, 'B')
        self.status = Status(self._bus)
        self.relay = RelayControl(self._bus)

    def write(self, command):
        self._bus.write(command)

    def read(self):
        self._bus.read()

    def query(self, command):
        return self._bus.query(command)

    def read_raw(self):
        return self._bus.read_raw()

    def disconnect(self):
        self._bus.close()

    def all_on(self):
        write = ':CONF:A:COMM:OUTP:ONOF ON'
        self._command.write(write)
        write = ':OUT:A ON'
        self._command.write(write)
        write = ':CONF:A:COMM:OUTP:ONOF OFF'
        self._command.write(write)

    def all_off(self):
        write = ':CONF:A:COMM:OUTP:ONOF ON'
        self._command.write(write)
        write = ':OUT:A OFF'
        self._command.write(write)
        write = ':CONF:A:COMM:OUTP:ONOF OFF'
        self._command.write(write)


class Common:
    def __init__(self, bus):
        self._bus = bus
        self._validate = ValidateRegister()
        self._command = Command(self._bus)

    # Clears event registers and errors
    def cls(self):
        write = "*CLS"
        self._command.write(write)

    # Read standard event enable register (no param)
    # Write with param
    def ese(self, reg_value=None):
        query = '*ESE?'
        write = '*ESE'
        return self._command.read_write(
                query, write, self._validate.register_8, reg_value)

    # Read and clear standard event enable register
    def esr(self):
        query = "*ESR?"
        return self._command.read(query)

    # Read instrument identification
    def idn(self):
        query = "*IDN?"
        return self._command.read(query)

    # Set the operation complete bit in the standard event register or queue
    # (param=1) places into output queue when operation complete
    def opc(self, reg_value=None):
        query = '*OPC?'
        write = '*OPC'
        return self._command.read_write(
                query, write, reg_value)

    # Returns the power supply to the saved setup (0...9)
    def rcl(self, preset_value=None):
        query = '*RCL?'
        write = '*RCL'
        return self._command.read_write(
                query, write, self._validate.preset, preset_value)

    # Returns the power supply to the *RST default conditions
    def rst(self):
        write = "*RST"
        self._command.write(write)
        self.cls()

    # Saves the present setup (1..9)
    def sav(self, preset_value=None):
        query = '*SAV?'
        write = '*SAV'
        return self._command.read_write(
                query, write, self._validate.preset, preset_value)

    # Programs the service request enable register
    def sre(self, reg_value=None):
        query = '*SRE?'
        write = '*SRE'
        return self._command.read_write(
                query, write, self._validate.register_8, reg_value)

    # Reads the status byte register
    def stb(self):
        query = "*STB?"
        return self._command.read(query)

    # command to trigger
    def trg(self):
        write = "*TRG"
        self._command.write(write)

    # Waits until all previous commands are executed
    def wait(self):
        write = "*WAI"
        self._command.write(write)

    # Perform self-tests
    def tst(self):
        query = "*TST"
        return self._command.read(query)


class Channel:
    def __init__(self, bus, channel: str):
        self._bus = bus
        self._validate = ValidateChannel()
        self._channel = self._validate.channel(channel)
        if isinstance(self._channel, (ValueError, TypeError)):
            raise self._channel
        self._command = Command(self._bus)
        self.values = {}
        self.values = {
                'output': self.output(),
                'voltage': self.voltage(),
                'current': self.current(),
                'current_range': self.current_range(),
                'measurement_interval': self.measurement_interval(),
                'average_count': self.average_count(),
                'impedance': self.impedance(),
                'output_bandwidth': self.output_bandwidth()}

        # Channel class shortcuts
        self.meas = Measure(self._bus, self._channel)
        self.log = Log(self._bus, self._channel)
        self.trig = Trigger(self._bus, self._channel)
        self.prot = Protection(self._bus, self._channel)

    def output(self, set_input_on_off=None):
        query = ':OUTP:' + self._channel + ':STAT?'
        write = ':OUT:' + self._channel
        return self._command.read_write(
                query, write, self._validate.on_off,
                set_input_on_off, self.values, 'output')

    def on(self):
        self.output('ON')

    def off(self):
        self.output('OFF')

    # resolution: 1mV
    def voltage(self, set_voltage=None):
        query = ':SOUR:' + self._channel + ':VOLT?'
        write = ':SOUR:' + self._channel + ':VOLT'
        return self._command.read_write(
                query, write, self._validate.voltage,
                set_voltage, self.values, 'voltage')

    # Sets current limit in Amps (max. 2.5A on voltages above 5V)
    # resolution: 1mA
    def current(self, set_current=None):
        query = ':SOUR:' + self._channel + ':CURR?'
        write = ':SOUR:' + self._channel + ':CURR:LIM'
        return self._command.read_write(
                query, write, self._validate.current,
                set_current, self.values, 'current')

    # Selects expected current measurement range
    def current_range(self, set_current_range=None):
        query = ':SENS:' + self._channel + ':CURR:RANG?'
        write = ':SENS:' + self._channel + ':CURR:RANG'
        return self._command.read_write(
                query, write, self._validate.current_range,
                set_current_range, self.values, 'current_range')

    # Sets the measurement interval for voltage and current
    def measurement_interval(self, set_measurement_interval=None):
        query = ':SENS:' + self._channel + ':MEAS:INT?'
        write = ':SENS:' + self._channel + ':MEAS:INT'
        return self._command.read_write(
                query, write, self._validate.measurement_interval,
                set_measurement_interval, self.values, 'measurement_interval')

    # Sets the measure average count
    def average_count(self, set_average_count=None):
        query = ':SENS:' + self._channel + ':AVER:COUN?'
        write = ':SENS:' + self._channel + ':AVER:COUN'
        return self._command.read_write(
                query, write, self._validate.average_count,
                set_average_count, self.values, 'average_count')

    def output_bandwidth(self, set_output_bandwidth=None):
        query = ':OUTP:' + self._channel + ':BAND?'
        write = ':OUTP:' + self._channel + ':BAND'
        return self._command.read_write(
                query, write, self._validate.output_bandwidth,
                set_output_bandwidth, self.values, 'output_bandwidth')

    # Specifies the output impedance to apply. 0 Ohms to
    # 1 Ohms in 10 mOhm steps
    def impedance(self, set_impedance=None):
        query = ':OUTP:' + self._channel + ':IMP?'
        write = ':OUTP:' + self._channel + ':IMP'
        return self._command.read_write(
                query, write, self._validate.impedance,
                set_impedance, self.values, 'impedance')


class Display:
    def __init__(self, bus):
        self._bus = bus
        self._validate = ValidateDisplay()
        self._command = Command(self._bus)
        self.values = {}
        self.values = {
                'display_on': self.enable(),
                'display_channel': self.channel()}

    def enable(self, set_enable_on_off=None):
        query = ':DISP:ENAB?'
        write = ':DISP:ENAB'
        return self._command.read_write(
            query, write, self._validate.on_off,
            set_enable_on_off, self.values, 'display_on')

    def on(self):
        self.enable('ON')

    def off(self):
        self.enable('OFF')

    # Changes the active display channel
    def channel(self, set_channel=None):
        query = ':DISP:CHAN?'
        write = ':DISP:CHAN'
        return self._command.read_write(
            query, write, self._validate.channel,
            set_channel, self.values, 'display_channel')


class Format:
    def __init__(self, bus, char_val):
        self._bus = bus
        self._validate = ValidateFormat()
        self._command = Command(self._bus)
        self.values = {}
        self.values = {
                'data_format': self.data(),
                'byte_order': self.border()}
        self.data(char_val)

    # Specifies the output data format for Fetch, Read and Message command.
    def data(self, set_data=None):
        query = ':FORM:DATA?'
        write = ':FORM:DATA'
        return self._command.read_write(
            query, write, self._validate.data,
            set_data, self.values, 'data_format')

    # Specifies byte order for non ASCII output formats.
    def border(self, set_border=None):
        query = ':FORM:BORD?'
        write = ':FORM:BORD'
        return self._command.read_write(
            query, write, self._validate.border,
            set_border, self.values, 'byte_order')


class Log:
    def __init__(self, bus, channel):
        self._bus = bus
        self._validate = ValidateLog()
        self._channel = channel
        self._command = Command(self._bus)
        self.values = {}
        self.values = {
                'sampling_on': self.get_pulse_state(),
                'sample_channel': self.sample_channel(),
                'sample_type': self.sample_type(),
                'sample_interval': self.sample_interval(),
                'sample_length': self.sample_length()}
        self.log_data = {}

        # PulseAnalysis class shortcuts
        self.com = Common(self._bus)
        self.status = Status(self._bus)

    def sample_length(self, set_sample_length=None):
        query = ':SENS:' + self._channel + ':PULS:SAMP:LENG?'
        write = ':SENS:' + self._channel + ':PULS:SAMP:LENG'
        return self._command.read_write(
                query, write, self._validate.sample_length,
                set_sample_length, self.values, 'sample_length')

    def sample_channel(self, set_sample_channel=None):
        query = ':SENS:' + self._channel + ':PULS:MEAS:CHAN?'
        write = ':SENS:' + self._channel + ':PULS:MEAS:CHAN'
        return self._command.read_write(
                query, write, self._validate.sample_channel,
                set_sample_channel, self.values, 'sample_source')

    def sample_type(self, set_sample_type=None):
        query = ':SENS:' + self._channel + ':PULS:MEAS:TYPE?'
        write = ':SENS:' + self._channel + ':PULS:MEAS:TYPE'
        return self._command.read_write(
                query, write, self._validate.sample_type,
                set_sample_type, self.values, 'sample_type')

    def sample_interval(self, set_sample_interval=None):
        query = ':SENS:' + self._channel + ':PULS:SAMP:INT?'
        write = ':SENS:' + self._channel + ':PULS:SAMP:INT'
        return self._command.read_write(
                query, write, self._validate.sample_interval,
                set_sample_interval, self.values, 'sample_interval')

    def get_pulse_state(self):
        query = ':SENS:' + self._channel + ':PULS:MEAS:STAR?'
        return self._command.read(query)

    def start_sample(self):
        self.log_data.clear()
        # Clear the error queue
        self.status.clear_error_queue()
        # Clear measurement event register
        self.status.get_meas_event_reg()
        # Save current measurement enable register
        enable_reg = int(self.status.meas_enable_reg())
        # Enable measurement events:
        # pulse trigger timeout; reading available; measurement overflow
        if self._channel == 'A':
            self.status.meas_enable_reg(56)
            reading_avail = 32
            trigger_timeout = 16
            meas_overflow = 8
            pulse_start = '*AARM'
        else:
            self.status.meas_enable_reg(448)
            reading_avail = 256
            trigger_timeout = 128
            meas_overflow = 64
            pulse_start = '*BARM'
        sre_status_bit = 1

        # Enable service request for measurement bit (MSB)
        self.com.sre(sre_status_bit)

        # Enable pulse measurement
        self.com.wait()
        write = pulse_start
        self._command.write(write)

        # Wait for SRQ
        self._bus.wait_for_srq(10000)
        self.com.sre(0)

        # Get measurement event register
        event_reg = int(self.status.get_meas_event_reg())
        if event_reg & reading_avail:
            data = self._bus.query(':FETC:' + self._channel + ':ARR?')
            if self.values['sample_channel'] in ['CURR', 'CURRENT']:
                self.log_data['current'] = np.array(data.split(';'), dtype='f')
            else:
                self.log_data['voltage'] = np.array(data.split(';'), dtype='f')
            self.log_data['seconds'] = np.arange(
                    0,
                    float(self.values['sample_interval'])
                    * int(self.values['sample_length']),
                    float(self.values['sample_interval']))
        elif event_reg & trigger_timeout:
            print('Trigger timeout channel: ' + self._channel)
        else:
            print('Unknown error, event: ' + str(event_reg))
        if event_reg & meas_overflow:
            print('Warning: measurement range overflow on channel: ' + self._channel)
        # Restore measurement enable register
        self.status.meas_enable_reg(enable_reg)


class Measure:
    def __init__(self, bus, channel):
        self._bus = bus
        self._channel = channel
        self._command = Command(self._bus)
        self._validate = ValidateChannel()
        self.values = {}
        self.values = {'sense': self.sense()}
        # self._sense = Channel.sense

    # Selects Fetch, Read, Measure function type
    def sense(self, set_sense=None):
        query = ':SENS:' + self._channel + ':FUNC?'
        write = ':SENS:' + self._channel + ':FUNC'
        return self._command.read_write(
                query, write, self._validate.sense,
                set_sense, self.values, 'sense')

    def __get_stat(self, meas_source: str, stat_type: str):
        if meas_source not in self.values['sense']:
            self.sense(meas_source)
        query = ':MEAS:' + self._channel + ':' + stat_type + '?'
        return self._command.read(query)

    # ###############################
    # Channel measurement functions #
    # ###############################

    def voltage(self):
        query = ':MEAS:' + self._channel + ':VOLT?'
        return self._command.read(query)

    def current(self):
        query = ':MEAS:' + self._channel + ':CURR?'
        return self._command.read(query)

    def power(self):
        volts = np.single(self.voltage())
        curr = np.single(self.current())
        return str(volts * curr)

    def current_low(self):
        return self.__get_stat('CURR', 'LOW')

    def current_high(self):
        return self.__get_stat('CURR', 'HIGH')

    def current_min(self):
        return self.__get_stat('CURR', 'MIN')

    def current_peak(self):
        return self.__get_stat('CURR', 'PEAK')

    def current_max(self):
        return self.current_peak()

    def current_avg(self):
        return self.__get_stat('CURR', 'AVER')

    def current_rms(self):
        return self.__get_stat('CURR', 'RMS')

    def voltage_low(self):
        return self.__get_stat('VOLT', 'LOW')

    def voltage_high(self):
        return self.__get_stat('VOLT', 'HIGH')

    def voltage_min(self):
        return self.__get_stat('VOLT', 'MIN')

    def voltage_peak(self):
        return self.__get_stat('VOLT', 'PEAK')

    def voltage_max(self):
        return self.voltage_peak()

    def voltage_rms(self):
        return self.__get_stat('VOLT', 'RMS')

    def voltage_dvm(self):
        return self.__get_stat('VOLT', 'DVM')

    def c(self):
        return self.current()

    def clow(self):
        return self.current_low()

    def chigh(self):
        return self.current_high()

    def crms(self):
        return self.current_rms()

    def cpeak(self):
        return self.current_peak()

    def cmax(self):
        return self.current_peak()

    def cmin(self):
        return self.current_min()

    def v(self):
        return self.voltage()

    def vlow(self):
        return self.voltage_low()

    def vhigh(self):
        return self.voltage_high()

    def vrms(self):
        return self.voltage_rms()

    def vpeak(self):
        return self.voltage_peak()

    def vmax(self):
        return self.voltage_peak()

    def vmin(self):
        return self.voltage_min()

    def p(self):
        return self.power()


class RelayControl:
    def __init__(self, bus):
        self._bus = bus

        # RelayControl class shortcuts
        self.r1 = Relay(self._bus, 1)
        self.r2 = Relay(self._bus, 2)
        self.r3 = Relay(self._bus, 3)
        self.r4 = Relay(self._bus, 4)


class Relay:
    def __init__(self, bus, num=1):
        self._bus = bus
        self._command = Command(self._bus)
        self._validate = ValidateRelay()
        num_validated = self._validate.relay_number(num)
        if isinstance(num_validated, (ValueError, TypeError)):
            raise num_validated
        self.values = {}
        self.values['relay'] = num_validated
        self.values['state'] = self.enable()

    def enable(self, set_relay_on_off=None):
        query = ':OUTP:REL' + str(self.values['relay']) + '?'
        write = ':OUTP:REL' + str(self.values['relay'])
        return self._command.read_write(
                query, write, self._validate.on_off,
                set_relay_on_off, self.values, 'state')

    def on(self):
        self.enable('ON')

    def off(self):
        self.enable('OFF')


class Status:
    def __init__(self, bus):
        self._bus = bus
        self._validate = ValidateRegister()
        self._command = Command(self._bus)
        # Status class shortcuts
        self.com = Common(self._bus)

    def get_meas_event_reg(self):
        query = ':STAT:MEAS:EVEN?'
        return self._command.read(query)

    def get_meas_condition_reg(self):
        query = ':STAT:MEAS:COND?'
        return self._command.read(query)

    def meas_enable_reg(self, reg_value=None):
        query = ':STAT:MEAS:ENAB?'
        write = ':STAT:MEAS:ENAB'
        return self._command.read_write(
                query, write, self._validate.register_16, reg_value)

    def get_opr_event_reg(self):
        query = ':STAT:OPER:EVEN?'
        return self._command.read(query)

    def get_opr_condition_reg(self):
        query = ':STAT:OPER:COND?'
        return self._command.read(query)

    def opr_enable_reg(self, reg_value=None):
        query = ':STAT:OPER:ENAB?'
        write = ':STAT:OPER:ENAB'
        return self._command.read_write(
                query, write, self._validate.register_16, reg_value)

    def get_ques_event_reg(self):
        query = ':STAT:QUES:EVEN?'
        return self._command.read(query)

    def get_ques_condition_reg(self):
        query = ':STAT:QUES:COND?'
        return self._command.read(query)

    def ques_enable_reg(self, reg_value=None):
        query = ':STAT:QUES:ENAB?'
        write = ':STAT:QUES:ENAB'
        return self._command.read_write(
                query, write, self._validate.register_16, reg_value)

    def reset_all_status_reg(self):
        write = ':STAT:PRES'
        self._command.write(write)

    def clear_error_queue(self):
        write = ':SYST:CLE'
        self._command.write(write)

    def get_error_queue(self):
        query = ':SYST:ERR?'
        return self._command.read(query)


class Trigger:
    def __init__(self, bus, channel):
        self._bus = bus
        self._validate = ValidateTrigger()
        self._command = Command(self._bus)
        self._channel = channel
        self.values = {}
        self.values = {
                'source': self.source(),
                'level_low': self.level_low(),
                'level_high': self.level_high(),
                'level_dvm': self.level_dvm(),
                'slope': self.slope(),
                'count': self.count(),
                'offset': self.offset(),
                'timeout': self.timeout()}

    # #######################
    # NGMO trigger commands #
    # #######################

    # Sends a “SENSE:PULSE:START ON" command to both channels
    def arm(self):
        write = '*ARM'
        self._command.write(write)

    # Sends a “SENSE:PULSE:START ON" command to channel A
    def aarm(self):
        write = '*AARM'
        self._command.write(write)

    # Sends a “SENSE:PULSE:START ON" command to channel B
    def barm(self):
        write = '*BARM'
        self._command.write(write)

    # command to both channels
    def trg(self):
        write = '*TTRG'
        self._command.write(write)

    # Sends a “SENSE:PULSE:START ON" and a soft trigger
    # command to channel A
    def atrg(self):
        write = '*ATRg'
        self._command.write(write)

    # Sends a “SENSE:PULSE:START ON" and a soft trigger
    # command to channel B
    def btrg(self):
        write = '*BTRg'
        self._command.write(write)

    # ############################
    # Trigger settings functions #
    # ############################

    def source(self, set_source=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:SOUR?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:SOUR'
        return self._command.read_write(
                query, write, self._validate.source,
                set_source, self.values, 'source')

    def level_low(self, set_level_low=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:LEV:LOW?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:LEV:LOW'
        return self._command.read_write(
                query, write, self._validate.level_low,
                set_level_low, self.values, 'level_low')

    def level_high(self, set_level_high=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:LEV:HIGH?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:LEV:HIGH'
        return self._command.read_write(
                query, write, self._validate.level_high,
                set_level_high, self.values, 'level_high')

    def level_dvm(self, set_level_dvm=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:LEV:DVM?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:LEV:DVM'
        return self._command.read_write(
                query, write, self._validate.level_dvm,
                set_level_dvm, self.values, 'level_dvm')

    def count(self, set_count=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:COUN?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:COUN'
        return self._command.read_write(
                query, write, self._validate.count,
                set_count, self.values, 'count')

    def slope(self, set_slope=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:SLOP?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:SLOP'
        return self._command.read_write(
                query, write, self._validate.slope,
                set_slope, self.values, 'slope')

    def offset(self, set_offset=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:OFFS?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:OFFS'
        return self._command.read_write(
                query, write, self._validate.offset,
                set_offset, self.values, 'offset')

    def timeout(self, set_timeout=None):
        query = ':SENS:' + self._channel + ':PULS:TRIG:TIM?'
        write = ':SENS:' + self._channel + ':PULS:TRIG:TIM'
        return self._command.read_write(
                query, write, self._validate.timeout,
                set_timeout, self.values, 'timeout')


# @TODO In progress
class Protection:
    def __init__(self, bus, channel):
        self._bus = bus
        self._channel = channel

    # ###############################
    # Channel protection functions #
    # ###############################

    def open_sense_protect_on(self):
        self._bus.write(':OUTP:' + self._channel + ':OPEN:ON')

    def open_sense_protect_off(self):
        self._bus.write(':OUTP:' + self._channel + ':OPEN:OFF')

    def get_open_sense_protect(self):
        return self._bus.query(':OUTP:' + self._channel + ':OPEN?')
    pass


# @TODO Not implemented
class Config:
    def __init__(self, bus, channel):
        self._bus = bus
        pass


class Validate:
    def float_range(self):
        return lambda x, y: y[0] <= x <= y[1]

    def int_range(self):
        return lambda x, y: x in range(y[0], y[1] + 1)

    def find_element(self):
        return lambda x, y: x in y

    def error_text(self, warning_type, error_type):
        ansi_esc_seq = {'HEADER':    '\033[95m',
                        'OKBLUE':    '\033[94m',
                        'OKGREEN':   '\033[92m',
                        'WARNING':   '\033[93m',
                        'FAIL':      '\033[91m',
                        'ENDC':      '\033[0m',
                        'BOLD':      '\033[1m',
                        'UNDERLINE': '\033[4m'
                        }
        return str(ansi_esc_seq[warning_type] + str(error_type) + ansi_esc_seq['ENDC'])

    def float_rng_and_str_tuples(self, validation_set, value, round_to):
        if isinstance(value, (float, int)):
            val = round(float(value), round_to)
            validator = self.float_range()
            if validator(val, validation_set[0]):
                return str(value)
            else:
                return ValueError('ValueError!\n'
                                  'Not in range:(float, int) {}\n'
                                  'or in set:(str) {}'.format(
                                   validation_set[0],
                                   validation_set[1]))
        elif isinstance(value, str):
            val = value.lower()
            validator = self.find_element()
            if validator(val, str(validation_set[1]).lower()):
                return val.upper()
            else:
                return ValueError('ValueError!\n'
                                  'Not in set:(str) {}\n'
                                  'or in range:(float, int) {}'.format(
                                   validation_set[1],
                                   validation_set[0]))
        else:
            return TypeError('TypeError!\n'
                             'Received type: {}\n'
                             'Valid types: {}, {}, {}'.format(
                              type(value), int, float, str))

    def int_rng_and_str_tuples(self, validation_set, value):
        if isinstance(value, int):
            val = value
            validator = self.int_range()
            if validator(val, validation_set[0]):
                return str(value)
            else:
                return ValueError('ValueError!\n'
                                  'Not in range:(int) {}\n'
                                  'or in set:(str) {}'.format(
                                   validation_set[0],
                                   validation_set[1]))
        elif isinstance(value, str):
            val = value.lower()
            validator = self.find_element()
            if validator(val, str(validation_set[1]).lower()):
                return val.upper()
            else:
                return ValueError('ValueError!\n'
                                  'Not in set:(str) {}\n'
                                  'or in range:(int) {}'.format(
                                   validation_set[1],
                                   validation_set[0]))
        else:
            return TypeError('TypeError!\n'
                             'Received type: {}\n'
                             'Valid types: {}, {}'.format(
                              type(value), int, str))

    def float_and_str_tuples(self, validation_set, value):
        if isinstance(value, (float, int)):
            validator = self.find_element()
            val = float(value)
            if validator(val, validation_set[0]):
                return str(value)
            else:
                return ValueError('ValueError!\n'
                                  'Not in set:(float, int) {}\n'
                                  'or in set:(str) {}'.format(
                                   validation_set[0],
                                   validation_set[1]))
        elif isinstance(value, str):
            val = value.lower()
            validator = self.find_element()
            if validator(val, str(validation_set[1]).lower()):
                return val.upper()
            else:
                return ValueError('ValueError!\n'
                                  'Not in set:(str) {}\n'
                                  'or in set:(float, str) {}'.format(
                                   validation_set[1],
                                   validation_set[0]))
        else:
            return TypeError('TypeError!\n'
                             'Received type: {}\n'
                             'Valid types: {}, {}, {}'.format(
                              type(value), int, float, str))

    def int_and_str_tuples(self, validation_set, value):
        if isinstance(value, int):
            validator = self.find_element()
            val = float(value)
            if validator(val, validation_set[0]):
                return str(value)
            else:
                return ValueError('ValueError!\n'
                                  'Not in set:(int) {}\n'
                                  'or in set:(str) {}'.format(
                                   validation_set[0],
                                   validation_set[1]))
        elif isinstance(value, str):
            val = value.lower()
            validator = self.find_element()
            if validator(val, str(validation_set[1]).lower()):
                return val.upper()
            else:
                return ValueError('ValueError!\n'
                                  'Not in set:(str) {}\n'
                                  'or in set:(int) {}'.format(
                                   validation_set[1],
                                   validation_set[0]))
        else:
            return TypeError('TypeError!\n'
                             'Received type: {}\n'
                             'Valid types: {}, {}'.format(
                              type(value), int, str))

    def str_tuple(self, validation_set, value):
        if isinstance(value, str):
            val = value.lower()
            validator = self.find_element()
            if validator(val, str(validation_set).lower()):
                return val.upper()
            else:
                return ValueError('ValueError!\n'
                                  'Not in set:(str) {}'.format(
                                   validation_set))
        else:
            return TypeError('TypeError!\n'
                             'Received type: {}\n'
                             'Valid types: {}'.format(
                              type(value), str))

    def int_rng_tuple(self, validation_set, value):
        if isinstance(value, int):
            val = value
            validator = self.int_range()
            if validator(val, validation_set):
                return str(val)
            else:
                return ValueError('ValueError!\n'
                                  'Not in range:(int) {}'.format(
                                   validation_set))
        else:
            return TypeError('TypeError!\n'
                             'Received type: {}\n'
                             'Valid types: {}'.format(
                              type(value), int))


class ValidateChannel(Validate):
    def __init__(self):
        super().__init__()

    def on_off(self, value):
        on_off_values = (0, 1), ('ON', 'OFF')
        return self.int_and_str_tuples(on_off_values, value)

    def voltage(self, value):
        voltage_values = (0.0, 15.0), ('min', 'max', 'def', 'default')
        return self.float_rng_and_str_tuples(voltage_values, value, 3)

    def current(self, value):
        current_values = (0.0, 5), ('min', 'max', 'def', 'default')
        return self.float_rng_and_str_tuples(current_values, value, 3)

    def impedance(self, value):
        impedance_values = (0.0, 1.0), ('min', 'max', 'def', 'default')
        return self.float_rng_and_str_tuples(impedance_values, value, 2)

    def sense(self, value):
        sense_values = ('volt', 'voltage', 'curr',
                        'current', 'dvm', 'dvmeter',
                        'aver', 'average', 'peak',
                        'min', 'high', 'low', 'rms'
                        )

        return self.str_tuple(sense_values, value)

    def current_range(self, value):
        current_range_values = (5.0, 0.5, 0.005), ('auto', 'low', 'high',
                                                   'min', 'max', 'def',
                                                   'default', '5a', '0.5a',
                                                   '0.005a'
                                                   )
        return self.float_and_str_tuples(current_range_values, value)

    def measurement_interval(self, value):
        meas_interval_values = (0.002, 0.2), ('max', 'min', 'def', 'default')
        return self.float_rng_and_str_tuples(meas_interval_values, value, 3)

    def average_count(self, value):
        average_count_values = (1, 10), ('min', 'max', 'def', 'default')
        return self.int_rng_and_str_tuples(average_count_values, value)

    def output_bandwidth(self, value):
        output_bandwidth_values = ('high', 'low', 'min',
                                   'max', 'def', 'default'
                                   )
        return self.str_tuple(output_bandwidth_values, value)

    def channel(self, value):
        channel_values = ('a', 'b')
        return self.str_tuple(channel_values, value)


class ValidateDisplay(Validate):
    def __init__(self):
        super().__init__()

    def channel(self, value):
        channel_values = ('a', 'b', 'dvma', 'dvmb', 'min', 'max', 'def', 'default')
        return self.str_tuple(channel_values, value)

    def on_off(self, value):
        on_off_values = (0, 1), ('ON', 'OFF')
        return self.int_and_str_tuples(on_off_values, value)


class ValidateFormat(Validate):
    def __init__(self):
        super().__init__()

    def data(self, value):
        data_values = ('ascii', 'asc', 'long',
                       'sre', 'sreal', 'dreal',
                       'dre', 'min', 'max', 'def'
                       )
        return self.str_tuple(data_values, value)

    def border(self, value):
        border_values = ('normal', 'norm', 'swapped',
                         'swap', 'min', 'max',
                         'def', 'default'
                         )
        return self.str_tuple(border_values, value)


class ValidateLog(Validate):
    def __init__(self):
        super().__init__()

    def sample_length(self, value):
        sample_length_values = (1, 5000), ('min', 'max',
                                           'def', 'default'
                                           )
        return self.int_rng_and_str_tuples(sample_length_values, value)

    def sample_channel(self, value):
        sample_channel_values = ('current', 'curr', 'dvm',
                                 'min', 'max', 'def', 'default'
                                 )
        return self.str_tuple(sample_channel_values, value)

    def sample_type(self, value):
        sample_type_values = ('aver', 'average', 'peak',
                              'min', 'high', 'low', 'rms'
                              )
        return self.str_tuple(sample_type_values, value)

    def sample_interval(self, value):
        sample_interval_values = (0.00001, 1.0), ('min', 'max', 'def', 'default')
        return self.float_rng_and_str_tuples(sample_interval_values, value, 5)


class ValidateRegister(Validate):
    def __init__(self):
        super().__init__()

    def register_8(self, value):
        register_values = (0, 128)
        return self.int_rng_tuple(register_values, value)

    def register_16(self, value):
        register_values = (0, 65535)
        return self.int_rng_tuple(register_values, value)

    def preset(self, value):
        preset_values = (0, 9)
        return self.int_rng_tuple(preset_values, value)


class ValidateRelay(Validate):
    def __init__(self):
        super().__init__()

    def relay_number(self, value):
        relay_number_values = (1, 4)
        return self.int_rng_tuple(relay_number_values, value)

    def on_off(self, value):
        on_off_values = (0, 1), ('ON', 'OFF')
        return self.int_and_str_tuples(on_off_values, value)


class ValidateTrigger(Validate):
    def __init__(self):
        super().__init__()

    def source (self, value):
        source_values = ('int', 'ext', 'min',
                         'max', 'def', 'default'
                         )
        return self.str_tuple(source_values, value)

    def level_low(self, value):
        level_low_values = (0, 0.5), ('auto', 'min', 'max',
                                      'def', 'default'
                                      )
        return self.float_rng_and_str_tuples(level_low_values, value, 3)

    def level_high(self, value):
        level_high_values = (0, 7.0), ('auto', 'min', 'max',
                                       'def', 'default'
                                       )
        return self.float_rng_and_str_tuples(level_high_values, value, 3)

    def level_dvm(self, value):
        level_dvm_values = (-5.999, 25.0), ('auto', 'min', 'max',
                                            'def', 'default'
                                            )
        return self.float_rng_and_str_tuples(level_dvm_values, value, 3)

    def count(self, value):
        count_values = (1, 100), ('min', 'max', 'def', 'default')
        return self.int_rng_and_str_tuples(count_values, value)

    def slope(self, value):
        slope_values = ('pos', 'neg', 'min',
                        'max', 'def', 'default'
                        )
        return self.str_tuple(slope_values, value)

    def offset(self, value):
        offset_values = (-5000, 50000), ('min', 'max', 'def', 'default')
        return self.int_rng_and_str_tuples(offset_values, value)

    def timeout(self, value):
        timeout_values = (0.001, 60), ('inf', 'min', 'max',
                                       'def', 'default')
        return self.float_rng_and_str_tuples(timeout_values, value, 3)


class Command(Validate):
    def __init__(self, bus):
        super().__init__()
        self._bus = bus

    def read_write_old(self, query: str, write: str,
                  validator=None, value=None,
                   value_set=None, value_key=None):
        if value is None:
            qvalue = self._bus.query(query)

        else:
            if validator is not None:
                val = validator
                if isinstance(val, (ValueError, TypeError)):
                    print(self.error_text('WARNING', val))
                else:
                    self._bus.write(write)
                    if value_set is not None:
                        value_set[value_key] = self._bus.query(query)
                    return None

            else:
                self._bus.write(write)
                if value_set is not None:
                    value_set[value_key] = self._bus.query(query)
                return None

    def read_write(self, query: str, write: str,
                   validator=None, value=None,
                   value_dict=None, value_key=None):
        if value is None:
            return self._bus.query(query)
        else:
            if validator is not None:
                val = validator(value)
                if isinstance(val, (ValueError, TypeError)):
                    print(self.error_text('WARNING', val))
                else:
                    write = write + ' ' + str(value)
                    self._bus.write(write)
                    if value_dict is not None:
                        value_dict[value_key] = self._bus.query(query)
                    return None

            else:
                write = write + ' ' + str(value)
                self._bus.write(write)
                if value_dict is not None:
                    value_dict[value_key] = self._bus.query(query)
                return None

    def read(self, query: str):
        return self._bus.query(query)

    def write(self, write: str, validator=None):
        if validator is None:
            self._bus.write(write)
        else:
            val = validator
            if isinstance(val, (ValueError, TypeError)):
                print(self.error_text('WARNING', val))
            else:
                self._bus.write(write)