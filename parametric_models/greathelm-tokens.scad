// Greathelm tokens, sized to the 15mm model bases.
//
// Damage and momentum: teardrops, so they point at a model on the mat.
//   1 on top, 2 underneath. Flip to go from 1 to 2.
// Riposte, parry, block, dodge: shields with a letter on both faces.
// Gruesome death: a plain disc with a skull on both faces.
//
// Two colours: export layer=body and layer=inlay for the same part, then
// load both STLs in Bambu Studio as one object with two parts.
// One colour: export layer=body on its own for debossed faces.
//
// greathelm-box.scad reads token sizes and counts from this file,
// so keep the two files in the same folder.

/* [Part] */
part = "preview"; // [preview, damage, momentum, riposte, parry, block, dodge, death]
layer = "all";    // [all, body, inlay]
sets = 2;         // players to print for

/* [Counts per player] */
damage_count = 6;     // one per knight, flipped from 1 to 2
momentum_count = 5;
defence_count = 1;    // of each defence type
death_count = 3;

/* [Teardrop and disc] */
token_d = 15;         // matches the model bases
tip_len = 5.5;        // how far the point reaches past the circle
tip_r = 0.8;

/* [Shield] */
shield_w = 15;        // at the widest point
shield_h = 20;
shield_tip_round = 0.35;   // rounding on the horns and the point
shield_notch_round = 0.4;  // rounding inside the notches

/* [All tokens] */
token_t = 3;
chamfer = 0.4;

/* [Faces] */
inlay_depth = 0.6;
font = "Liberation Sans:style=Bold";
number_size = 9;
letter_size = 8;
skull_h = 8.5;

/* [Layout] */
gap = 3;

/* [Hidden] */
$fn = 64;
eps = 0.01;
types = ["damage", "momentum", "riposte", "parry", "block", "dodge", "death"];

function is_drop(t)   = t == "damage" || t == "momentum";
function is_shield(t) = t == "riposte" || t == "parry" || t == "block" || t == "dodge";

function count_of(t) =
  t == "damage" ? damage_count :
  t == "momentum" ? momentum_count :
  t == "death" ? death_count : defence_count;

function bbox_of(t) =
  is_drop(t) ? [token_d, token_d + tip_len] :
  is_shield(t) ? [shield_w, shield_h] : [token_d, token_d];

function letter_of(t) =
  t == "riposte" ? "R" : t == "parry" ? "P" : t == "block" ? "B" : "D";

function body_colour(t) =
  t == "damage" ? "firebrick" : t == "momentum" ? "gold" :
  t == "death" ? "#2a2a2a" : "steelblue";

function inlay_colour(t) =
  t == "momentum" ? "#2a2a2a" : t == "death" ? "ivory" : "white";

function sum(v, i = 0) = i < len(v) ? v[i] + sum(v, i + 1) : 0;

// Read by greathelm-box.scad
function token_thickness() = token_t;
function tokens_per_side() = sum([for (t = types) count_of(t)]);
function tokens_area_per_side() =
  sum([for (t = types) count_of(t) * bbox_of(t)[0] * bbox_of(t)[1]]);

// ---------- 2D outlines ----------
module drop2d() hull() {
  circle(d = token_d);
  translate([0, token_d / 2 + tip_len - tip_r]) circle(r = tip_r);
}

// Shield outline: dipped top edge, horns at the top corners, a notch
// under each horn, sides bulging out then curving to a blunt point.
// Drawn as the right half in units of width, y measured down from the top.
function bez2(p0, p1, p2, n = 12) =
  [for (i = [0 : n]) let(t = i / n) pow(1 - t, 2) * p0 + 2 * (1 - t) * t * p1 + t * t * p2];
function bez3(p0, p1, p2, p3, n = 20) =
  [for (i = [0 : n]) let(t = i / n)
    pow(1 - t, 3) * p0 + 3 * pow(1 - t, 2) * t * p1 + 3 * (1 - t) * t * t * p2 + pow(t, 3) * p3];
function tail(v) = [for (i = [1 : len(v) - 1]) v[i]];

shield_len = 1.40;   // height of the drawn half, in widths
shield_right = concat(
  bez2([0, 0.04], [0.3, 0.04], [0.51, -0.03]),                      // top edge up to the horn
  tail(bez2([0.51, -0.03], [0.48, 0.04], [0.455, 0.11])),           // horn down into the notch
  tail(bez3([0.455, 0.11], [0.49, 0.13], [0.5, 0.19], [0.5, 0.26])),// out to full width
  tail(bez3([0.5, 0.26], [0.5, 0.95], [0.26, 1.24], [0, shield_len])) // straight sides, then the point
);
shield_left = [for (i = [len(shield_right) - 2 : -1 : 1]) [-shield_right[i][0], shield_right[i][1]]];

// Centred on its bounding box, scaled to shield_w by shield_h.
module shield2d() {
  sx = shield_w;
  sy = shield_h / shield_len;
  mid = shield_len / 2;
  o = shield_tip_round;
  c = shield_notch_round;
  offset(r = o) offset(r = -o) offset(r = -c) offset(r = c)
    polygon([for (p = concat(shield_right, shield_left)) [p[0] * sx, (mid - p[1]) * sy]]);
}

module outline2d(t) {
  if (is_drop(t)) drop2d();
  else if (is_shield(t)) shield2d();
  else circle(d = token_d);
}

// ---------- 2D faces ----------
module label(s, size)
  text(s, size = size, font = font, halign = "center", valign = "center");

module skull2d() {
  scale(skull_h / 8.4) difference() {
    union() {
      translate([0, 1.2]) circle(r = 3.6);
      translate([-2.2, -3.6]) offset(r = 0.6) offset(delta = -0.6) square([4.4, 3.4]);
    }
    for (x = [-1.45, 1.45]) translate([x, 1.0]) circle(r = 1.15);
    translate([0, -0.9]) polygon([[-0.6, -0.6], [0.6, -0.6], [0, 0.5]]);
    for (x = [-0.8, 0.8]) translate([x - 0.3, -3.8]) square([0.6, 1.5]);
  }
}

module face2d(t, side) {
  if (is_drop(t)) label(side == "top" ? "1" : "2", number_size);
  else if (is_shield(t)) translate([0, 0.10 * shield_h / shield_len]) label(letter_of(t), letter_size);
  else skull2d();
}

// ---------- 3D ----------
// Stepped chamfer top and bottom. Works for the concave shield outline,
// and the steps are finer than a print layer.
chamfer_steps = 4;
module body_solid(t) {
  s = chamfer / chamfer_steps;
  union() {
    for (i = [0 : chamfer_steps - 1]) {
      inset = chamfer - (i + 0.5) * s;
      translate([0, 0, i * s]) linear_extrude(s + eps) offset(r = -inset) outline2d(t);
      translate([0, 0, token_t - (i + 1) * s - eps]) linear_extrude(s + eps) offset(r = -inset) outline2d(t);
    }
    translate([0, 0, chamfer]) linear_extrude(token_t - 2 * chamfer) outline2d(t);
  }
}

// Bottom face is mirrored so it reads right after flipping along the long axis.
module inlay(t, e = 0) {
  translate([0, 0, token_t - inlay_depth]) linear_extrude(inlay_depth + e) face2d(t, "top");
  translate([0, 0, -e]) linear_extrude(inlay_depth + e) mirror([1, 0]) face2d(t, "bottom");
}

module token(t) {
  if (layer != "inlay") color(body_colour(t)) difference() { body_solid(t); inlay(t, eps); }
  if (layer != "body") color(inlay_colour(t)) inlay(t);
}

module plate(t) {
  n = count_of(t) * sets;
  b = bbox_of(t);
  cols = ceil(sqrt(n));
  for (i = [0 : n - 1])
    translate([(i % cols) * (b[0] + gap), floor(i / cols) * (b[1] + gap), 0])
      token(t);
}

// Top row: every type face up. Bottom row: flipped along the long axis.
module preview() {
  pitch = max(token_d, shield_w) + gap;
  row = token_d + tip_len + gap;
  for (i = [0 : len(types) - 1]) {
    translate([i * pitch, 0, 0]) token(types[i]);
    translate([i * pitch, -row, token_t]) rotate([0, 180, 0]) token(types[i]);
  }
}

if (part == "preview") preview();
else plate(part);
