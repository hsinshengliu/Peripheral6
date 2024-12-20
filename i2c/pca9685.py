#! python3
import logging
import math
import time
import subprocess
import argparse

class MCP2221A:
    def __init__(self, bus: int, addr: int) -> None:
        """Constructor"""
        self.bus = bus
        self.addr = addr
        self.detect()

    def detect(self) -> None:
        ret: CompletedProcess = None
        retval: str = None
        cmd: list = ["i2cdetect", "-y", "%d"%(self.bus), "0x%02x"%(self.addr), "0x%02x"%(self.addr)]
        ret = subprocess.run(cmd, capture_output=True)  # go to sleep
        retval = ret.stdout.decode(encoding="utf-8")
        logging.debug("cmd = %s; retval = %s%s" % (" ".join(cmd), "\n", retval))

    def __del__(self):
        """Destructor"""
        pass

class PCA9685(MCP2221A):
    # Registers/etc:
    ADDRESS: int            = 0x40
    MODE1: int              = 0x00
    MODE2: int              = 0x01
    SUBADR1: int            = 0x02
    SUBADR2: int            = 0x03
    SUBADR3: int            = 0x04
    PRESCALE: int           = 0xFE
    LED0_ON_L: int          = 0x06
    LED0_ON_H: int          = 0x07
    LED0_OFF_L: int         = 0x08
    LED0_OFF_H: int         = 0x09
    ALL_LED_ON_L: int       = 0xFA
    ALL_LED_ON_H: int       = 0xFB
    ALL_LED_OFF_L: int      = 0xFC
    ALL_LED_OFF_H: int      = 0xFD
    # Bits:
    RESTART: int            = 0x80
    SLEEP: int              = 0x10
    ALLCALL: int            = 0x01
    INVRT: int              = 0x10
    OUTDRV: int             = 0x04

    def __init__(self, bus: int = 0, addr: int = ADDRESS) -> None:
        """Constructor"""
        super().__init__(bus, addr)
        self.set_all_pwm(0, 0)
        self.write_reg(PCA9685.MODE2, PCA9685.OUTDRV)
        self.write_reg(PCA9685.MODE1, PCA9685.ALLCALL)
        time.sleep(0.005)  # wait for oscillator
        mode1: int = self.read_reg(PCA9685.MODE1)
        logging.debug("mode1 = 0x%02X" % (mode1))
        mode1 = mode1 & ~PCA9685.SLEEP  # wake up (reset sleep)
        self.write_reg(PCA9685.MODE1, mode1)
        time.sleep(0.005)  # wait for oscillator

    def set_pwm_freq(self, freq_hz: int) -> None:
        """Set the PWM frequency to the provided value in hertz."""
        prescaleval = 25000000.0    # 25MHz
        prescaleval /= 4096.0       # 12-bit
        prescaleval /= float(freq_hz)
        prescaleval -= 1.0
        logging.debug("Setting PWM frequency to {0} Hz".format(freq_hz))
        logging.debug("Estimated pre-scale: {0}".format(prescaleval))
        prescale = int(math.floor(prescaleval + 0.5))
        logging.debug("Final pre-scale: {0}".format(prescale))
        oldmode: int = self.read_reg(PCA9685.MODE1)
        logging.debug("oldmode = 0x%02X" % (oldmode))
        newmode: int = (oldmode & ~PCA9685.RESTART) | PCA9685.SLEEP    # sleep
        self.write_reg(PCA9685.MODE1, newmode)
        self.write_reg(PCA9685.PRESCALE, prescale)
        self.write_reg(PCA9685.MODE1, oldmode)
        time.sleep(0.005)
        self.write_reg(PCA9685.MODE1, oldmode | PCA9685.RESTART)

    def set_pwm(self, channel, on, off) -> None:
        """Sets a single PWM channel."""
        self.write_reg(PCA9685.LED0_ON_L+4*channel, on & 0xFF)
        self.write_reg(PCA9685.LED0_ON_H+4*channel, on >> 8)
        self.write_reg(PCA9685.LED0_OFF_L+4*channel, off & 0xFF)
        self.write_reg(PCA9685.LED0_OFF_H+4*channel, off >> 8)

    def set_all_pwm(self, on, off) -> None:
        """Sets all PWM channels."""
        self.write_reg(PCA9685.ALL_LED_ON_L, on & 0xFF)
        self.write_reg(PCA9685.ALL_LED_ON_H, on >> 8)
        self.write_reg(PCA9685.ALL_LED_OFF_L, off & 0xFF)
        self.write_reg(PCA9685.ALL_LED_OFF_H, off >> 8)

    def software_reset(self) -> None:
        self.write_raw(0x06)

    def write_raw(self, raw: int) -> None:
        ret: CompletedProcess = None
        retval: str = None
        cmd: list = ["i2cset", "-y", "%d"%(self.bus), "0x%02x"%(self.addr), "0x%02x"%(raw)]
        ret = subprocess.run(cmd, capture_output=True)  # go to sleep
        retval = ret.stdout.decode(encoding="utf-8")
        logging.debug("cmd = %s; retval = %s" % (" ".join(cmd), retval))

    def write_reg(self, reg: int, regval: int) -> None:
        ret: CompletedProcess = None
        retval: str = None
        cmd: list = ["i2cset", "-y", "%d"%(self.bus), "0x%02x"%(self.addr), "0x%02x"%(reg), "0x%02x"%(regval)]
        ret = subprocess.run(cmd, capture_output=True)  # go to sleep
        retval = ret.stdout.decode(encoding="utf-8")
        logging.debug("cmd = %s; retval = %s" % (" ".join(cmd), retval))

    def read_reg(self, reg: int) -> int:
        ret: CompletedProcess = None
        retval: str = None
        cmd: list = ["i2cget", "-y", "%d"%(self.bus), "0x%02x"%(self.addr), "0x%02x"%(reg)]
        ret = subprocess.run(cmd, capture_output=True)
        logging.debug("cmd = %s; retval = %s" % (" ".join(cmd), retval))
        regval = int(ret.stdout.decode(encoding="utf-8"), 16)
        return regval

    def __del__(self) -> None:
        """Destructor"""
        pass

if __name__ == "__main__":
    my_parser = argparse.ArgumentParser(description="CLI argument parsing")
    my_parser.add_argument("-v",
        "--verbose",
        action="store_true",
        help="verbosity")
    my_parser.add_argument("-b",
        "--bus",
        metavar="bus",
        default=0,
        type=int,
        help="bus")
    my_parser.add_argument("-m",
        "--mode",
        metavar="mode",
        default="stop",
        choices=["stop", "swing_ch0", "swing_ch1", "swing_all", "forward_all", "backward_all"],
        type=str,
        help="mode of servo")
    args = my_parser.parse_args()
    if(args.verbose == True):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)
    logging.debug("args: " + repr(args))
    
    # Initialize the PCA9685 using the default address (0x40).
    pwm = PCA9685(bus = args.bus)

    # Configure min and max servo pulse lengths
    servo_min = 150  # Min pulse length out of 4096
    servo_max = 600  # Max pulse length out of 4096

    if args.mode == "stop":
        print("trying to reset...")
        pwm.software_reset()
    elif args.mode == "forward_all":
        # Set frequency to 60Hz, good for servos.
        pwm.set_pwm_freq(60)
        pwm.set_all_pwm(0, servo_min)
    elif args.mode == "backward_all":
        # Set frequency to 60Hz, good for servos.
        pwm.set_pwm_freq(60)
        pwm.set_all_pwm(0, servo_max)
    elif args.mode == "swing_all":
        # Set frequency to 60Hz, good for servos.
        pwm.set_pwm_freq(60)
        print("Moving servo on every channel, press Ctrl-C to quit...")
        while True:
            # Move servo on all channels between extremes.
            pwm.set_all_pwm(0, servo_min)
            time.sleep(1)
            pwm.set_all_pwm(0, servo_max)
            time.sleep(1)
    elif args.mode == "swing_ch0" or args.mode == "swing_ch1":
        ch: int = 0
        if args.mode == "swing_ch0":
            ch = 0
        else:
            ch = 1
        # Set frequency to 60Hz, good for servos.
        pwm.set_pwm_freq(60)
        print("Moving servo on channel %d, press Ctrl-C to quit..." % (ch))
        while True:
            # Move servo on channel O between extremes.
            pwm.set_pwm(ch, 0, servo_min)
            time.sleep(1)
            pwm.set_pwm(ch, 0, servo_max)
            time.sleep(1)
    else:
        pass

#Peripheral6 - by Leo Liu

