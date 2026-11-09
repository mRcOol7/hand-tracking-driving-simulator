"""Prototype and test realistic steering wheel rendering for Truck and Mustang GT."""

import os
import sys
import math
import numpy as np
import cv2

def rotate_pt(x, y, rad, cx, cy):
    """Rotate local (x, y) around (cx, cy) by angle in radians."""
    rx = x * math.cos(rad) - y * math.sin(rad)
    ry = x * math.sin(rad) + y * math.cos(rad)
    return int(cx + rx), int(cy + ry)

def draw_sport_wheel(img, cx, cy, angle_deg, radius=130):
    """Draw ultra-realistic Mustang GT / Racing flat-bottom steering wheel."""
    rad = math.radians(angle_deg)

    # 1. Outer Leather Rim with Flat Bottom
    # Build local coordinates for flat-bottom wheel:
    # Circle for top 240 degrees (from 30 deg to 150 deg flat bottom)
    pts_outer = []
    pts_inner = []
    rim_thick = 24
    flat_cutoff_y = int(radius * 0.76)  # Flattens bottom

    # Sweep 360 degrees in local space
    for deg in range(0, 360, 4):
        d_rad = math.radians(deg)
        local_x = radius * math.cos(d_rad)
        local_y = radius * math.sin(d_rad)

        # Flat bottom clamp
        if local_y > flat_cutoff_y:
            local_y = flat_cutoff_y

        inner_r = radius - rim_thick
        in_x = inner_r * math.cos(d_rad)
        in_y = inner_r * math.sin(d_rad)
        if in_y > flat_cutoff_y - rim_thick:
            in_y = flat_cutoff_y - rim_thick

        pts_outer.append(rotate_pt(local_x, local_y, rad, cx, cy))
        pts_inner.append(rotate_pt(in_x, in_y, rad, cx, cy))

    # Rim drop shadow
    shadow_offset = 6
    pts_shadow = [(p[0] + 2, p[1] + shadow_offset) for p in pts_outer]
    cv2.polylines(img, [np.array(pts_shadow, np.int32)], True, (12, 12, 12), 10, cv2.LINE_AA)

    # Fill Rim Polygon (Outer and Inner)
    rim_poly = pts_outer + pts_inner[::-1]
    cv2.fillPoly(img, [np.array(rim_poly, np.int32)], (38, 38, 42), cv2.LINE_AA)

    # Draw outer rim leather texture / edge highlight
    cv2.polylines(img, [np.array(pts_outer, np.int32)], True, (65, 65, 70), 2, cv2.LINE_AA)
    cv2.polylines(img, [np.array(pts_inner, np.int32)], True, (80, 80, 85), 2, cv2.LINE_AA)

    # 2. Ergonomic 10-and-2 Contoured Thumb Rests (Swelled grips)
    for thumb_ang in [-138, -42]:
        t_rad = math.radians(thumb_ang)
        tx = (radius - rim_thick // 2) * math.cos(t_rad)
        ty = (radius - rim_thick // 2) * math.sin(t_rad)
        pt = rotate_pt(tx, ty, rad, cx, cy)
        cv2.circle(img, pt, 14, (32, 32, 35), -1, cv2.LINE_AA)
        cv2.circle(img, pt, 14, (100, 100, 110), 1, cv2.LINE_AA)
        # Thumb grip stitching lines
        for s_off in [-4, 0, 4]:
            st1 = rotate_pt(tx + s_off, ty - 8, rad, cx, cy)
            st2 = rotate_pt(tx + s_off, ty + 8, rad, cx, cy)
            cv2.line(img, st1, st2, (18, 18, 20), 1, cv2.LINE_AA)

    # 3. Metallic 3-Spoke Assembly (Left, Right, Bottom) with Weight-Reduction Cutouts
    hub_r = 38
    spoke_angles = [180, 0, 90]
    spoke_w_inner = 24
    spoke_w_outer = 32

    for sang in spoke_angles:
        s_rad = math.radians(sang)
        # Normal perpendicular vector
        nx = -math.sin(s_rad)
        ny = math.cos(s_rad)
        # Direction vector
        dx = math.cos(s_rad)
        dy = math.sin(s_rad)

        r_out = radius - rim_thick
        if sang == 90:
            r_out = flat_cutoff_y - rim_thick

        # 4 corners of spoke polygon
        p1 = rotate_pt(hub_r * dx + (spoke_w_inner / 2) * nx, hub_r * dy + (spoke_w_inner / 2) * ny, rad, cx, cy)
        p2 = rotate_pt(hub_r * dx - (spoke_w_inner / 2) * nx, hub_r * dy - (spoke_w_inner / 2) * ny, rad, cx, cy)
        p3 = rotate_pt(r_out * dx - (spoke_w_outer / 2) * nx, r_out * dy - (spoke_w_outer / 2) * ny, rad, cx, cy)
        p4 = rotate_pt(r_out * dx + (spoke_w_outer / 2) * nx, r_out * dy + (spoke_w_outer / 2) * ny, rad, cx, cy)

        # Brushed gunmetal spoke body
        spoke_poly = np.array([p1, p2, p3, p4], np.int32)
        cv2.fillPoly(img, [spoke_poly], (65, 65, 72), cv2.LINE_AA)
        cv2.polylines(img, [spoke_poly], True, (160, 160, 175), 2, cv2.LINE_AA)

        # Machined weight-reduction cutouts (speed slots)
        mid_r = (hub_r + r_out) / 2.0
        hole_pt = rotate_pt(mid_r * dx, mid_r * dy, rad, cx, cy)
        cv2.circle(img, hole_pt, 7, (20, 20, 22), -1, cv2.LINE_AA)
        cv2.circle(img, hole_pt, 7, (120, 120, 130), 1, cv2.LINE_AA)

    # 4. Center Hub & Momo/Mustang Allen Bolts
    cv2.circle(img, (cx, cy), hub_r + 3, (25, 25, 28), -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), hub_r, (85, 85, 95), 3, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), hub_r - 4, (40, 40, 45), -1, cv2.LINE_AA)

    # 6 Allen hex bolts around hub perimeter
    for b_deg in range(0, 360, 60):
        b_rad = math.radians(b_deg)
        bx = (hub_r - 9) * math.cos(b_rad)
        by = (hub_r - 9) * math.sin(b_rad)
        b_pt = rotate_pt(bx, by, rad, cx, cy)
        cv2.circle(img, b_pt, 3, (190, 190, 200), -1, cv2.LINE_AA)
        cv2.circle(img, b_pt, 1, (40, 40, 40), -1, cv2.LINE_AA)

    # Mustang GT Center Horn Button Emblem
    emblem_r = 18
    cv2.circle(img, (cx, cy), emblem_r, (20, 20, 22), -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), emblem_r, (0, 180, 255), 2, cv2.LINE_AA)
    # Red & Silver GT center badge
    cv2.putText(img, "GT", (cx - 10, cy + 5), cv2.FONT_HERSHEY_DUPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)

    # 5. Top 12 O'Clock Racing Alignment Stripe (Mustang Race Red + Pinstripes)
    top_deg = -90
    for offset_ang, width, color in [(-90, 8, (255, 255, 255)), (-90, 5, (30, 30, 230))]:
        t_rad = math.radians(offset_ang)
        p_top_out = rotate_pt(radius * math.cos(t_rad), radius * math.sin(t_rad), rad, cx, cy)
        p_top_in = rotate_pt((radius - rim_thick) * math.cos(t_rad), (radius - rim_thick) * math.sin(t_rad), rad, cx, cy)
        cv2.line(img, p_top_out, p_top_in, color, width, cv2.LINE_AA)


def draw_truck_wheel(img, cx, cy, angle_deg, radius=130):
    """Draw classic American heavy-duty semi-truck wheel (Peterbilt / Kenworth style)."""
    rad = math.radians(angle_deg)
    rim_thick = 22

    # Drop shadow
    cv2.circle(img, (cx + 2, cy + 6), radius, (15, 15, 18), 12, cv2.LINE_AA)

    # Outer Rim - Deep commercial charcoal / woodgrain
    cv2.circle(img, (cx, cy), radius, (50, 45, 40), rim_thick, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), radius + rim_thick // 2, (75, 70, 65), 2, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), radius - rim_thick // 2, (90, 85, 80), 2, cv2.LINE_AA)

    # 4 Heavy-duty Commercial Spokes (Cruiser layout: 35°, 145°, 215°, 325°)
    hub_r = 40
    spoke_angles = [35, 145, 215, 325]
    for sang in spoke_angles:
        s_rad = math.radians(sang)
        dx = math.cos(s_rad)
        dy = math.sin(s_rad)
        p_in = rotate_pt(hub_r * dx, hub_r * dy, rad, cx, cy)
        p_out = rotate_pt((radius - rim_thick // 2) * dx, (radius - rim_thick // 2) * dy, rad, cx, cy)
        # Chrome spoke body
        cv2.line(img, p_in, p_out, (180, 180, 190), 8, cv2.LINE_AA)
        cv2.line(img, p_in, p_out, (230, 230, 240), 3, cv2.LINE_AA)

    # Chrome Center Hub with Commercial Truck Horn Cap
    cv2.circle(img, (cx, cy), hub_r, (160, 160, 170), -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), hub_r, (240, 240, 250), 3, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), hub_r - 8, (35, 35, 40), -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), hub_r - 8, (190, 190, 200), 2, cv2.LINE_AA)

    # ATS Commercial Eagle / Truck Star in center
    cv2.circle(img, (cx, cy), 14, (0, 180, 255), -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), 14, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(img, "ATS", (cx - 13, cy + 4), cv2.FONT_HERSHEY_DUPLEX, 0.40, (0, 0, 0), 1, cv2.LINE_AA)

    # 12 o'clock center bead
    top_pt = rotate_pt(0, -radius, rad, cx, cy)
    cv2.circle(img, top_pt, 7, (0, 200, 255), -1, cv2.LINE_AA)
    cv2.circle(img, top_pt, 7, (255, 255, 255), 1, cv2.LINE_AA)


def test_render():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    for y in range(720):
        frame[y, :] = (int(25 + 15 * (y / 720)), int(22 + 10 * (y / 720)), int(20 + 8 * (y / 720)))

    # Draw both side by side: Truck Wheel on Left (turned +25 deg), Mustang GT Wheel on Right (turned -30 deg)
    draw_truck_wheel(frame, 380, 400, angle_deg=25.0)
    cv2.putText(frame, "HEAVY TRUCK WHEEL (ATS / ETS2)", (220, 580), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2, cv2.LINE_AA)

    draw_sport_wheel(frame, 900, 400, angle_deg=-30.0)
    cv2.putText(frame, "MUSTANG GT FLAT-BOTTOM RACING WHEEL", (690, 580), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 120), 2, cv2.LINE_AA)

    out_path = r"C:\Users\HP\.gemini\antigravity\brain\5e1151db-2f88-4861-83e2-3f9dc398caed\realistic_steering_wheels_preview.jpg"
    cv2.imwrite(out_path, frame)
    print(f"Saved preview to: {out_path}")

if __name__ == "__main__":
    test_render()
