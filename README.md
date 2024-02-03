# arduino-projects
This is a collection of miscellaneous projects that make use of the arduino infrastructure for implementing embedded systems

Projects:

rocket-computer:

    rocket_computer.ino

      Implements a data logging module for model rockets.  Records
      altitude and acceleration.  Formats into packets and transmits via
      RF95 LoRa radio.

    rocket_receiver.ino

      Serves as the interface between the rocket computer and a laptop
      that displays the results.  Plugs into laptop via USB port.
      Receives radio transmissions and writes them to a serial port.

    groundstation.py

      Provides visualization of data received from rocket computer.
      