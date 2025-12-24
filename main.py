import os

from dotenv import load_dotenv
from endpoints import Controller
from gpiozero import LED
from gpiozero.pins.pigpio import PiGPIOFactory

load_dotenv()

# Makes the connection to the pigpio of the remote raspberry pi
factory = PiGPIOFactory(os.getenv("PIGPIO_ADDR"), os.getenv("PIGPIO_PORT"))

# List of all LEDs pins (BCM pinout)
leds = [4, 17, 27, 22, 5, 6, 13, 19, 26, 21]

# Instantiation of all LEDs
factory_leds = []
for led in leds:
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

        if 0 > index >= len(leds):
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
        list(map(lambda x: x.off(), factory_leds))
        return "LEDs off"

class On(Controller):
    """handles /on requests"""

    async def GET(self):
        """
        Turns all the LEDs on
        """
        list(map(lambda x: x.on(), factory_leds))
        return "LEDs on"