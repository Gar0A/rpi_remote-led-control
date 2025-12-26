import os
import asyncio
import threading

from dotenv import load_dotenv
from endpoints import Controller
from gpiozero import LED
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

load_dotenv()

# Event used to manage the preset thread
stop_event = asyncio.Event()
running_thread = None

# Makes the connection to the pigpio of the remote raspberry pi
factory = PiGPIOFactory(os.getenv("PIGPIO_ADDR"), os.getenv("PIGPIO_PORT"))

# List of all LEDs pins (BCM pinout)
led_pins = [4, 17, 27, 22, 5, 6, 13, 19, 26, 21]

# Instantiation of all LEDs
factory_leds = []
for led in led_pins:
    led = LED(led, pin_factory=factory)
    led.off()
    factory_leds.append(led)


class Default(Controller):
    """`Default` handles / requests"""

    async def GET(self, **params):
        """
        Turns an individual LED on/off \n
        The parameter `index` must be passed \n
        example : \n
        ``url/?index=1`` (turns on/off the LED with index 1 in ``factory_leds``)
        """
        if params.get("index") is None or not params.get("index").isdigit():
            return "No index provided"

        index = int(params.get("index"))

        if 0 > index >= len(factory_leds):
            return "No LED found"

        selectedled = factory_leds[int(params.get("index"))]
        selectedled.toggle()

        return "LED on" if selectedled.value else "LED off"


class Off(Controller):
    """handles /off requests"""

    async def GET(self):
        """
        Turns all the LEDs off
        """
        # Stops any running preset
        stop_event.set()

        # Turn all LEDs off
        for led in factory_leds:
            led.off()

        return "LEDs off"


class On(Controller):
    """handles /on requests"""

    async def GET(self, **params):
        """
        Turns all the LEDs on
        """
        global running_thread

        # Stop any prior running thread and wait for it to finish
        if running_thread and running_thread.is_alive():
            stop_event.set()
            running_thread.join()

        stop_event.clear()
        if params.get("mode") is None:
            for led in factory_leds:
                led.on()
            return "LEDs on"
        else:
            # Runs a thread with the selected preset
            running_thread = threading.Thread(
                target=preset_runner,
                args=(stop_event, factory_leds, params["mode"]),
                daemon=True  # Ensures the thread dies if the main program exits
            )
            running_thread.start()

        return "LEDs animation started in background thread"


def preset_runner(event, leds, mode):
    """This runs in a separate thread, independent of the web server"""
    print("Thread started")
    try:
        # Turn all LEDs off
        for led in leds:
            led.off()

        if mode == "trailing":

            while not event.is_set():
                for led in leds:
                    if event.is_set():
                        break
                    led.toggle()
                    sleep(0.5)

        elif mode == "blinking":

            while not event.is_set():
                for led in leds:
                    if event.is_set():
                        break
                    led.toggle()

        elif mode == "pong":
            # Setup for mode
            index = 0
            back = False
            leds[index].on()

            while not event.is_set():
                sleep(0.5)
                # Checks if it needs to change direction (next index is out of range)
                if not back and index + 1 >= len(leds):
                    back = True
                elif back and index - 1 < 0:
                    back = False

                # Turns off the last LED and turns on the next one (depending on the direction: +/-)
                leds[index].off()

                if not back:
                    index += 1
                else:
                    index -= 1

                leds[index].on()

        elif mode == "pingpong":
            # Setup for mode
            index = 0
            index2 = len(leds) - 1
            back = False
            leds[index].on()
            leds[index2].on()

            while not event.is_set():
                sleep(0.5)
                # Checks if it needs to change direction (index is out of range or is at the middle of the list)
                if not back and index + 1 >= len(leds) / 2:
                    back = True
                elif back and index - 1 < 0:
                    back = False

                # Turns off the last LED on the right and on the left and turns on the next one (depending on the direction: +/-)
                leds[index].off()
                leds[index2].off()

                if not back:
                    index += 1
                    index2 -= 1
                else:
                    index -= 1
                    index2 += 1

                leds[index].on()
                leds[index2].on()


    finally:
        # Turn all LEDs off
        for led in leds:
            led.off()
        print("Cleaning up and exiting thread")
