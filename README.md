# Klipper Config for kiauh

Clone the kiauh repository and install Klipper, Moonraker, Fluidd, and mjpg\_streamer.

For direct printing from Cura, install the [Cura2MoonrakerPlugin](https://github.com/emtrax-ltd/Cura2MoonrakerPlugin).

Configuration created for Creality CR-10 V2 with a Phaetus Dragon hotend.

Issues when compiling input\_raspicam.so can be found [here](https://github.com/jacksonliam/mjpg-streamer/issues/259).

To setup a pi cam, run the following commands prior to installing mjpg-streamer:
```
sudo ln -s /usr /opt/vc
sudo apt install libraspberrypi-dev
```

After installing mjpg-streamer, modify the startup script in `/usr/local/bin/webcamd` line 219 with the following:
`if [[ "``vcgencmd get_camera``" == *"supported=1 detected=1"* ]]; then`

Be sure to set up the Raspberry Pi as an MCU to enable I2C. The instructions can be found [here](https://www.klipper3d.org/RPi_microcontroller.html?h=gpio).
