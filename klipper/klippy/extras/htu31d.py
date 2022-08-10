# HTU31D sensor
#
import logging
from . import bus

HTU31D_I2C_ADDR= 0x40

HTU31D_COMMANDS = {
    'READ_TEMP_HUM':    0x00,
    'CONVERSION':       0x40,
    'READ_SERIAL':      0x0A,
    'HEATER_ON':        0x04,
    'HEATER_OFF':       0x02,
    'RESET':            0x1E
}

class HTU31D:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.i2c = bus.MCU_I2C_from_config(
            config, default_addr=HTU31D_I2C_ADDR, default_speed=100000)
        self.report_time = config.getint('htu31d_report_time',30,minval=5)
        self.deviceId = config.get('sensor_type')
        self.temp = self.min_temp = self.max_temp = self.humidity = 0.
        self.sample_timer = self.reactor.register_timer(self._sample_htu31d)
        self.printer.add_object("htu31d " + self.name, self)
        self.printer.register_event_handler("klippy:connect",
                                            self.handle_connect)

    def handle_connect(self):
        self._init_htu31d()
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def setup_minmax(self, min_temp, max_temp):
        self.min_temp = min_temp
        self.max_temp = max_temp

    def setup_callback(self, cb):
        self._callback = cb

    def get_report_time_delta(self):
        return self.report_time

    def _init_htu31d(self):
        # Device Soft Reset
        self.i2c.i2c_write([HTU31D_COMMANDS['RESET']])
        # Wait 15ms after reset
        self.reactor.pause(self.reactor.monotonic() + .15)

        # Read ChipId
        params = self.i2c.i2c_read([HTU31D_COMMANDS['READ_SERIAL']], 4)
        response = bytearray(params['response'])
        serial = response[0]
        serial <<= 8
        serial |= response[1]
        serial <<= 8
        serial |= response[2]
        serial <<= 8
        serial |= response[3]

        if (serial == 0):
            logging.warn("htu31d: serial is 0")

        logging.info("htu31d initialized")

    def _sample_htu31d(self, eventtime):
        try:
            # send conversion command
            self.i2c.i2c_write([HTU31D_COMMANDS['CONVERSION']])

            # Wait
            self.reactor.pause(self.reactor.monotonic() + .02)

            params = self.i2c.i2c_write([HTU31D_COMMANDS['READ_TEMP_HUM']])
            params = self.i2c.i2c_read([],6)

            thdata = bytearray(params['response'])

            # read temperature
            raw_temp = thdata[0]
            raw_temp <<= 8
            raw_temp |= thdata[1]

            crc = self._checkCRC8(raw_temp)
            if (crc != thdata[2]):
                logging.warn("htu31d: Checksum error on Temperature reading!")
            else:
                temp = raw_temp
                temp /= 65535.0
                temp *= 165
                temp -= 40
                self.temp = temp

                logging.debug("htu31d: Temperature %.2f " % self.temp)

            # Read Humidity
            raw_hum = thdata[3]
            raw_hum <<= 8
            raw_hum |= thdata[4]

            crc = self._checkCRC8(raw_hum)
            if (crc != thdata[5]):
                logging.warn("htu31d: Checksum error on Humidity reading!")

            else:
                humidity = raw_hum
                humidity /= 65535.0
                humidity *= 100
                self.humidity = humidity

                logging.debug("htu31d: Humidity %.2f " % self.humidity)

        except Exception:
            logging.exception("htu31d: Error reading data")
            self.temp = self.humidity = .0
            return self.reactor.NEVER

        if self.temp < self.min_temp or self.temp > self.max_temp:
            self.printer.invoke_shutdown(
                "HTU31D temperature %0.1f outside range of %0.1f:%.01f"
                % (self.temp, self.min_temp, self.max_temp))

        measured_time = self.reactor.monotonic()
        print_time = self.i2c.get_mcu().estimated_print_time(measured_time)
        self._callback(print_time, self.temp)
        return measured_time + self.report_time

    def _checkCRC8(self, value):
        polynom = 0x988000
        msb = 0x800000
        mask = 0xFF8000
        result = value << 8

        while (msb != 0x80):
            if ((result & msb) > 0):
                result = ((result ^ polynom) & mask) | (result & ~mask)

            msb >>= 1
            mask >>= 1
            polynom >>= 1

        return result

    def get_status(self, eventtime):
        return {
            'temperature': round(self.temp, 2),
            'humidity': self.humidity,
        }


def load_config(config):
    # Register sensor
    pheater = config.get_printer().lookup_object("heaters")
    pheater.add_sensor_factory("HTU31D", HTU31D)
