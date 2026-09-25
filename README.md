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

`Brushograf_PCB-revB/` replaces the power section with a USB-C Power Delivery
supply feeding an adjustable motor rail, and adds a pendant port and an ESP
power switch.

**Schematic: complete and verified. PCB: all parts placed, routing still to do.**

The board grows from **198 x 48mm to 198 x 73mm** - 25mm added along the top
edge. Everything from rev A keeps its coordinates; all the new parts live in
the new strip. The RJ-12 needs about 19mm of depth behind the top edge and the
old board only had 11mm before the back-side SPI tracks, which is what forced
the growth.

### What rev B adds

**USB-C Power Delivery is now the only power inlet.** The barrel jack is gone,
along with its reverse-polarity FET and zener. J12 sits on the **left edge**
with the receptacle overhanging it; a CH224K sink controller (U6) requests
**9V**, set by the single 6.8k resistor R24 on CFG1 per the WCH datasheet. A
"PD OK" LED (D17) on the controller's power-good output shows when the contract
is up. VBUS reaches the converters through a 1.5A resettable fuse (F1).

PD offers no 7.5V fixed profile, so the 9V rail feeds two buck converters.

**Adjustable motor rail.** U7 (TPS54202, 2A) steps 9V down to the motor rail,
adjustable with trimmer RV1 over roughly **5.4 - 8.6V**, nominally 7.5V. The
divider is 100k on top and 7.5k plus the 10k trimmer below, against the
TPS54202's 0.596V reference. The wiper is tied to the top of the track, so a
lifted wiper drops the output rather than raising it.

> Running 5V-rated 28BYJ-48 motors at 7.5V is a deliberate overclock: about
> 300mA per motor with two phases energised, roughly 900mA for three. More
> torque and speed, but the motors will run noticeably warm. Set the trimmer to
> 5V first and work up.

**Separate 5V logic rail.** U8 (TPS54202) makes 5.07V for the ESP32. The DevKitC
cannot be fed 7.5V on its 5V pin - its onboard AMS1117 would burn about a watt -
so logic and motors get separate rails.

**ESP power switch.** SW1 is a panel **lever switch on the left edge**, actuator
overhanging the board. It is a 1P2T part used as a simple break: common to the
ESP32, one throw to the board's 5V, the other left open, so the far position
leaves the module running on its own USB supply while the rest of the board
stays powered. D14 (SS14) blocks USB 5V from back-feeding the logic buck.

**RJ-12 pendant port** on the **upper edge**, opening facing off the board. J13
brings UART1 out on GPIO 2 and 15 with switched 5V, behind a 0.5A resettable
fuse (F2), 330R series resistors and TVS clamps.

**J7 repurposed.** Pin 3 used to carry the raw barrel-jack rail straight to the
motors, which would have destroyed them with a 12V adapter. It now carries the
regulated adjustable rail; pin 1 is the 5V logic rail for testing, pin 2 the
motor rail.

### Status

| Area | State |
|---|---|
| Schematic | Complete. 75 parts, 120 nets, netlist verified net by net |
| ERC | At or below rev A in every category |
| Placement | All 36 new footprints placed, zones refilled |
| DRC | No new errors except on J12 - see below |
| Routing | **53 ratsnest connections outstanding** |

### Known DRC findings

- **J12 reports 27 `shorting_items` and 4 `hole_clearance` errors.** These are
  not caused by the placement: the same 31 errors appear with the untouched
  stock footprint alone on an otherwise empty board. The pads have genuine
  0.2-0.7mm gaps and nothing bridges them - zones, solder mask and neighbouring
  copper were each ruled out by experiment. Every USB-C footprint in the KiCad
  library has sub-0.25mm pad gaps, so swapping parts will not help. Worth
  opening in the GUI, where the marker shows interactively what it thinks is
  touching, before committing to fab.
- `allow_soldermask_bridges` is set on J12, which is the correct treatment for a
  fine-pitch connector and clears 23 mask-bridge errors.
- Everything else - 4 mounting-hole annular widths, U4's malformed courtyard,
  5 starved thermals - is inherited unchanged from rev A.

### Open questions

- **The RJ-12 pin order is unverified.** The board uses
  `1 = GND, 2 = +5V, 3 = TX, 4 = RX, 5 = +5V, 6 = GND`, chosen so a standard
  reversing modular cable keeps power and ground on the right contacts and swaps
  TX/RX. bdring's official FluidDial pinout could not be confirmed from public
  documentation - **check it against your cable before building**.
- GPIO2 is an ESP32 strapping pin. It must not be pulled high during boot or the
  chip enters download mode. An idle-high UART receiver at the pendant end is
  fine; anything that actively drives the line is not.

### Known issues carried over from rev A

- The `MISO` and `MOSI` net names are swapped relative to the SD card: net
  `MISO` (GPIO19) goes to the card's CMD/DI pin, which is physically MOSI. The
  card works and the FluidNC config is correct, but **J6's back silkscreen is
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
