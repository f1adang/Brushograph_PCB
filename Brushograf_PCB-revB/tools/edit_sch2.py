#!/usr/bin/env python3
"""Rev-B stage 2: USB-C PD input, adjustable motor buck, 5V logic buck,
ESP power switch and the RJ-12 FluidDial pendant port."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisexp import parse, dump, find, first, prop, propval, Str, f
from schbuild import Sheet, fmt, uid
import symlib

SCH = '/Users/gandalf/Documents/fun/Brushograph_PCB/Brushograf_PCB-revB/Brushograf_PCB-revB.kicad_sch'
doc = parse(open(SCH).read())
SU = str(first(doc, 'uuid')[1])
sh = Sheet(SU)

# footprint shorthands
R06   = 'Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder'
R12F  = 'Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder'
C06   = 'Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder'
C12F  = 'Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder'
C1210 = 'Capacitor_SMD:C_1210_3225Metric_Pad1.33x2.70mm_HandSolder'
SOT6  = 'Package_TO_SOT_SMD:SOT-23-6'
SOD323= 'Diode_SMD:D_SOD-323'
SMA   = 'Diode_SMD:D_SMA_Handsoldering'
LFP   = 'Inductor_SMD:L_7.3x7.3_H4.5'
USBC  = 'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'
SSOP10= 'Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm'
RJ12FP= 'Connector_RJ:RJ12_Amphenol_54601-x06_Horizontal'
TRIM   = 'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical'
SLIDE  = 'Button_Switch_THT:SW_DIP_SPSTx01_Slide_9.78x4.72mm_W7.62mm_P2.54mm'
FUSE06 = 'Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder'

def stub(part, pin, net, length=7.62, rot=None):
    """Short wire out of a pin, ending in a global label."""
    px, py = part.p(pin)
    dx, dy = px - part.x, py - part.y
    if abs(dx) >= abs(dy):
        ex, ey = px + (length if dx > 0 else -length), py
        r = 0 if dx > 0 else 180
    else:
        ex, ey = px, py + (length if dy > 0 else -length)
        r = 90 if dy < 0 else 270
    sh.wire(px, py, ex, ey)
    sh.label(net, ex, ey, rot if rot is not None else r)
    return (ex, ey)

def gnd_stub(part, pin, length=7.62):
    px, py = part.p(pin)
    sh.wire(px, py, px, py + length)
    sh.gnd(px, py + length)


# ============================== rework of the existing sheet ==============================
# The linear regulator and its blocking diode are replaced by the two bucks
# below, so U5, the old D14 and the wiring between them come out.
def drop_symbol(ref):
    for s in find(doc, 'symbol'):
        if propval(s, 'Reference') == ref:
            doc.remove(s); return True
    return False

def drop_wire(x1, y1, x2, y2):
    for w in find(doc, 'wire'):
        pts = sorted((round(f(p[1]), 3), round(f(p[2]), 3)) for p in first(w, 'pts')[1:])
        if pts == sorted([(x1, y1), (x2, y2)]):
            doc.remove(w); return True
    return False

def drop_junction(x, y):
    for j in find(doc, 'junction'):
        a = first(j, 'at')
        if abs(f(a[1]) - x) < 1e-3 and abs(f(a[2]) - y) < 1e-3:
            doc.remove(j); return True
    return False

def drop_gnd_at(x, y):
    for s in find(doc, 'symbol'):
        if str(first(s, 'lib_id')[1]) != 'power:GND':
            continue
        a = first(s, 'at')
        if abs(f(a[1]) - x) < 1e-3 and abs(f(a[2]) - y) < 1e-3:
            doc.remove(s); return True
    return False

assert drop_symbol('U5'), 'U5 not found'
assert drop_symbol('D14'), 'old D14 not found'
for seg in [(125.73, 22.86, 128.27, 22.86),   # U5 IN stub
            (125.73, 13.97, 125.73, 22.86),
            (167.64, 13.97, 125.73, 13.97),
            (167.64, 24.13, 167.64, 13.97),
            (143.51, 22.86, 143.51, 30.48),   # U5 OUT stub
            (135.89, 30.48, 135.89, 33.02)]:  # U5 GND stub
    assert drop_wire(*seg), f'wire {seg} not found'
assert drop_junction(167.64, 24.13), 'junction not found'
assert drop_gnd_at(135.89, 33.02), 'U5 GND symbol not found'

# what is left of the old regulator output run now becomes the 5V system rail
sh.label('5V_SYS', 151.13, 30.48, 180)

# J7 pin 3 used to be the raw barrel-jack rail, which would now be 9-20V and
# would destroy the motors. It becomes the adjustable motor rail instead.
for gl in find(doc, 'global_label'):
    a = first(gl, 'at')
    if str(gl[1]) == '5V-EXT' and abs(f(a[1]) - 163.83) < 0.01:
        gl[1] = Str('MOTOR_V'); break
else:
    raise SystemExit('ERROR: J7 5V-EXT label not found')

# pendant UART out to the ESP32
sh.wire(157.48, 57.15, 152.4, 57.15)          # U4 pin 23, GPIO15
sh.label('PEND_RX', 152.4, 57.15, 180)
sh.wire(223.52, 46.99, 228.6, 46.99)          # U4 pin 24, GPIO2
sh.label('PEND_TX', 228.6, 46.99, 0)

# =====================================================  USB-C + CH224K PD sink
J12 = sh.place('Connector', 'USB_C_Receptacle_USB2.0_16P', 'J12', 'USB-C PD in',
               USBC, 60, 245, 0, ref_at=(60, 214, None), val_at=(60, 216.54, None))
sh.wire(*J12.p('A1'), J12.p('A1')[0], J12.p('A1')[1] + 5.08)
sh.gnd(J12.p('A1')[0], J12.p('A1')[1] + 5.08)
sh.wire(*J12.p('SH'), J12.p('SH')[0], J12.p('SH')[1] + 5.08)
sh.gnd(J12.p('SH')[0], J12.p('SH')[1] + 5.08)
vb_pt = stub(J12, 'A4', 'VBUS')             # all four VBUS pins share one point
# VBUS is fed by the connector, so flag it as a source for ERC
sh.wire(vb_pt[0], vb_pt[1], vb_pt[0], vb_pt[1] - 7.62)
sh.pwrflag(vb_pt[0], vb_pt[1] - 7.62, 0)
stub(J12, 'A5', 'USB_CC1')
stub(J12, 'B5', 'USB_CC2')
# D+ / D- : the A and B contacts are separate points, tie each pair together
for a, b, net in (('A6', 'B6', 'USB_DP'), ('A7', 'B7', 'USB_DM')):
    ax, ay = J12.p(a); bx, by = J12.p(b)
    sh.wire(ax, ay, ax + 5.08, ay); sh.wire(bx, by, bx + 5.08, by)
    sh.wire(ax + 5.08, ay, bx + 5.08, by)
    sh.wire(bx + 5.08, by, bx + 10.16, by)
    sh.label(net, bx + 10.16, by, 0)
for nc in ('A8', 'B8'):
    x, y = J12.p(nc)
    sh.items.append(['no_connect', ['at', fmt(x), fmt(y)], ['uuid', uid('nc')]])

U6 = sh.place('Interface_USB', 'CH224K', 'U6', 'CH224K', SSOP10, 140, 245, 0,
              ref_at=(140, 228, None), val_at=(140, 230.54, None))
stub(U6, 'CC1', 'USB_CC1'); stub(U6, 'CC2', 'USB_CC2')
stub(U6, 'DP', 'USB_DP');   stub(U6, 'DM', 'USB_DM')
gnd_stub(U6, 'GND')
# VDD: 5.1k series from VBUS + 1uF decoupling (datasheet 6.1)
vdd = U6.p('VDD')
sh.wire(vdd[0], vdd[1], vdd[0], vdd[1] - 6.35)
R22 = sh.place('Device', 'R', 'R22', '5.1k', R06, vdd[0], vdd[1] - 10.16, 0)
sh.wire(vdd[0], vdd[1] - 6.35, *R22.p('2'))
sh.wire(*R22.p('1'), R22.p('1')[0], R22.p('1')[1] - 3.81)
sh.label('VBUS', R22.p('1')[0], R22.p('1')[1] - 3.81, 90)
C9 = sh.place('Device', 'C', 'C9', '1uF', C06, vdd[0] + 7.62, vdd[1] - 2.54, 0)
sh.route((vdd[0], vdd[1] - 6.35), C9.p('1'), horiz_first=False)
sh.junction(vdd[0], vdd[1] - 6.35)
sh.wire(*C9.p('2'), C9.p('2')[0], C9.p('2')[1] + 2.54)
sh.gnd(C9.p('2')[0], C9.p('2')[1] + 2.54)
# VBUS sense pin: 5.1k series to VBUS
vb = U6.p('VBUS')
sh.wire(vb[0], vb[1], vb[0], vb[1] - 6.35)
R23 = sh.place('Device', 'R', 'R23', '5.1k', R06, vb[0] - 12.7, vb[1] - 12.7, 0)
sh.wire(vb[0], vb[1] - 6.35, vb[0] - 12.7, vb[1] - 6.35)
sh.wire(vb[0] - 12.7, vb[1] - 6.35, *R23.p('2'))
sh.wire(*R23.p('1'), R23.p('1')[0], R23.p('1')[1] - 3.81)
sh.label('VBUS', R23.p('1')[0], R23.p('1')[1] - 3.81, 90)
# CFG1 = 6.8k to GND -> request 9V (CFG2/CFG3 left floating per datasheet 5.2.1)
c1 = U6.p('CFG1')
sh.wire(c1[0], c1[1], c1[0] + 7.62, c1[1])
R24 = sh.place('Device', 'R', 'R24', '6.8k', R06, c1[0] + 7.62, c1[1] + 6.35, 0)
sh.wire(c1[0] + 7.62, c1[1], *R24.p('1'))
sh.wire(*R24.p('2'), R24.p('2')[0], R24.p('2')[1] + 2.54)
sh.gnd(R24.p('2')[0], R24.p('2')[1] + 2.54)
for nc in ('CFG2', 'CFG3'):
    x, y = U6.p(nc)
    sh.items.append(['no_connect', ['at', fmt(x), fmt(y)], ['uuid', uid('nc')]])
# PG (open drain, active low) drives a "PD OK" LED off the 5V rail
pg = U6.p('PG')
sh.wire(pg[0], pg[1], pg[0] + 5.08, pg[1])
D17 = sh.place('Device', 'LED', 'D17', 'PD OK', 'LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder',
               pg[0] + 12.7, pg[1], 0)
sh.wire(pg[0] + 5.08, pg[1], *D17.p('K'))
R25 = sh.place('Device', 'R', 'R25', '1k', R06, pg[0] + 25.4, pg[1], 90)
near25 = min(R25.p('1'), R25.p('2'), key=lambda q: q[0])
far25 = max(R25.p('1'), R25.p('2'), key=lambda q: q[0])
sh.wire(*D17.p('A'), *near25)
sh.wire(*far25, far25[0] + 5.08, pg[1])
sh.label('5V_SYS', far25[0] + 5.08, pg[1], 0)

# =====================================================  input OR-ing -> VSUP
YB = 300.0
D15 = sh.place('Device', 'D_Schottky', 'D15', 'SS34', SMA, 75, YB, 180)
sh.wire(D15.p('A')[0] - 7.62, YB, *D15.p('A'))
sh.label('VBUS', D15.p('A')[0] - 7.62, YB, 180)
D16 = sh.place('Device', 'D_Schottky', 'D16', 'SS34', SMA, 75, YB + 10.16, 180)
sh.wire(D16.p('A')[0] - 7.62, YB + 10.16, *D16.p('A'))
sh.label('VIN_DC', D16.p('A')[0] - 7.62, YB + 10.16, 180)
RAIL = D15.p('K')[0] + 7.62
sh.wire(*D15.p('K'), RAIL, YB)
sh.wire(*D16.p('K'), RAIL, YB + 10.16)
sh.wire(RAIL, YB - 7.62, RAIL, YB + 10.16)
sh.junction(RAIL, YB)
sh.pwrflag(RAIL, YB - 7.62, 0)
C10 = sh.place('Device', 'C', 'C10', '22uF/35V', C1210, RAIL + 12.7, YB + 5.08, 0)
sh.wire(RAIL, YB + 5.08, *C10.p('1'))
sh.junction(RAIL, YB + 5.08)
sh.wire(*C10.p('2'), C10.p('2')[0], C10.p('2')[1] + 2.54)
sh.gnd(C10.p('2')[0], C10.p('2')[1] + 2.54)
sh.wire(RAIL, YB + 5.08, RAIL + 25.4, YB + 5.08)
sh.label('VSUP', RAIL + 25.4, YB + 5.08, 0)

# =====================================================  buck converters
def buck(ref_u, X, Y, vout_net, l_ref, l_val, cin_ref, cb_ref, cout_refs,
         rtop_ref, rtop_val, rbot_ref, rbot_val, trim=None, cin_val='10uF/35V'):
    U = sh.place('Regulator_Switching', 'TPS54202DDC', ref_u, 'TPS54202', SOT6, X, Y, 0,
                 ref_at=(X, Y - 12.7, None), val_at=(X, Y - 10.16, None))
    vin = U.p('VIN')
    sh.wire(vin[0] - 25.4, vin[1], *vin)
    sh.label('VSUP', vin[0] - 25.4, vin[1], 180)
    Cin = sh.place('Device', 'C', cin_ref, cin_val, C1210, vin[0] - 12.7, vin[1] + 6.35, 0)
    sh.wire(vin[0] - 12.7, vin[1], *Cin.p('1'))
    sh.junction(vin[0] - 12.7, vin[1])
    sh.wire(*Cin.p('2'), Cin.p('2')[0], Cin.p('2')[1] + 2.54)
    sh.gnd(Cin.p('2')[0], Cin.p('2')[1] + 2.54)
    x, y = U.p('EN')
    sh.items.append(['no_connect', ['at', fmt(x), fmt(y)], ['uuid', uid('nc')]])
    gnd_stub(U, 'GND', 5.08)
    # SW -> inductor -> output rail
    sw = U.p('SW'); boot = U.p('BOOT')
    L = sh.place('Device', 'L', l_ref, l_val, LFP, sw[0] + 15.24, sw[1], 90)
    sh.wire(sw[0], sw[1], *L.p('1'))
    sh.junction(sw[0] + 7.62, sw[1]) if False else None
    # BOOT cap from BOOT to the SW node
    Cb = sh.place('Device', 'C', cb_ref, '100nF', C06, sw[0] + 7.62, boot[1] - 6.35, 90)
    sh.wire(boot[0], boot[1], boot[0], boot[1] - 6.35)
    sh.wire(boot[0], boot[1] - 6.35, *Cb.p('1'))
    sh.wire(*Cb.p('2'), sw[0] + 7.62, boot[1] - 6.35)
    sh.wire(sw[0] + 7.62, boot[1] - 6.35, sw[0] + 7.62, sw[1])
    sh.junction(sw[0] + 7.62, sw[1])
    OUT = L.p('2')[0] + 7.62
    sh.wire(*L.p('2'), OUT, sw[1])
    # output caps
    prev = OUT
    for i, cr in enumerate(cout_refs):
        cx = OUT + 10.16 * (i + 1)
        C = sh.place('Device', 'C', cr, '22uF/25V', C1210, cx, sw[1] + 6.35, 0)
        sh.wire(prev, sw[1], cx, sw[1])
        sh.junction(cx, sw[1])
        sh.wire(cx, sw[1], *C.p('1'))
        sh.wire(*C.p('2'), C.p('2')[0], C.p('2')[1] + 2.54)
        sh.gnd(C.p('2')[0], C.p('2')[1] + 2.54)
        prev = cx
    sh.wire(prev, sw[1], prev + 12.7, sw[1])
    sh.label(vout_net, prev + 12.7, sw[1], 0)
    # feedback divider taken from the output rail
    fb = U.p('FB')
    FBX = OUT + 5.08
    Rt = sh.place('Device', 'R', rtop_ref, rtop_val, R06, FBX, sw[1] + 8.89, 0)
    sh.wire(OUT, sw[1], FBX, sw[1])
    sh.junction(OUT, sw[1]) if False else None
    sh.wire(FBX, sw[1], *Rt.p('1'))
    sh.junction(FBX, sw[1])
    node = Rt.p('2')
    sh.route(node, (fb[0] + 2.54, fb[1]), horiz_first=False)
    sh.wire(fb[0], fb[1], fb[0] + 2.54, fb[1])
    sh.junction(*node)
    Rb = sh.place('Device', 'R', rbot_ref, rbot_val, R06, FBX, node[1] + 7.62, 0)
    sh.wire(node[0], node[1], *Rb.p('1'))
    if trim:
        # RV1 sits below the fixed bottom resistor; the wiper is tied to its top
        # end, so the element in circuit is R(top..gnd) || R(wiper..gnd) and a
        # lifted wiper simply leaves the full track in place -> Vout drops, safe.
        My = Rb.p('2')[1] + 2.54
        RV = sh.place('Device', 'R_Potentiometer_Small', trim[0], trim[1], TRIM,
                      FBX, My + 2.54, 0)
        sh.wire(*Rb.p('2'), FBX, My)
        sh.junction(FBX, My)
        wx, wy = RV.p('2')
        sh.wire(wx, wy, wx + 3.81, wy)
        sh.wire(wx + 3.81, wy, wx + 3.81, My)
        sh.wire(wx + 3.81, My, FBX, My)
        sh.wire(*RV.p('3'), RV.p('3')[0], RV.p('3')[1] + 2.54)
        sh.gnd(RV.p('3')[0], RV.p('3')[1] + 2.54)
    else:
        sh.wire(*Rb.p('2'), Rb.p('2')[0], Rb.p('2')[1] + 2.54)
        sh.gnd(Rb.p('2')[0], Rb.p('2')[1] + 2.54)
    return U

# motor rail: 100k / (7.5k + 5k trim) -> about 5.4 .. 8.6 V, 7.5 V nominal
buck('U7', 390, 240, 'MOTOR_V', 'L1', '10uH 3.5A', 'C11', 'C12',
     ['C13', 'C14'], 'R26', '100k', 'R27', '7.5k', trim=('RV1', '10k'))
# logic rail: 75k / 10k -> 5.07 V
buck('U8', 390, 330, '5V_LOGIC', 'L2', '15uH 2A', 'C15', 'C16',
     ['C17'], 'R28', '75k', 'R29', '10k')

# =====================================  5V system rail: blocking diode + switch
YS = 330.0
D14n = sh.place('Device', 'D_Schottky', 'D14', 'SS14', SMA, 75, YS, 180)
sh.wire(D14n.p('A')[0] - 7.62, YS, *D14n.p('A'))
sh.label('5V_LOGIC', D14n.p('A')[0] - 7.62, YS, 180)
SW1 = sh.place('Switch', 'SW_SPST', 'SW1', 'ESP POWER', SLIDE, 105, YS, 0,
               ref_at=(105, YS - 6.35, None), val_at=(105, YS - 3.81, None))
sh.wire(*D14n.p('K'), *SW1.p('1'))
sh.wire(*SW1.p('2'), SW1.p('2')[0] + 10.16, YS)
sh.label('5V_SYS', SW1.p('2')[0] + 10.16, YS, 0)
# (5V_SYS already carries a PWR_FLAG up at the ESP32 end of the rail)

# =====================================  RJ-12 pendant port (FluidDial)
# All six contacts leave the connector as short stubs carrying global labels;
# the protection network sits beside it. That keeps the fan-out readable.
#
#   pin 1 GND | 2 +5V | 3 TX | 4 RX | 5 +5V | 6 GND
#
# The order is symmetric on purpose: a standard reversing modular cable keeps
# power and ground on the right contacts and swaps TX/RX, which is the crossover
# the pendant needs.  >>> CHECK THIS AGAINST YOUR FLUIDDIAL CABLE BEFORE BUILDING <<<
YP = 330.0
J13 = sh.place('Connector', 'RJ12', 'J13', 'FluidDial pendant', RJ12FP, 250, YP, 180,
               ref_at=(250, YP - 16.51, None), val_at=(250, YP - 13.97, None))
PEND_PINS = [('1', 'GND', 5.08), ('2', 'PEND_5V', 10.16), ('3', 'PEND_TX_CON', 15.24),
             ('4', 'PEND_RX_CON', 20.32), ('5', 'PEND_5V', 25.4), ('6', 'GND', 30.48)]
for pin, net, ln in PEND_PINS:
    px, py = J13.p(pin)
    sh.wire(px, py, px - ln, py)
    if net == 'GND':
        sh.gnd(px - ln, py, 270)
    else:
        sh.label(net, px - ln, py, 180)

# pendant supply: 5V_SYS through a resettable fuse
F2 = sh.place('Device', 'Polyfuse', 'F2', '0.5A', FUSE06, 205, YP + 20.32, 90)
sh.wire(F2.p('1')[0] - 7.62, F2.p('1')[1], *F2.p('1'))
sh.label('5V_SYS', F2.p('1')[0] - 7.62, F2.p('1')[1], 180)
sh.wire(*F2.p('2'), F2.p('2')[0] + 7.62, F2.p('2')[1])
sh.label('PEND_5V', F2.p('2')[0] + 7.62, F2.p('2')[1], 0)

# UART lines: series resistor plus a TVS clamp on each, as on the official module
for pin_net, gpio_net, rref, dref, ry in (
        ('PEND_TX_CON', 'PEND_TX', 'R30', 'D18', YP + 27.94),
        ('PEND_RX_CON', 'PEND_RX', 'R31', 'D19', YP + 52.07)):
    Rs = sh.place('Device', 'R', rref, '330', R06, 220, ry, 90)
    right = max(Rs.p('1'), Rs.p('2'), key=lambda q: q[0])
    left = min(Rs.p('1'), Rs.p('2'), key=lambda q: q[0])
    sh.wire(*right, right[0] + 7.62, ry)
    sh.label(pin_net, right[0] + 7.62, ry, 0)
    nx = left[0] - 7.62
    sh.wire(*left, nx, ry)
    Dt = sh.place('Device', 'D_TVS', dref, 'PESD5V0S1BA', SOD323, nx, ry + 8.89, 0)
    sh.wire(nx, ry, *Dt.p('1'))
    sh.junction(nx, ry)
    sh.wire(*Dt.p('2'), Dt.p('2')[0], Dt.p('2')[1] + 2.54)
    sh.gnd(Dt.p('2')[0], Dt.p('2')[1] + 2.54)
    sh.wire(nx, ry, nx - 10.16, ry)
    sh.label(gpio_net, nx - 10.16, ry, 180)

# =====================================  merge into the sheet
libsec = first(doc, 'lib_symbols')
have = {str(s[1]) for s in find(libsec, 'symbol')}
for k, s in sorted(sh.libs.items()):
    if k not in have:
        libsec.append(s); have.add(k)
anchor = doc.index(first(doc, 'sheet_instances'))
doc[anchor:anchor] = sh.items
open(SCH, 'w').write(dump(doc) + '\n')
print(f'stage 2: +{len([i for i in sh.items if i[0]=="symbol"])} symbols, '
      f'{len([i for i in sh.items if i[0]=="wire"])} wires, '
      f'{len([i for i in sh.items if i[0]=="global_label"])} labels')
