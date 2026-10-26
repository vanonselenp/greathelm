// Greathelm travel box
// Base, lid and a player tray. Print the tray twice.
// Stack, bottom to top: two player trays, then the card layer (maps,
// player cards, rulebook), then the lid. The cards hold everything in
// the wells. With both trays out, the empty base is the dice tray.
//
// All dimensions in mm. Set `part`, render, export STL.
// Print orientation: base and tray open side up, lid top face down.

/* [Part] */
part = "assembly"; // [assembly, exploded, base, lid, tray]

/* [Card layer] */
card_w = 170;           // map card, long side
card_d = 120;           // map card, short side
map_count = 4;
map_t = 0.5;            // one map card
player_card_count = 4;  // colour card and dice card per player
player_card_t = 0.5;
rulebook_t = 3;         // A6 booklet, lies landscape on the maps
card_slack = 1.0;       // headroom over the card stack
card_clear = 0.75;      // gap from card edge to wall, per side

/* [Wells] */
well_h = 20;            // tested: six jumbled models sit below 20mm

/* [Models] */
models_per_side = 6;
base_d = 15;            // model base diameter
model_slop = 2;         // well area allows for six standing models

/* [Dice] */
dice_per_side = 10;
dice_layers = 1;
die = 12;
die_slop = 0.6;

/* [Tokens] */
// Counts per player. Sizes match greathelm-tokens.scad.
damage_count = 6;
momentum_count = 12;
defence_count = 4;      // riposte, parry, block, dodge
death_count = 5;
token_d = 15;           // teardrop and disc diameter
token_tip = 5.5;        // teardrop point past the circle
shield_w = 15;
shield_h = 20;
token_t = 3;
token_fill = 0.5;       // token bounding boxes as a share of the well. Lower = roomier.

/* [Box] */
wall_inner_t = 1.2;     // base wall left above the lid rebate
lid_skirt_t = 1.2;
lid_clear = 0.2;        // fit gap, lid skirt to base rebate
rebate_h = 6;           // lid skirt overlap
floor_t = 1.6;
lid_top_t = 1.6;
corner_r = 3;
thumb_notch_w = 22;     // finger cuts in the long walls to lift the cards

/* [Trays] */
tray_floor_t = 1.2;
tray_wall_t = 1.6;
tray_div_t = 1.2;
tray_clear = 0.3;       // tray to wall, per side
tray_gap = 0.5;         // between the two trays
tray_top_clear = 0.3;   // tray top to card stack
scoop_r = 6;            // rounded floor edges in dice and token wells
finger_min = 20;        // narrowest well a finger gets into

/* [Lid decoration] */
lid_hexes = true;
hex_flat = 15;          // flat to flat, match the maps
hex_groove = 0.8;
hex_depth = 0.6;
hex_margin = 6;

/* [Printer] */
bed = 180;              // A1 Mini

/* [Hidden] */
$fn = 48;
eps = 0.01;

tk_n    = damage_count + momentum_count + defence_count + death_count;
tk_area = (damage_count + momentum_count) * token_d * (token_d + token_tip)
        + defence_count * shield_w * shield_h
        + death_count * token_d * token_d;   // sum of token bounding boxes, one player
tk_t    = token_t;

// ---------- derived ----------
wall   = wall_inner_t + lid_clear + lid_skirt_t;
step   = lid_skirt_t + lid_clear;          // rebate depth into the wall
in_w   = card_w + 2 * card_clear;
in_d   = card_d + 2 * card_clear;
out_w  = in_w + 2 * wall;
out_d  = in_d + 2 * wall;

card_stack_h = map_count * map_t + player_card_count * player_card_t
             + rulebook_t + card_slack;

cell     = base_d + model_slop;
pocket_h = well_h;
tray_h   = tray_floor_t + pocket_h;

base_h   = floor_t + tray_h + tray_top_clear + card_stack_h;
card_z   = floor_t + tray_h + tray_top_clear;
skirt_h  = rebate_h - 0.3;                 // lid seats on the rim, not the shoulder
lid_h    = lid_top_t + skirt_h;
closed_h = base_h + lid_top_t;

tray_w  = in_w - 2 * tray_clear;
tray_d  = (in_d - 2 * tray_clear - tray_gap) / 2;
avail_d = tray_d - 2 * tray_wall_t;        // every well spans the tray's short axis

// model well
m_rows = max(1, floor(avail_d / cell));
m_cols = ceil(models_per_side / m_rows);
m_w    = m_cols * cell;

// dice well
d_cell   = die + die_slop;
d_layers = dice_layers;
d_depth  = d_layers * die + 0.5;
d_rows   = max(1, floor(avail_d / d_cell));
d_cols   = ceil(ceil(dice_per_side / d_layers) / d_rows);
d_w      = max(finger_min, d_cols * d_cell);

// token well: loose pile
t_w = max(finger_min, ceil(tk_area * tk_t / token_fill / (avail_d * pocket_h)));

// x positions along the tray
x_m = tray_wall_t;
x_d = x_m + m_w + tray_div_t;
x_t = x_d + d_w + tray_div_t;
x_r = x_t + t_w + tray_div_t;               // terrain bay start
r_w = tray_w - tray_wall_t - x_r;          // terrain bay length

// ---------- report ----------
echo(str("BOX outside ", out_w, " x ", out_d, " x ", closed_h, " closed"));
echo(str("BED margin ", (bed - out_w) / 2, " per side on the long axis"));
echo(str("CARD stack ", card_stack_h, " incl. slack"));
echo(str("TRAY ", tray_w, " x ", tray_d, " x ", tray_h, ", wells ", pocket_h, " deep"));
echo(str("WELL models ", m_w, " x ", avail_d, " x ", pocket_h));
echo(str("WELL dice ", d_w, " x ", avail_d, " x ", d_depth, " (", d_cols, "x", d_rows, ", ", d_layers, " layer)"));
echo(str("WELL tokens ", t_w, " x ", avail_d, " x ", pocket_h, " (", tk_n, " tokens)"));
echo(str("WELL terrain ", r_w, " x ", avail_d, " x ", pocket_h));
echo(str("DICE TRAY base empty ", in_w, " x ", in_d, " x ", base_h - floor_t));

if (out_w > bed || out_d > bed) echo("WARNING: box is larger than the bed");
assert(r_w > 10, str("No room left for terrain: ", r_w, " mm. Shrink a well."));
assert(d_depth <= pocket_h, "Dice well deeper than tray");

// ---------- helpers ----------
module rrect(size, r) {
  r2 = max(eps, min(r, size[0] / 2, size[1] / 2));
  translate([r2, r2]) offset(r = r2) square([size[0] - 2 * r2, size[1] - 2 * r2]);
}

// Pocket with rounded floor edges along both long sides, for scooping.
module scoop_pocket(w, d, h, r) {
  rr = max(0.2, min(r, d / 2, h));
  hull() {
    translate([0, 0, h - eps]) cube([w, d, eps]);
    for (y = [rr, d - rr])
      translate([0, y, rr]) rotate([0, 90, 0]) cylinder(r = rr, h = w);
  }
}

// ---------- parts ----------
// Wells left to right: models, dice, tokens, terrain.
// Dice and tokens get scooped floors. Models and terrain stay square.
module tray() {
  over = 1;  // pockets break through the top
  difference() {
    linear_extrude(tray_h) rrect([tray_w, tray_d], 1.5);
    translate([x_m, tray_wall_t, tray_h - pocket_h])
      cube([m_w, avail_d, pocket_h + over]);
    translate([x_d, tray_wall_t, tray_h - d_depth])
      scoop_pocket(d_w, avail_d, d_depth + over, scoop_r);
    translate([x_t, tray_wall_t, tray_h - pocket_h])
      scoop_pocket(t_w, avail_d, pocket_h + over, scoop_r);
    translate([x_r, tray_wall_t, tray_h - pocket_h])
      cube([r_w, avail_d, pocket_h + over]);
  }
}

module base() {
  difference() {
    union() {
      linear_extrude(base_h - rebate_h) rrect([out_w, out_d], corner_r);
      translate([step, step, 0])
        linear_extrude(base_h) rrect([out_w - 2 * step, out_d - 2 * step], corner_r - step);
    }
    translate([wall, wall, floor_t])
      linear_extrude(base_h) rrect([in_w, in_d], 1);
    // thumb notches, both long walls, down to the bottom of the card stack
    r = thumb_notch_w / 2;
    hull() {
      translate([out_w / 2, -1, card_z + r]) rotate([-90, 0, 0]) cylinder(r = r, h = out_d + 2);
      translate([out_w / 2 - r, -1, card_z + r]) cube([2 * r, out_d + 2, base_h]);
    }
  }
}

module hex_grid_2d(w, d) {
  R  = hex_flat / sqrt(3);
  dx = 1.5 * R;
  cols = ceil(w / dx) + 2;
  rows = ceil(d / hex_flat) + 2;
  for (i = [-1 : cols], j = [-1 : rows])
    translate([i * dx, j * hex_flat + (i % 2 == 0 ? 0 : hex_flat / 2)])
      difference() {
        offset(delta = hex_groove / 2) circle(r = R, $fn = 6);
        offset(delta = -hex_groove / 2) circle(r = R, $fn = 6);
      }
}

// Modelled in print orientation: top plate on the bed, skirt up.
module lid() {
  fw = out_w - 2 * hex_margin;
  fd = out_d - 2 * hex_margin;
  difference() {
    linear_extrude(lid_h) rrect([out_w, out_d], corner_r);
    translate([lid_skirt_t, lid_skirt_t, lid_top_t])
      linear_extrude(lid_h) rrect([out_w - 2 * lid_skirt_t, out_d - 2 * lid_skirt_t], corner_r - lid_skirt_t);
    if (lid_hexes)
      translate([0, 0, -eps]) linear_extrude(hex_depth + eps) {
        translate([hex_margin, hex_margin]) intersection() {
          rrect([fw, fd], 2);
          translate([fw / 2 - floor(fw / 2 / (1.5 * hex_flat / sqrt(3))) * 1.5 * hex_flat / sqrt(3),
                     fd / 2 - floor(fd / 2 / hex_flat) * hex_flat])
            hex_grid_2d(fw, fd);
        }
        // border
        translate([hex_margin, hex_margin]) difference() {
          offset(delta = hex_groove / 2) rrect([fw, fd], 2);
          offset(delta = -hex_groove / 2) rrect([fw, fd], 2);
        }
      }
  }
}

// ---------- assembly ----------
module assembly(e = 0) {
  color("tan") base();
  color("steelblue")
    translate([wall + tray_clear, wall + tray_clear, floor_t + e]) tray();
  color("firebrick")
    translate([wall + tray_clear + tray_w, wall + tray_clear + 2 * tray_d + tray_gap, floor_t + e])
      rotate([0, 0, 180]) tray();
  color("white", 0.9)
    translate([wall + card_clear, wall + card_clear, card_z + 2 * e])
      cube([card_w, card_d, card_stack_h - card_slack]);
  color("burlywood")
    translate([0, out_d, base_h + lid_top_t + 3 * e]) rotate([180, 0, 0]) lid();
}

if (part == "assembly") assembly(0);
else if (part == "exploded") assembly(tray_h + 15);
else if (part == "base") base();
else if (part == "lid") lid();
else if (part == "tray") tray();
