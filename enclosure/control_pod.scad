// ============================================================================
// WiggleCam control pod — two-shell enclosure for the camera's brain:
//   * Waveshare 4.3" DSI touchscreen (left of the user face)
//   * camera-controller PCB (this repo) behind the right-hand control
//     strip, components facing OUT: encoder knob, status-LED light
//     pipe and BOOTSEL/RUN poke-holes come through the face, USB-C
//     exits the right wall
//   * Raspberry Pi 5 flat on the rear-shell floor behind the screen
//
// All PCB feature positions come from board_dims.scad, which is
// GENERATED from the routed .kicad_pcb — the case cannot drift from
// the board. Screen and Pi dimensions are parameters: MEASURE YOUR
// DELIVERED PARTS with calipers before printing (vendor drawings
// drift between revisions).
//
// Set PART, render (F6), File > Export STL. Or headless:
//   OpenSCAD -o front.stl -D 'PART="front"' control_pod.scad
// ============================================================================

include <board_dims.scad>

PART = "assembly";   // "front" | "back" | "assembly"

// ---- outer geometry --------------------------------------------------------
wall   = 2.5;        // print-service safe for PETG / MJF nylon
gap    = 4;          // module-to-module breathing room
inner_h = 84;        // interior height (screen module 76 + margin)

// ---- screen (Waveshare 4.3" DSI — MEASURE YOURS, Rev 2.2+) ----------------
scr_w = 122;  scr_h = 76;      // module outline           TODO(measure)
scr_view_w = 106; scr_view_h = 63;  // visible area         TODO(measure)
scr_hole_dx = 114; scr_hole_dy = 68; // M3 pattern          TODO(measure)
scr_t = 8;                     // module thickness incl. PCB bulge

// ---- Raspberry Pi 5 --------------------------------------------------------
pi_w = 85;  pi_h = 56;
pi_hole_dx = 58; pi_hole_dy = 49; pi_hole_off = 3.5;  // from corner
pi_stack_h = 24;               // Pi + active cooler + margin

// ---- derived layout --------------------------------------------------------
// user face: [gap][screen 122][gap][controller strip pcb_h=50][gap]
strip_w  = pcb_h;                       // controller mounts portrait
inner_w  = gap + scr_w + gap + strip_w + gap;
outer_w  = inner_w + 2*wall;
outer_h  = inner_h + 2*wall;
front_d  = 12;                          // front shell depth
back_d   = 28;                          // rear shell depth
scr_x0   = wall + gap;                  // screen pocket left edge
strip_x0 = wall + gap + scr_w + gap;    // strip left edge
face_cy  = outer_h/2;

// controller placement on the strip: board rotated -90° (as seen from
// the front), so board-local (x, y_down) -> face (u, v_up):
//   u = strip_x0 + y      v = wall + (inner_h-pcb_w)/2 + x
// (USB-C bottom edge -> right wall; encoder lands low-right)
strip_y0 = wall + (inner_h - pcb_w)/2;
function fpos(p) = [strip_x0 + p[1], strip_y0 + p[0]];

// screws joining the shells: M3 heat-set inserts in the back shell
screws = [[6, 6], [outer_w/2, 6], [outer_w-6, 6],
          [6, outer_h-6], [outer_w/2, outer_h-6], [outer_w-6, outer_h-6]];
insert_d = 4.2; insert_h = 6;

$fn = 48;

// ============================================================================
// helpers
// ============================================================================
module rbox(w, h, d, r=3) {
    linear_extrude(d) offset(r) offset(-r) square([w, h]);
}

module shell(depth) {                    // open box, floor at z=0
    difference() {
        rbox(outer_w, outer_h, depth);
        translate([wall, wall, wall])
            rbox(inner_w, inner_h, depth);
    }
}

module boss(h, screw_d=2.0, od=6) {      // standoff with pilot hole
    difference() {
        cylinder(d=od, h=h);
        translate([0, 0, 1]) cylinder(d=screw_d, h=h);
    }
}

// ============================================================================
// FRONT shell: bezel + screen pocket + control strip + PCB bosses
// ============================================================================
module front_shell() {
    difference() {
        shell(front_d);

        // screen viewing aperture (through the face)
        translate([scr_x0 + (scr_w-scr_view_w)/2,
                   face_cy - scr_view_h/2, -1])
            cube([scr_view_w, scr_view_h, wall+2]);

        // screen module pocket (recessed from the inside)
        translate([scr_x0 - 0.5, face_cy - scr_h/2 - 0.5, wall])
            cube([scr_w + 1, scr_h + 1, scr_t]);

        // ---- control strip cutouts, from the real PCB coordinates --
        // encoder bushing (fix with its own nut + washer)
        translate([fpos(enc_shaft)[0], fpos(enc_shaft)[1], -1])
            cylinder(d=enc_bush_d, h=front_d+2);
        // WS2812 light pipe (3 mm acrylic rod, press fit)
        translate([fpos(ws2812)[0], fpos(ws2812)[1], -1])
            cylinder(d=3.2, h=wall+2);
        // BOOTSEL / RUN poke-holes (pen tip; labels in silk below)
        for (p = [btn_bootsel, btn_run])
            translate([fpos(p)[0], fpos(p)[1], -1])
                cylinder(d=3.5, h=wall+2);
    }

    // screen corner bosses (M3 self-tap into plastic)
    for (sx = [-1, 1], sy = [-1, 1])
        translate([scr_x0 + scr_w/2 + sx*scr_hole_dx/2,
                   face_cy + sy*scr_hole_dy/2, wall])
            boss(scr_t - 1, screw_d=2.5, od=7);

    // controller PCB bosses — EXACT hole positions from the layout,
    // board component-side toward the face, 5 mm standoff so the
    // encoder body (6.5 mm) plus face wall consume the bushing height
    for (p = pcb_holes)
        translate([fpos(p)[0], fpos(p)[1], wall])
            boss(5, screw_d=2.0, od=6);
}

// ============================================================================
// BACK shell: Pi bay, vents, cable slots, USB window, tripod nut
// ============================================================================
module back_shell() {
    difference() {
        union() {
            shell(back_d);
            // heat-set insert towers for the shell screws
            for (p = screws)
                translate([p[0], p[1], wall])
                    difference() {
                        cylinder(d=insert_d+3.6, h=back_d-wall);
                        translate([0, 0, back_d-wall-insert_h])
                            cylinder(d=insert_d, h=insert_h+1);
                    }
        }

        // ---- right wall: controller USB-C (board bottom edge faces
        // this wall after the -90° mounting rotation).
        // v-position mirrors fpos(); depth = front_d + boss + pcb over
        // the parting line, i.e. near the parting face of this shell
        translate([outer_w - wall - 1,
                   strip_y0 + usbc_center[0] - usbc_w/2,
                   back_d - 4.5])
            cube([wall + 2, usbc_w, usbc_h + 1.4]);

        // ---- left wall: Pi ports window (USB-C power + micro-HDMI,
        // bench use; in the camera, power arrives via the harness)
        translate([-1, face_cy - 27, wall + 3])
            cube([wall + 2, 54, 15]);

        // ---- top wall: LED JST cable slots + camera-ribbon slit
        for (p = [jst_led1, jst_led2])
            translate([strip_x0 + p[1] - 4, outer_h - wall - 1,
                       back_d - 8])
                cube([8, wall + 2, 9]);
        translate([scr_x0 + 20, outer_h - wall - 1, back_d - 5])
            cube([24, wall + 2, 3.5]);   // 22-pin camera ribbon

        // ---- bottom wall: VBAT + shutter JST slots
        for (p = [jst_vbat_in, jst_vbat_out, jst_shutter])
            translate([strip_x0 + p[1] - 4, -1, back_d - 8])
                cube([8, wall + 2, 9]);

        // ---- vents over the Pi bay
        for (i = [0:7])
            translate([scr_x0 + 12 + i*9, -1, wall + 6])
                cube([4, wall + 2, back_d - 14]);

        // ---- tripod: 1/4-20 hex nut pocket + bolt clearance,
        // bottom wall under the screen bay
        translate([scr_x0 + scr_w/2, wall/2 + 0.6, 14])
            rotate([90, 0, 0]) {
                cylinder(d=6.8, h=wall+2, center=true);     // bolt
                translate([0, 0, -wall])
                    cylinder(d=11.4/cos(30), h=wall, $fn=6); // nut
            }
    }

    // Pi 5 bosses on the floor, bay centered behind the screen
    pi_x0 = scr_x0 + (scr_w - pi_w)/2;
    pi_y0 = face_cy - pi_h/2;
    for (p = [[pi_hole_off, pi_hole_off],
              [pi_hole_off + pi_hole_dx, pi_hole_off],
              [pi_hole_off, pi_hole_off + pi_hole_dy],
              [pi_hole_off + pi_hole_dx, pi_hole_off + pi_hole_dy]])
        translate([pi_x0 + p[0], pi_y0 + p[1], wall])
            boss(4, screw_d=2.0, od=6.5);
}

// ============================================================================
// assembly view (mockups only — for the README render / sanity check)
// ============================================================================
module assembly() {
    front_shell();
    translate([0, 0, front_d + back_d + 8])
        mirror([0, 0, 1]) back_shell();
    // controller PCB mock, portrait on the strip
    color("green")
        translate([strip_x0, strip_y0, wall + 5])
            translate([0, pcb_w, 0]) rotate([0, 0, -90])
                cube([pcb_w, pcb_h, pcb_t]);
    // screen mock
    color([0.15, 0.15, 0.18])
        translate([scr_x0, face_cy - scr_h/2, wall])
            cube([scr_w, scr_h, scr_t - 1]);
}

if (PART == "front")    front_shell();
if (PART == "back")     back_shell();
if (PART == "assembly") assembly();
