// Five 8 mm LumenPnP feeders on a 5 x 3 Gridfinity footprint.
// Prototype 06 — millimeters; print feet-down, validate physical fit.
// Hardware license: CERN-OHL-W-2.0, as in the repository root LICENSE.
// Axes match cad/assembly-8.FCStd: X along feeder, Y across slots, Z up.
$fn = 48;

slots = 5;
slot_pitch = 24;
grid_x = 5;
grid_y = 3;
grid_pitch = 42;
// Raise every feeder contact together; retain the 9 mm floor and foot profile.
reel_lift = 10;
body_lift = 2 + reel_lift;
base_thickness = 9;
feeder_z = 67 + body_lift;
// Reference reel: 180 mm OD assumed until measured; repository reel is 177 mm.
// Axle X/Z follow the saved assembly thimble center. Y is relative to a lane.
reel_diameter = 180;
reel_width = 12;
reel_axle_x = -179.9;
// Place the inner flange 0.15 mm away from the arm face at local Y = 3.15.
reel_axle_y = 3.0-reel_width/2;
reel_axle_z = feeder_z + 30.5;
reel_radial_clearance = 4; // Doubled rear relief for reel size variation.
front_slot_width = 16.4; // 15 mm frame + 0.7 mm each side
rear_slot_width = 14;   // 11.5 mm arm + clearance
electronics_slot_width = 22; // 2 mm dividers at 24 mm pitch
magnet_holes = true;
magnet_diameter = 6.5;
magnet_depth = 2.4;
labels = true;
// Flat frame underside behind the lower PCB corner, right of the lever
// when viewed from the PCB side. Local Y is relative to the slot center.
frame_support_x = [-49,-38];
frame_support_y = [-6.5,5];
frame_support_z = feeder_z-40;
// Other exports: "support", "reel_reference" and "parameters".
render_part = "holder";

length = grid_x*grid_pitch - 0.5;
width = grid_y*grid_pitch - 0.5;
eps = 0.01;
assert(grid_x == 5, "This first cradle profile uses a five-cell length.");
assert(slot_pitch-electronics_slot_width >= 2,
       "Keep at least 2 mm between electronics pockets.");
assert((slots-1)*slot_pitch + electronics_slot_width < width-6,
       "Increase grid_y or reduce slot count: keep at least 3 mm outer walls.");

module rounded_rectangle(w,d,r) {
    hull() for(x=[-w/2+r,w/2-r],y=[-d/2+r,d/2-r])
        translate([x,y]) circle(r=r);
}

module slice(w,d,r,z) {
    translate([0,0,z]) linear_extrude(eps) rounded_rectangle(w,d,r);
}

module foot() {
    // Standard Gridfinity bin foot: 0.8 / 1.8 / 2.15 mm profile.
    hull() { slice(35.6,35.6,0.8,0); slice(37.2,37.2,1.6,0.8); }
    hull() { slice(37.2,37.2,1.6,0.8); slice(37.2,37.2,1.6,2.6); }
    hull() { slice(37.2,37.2,1.6,2.6); slice(41.5,41.5,3.75,4.75); }
}

module printable_base() {
    intersection() {
        union() {
            for (i=[0:grid_x-1],j=[0:grid_y-1])
                translate([(i-(grid_x-1)/2)*grid_pitch,
                           (j-(grid_y-1)/2)*grid_pitch,0]) {
                    foot();
                    // Above the standard 4.75 mm mating profile, expand each
                    // rounded foot at 45 degrees until adjacent roofs meet.
                    // Their union forms pointed vaults instead of bridge decks.
                    rise = base_thickness-4.75;
                    hull() {
                        slice(41.5,41.5,3.75,4.75);
                        slice(41.5+2*rise,41.5+2*rise,3.75+rise,
                              base_thickness);
                    }
                }
        }
        linear_extrude(base_thickness)
            rounded_rectangle(length,width,3.75);
    }
}

module magnet_pocket() {
    translate([0,0,-eps]) cylinder(d=magnet_diameter,h=magnet_depth+eps);
    // A conical 45-degree roof closes gradually; no horizontal hole ceiling.
    translate([0,0,magnet_depth])
        cylinder(d1=magnet_diameter,d2=0,h=magnet_diameter/2);
}

module reel_relief() {
    // Remove the lower reel envelope across the rear, including divider tips.
    // This is an open top scallop. Its surface faces upward, not an overhang.
    translate([reel_axle_x,0,reel_axle_z]) rotate([90,0,0])
        cylinder(r=reel_diameter/2+reel_radial_clearance,
                 h=width+2,center=true,$fn=256);
}

module reel_reference() {
    // Conservative annular envelope, not a printable reel design.
    translate([reel_axle_x,reel_axle_y,reel_axle_z]) rotate([90,0,0])
        difference() {
            cylinder(d=reel_diameter,h=reel_width,center=true,$fn=256);
            cylinder(d=13.3,h=reel_width+2,center=true,$fn=96);
        }
}

module xz_prism(points,w) {
    // Extrude a side profile symmetrically across Y.
    rotate([90,0,0]) linear_extrude(w,center=true) polygon(points);
}

module shell() {
    // Low central rails expose the latch/PCB pocket; raised ends guide plastic.
    intersection() {
        xz_prism([
            [-length/2,base_thickness], [length/2,base_thickness],
            [length/2,29+body_lift], [95,29+body_lift],
            [91,80+body_lift], [88,80+body_lift], [84,65+body_lift],
            [15,65+body_lift], [7,31+body_lift], [-70,31+body_lift],
            [-78,58.1+body_lift], [-length/2,68.2+body_lift]
        ], width);
        translate([0,0,base_thickness-eps])
            linear_extrude(100) rounded_rectangle(length,width,3.75);
    }
}

module channel() {
    // The front housing rests on its flat underside at source Z = -20.
    translate([14,-front_slot_width/2,feeder_z-20])
        cube([74,front_slot_width,100]);
    // 0.8 mm lead-in chamfers along the top of the front channel.
    hull() {
        translate([14,-front_slot_width/2,63.8+body_lift]) cube([74,front_slot_width,eps]);
        translate([14,-front_slot_width/2-0.8,65.01+body_lift]) cube([74,front_slot_width+1.6,eps]);
    }
    // Carry the flared entrance all the way through the tall nose stop.
    // Ending the flare below that stop would leave a downward-facing ledge.
    translate([14,-front_slot_width/2-0.8,65+body_lift])
        cube([74,front_slot_width+1.6,100]);
    // Open top and bottom clearance around the board, latch, gears and wiring.
    translate([-78,-electronics_slot_width/2,base_thickness])
        cube([92,electronics_slot_width,110]);
    // Ramp follows the arm underside over X -105..-78. It remains open-ended.
    // z = 16.66 - 0.3756*x at feeder_z=67: sampled CAD minus 0.1 mm.
    xz_prism([
        [-length/2-1,feeder_z-50.34-0.3756*(-length/2-1)],
        [-78,feeder_z-50.34-0.3756*(-78)], [-78,130],[-length/2-1,130]
    ], rear_slot_width);
}

module cradle_without_frame_support() {
    difference() {
        union() {
            printable_base();
            shell();
        }
        for (i=[0:slots-1]) translate([0,(i-(slots-1)/2)*slot_pitch,0]) channel();
        reel_relief();
        if (magnet_holes)
            for (i=[0:grid_x-1],j=[0:grid_y-1],x=[-13,13],y=[-13,13])
                translate([(i-(grid_x-1)/2)*grid_pitch+x,(j-(grid_y-1)/2)*grid_pitch+y,0])
                    magnet_pocket();
        if (labels)
            for (i=[0:slots-1])
                translate([98,(i-(slots-1)/2)*slot_pitch,28.4+body_lift])
                    rotate([0,0,90]) linear_extrude(1)
                        text(str("0",i+1),size=5,halign="center",valign="center",font="Liberation Sans:style=Bold");
    }
}

module frame_support() {
    w = frame_support_x[1]-frame_support_x[0];
    d = frame_support_y[1]-frame_support_y[0];
    c = 0.6;
    translate([(frame_support_x[0]+frame_support_x[1])/2,
               (frame_support_y[0]+frame_support_y[1])/2,0]) {
        translate([0,0,base_thickness-eps])
            linear_extrude(frame_support_z-c-base_thickness+eps)
                rounded_rectangle(w,d,1);
        hull() {
            slice(w,d,1,frame_support_z-c-eps);
            slice(w-2*c,d-2*c,1-c,frame_support_z-eps);
        }
    }
}

module holder() {
    union() {
        cradle_without_frame_support();
        // Add after pocket subtraction; each boss joins the pocket floor.
        for (i=[0:slots-1])
            translate([0,(i-(slots-1)/2)*slot_pitch,0]) frame_support();
    }
}

if (render_part == "parameters")
    echo([slots,slot_pitch,length,width,80+body_lift,feeder_z,
          base_thickness,31+body_lift,reel_lift,reel_diameter,reel_width,
          reel_axle_x,reel_axle_y,reel_axle_z,reel_radial_clearance]);
else if (render_part == "reel_reference") reel_reference();
else if (render_part == "support") frame_support();
else holder();
