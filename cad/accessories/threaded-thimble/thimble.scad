// Threaded reel-retaining thimble, prototype 01. Units: mm.
// The native datum matches cad/FDM/thimble.FCStd. Axis +Z points away
// from the spool arm; the original quarter-turn key occupies Z=-2.5..0.
// Both exported parts are already oriented on Z=0 for printing.
part = "thimble"; // [thimble, screw, assembly, section, male, female, body-native]

head_diameter = 30;
head_thickness = 3;
shaft_diameter = 11.5;
seat_z = 11.5;               // Preserve the original lip's inner contact plane.
key_depth = 2.5;
bore_cone_tip_z = 0.08;     // Conical roof when printed mouth-down.
stem_length = 8.0;
thread_diameter = 8.0;       // Custom profile; NOT an ISO M8 thread.
thread_pitch = 2.0;          // Single-start, right-hand.
thread_depth = 0.65;         // Radial: 6.7 mm minor diameter.
thread_crest = 0.4;
thread_flank = 0.7;          // 43 degree flank from the vertical print axis.
radial_clearance = 0.25;     // Normal fit: 0.50 mm diametral clearance.
locking_interference = 0.08;// Nominal elastic radial compression at the tip.
pilot_length = 1.5;         // Smooth split pilot below the load-bearing threads.
locking_collar_top_z = 4.8;
split_width = 1.0;
split_end_z = 9.5;          // Four flexible fingers; 2 mm solid neck at head.

angular_steps = 128;
steps_per_pitch = 80;
$fn = 128;
eps = 0.01;

assert(head_diameter > shaft_diameter);
assert(seat_z-stem_length > bore_cone_tip_z+thread_diameter/2-thread_depth-locking_interference);
assert(thread_crest+2*thread_flank < thread_pitch);
assert((shaft_diameter-thread_diameter)/2-radial_clearance >= 1.4);
assert(locking_interference >= 0 && locking_interference <= 0.15);
assert(radial_clearance >= 0.15);

function clamp(v,a,b) = min(b,max(a,v));
function phase_distance(z,a) =
    let(t=z-thread_pitch*a/360)
    abs(t-thread_pitch*floor(t/thread_pitch+0.5));
function thread_radius(z,a) =
    thread_diameter/2-thread_depth*
    clamp((phase_distance(z,a)-thread_crest/2)/thread_flank,0,1);
function pilot_radius() = thread_diameter/2-thread_depth;
function female_radius(z,a) = min(thread_radius(z,a)+radial_clearance,
    pilot_radius()-locking_interference+max(0,z-locking_collar_top_z),
    max(0,z-bore_cone_tip_z));
function male_radius(z,a) = min(thread_radius(z,a),
    // Smooth pilot, a small nose chamfer, then a 45 degree thread lead-in.
    pilot_radius()-0.3+max(0,z-(seat_z-stem_length)),
    pilot_radius()+max(0,z-(seat_z-stem_length+pilot_length)));

// Closed, radially sampled helical solid. Female uses the same phase and
// profile as male plus radial clearance, so mating geometry is explicit.
// Each end is capped with a fan; no coincident overlapping thread strips.
module threaded_solid(z0,z1,female=false) {
    n=angular_steps;
    layers=ceil((z1-z0)/thread_pitch*steps_per_pitch);
    first=female ? 1 : 0; // A single apex, not 128 coincident cone-tip vertices.
    rings=layers-first+1;
    points=concat(
        [for (j=[first:layers],i=[0:n-1])
            let(z=z0+(z1-z0)*j/layers,a=i*360/n,
                r=female ? female_radius(z,a) : male_radius(z,a))
            [r*cos(a),r*sin(a),z]],
        [[0,0,z0],[0,0,z1]]);
    bottom=rings*n;
    top=bottom+1;
    faces=concat(
        [for(j=[0:rings-2],i=[0:n-1])
            [j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n]],
        [for(j=[0:rings-2],i=[0:n-1])
            [j*n+i,(j+1)*n+(i+1)%n,(j+1)*n+i]],
        [for(i=[0:n-1]) [bottom,(i+1)%n,i]],
        [for(i=[0:n-1]) [top,(rings-1)*n+i,(rings-1)*n+(i+1)%n]]);
    // OpenSCAD expects clockwise face winding when viewed from outside.
    polyhedron(points,[for(f=faces) [f[2],f[1],f[0]]],convexity=16);
}

module original_shoulder() {
    // Original D-shaped upper face of the mounting groove. The key and
    // this shoulder together locate and capture the spool arm.
    intersection() {
        circle(r=5);
        translate([-6,-3]) square([12,10]);
    }
}

module body_blank() {
    union() {
        import("reference/quarter-turn-mount.stl",convexity=6);
        // Preserve the original upper mounting shoulder at native Z=0.
        // Mouth-down printing puts this face on top of its supporting body.
        hull() {
            translate([0,0,0.5]) linear_extrude(0.02) original_shoulder();
            translate([0,0,3.25]) cylinder(h=0.02,d=shaft_diameter);
        }
        translate([0,0,3.25]) cylinder(h=seat_z-3.25,d=shaft_diameter);
    }
}

module bore() {
    // A 45 degree conical roof closes entirely ABOVE the original key.
    threaded_solid(bore_cone_tip_z,seat_z+0.15,true);
    // Entry chamfer and phase-free lead-in at the mouth.
    translate([0,0,seat_z-1.05])
        cylinder(h=1.05+eps,r1=thread_diameter/2-thread_depth+radial_clearance,
                 r2=thread_diameter/2+radial_clearance+0.35);
}

module thimble_native() { difference() { body_blank(); bore(); } }

module split_cut() {
    // Rounded slot termination distributes bending at each finger's root.
    union() {
        translate([-split_width/2,-8,seat_z-stem_length-1])
            cube([split_width,16,split_end_z-split_width/2-(seat_z-stem_length)+1]);
        translate([0,0,split_end_z-split_width/2]) rotate([90,0,0])
            cylinder(h=16,r=split_width/2,center=true,$fn=32);
    }
}

module screw_native() {
    union() {
        difference() {
            threaded_solid(seat_z-stem_length,seat_z+eps);
            split_cut();
            rotate([0,0,90]) split_cut();
        }
        // A flat central shoulder bottoms against the thimble, leaving
        // the reel free. Rim chamfers and shallow scallops aid hand grip.
        difference() {
            translate([0,0,seat_z]) rotate_extrude()
                polygon([[0,0],[head_diameter/2-0.3,0],
                    [head_diameter/2,0.3],[head_diameter/2,head_thickness-0.3],
                    [head_diameter/2-0.3,head_thickness],[0,head_thickness]]);
            for (a=[15:30:345]) rotate([0,0,a])
                translate([head_diameter/2+1.9,0,seat_z-eps])
                    cylinder(h=head_thickness+2*eps,r=2.4,$fn=48);
        }
    }
}

if (part=="thimble") translate([0,0,seat_z]) rotate([180,0,0]) thimble_native();
else if (part=="screw") translate([0,0,seat_z+head_thickness])
    rotate([180,0,0]) screw_native();
else if (part=="body-native") thimble_native();
else if (part=="male") threaded_solid(seat_z-stem_length,seat_z);
else if (part=="female") bore();
else if (part=="assembly") {
    color("Teal") thimble_native(); color("Orange") screw_native();
}
else if (part=="section") intersection() {
    union() { thimble_native(); screw_native(); }
    translate([-20,0,-5]) cube([40,20,30]);
}
else assert(false,"Unknown part");
