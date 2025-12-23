import os

from dotenv import load_dotenv
from endpoints import Controller
from gpiozero import LED
from gpiozero.pins.pigpio import PiGPIOFactory

load_dotenv()

# Makes the connection to the pigpio of the remote raspberry pi
factory = PiGPIOFactory(os.getenv("PIGPIO_ADDR"), os.getenv("PIGPIO_PORT"))

# Uses BCM pinout
led = LED(26, pin_factory=factory)


class Default(Controller):
    """`Default` handles / requests"""
    async def GET(self):
        led.toggle()
        return "LED on" if led.value else "LED off"