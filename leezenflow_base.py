import argparse
import time
import sys
import os
import threading
import configparser
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))

from rgbmatrix import RGBMatrix, RGBMatrixOptions

from message_interpreter import Interpreter
from simulations import Simulation
from shared_state import SharedState

class LeezenflowBase(object):
    def __init__(self, command_line_args):
        self.args = command_line_args

    def receiver(self, mode, run_event):
        interpreter = Interpreter()

        # Modify incomming messages (e.g. to smooth values)
        if self.args.modifier == 1:
            from message_modifier import ModifierHoerstertor
            modify = ModifierHoerstertor().smooth
        else:
            print("No modifier selected.")
            modify = lambda x: x # Return value unchanged
 
        # Read config.ini
        try:    
            config = configparser.ConfigParser()
            config.read('config.ini')
        except KeyError:
            print("Configuration file or values within missing...")

        # Select SPATEM message receiver 
        if mode == "mqtt":
            from receivers.mqtt import MQTTReceiver
            client = MQTTReceiver(config=config, interpreter=interpreter, modify=modify)
            client.start()
            while run_event.is_set():
                client.loop()
        elif mode == "udp":
            from receivers.udp import UDPReceiver
            SharedState.interpreter = interpreter.interpret_message
            SharedState.modifier = modify
            client = UDPReceiver(config=config)
            client.run()
        else:
            print("No messages will be received. Use tests to simulate messages.")

    def process(self):
        options = RGBMatrixOptions()
        if self.args.led_gpio_mapping != None:
          options.hardware_mapping = self.args.led_gpio_mapping
        options.rows = self.args.led_rows
        options.cols = self.args.led_cols
        options.chain_length = self.args.led_chain
        options.parallel = self.args.led_parallel
        options.row_address_type = self.args.led_row_addr_type
        options.multiplexing = self.args.led_multiplexing
        options.pwm_bits = self.args.led_pwm_bits
        options.brightness = self.args.led_brightness
        options.pwm_lsb_nanoseconds = self.args.led_pwm_lsb_nanoseconds
        options.led_rgb_sequence = self.args.led_rgb_sequence
        options.pixel_mapper_config = self.args.led_pixel_mapper
        options.panel_type = self.args.led_panel_type
        if self.args.led_show_refresh:
          options.show_refresh_rate = 1
        if self.args.led_slowdown_gpio != None:
            options.gpio_slowdown = self.args.led_slowdown_gpio
        if self.args.led_no_hardware_pulse:
          options.disable_hardware_pulsing = True
        self.matrix = RGBMatrix(options = options)

        # Initialize threading
        run_event = threading.Event()
        run_event.set()

        # Thread for animation
        t1 = threading.Thread(target = self.run, args = (None,run_event))

        # Select receiver
        if self.args.receiver == 0:
            pass
        elif self.args.receiver == 1:
            t2 = threading.Thread(target = self.receiver(mode="mqtt"), args = (None,run_event))
        elif self.args.receiver == 2:
            t2 = threading.Thread(target = self.receiver, args = ("udp",run_event))
        else:
            raise Exception("Invalid receiver argument.")

        # Select test mode 
        if self.args.test == -1:
            pass
        elif self.args.test == 0:
            t2 = threading.Thread(target = Simulation.phase_switch_simulation_4_phases, args = (5,run_event))
        elif self.args.test == 1:
            t2 = threading.Thread(target = Simulation.mqtt_log, args = (None,run_event))
        elif self.args.test == 2:
            t2 = threading.Thread(target = Simulation.log_simulation, args = (None,run_event))
        elif self.args.test == 3:
            t2 = threading.Thread(target = Simulation.phase_switch_simulation, args = (5,run_event))
        elif self.args.test == 4:
            t2 = threading.Thread(target = Simulation.phase_switch_simulation, args = (30,run_event))            
        elif self.args.test == 5:
            t2 = threading.Thread(target = Simulation.phase_update_simulation, args = ("red",run_event))
        elif self.args.test == 6:
            t2 = threading.Thread(target = Simulation.phase_fast_simulation, args = ("green",run_event))
        elif self.args.test == 7:
            t2 = threading.Thread(target = Simulation.stale_prediction, args = (None,run_event))
        elif self.args.test == 8:
            t2 = threading.Thread(target = Simulation.log_simulation, args = (None,run_event))
        else:
            raise Exception("Invalid test argument.")

        # Start threads
        print("Press CTRL-C to stop leezenflow")
        t1.start()
        try:
            t2.start()
        except UnboundLocalError:
            print("Cannot run without either test dataset or receiver. Use flag --test 0 to run with test dataset 0.")

        try:
            while True:
                time.sleep(.1)
        except KeyboardInterrupt:
            print("Attempting to close threads...")
            run_event.clear()
            t1.join()
            t2.join()
            print ("Threads successfully closed.")

        return True
