# Remote LED Control
## Goal
The purpose of this project is to learn more about the use of **GPIO** on a Raspberry Pi.

## Milestones
1. Basic implementation
   1. Turn an LED on and off remotely
   2. Control it via an endpoint on the local machine
2. Implementation of multiple LEDs
   1. Turn multiple LEDs on and off individually
   2. Use a single endpoint for control
3. Customization
   1. Include simple presets (flowing, blinking, etc.)
   2. Create a simple web interface

## How to run
1. Copy the .env.example and fill it with your environment variables
2. After cloning the repository, run `python -m venv .venv` and `pip install -r requirements.txt` to set up the environment
3. The web server used to toggle the LED is ready to serve : `endpoints --prefix=main --host=localhost:8000`
4. You can now access the web interface at `localhost:8000`  or make a POST request to `localhost:8000` to control the LEDs
   1. Toggle a single LED : `/` with the argument `index` (in the body of the request) with the index of the LED (ex : `curl -X POST -d "index=0" http://localhost:8000/`)
   2. Turn all LEDs off : `/off` (ex : `curl -X POST http://localhost:8000/off`)
   3. Turn all LEDs on : `/on` (ex : `curl -X POST http://localhost:8000/on`)
      1. You can pass the argument `mode` (in the body of the request) with one of the following : `trailing`, `blinking`, `pong` or `pingpong` (ex : `curl -X POST -d "mode=blinking" http://localhost:8000/on`)