// Continuous 4 mm spool arm and integrated thimble, prototype 04. Units: mm.
// Uses the proven prototype-01 bore and the unchanged retaining screw.
// Native coordinates match the thimble/arm reference assembly; +Z is outward.
use <thimble.scad>

part = "arm"; // [arm, native, bore, section]
spindle_extension = 1; // Usable reel space is 1 mm less than prototype 02.
arm_back_z = -2.4;
arm_face_z = 0.1;
reinforcement_height = 1.5; // Original 2.5 mm beam plus 1.5 mm = 4 mm throughout.
reinforcement_end = 116; // Overlap the diagonal tape guard; low beam ends at X=115.225.
original_seat_z = 11.5;
spindle_diameter = 11.5;
socket_fill_radius = 8.5;
root_fillet_radius = 0.4; // Maximum root OD 12.3 mm, inside the 13.3 mm reference hub.
$fn = 128;

reel_face_z = arm_face_z + reinforcement_height;
bore_shift = spindle_extension + reinforcement_height;
new_seat_z = original_seat_z + bore_shift;

assert(spindle_extension >= 0);
assert(spindle_diameter + 2*root_fillet_radius < 13.3);
assert(reinforcement_height >= 0);

module reinforcement() {
    intersection() {
        // Follow the existing beam outline just below its upper face. This
        // keeps the original notch and outline and adds no unsupported ledge.
        translate([0,0,arm_face_z-0.01])
            linear_extrude(reinforcement_height+0.01)
                union() {
                    projection(cut=true)
                        translate([0,0,-arm_face_z+0.01])
                            import("reference/spool-arm.stl",convexity=10);
                    circle(r=socket_fill_radius);
                }
        // Continue at full thickness into the guard, across its diagonal
        // junction. No ramp or thin neck. The taller guard remains intact.
        translate([-20,-70,arm_face_z-0.02])
            cube([reinforcement_end+20,90,reinforcement_height+0.03]);
    }
}

module integrated_blank() {
    union() {
        import("reference/spool-arm.stl",convexity=10);
        reinforcement();
        // Remove the entire detachable interface by filling the socket,
        // including its locking grooves, through the arm's full thickness.
        translate([0,0,arm_back_z-0.01])
            cylinder(h=arm_face_z-arm_back_z+0.01,r=socket_fill_radius);
        // One continuous spindle merges into that solid backing. No key,
        // narrow neck or quarter-turn joint remains in the printed part.
        translate([0,0,arm_back_z-0.01])
            cylinder(h=new_seat_z-arm_back_z+0.01,d=spindle_diameter);
        // Small concave root fillet. It stays within the reel's hub bore,
        // so it does not consume the specified usable reel width.
        rotate_extrude() polygon(concat(
            [[0,reel_face_z-0.01],
             [spindle_diameter/2+root_fillet_radius,reel_face_z-0.01]],
            [for(a=[-90:-5:-180])
                [spindle_diameter/2+root_fillet_radius+root_fillet_radius*cos(a),
                 reel_face_z+root_fillet_radius+root_fillet_radius*sin(a)]],
            [[0,reel_face_z+root_fillet_radius]]));
    }
}

module integrated_bore() {
    // Translate the complete validated bore, collar and lead-in as a unit.
    // The same cap screws into the new position with identical engagement.
    translate([0,0,bore_shift]) bore();
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
