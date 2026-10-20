// Integrated spool arm and threaded thimble, prototype 02. Units: mm.
// Uses the proven prototype-01 bore and the unchanged retaining screw.
// Native coordinates match the thimble/arm reference assembly; +Z is outward.
use <thimble.scad>

part = "arm"; // [arm, native, bore, section]
spindle_extension = 2;
arm_back_z = -2.4;
arm_face_z = 0.1;
original_seat_z = 11.5;
spindle_diameter = 11.5;
socket_fill_radius = 8.5;
root_fillet_radius = 0.4; // Maximum root OD 12.3 mm, inside the 13.3 mm reference hub.
$fn = 128;

new_seat_z = original_seat_z + spindle_extension;

assert(spindle_extension >= 0);
assert(spindle_diameter + 2*root_fillet_radius < 13.3);

module integrated_blank() {
    union() {
        import("reference/spool-arm.stl",convexity=10);
        // Remove the entire detachable interface by filling the socket,
        // including its locking grooves, through the arm's full thickness.
        translate([0,0,arm_back_z-0.01])
            cylinder(h=arm_face_z-arm_back_z+0.01,r=socket_fill_radius);
        // One continuous spindle merges into that solid backing. No key,
        // narrow neck or quarter-turn joint remains in the printed part.
        translate([0,0,arm_back_z-0.01])
            cylinder(h=new_seat_z-arm_back_z+0.01,d=spindle_diameter);
        // Small concave root fillet. It stays within the reel's hub bore,
        // so it does not consume the extra 2 mm of usable reel width.
        rotate_extrude() polygon(concat(
            [[0,arm_face_z-0.01],
             [spindle_diameter/2+root_fillet_radius,arm_face_z-0.01]],
            [for(a=[-90:-5:-180])
                [spindle_diameter/2+root_fillet_radius+root_fillet_radius*cos(a),
                 arm_face_z+root_fillet_radius+root_fillet_radius*sin(a)]],
            [[0,arm_face_z+root_fillet_radius]]));
    }
}

module integrated_bore() {
    // Translate the complete validated bore, collar and lead-in as a unit.
    // The same cap screws into the new position with identical engagement.
    translate([0,0,spindle_extension]) bore();
}

module integrated_arm_native() {
    intersection() {
        difference() { integrated_blank(); integrated_bore(); }
        // Snap the imported STL's -2.400000095 mm bottom to the exact bed
        // datum, avoiding microscopic coplanar cracks at the filled socket.
        translate([-20,-70,arm_back_z]) cube([180,90,40]);
    }
}

if (part == "arm") translate([0,0,-arm_back_z]) integrated_arm_native();
else if (part == "native") integrated_arm_native();
else if (part == "bore") integrated_bore();
else if (part == "section") intersection() {
    integrated_arm_native();
    translate([-15,0,-5]) cube([35,15,25]);
}
else assert(false,"Unknown part");
