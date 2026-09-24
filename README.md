# Brushograph PCB

This repository contains the KiCad PCB design files for the Brushograph (miniPenzlograf) project, a pen-plotting device designed for creating artistic drawings and patterns.

**A manufacturing-ready PCB-design to run FluidNC on ESP32 including ULN2003 drivers for 3 uni-polar stepper motors (28byj-48)**

![Brushograph PCB](photos/PCB_white.jpg)

**A DIY etchable PCB-design to run FluidNC on ESP32 including ULN2003 drivers for 3 uni-polar stepper motors (28byj-48)**

![Brushograph PCB](photos/Brushograph_PCB_01.jpg)

## About Brushograph

This PCB repository is part of the larger Brushograph project, which explores "Ways of painting with a mechatronic brush" - an intersection between classical artistic techniques and modern technology.

**Main Documentation:**
- [Brushograph Wiki](https://wiki.sgmk-ssam.ch/wiki/Brushograph) - Complete project documentation

## Project Structure

- `Brusograf_PCB/` - Original KiCad project (DIY etchable, single layer)
  - `MASK/` - Mask files in SVG and PDF for PCB silkscreen
- `Brushograf_PCB-china/` - Rev A: manufacturing-ready project and Gerbers
  - `Gerber_Brusograf_black.zip` - Zipped Gerbers ready to upload to a PCB manufacturer
- `Brushograf_PCB-revB/` - Rev B: work in progress (see "Rev B" below)
- `FluidNC_config/` - Configuration for FluidNC firmware
  - `config_pink.yaml` - Rev A config
  - `config_revB.yaml` - Rev B config, adds the pendant UART
- `photos/` - Project photos and documentation images

## Rev B (in progress)

`Brushograf_PCB-revB/` is a revision that replaces the power section with a
USB-C Power Delivery supply feeding an adjustable motor rail, and adds a pendant
port and an ESP power switch.

**Schematic: complete and verified.** **PCB layout: partially done** - see Status below.

### What rev B adds

**USB-C Power Delivery input.** A USB-C receptacle (J12) with a CH224K sink
controller (U6) requests **9V** from the charger - set by the single 6.8k
resistor R24 on CFG1, per the CH224K datasheet. A "PD OK" LED (D17) off the
controller's power-good output shows when the contract is up. PD offers no 7.5V
fixed profile, so the 9V rail feeds two buck converters instead.

**Adjustable motor rail.** U7 (TPS54202, 2A) steps 9V down to the motor rail,
adjustable with trimmer RV1 over roughly **5.4 - 8.6V**, nominally 7.5V. The
divider is 100k on top and 7.5k plus the 10k trimmer below, against the
TPS54202's 0.596V reference. The trimmer's wiper is tied to its top end, so a
lifted wiper raises the bottom resistance and drops the output rather than
raising it.

> Running 5V-rated 28BYJ-48 motors at 7.5V is a deliberate overclock: about
> 300mA per motor with two phases energised, roughly 900mA for three. More
> torque and speed, but the motors will run noticeably warm. Set the trimmer to
> 5V first and work up.

**Separate 5V logic rail.** U8 (TPS54202) makes 5.07V for the ESP32. The DevKitC
cannot be fed 7.5V on its 5V pin - its onboard AMS1117 would dissipate about a
watt - so logic and motors get separate rails.

**ESP power switch.** SW1 cuts the board's 5V feed to the ESP32, so the module
can be powered and flashed from USB while the rest of the board stays up.
D14 (SS14) blocks USB 5V from back-feeding the logic buck.

**RJ-12 pendant port.** J13 brings UART1 (GPIO 2 = TX, GPIO 15 = RX) and
switched 5V out to a FluidDial pendant, with a 0.5A resettable fuse (F2), 330R
series resistors and TVS clamps, mirroring the protection on bdring's official
pendant module.

**Barrel-jack input protection.** The original jack is kept as an alternative
DC input: F1 (1.5A polyfuse), Q1 (AO3401A P-FET reverse-polarity protection)
with a 10V zener gate clamp, and C7. It is Schottky-OR'd with USB-C VBUS
(D15/D16) onto the shared `VSUP` rail, so either source can power the board and
neither back-feeds the other.

**J7 repurposed.** J7 pin 3 used to carry the raw barrel-jack rail straight to
the motors - with a 12V adapter that would destroy them. It now carries the
regulated adjustable rail (`MOTOR_V`); pin 1 is the 5V logic rail for testing,
pin 2 is the motor rail.

### Status

| Area | State |
|---|---|
| Schematic | Complete. ERC clean relative to rev A; netlist verified net-by-net |
| Barrel-jack protection | Placed on the PCB, DRC clean |
| USB-C / PD / bucks / pendant | **Schematic only** - not yet placed on the PCB |
| Board outline | Still 198 x 48mm; **must grow** to fit the new power section |
| Routing | 8 ratsnest connections outstanding |

The new power section needs roughly **1100mm2**, and a USB-C receptacle has to
sit on a board edge. The largest contiguous pocket that is free on both layers
is about **12 x 35mm**, and it sits under the Coconuts logo at the right-hand
end; the remaining free copper is fragmented and mostly back-side only. So the
board has to grow before the power section can be laid out.

Zones must be refilled in pcbnew after opening the PCB - the command-line DRC
does not refill them, which is why it reports zone-clearance violations.

### Open questions

- **The RJ-12 pin order is unverified.** The board uses
  `1 = GND, 2 = +5V, 3 = TX, 4 = RX, 5 = +5V, 6 = GND`, chosen so that a
  standard reversing modular cable keeps power and ground on the right contacts
  and swaps TX/RX. bdring's official FluidDial pinout could not be confirmed
  from public documentation - **check it against your cable before building**.
- GPIO2 is an ESP32 strapping pin. It must not be pulled high during boot or the
  chip enters download mode. An idle-high UART receiver at the pendant end is
  fine; anything that actively drives the line is not.

### Known issues carried over from rev A

- The `MISO` and `MOSI` net names are swapped relative to the SD card: net
  `MISO` (GPIO19) goes to the card's CMD/DI pin, which is physically MOSI. The
  card works, and the FluidNC config is correct, but **J6's back silkscreen is
  mislabelled** - an external SD module wired to J6 per the silk will have DI
  and DO reversed.
- R1-R12 and C1-C3 still have no values in the schematic, so the BOM is not
  directly orderable.
- The four mounting holes are plated pads with zero annular ring and should be
  non-plated.

## Features

- Custom PCB design for the Brushograph device
- ESP32-based control board with FluidNC firmware support
- Integrated ULN2003 drivers for 3 uni-polar stepper motors (28byj-48)
- DIY etchable single-layer design for easy home fabrication
- Rounded PCB version available
- Configuration files for FluidNC firmware (custom fork for support uni-polar steppers)

## Hardware Configuration

### ESP32 Pin Configuration

Phase order below matches `FluidNC_config/config_revB.yaml`. Note it is the
reverse of what older revisions of this README listed - reversing the phase
order simply reverses the direction of travel.

#### X-Axis Motor (Unipolar)
- Phase 0: GPIO 27
- Phase 1: GPIO 14
- Phase 2: GPIO 13
- Phase 3: GPIO 4

#### Y-Axis Motor (Unipolar)
- Phase 0: GPIO 22
- Phase 1: GPIO 21
- Phase 2: GPIO 17
- Phase 3: GPIO 16

#### Z-Axis Motor (Unipolar)
- Phase 0: GPIO 32
- Phase 1: GPIO 33
- Phase 2: GPIO 25
- Phase 3: GPIO 26

#### SD Card (SPI)
- MOSI: GPIO 19  (net labelled `MISO` on the schematic - see Known issues)
- MISO: GPIO 23  (net labelled `MOSI` on the schematic - see Known issues)
- SCK: GPIO 18
- CS: GPIO 5

#### Pendant UART (rev B)
- TX: GPIO 2 (J13)
- RX: GPIO 15 (J13)

#### Still free
GPIO 34, 35, 36 and 39 (all input-only), GPIO 12, and UART0 on GPIO 1/3.

The four input-only pins are the natural place for limit switches if homing is
added later; they have no internal pull-ups, so each would need an external one.

### Motor Configuration

`config_revB.yaml` in the FluidNC_config directory carries the settings for the
stepper motors. There are no limit switches, so no homing cycles are defined and
every limit pin is `NO_PIN`:

- X/Y axis: 93 steps/mm, 1500 mm/min max rate, 80 mm/s2 acceleration
- Z axis: 108 steps/mm, 1000 mm/min max rate, 40 mm/s2 acceleration

### 28BYJ-48 Stepper Motors

The PCB is designed specifically for the commonly available and inexpensive 28BYJ-48 unipolar stepper motors:
- 5V DC operation
- Gear reduction ratio of 1:64
- Step angle of 5.625° (64 steps per revolution)
- 4-phase operation via ULN2003 driver

## Getting Started

To view or modify the PCB design:
1. Install KiCad (version 6.0 or later recommended)
2. Open the `.kicad_pro` project file in the `Brusograf_PCB` directory
     - For the latest manufacturing-ready version, you can also open the project in `Brushograf_PCB-china/`

For complete setup instructions, including firmware and mechanical assembly, please refer to the [Brushograph Wiki](https://wiki.sgmk-ssam.ch/wiki/Brushograph).

## Manufacturing-ready files

- Latest Gerbers (ZIP, ready for fab): [`Brushograf_PCB-china/Gerber_Brusograf_black.zip`](Brushograf_PCB-china/Gerber_Brusograf_black.zip)
- Gerber folder (all layers and drill files): [`Brushograf_PCB-china/Gerber_Brusograf/`](Brushograf_PCB-china/Gerber_Brusograf/)

## Related Repositories

- [FluidNC for unipolar steppers](https://git.kompot.si/g1smo/FluidNC) - Forked and reworked version of FluidNC to support uni-polar steppers

## License

[Specify license here]

## Credits

Designed by dusjagr

The Brushograph project is based on Dominik Mahnič's "Brušografia" concept, bridging traditional painting and technology.

## Contact

[Your contact information here]
