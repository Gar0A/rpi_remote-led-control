import os
import asyncio
import threading

from dotenv import load_dotenv
from endpoints import Controller, CallError
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

    async def GET(self):
        """
        Renders the web interface for remote LED control.
        Provides a selection for presets or a custom manual control mode using checkboxes
        """
        # Generate checkbox HTML based on current LED states
        checkboxes_html = ""
        for i, led in enumerate(factory_leds):
            checked = "checked" if led.is_active else ""
            checkboxes_html += f"""
                            <label class="flex items-center space-x-3 p-3 bg-gray-100 rounded-lg cursor-pointer hover:bg-gray-200 transition">
                                <input type="checkbox" class="led-checkbox w-5 h-5" data-index="{i}" {checked}>
                                <span class="text-gray-700 font-medium">LED {i} (Pin {led_pins[i]})</span>
                            </label>
                            """

        return f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Remote LED Control</title>
                <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
              </head>
              <body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
                <main class="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md">
                    <h1 class="text-2xl font-bold text-gray-800 mb-6 text-center">Remote LED Control</h1>
    
                    <div class="mb-6">
                        <label class="block text-sm font-semibold text-gray-600 mb-2">Control Mode</label>
                        <select id="modeSelect" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
                            <option value="custom">Custom (Manual Control)</option>
                            <option value="trailing">Preset: Trailing</option>
                            <option value="blinking">Preset: Blinking</option>
                            <option value="pong">Preset: Pong</option>
                            <option value="pingpong">Preset: Ping-Pong</option>
                            <option value="off">All Off</option>
                        </select>
                    </div>
    
                    <div id="customControls" class="flex flex-col gap-3">
                        <p class="text-sm text-gray-500 mb-2">Manual Toggle:</p>
                        {checkboxes_html}
                    </div>
                </main>
    
                <script>
                    const modeSelect = document.getElementById('modeSelect');
                    const customControls = document.getElementById('customControls');
                    const checkboxes = document.querySelectorAll('.led-checkbox');
    
                    // Utility to make POST requests
                    async function sendCommand(url, data = {{}}) {{
                        const formData = new URLSearchParams();
                        for (const key in data) formData.append(key, data[key]);
    
                        return fetch(url, {{
                            method: 'POST',
                            body: formData
                        }});
                    }}
    
                    // Handle Mode Changes
                    modeSelect.addEventListener('change', async (e) => {{
                        const mode = e.target.value;
    
                        if (mode === 'custom') {{
                            // Stop animations and show checkboxes
                            await sendCommand('/off');
                            customControls.classList.remove('hidden');
                            checkboxes.forEach(cb => cb.checked = false);
                        }} else if (mode === 'off') {{
                            await sendCommand('/off');
                            customControls.classList.add('hidden');
                        }} else {{
                            // Hide checkboxes and start preset
                            customControls.classList.add('hidden');
                            await sendCommand('/on', {{ mode: mode }});
                        }}
                    }});
    
                    // Handle Individual Checkbox Toggles
                    checkboxes.forEach(checkbox => {{
                        checkbox.addEventListener('change', async (e) => {{
                            const index = e.target.dataset.index;
                            await sendCommand('/', {{ index: index }});
                        }});
                    }});
                </script>
              </body>
            </html>
        """

    async def POST(self, **kwargs):
        """
        Toggles an individual LED on/off

        Args:
            **kwargs: Arbitrary keyword arguments.
                ``index`` (str/int) The index of the LED in `factory_leds` to toggle

        Returns:
            str: "OK" if successful

        Raises:
            CallError: 422 if index is missing, not a digit or out of range
        """
        # Handle the logic for toggling via AJAX if an index is provided
        if kwargs.get("index") is not None and kwargs.get("index").isdigit():
            index = int(kwargs.get("index"))
            if 0 <= index < len(factory_leds):
                factory_leds[index].toggle()
            return "OK"
        raise CallError(422, "Missing or invalid LED index")


class Off(Controller):
    """handles /off requests"""

    async def POST(self):
        """
        Stops any active preset animation thread and turns all LEDs off
        """
        # Stops any running preset
        stop_event.set()

        # Turn all LEDs off
        for led in factory_leds:
            led.off()

        return "LEDs off"


class On(Controller):
    """handles /on requests"""

    async def POST(self, **kwargs):
        """
        Turns all LEDs on or starts a background preset animation thread

        Args:
            **kwargs: Arbitrary keyword arguments.
                ``index`` (str): The index of the LED in `factory_leds` to toggle

        Returns:
            str: Success message indicating either LEDs are on or animation started

        Raises:
            CallError: 422 if an invalid mode is provided
        """
        global running_thread
        mode = kwargs.get("mode")

        # Validate the preset mode if one is provided
        valid_modes = ["trailing", "blinking", "pong", "pingpong"]
        if mode and mode not in valid_modes:
            raise CallError(422, f"Invalid preset mode: {mode}")

        # Stop any prior running thread and wait for it to finish
        if running_thread and running_thread.is_alive():
            stop_event.set()
            running_thread.join()

        stop_event.clear()
        if mode is None:
            for led in factory_leds:
                led.on()
            return "LEDs on"
        else:
            # Runs a thread with the selected preset
            running_thread = threading.Thread(
                target=preset_runner,
                args=(stop_event, factory_leds, mode),
                daemon=True  # Ensures the thread dies if the main program exits
            )
            running_thread.start()

        return "LEDs animation started in background thread"


def preset_runner(event, leds, mode):
    """This runs in a separate thread (for the presets), independent of the web server"""
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
