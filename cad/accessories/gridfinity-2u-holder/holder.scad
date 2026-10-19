// Gridfinity four-slot cradle for 16 mm and 24 mm Opulo 2u feeders.
// Prototype 02. Millimeters; physical fit and motion remain untested.
// CERN-OHL-W-2.0, as in the repository root LICENSE.
// CAD source: opulo-inc/feeder 2u, e96d03cb3d28bcb62ed9e09e28752d2cbe735102.
$fn = 48;
slots = 4;
slot_pitch = 42;
grid_x = 5;
grid_y = 4;
grid_pitch = 42;
base_thickness = 9;
feeder_z = 69;
feeder_x = 15.5;
feeder_y = -13.25;
frame_y_center = 15.425;
front_slot_width = 32.45; // 30.85 mm frame plus 0.8 mm each side.
electronics_slot_width = 37.2; // Includes the board-side component envelope.
magnet_diameter = 6.5;
magnet_depth = 2.4;
magnet_holes = true;
labels = true;
render_part = "holder"; // "support" exports the rear frame seat at lane zero.
length = grid_x*grid_pitch-0.5;
width = grid_y*grid_pitch-0.5;
eps = 0.01;
assert(grid_x == 5 && grid_y == 4 && slots == 4);

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

module xz_prism(points,w) {
    // Extrude a side profile symmetrically across Y.
    rotate([90,0,0]) linear_extrude(w,center=true) polygon(points);
}

// Overall section in source-assembly X, shifted to center the 171 mm body.
module shell() {
    intersection() {
        xz_prism([
            [-length/2,base_thickness],[length/2,base_thickness],
            [length/2,25],[92.5,49],[54.5,49],[45.5,31],
            [5.5,31],[-18,65],[-80.5,65],[-86.5,85],
            [-89.5,85],[-91.5,25],[-length/2,25]
        ],width);
        translate([0,0,base_thickness-eps])
            linear_extrude(100) rounded_rectangle(length,width,3.75);
    }
}

module channel() {
    yc = feeder_y + frame_y_center;
    // Flat front housing seat at source Z=-30. The curved nose clears it.
    translate([-102+feeder_x,yc-front_slot_width/2,feeder_z-30])
        cube([68.5,front_slot_width,120]);
    // Open lead-ins continue upward to avoid a hidden ceiling at the stop.
    hull() {
        translate([-102+feeder_x,yc-front_slot_width/2,63.5])
            cube([68.5,front_slot_width,eps]);
        translate([-102+feeder_x,yc-front_slot_width/2-1,65.01])
            cube([68.5,front_slot_width+2,eps]);
    }
    translate([-102+feeder_x,yc-front_slot_width/2-1,65])
        cube([68.5,front_slot_width+2,120]);
    // Deep open space for the wide release lever and bottom PCB edge.
    translate([-33.5+feeder_x,-electronics_slot_width/2,base_thickness])
        cube([105.5,electronics_slot_width,150]);
}

module frame_support() {
    // Seat only on plastic, behind the PCB and beyond the release lever.
    // Source footprint X=40..66, Y=3..29; source contact surface Z=-40.
    w=26; d=26; c=0.6;
    translate([53+feeder_x,16+feeder_y,0]) {
        translate([0,0,base_thickness-eps])
            linear_extrude(feeder_z-40-c-base_thickness+eps)
                rounded_rectangle(w,d,1.2);
        hull() {
            slice(w,d,1.2,feeder_z-40-c-eps);
            slice(w-2*c,d-2*c,1.2-c,feeder_z-40-eps);
        }
    }
}

module holder() {
    union() {
        difference() {
            union() { printable_base(); shell(); }
            for(i=[0:slots-1])
                translate([0,(i-(slots-1)/2)*slot_pitch,0]) channel();
            if(magnet_holes)
                for(i=[0:grid_x-1],j=[0:grid_y-1],x=[-13,13],y=[-13,13])
                    translate([(i-(grid_x-1)/2)*grid_pitch+x,
                               (j-(grid_y-1)/2)*grid_pitch+y,0]) magnet_pocket();
            if(labels)
                for(i=[0:slots-1])
                    translate([-98,(i-(slots-1)/2)*slot_pitch,24.4])
                        rotate([0,0,-90]) linear_extrude(1)
                            text(str("16/24 - 0",i+1),size=4,
                                 halign="center",valign="center",font="Liberation Sans:style=Bold");
        }
        for(i=[0:slots-1])
            translate([0,(i-(slots-1)/2)*slot_pitch,0]) frame_support();
    }
}

if(render_part == "support") frame_support();
else holder();
