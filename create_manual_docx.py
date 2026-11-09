"""
create_manual_docx.py
Generates a complete, professional, beautifully styled Word Document (.docx)
User Manual for ATS Visual Hand-Tracking Steering Wheel.
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOCX_OUTPUT_PATH = r"E:\ats-hand-steering\ATS_Visual_Driving_User_Manual.docx"
IMAGES_DIR = r"E:\ats-hand-steering\images"

def set_cell_background(cell, fill_hex):
    """Sets the background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=140, bottom=140, left=200, right=200):
    """Sets internal padding for a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_callout_box(doc, text_lines, title="PRO TIP", bg_hex="EBF3FA", border_hex="1B365D"):
    """Adds a stylish callout box with a colored left border."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=160, bottom=160, left=240, right=240)
    
    # Left border only
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="32" w:space="0" w:color="{border_hex}"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    run_title = p.add_run(f"[{title}] ")
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    run_title.font.size = Pt(10.5)
    
    for i, line in enumerate(text_lines):
        if i > 0:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
        run = p.add_run(line)
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    
    # spacing after table
    post_p = doc.add_paragraph()
    post_p.paragraph_format.space_after = Pt(6)

def add_image_figure(doc, img_path, caption_text, width=Inches(5.4)):
    """Inserts a centered image with a styled caption."""
    if os.path.exists(img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(3)
        p_img.add_run().add_picture(img_path, width=width)
        
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(12)
        run_cap = p_cap.add_run(caption_text)
        run_cap.font.size = Pt(9.5)
        run_cap.font.italic = True
        run_cap.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    else:
        print(f"Warning: Image file not found: {img_path}")

def build_user_manual():
    doc = Document()
    
    # Page setup - 0.8 inch margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.8)
        s.bottom_margin = Inches(0.8)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)
    
    # Color palette
    NAVY = RGBColor(0x1B, 0x36, 0x5D)
    SLATE = RGBColor(0x4B, 0x6B, 0x94)
    TEXT_DARK = RGBColor(0x22, 0x22, 0x22)
    GREEN = RGBColor(0x2E, 0x7D, 0x32)
    
    # Document Header Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(2)
    run_title = p_title.add_run("AMERICAN TRUCK SIMULATOR")
    run_title.font.name = "Segoe UI"
    run_title.font.size = Pt(26)
    run_title.font.bold = True
    run_title.font.color.rgb = NAVY
    
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(8)
    run_sub = p_sub.add_run("AI Visual Hand-Tracking Steering Wheel | Complete User Manual")
    run_sub.font.name = "Segoe UI"
    run_sub.font.size = Pt(14)
    run_sub.font.bold = True
    run_sub.font.color.rgb = SLATE
    
    # Subtitle meta line
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(16)
    run_meta = p_meta.add_run("Zero Installation Required  *  Plug-and-Play Portable Edition  *  Full 900° Rotation  *  Phone Webcam Ready")
    run_meta.font.name = "Segoe UI"
    run_meta.font.size = Pt(9.5)
    run_meta.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
    
    # Horizontal rule
    hr = doc.add_paragraph()
    hr.paragraph_format.space_after = Pt(14)
    hr_run = hr.add_run("-" * 72)
    hr_run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    
    # SECTION 1: QUICK START
    h1 = doc.add_heading(level=1)
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(6)
    r1 = h1.add_run("1. Quick Start in 60 Seconds (Zero Tech Hassle)")
    r1.font.color.rgb = NAVY
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.add_run("Welcome to your virtual driving cockpit! This software turns any ordinary webcam or smartphone camera into an ultra-precise, enterprise-grade truck steering wheel. You ")
    r_bold = p.add_run("do NOT need to install Python, drivers, or any programming software.")
    r_bold.font.bold = True
    p.add_run(" Everything is pre-bundled and configured to run straight out of the folder.")
    
    steps = [
        ("Step 1: Extract the Zip File", "Extract the downloaded 'ATS_Hand_Steering_Portable.zip' folder anywhere on your computer (for example, on your Desktop)."),
        ("Step 2: Double-Click 'run.bat'", "Inside the extracted folder, double-click the file named 'run.bat'. A tracking camera window with a futuristic HUD steering wheel and digital gauges will immediately pop up!"),
        ("Step 3: Launch American Truck Simulator", "Open ATS. The game automatically recognizes your hand movements as a smooth, real Xbox 360 controller."),
        ("No ATS installed yet?", "No problem! Simply double-click 'play_demo.bat' to test drive an interactive 3D Highway Truck Simulation right on your laptop screen!")
    ]
    
    for title, desc in steps:
        sp = doc.add_paragraph()
        sp.paragraph_format.space_before = Pt(3)
        sp.paragraph_format.space_after = Pt(3)
        sp.paragraph_format.left_indent = Inches(0.25)
        st_run = sp.add_run(f"•  {title}: ")
        st_run.font.bold = True
        st_run.font.color.rgb = NAVY
        sp.add_run(desc)
        
    add_callout_box(doc, [
        "First-time controller setup: If this is the very first time running the virtual controller, double-click 'install_gamepad_driver.bat' to install the official Windows ViGEmBus controller driver. It only takes 5 seconds and only needs to be done once."
    ], title="ONE-TIME DRIVER TIP")
    
    # SECTION 2: GESTURES GUIDE
    h2 = doc.add_heading(level=1)
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(6)
    r2 = h2.add_run("2. Visual Hand Gestures Guide (Drive Like a Real Trucker)")
    r2.font.color.rgb = NAVY
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(8)
    p.add_run("Sit comfortably about 1.5 to 3 feet in front of your camera. Raise both hands into the air as if holding a real 14-inch truck steering wheel. The AI will instantly lock onto your hands and draw responsive neon tracking rings around them.")

    # Steering Subsection
    h2_sub1 = doc.add_heading(level=2)
    h2_sub1.paragraph_format.space_before = Pt(8)
    h2_sub1.paragraph_format.space_after = Pt(4)
    r = h2_sub1.add_run("A. Steering & 900° Hand-Over-Hand Rotation")
    r.font.color.rgb = SLATE

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.add_run("•  ")
    p.add_run("Turn Left: ").font.bold = True
    p.add_run("Lower your left hand and raise your right hand. Your truck smoothly steers to the left.\n")
    p.add_run("•  ")
    p.add_run("Turn Right: ").font.bold = True
    p.add_run("Lower your right hand and raise your left hand. Your truck smoothly steers to the right.\n")
    p.add_run("•  ")
    p.add_run("Full 900° Enterprise Wheel Rotation: ").font.bold = True
    p.add_run("Unlike basic webcams that break when hands cross over, our Polar Tangential Torque Engine allows you to fully rotate hands 180°, 360°, and even perform hand-over-hand hairpin turns smoothly!")

    add_image_figure(doc, os.path.join(IMAGES_DIR, "gesture_steering.jpg"),
                     "Figure 1: Natural Steering Grip & Full Hand-Over-Hand Continuous Wheel Rotation")

    # Pedals Subsection
    h2_sub2 = doc.add_heading(level=2)
    h2_sub2.paragraph_format.space_before = Pt(10)
    h2_sub2.paragraph_format.space_after = Pt(4)
    r = h2_sub2.add_run("B. Dynamic Pedals (Pinch to Accelerate & Brake)")
    r.font.color.rgb = SLATE

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.add_run("You don't need physical floor pedals! Use intuitive finger pinches (bringing your thumb tip and index fingertip together):")

    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(4)
    p.add_run("1.  ")
    r_gas = p.add_run("Right Hand Pinch = GAS (Accelerator): ")
    r_gas.font.bold = True
    r_gas.font.color.rgb = GREEN
    p.add_run("Pinch your right thumb and index finger together. The closer your fingers touch, the more throttle your truck delivers (0% to 100% analog response). Open your fingers to release the gas pedal.")

    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(6)
    p.add_run("2.  ")
    r_brk = p.add_run("Left Hand Pinch = BRAKE / REVERSE: ")
    r_brk.font.bold = True
    r_brk.font.color.rgb = RGBColor(0xC0, 0x20, 0x20)
    p.add_run("Pinch your left thumb and index finger together. Your truck firmly applies the brakes. When stopped, holding this pinch engages reverse gear.")

    add_image_figure(doc, os.path.join(IMAGES_DIR, "gesture_pedals_pinch.jpg"),
                     "Figure 2: Analog Throttle & Brake Pedals via Micro-Pinch Gesture")

    # Transmission Shifting & Physical Controller Subsection
    h2_sub3 = doc.add_heading(level=2)
    h2_sub3.paragraph_format.space_before = Pt(10)
    h2_sub3.paragraph_format.space_after = Pt(4)
    r = h2_sub3.add_run("C. Transmission Shifting (Drive, Reverse, Neutral) & Physical Xbox Controller")
    r.font.color.rgb = SLATE

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.add_run("•  ")
    p.add_run("Shift into DRIVE [D] (1st Gear): ").font.bold = True
    p.add_run("Push your right hand forward toward the screen. The system pulses Button A (Shift Up) directly to ATS, engaging forward gear with green HUD feedback!\n")
    p.add_run("•  ")
    p.add_run("Shift into REVERSE [R]: ").font.bold = True
    p.add_run("Pull your left hand downward. The system pulses Button X (Shift Down) into ATS, engaging Reverse gear.\n")
    p.add_run("•  ")
    p.add_run("Shift into NEUTRAL [N]: ").font.bold = True
    p.add_run("Press key [N] on your keyboard to instantly select Neutral transmission.\n")
    p.add_run("•  ")
    p.add_run("Simultaneous Physical Xbox Controller Pass-Through: ").font.bold = True
    p.add_run("You can plug in your physical Xbox controller at any time! Hand tracking steers the vehicle (Left Stick X), while your physical controller's analog triggers (RT/LT for Gas/Brake), right thumbstick (camera look around), and buttons merge simultaneously into ATS without any driver conflicts!\n")
    p.add_run("•  ")
    p.add_run("Eliminating Xbox Device Name Conflicts (DualShock 4 Mode - Key [G]): ").font.bold = True
    p.add_run("When both a physical Xbox controller and a virtual controller are active, Windows normally names both 'Controller (XBOX 360)'. By default, the software now emulates a Sony DualShock 4 ('Wireless Controller'). This gives the physical controller and virtual hand wheel completely distinct names, so games can bind to both simultaneously without confusion! Press [G] anytime to toggle between DualShock 4 and Xbox 360 mode.")

    # Sports Car / Mustang GT Subsection
    h2_sub4 = doc.add_heading(level=2)
    h2_sub4.paragraph_format.space_before = Pt(10)
    h2_sub4.paragraph_format.space_after = Pt(4)
    r_sub4 = h2_sub4.add_run("D. Sports Car & Mustang GT High-Speed Racing Mode (Key [V])")
    r_sub4.font.color.rgb = SLATE

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.line_spacing = 1.2
    p_sp.paragraph_format.space_after = Pt(6)
    p_sp.add_run("Driving a 500-horsepower Ford Mustang, Ferrari, or supercar in Forza Horizon, Assetto Corsa, or BeamNG requires a dramatically faster steering rack than a heavy commercial semi-truck. Press ").font.color.rgb = TEXT_DARK
    p_sp.add_run("[V]").font.bold = True
    p_sp.add_run(" on your keyboard to instantly switch vehicle profiles:\n")
    p_sp.add_run("1.  TRUCK Profile (ATS / ETS2): ").font.bold = True
    p_sp.add_run("70.0° maximum angle, 3.5° deadzone, 2.4 S-curve exponent for calm, rock-steady highway cruising.\n")
    p_sp.add_run("2.  SPORT Profile (Mustang GT / Supercars): ").font.bold = True
    p_sp.add_run("38.0° fast steering lock, 1.8° tight deadzone, 1.6 S-curve exponent for razor-sharp turn-in, rapid drift counter-steering, and high-speed stability! The on-screen steering wheel automatically morphs into an authentic flat-bottom Mustang GT racing wheel with red centering stripe, speed cutouts, and contoured thumb rests!")

    add_image_figure(doc, os.path.join(IMAGES_DIR, "gesture_horn_indicator.jpg"),
                     "Figure 3: Interactive Horn Center Push and Outward Turn Signal Gestures")

    # SECTION 3: PHONE AS WEBCAM
    h3 = doc.add_heading(level=1)
    h3.paragraph_format.space_before = Pt(14)
    h3.paragraph_format.space_after = Pt(6)
    r3 = h3.add_run("3. Using Your Phone as a Webcam (High-Speed & Zero Latency)")
    r3.font.color.rgb = NAVY

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.add_run("If your gaming laptop doesn't have a webcam, or if you want superior 60 FPS video tracking quality, use your Android or iPhone! Phone cameras have exceptional clarity and ultra-wide lenses perfect for hand tracking.")

    add_image_figure(doc, os.path.join(IMAGES_DIR, "phone_webcam_setup.jpg"),
                     "Figure 4: Gaming Laptop & Smartphone Camera Setup (USB or Wi-Fi)")

    phone_steps = [
        ("Method A: DroidCam (Recommended - 60 FPS USB)", 
         "1. Install free 'DroidCam' on your phone (Google Play Store / Apple App Store).\n"
         "2. Install the free DroidCam Windows client on your PC.\n"
         "3. Connect your phone with a USB charging cable and select 'USB' in DroidCam.\n"
         "4. Double-click 'run.bat' - the hand tracker automatically detects and uses DroidCam immediately!"),
        
        ("Method B: Iriun 4K Webcam (Alternative)", 
         "1. Install 'Iriun Webcam' on phone and PC.\n"
         "2. Connect both to the same home Wi-Fi network (or via USB cable).\n"
         "3. The camera appears as Camera Index 0 or 1 seamlessly."),
        
        ("Method C: IP Webcam (Direct Network Stream)", 
         "If using the popular 'IP Webcam' app on Android:\n"
         "1. Tap 'Start Server' at the bottom of the app on your phone.\n"
         "2. Note the Wi-Fi IP address shown on the phone (e.g., http://192.168.1.15:8080/video).\n"
         "3. Open 'config.py' in Notepad and set PHONE_STREAM_URL = 'http://192.168.1.15:8080/video'.\n"
         "4. Save and run 'run.bat'!")
    ]

    for m_title, m_desc in phone_steps:
        p_m = doc.add_paragraph()
        p_m.paragraph_format.space_before = Pt(4)
        p_m.paragraph_format.space_after = Pt(2)
        p_m.paragraph_format.left_indent = Inches(0.2)
        r_mt = p_m.add_run(f"•  {m_title}\n")
        r_mt.font.bold = True
        r_mt.font.color.rgb = NAVY
        p_m.add_run(m_desc)

    # SECTION 4: SINGLE SCREEN & PIP
    h4 = doc.add_heading(level=1)
    h4.paragraph_format.space_before = Pt(14)
    h4.paragraph_format.space_after = Pt(6)
    r4 = h4.add_run("4. Playing in American Truck Simulator (Single Screen / PiP Mode)")
    r4.font.color.rgb = NAVY

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.add_run("Do you have only one monitor or laptop screen? Here is how to play ATS with your camera HUD visible at all times:")

    ats_steps = [
        ("Step 1: In ATS Graphics Settings, set Display to 'Borderless Window'",
         "In American Truck Simulator, open Options -> Graphics -> Set Display Mode to 'Borderless Window' (or Fullscreen Window)."),
        ("Step 2: Press [O] to switch to Compact PiP (Picture-in-Picture) Overlay",
         "When running 'run.bat', press the 'O' key on your keyboard. The tracking window instantly transforms into a sleek, semi-transparent 320x240 Always-On-Top Mini PiP floating in the top-right corner of your screen!"),
        ("Step 3: Play Seamlessly",
         "ATS will fill your entire display, and your live hand tracking HUD will float right above your truck windscreen like a real digital cockpit rearview mirror!")
    ]

    for title, desc in ats_steps:
        sp = doc.add_paragraph()
        sp.paragraph_format.space_before = Pt(3)
        sp.paragraph_format.space_after = Pt(3)
        sp.paragraph_format.left_indent = Inches(0.25)
        st_run = sp.add_run(f"•  {title}: ")
        st_run.font.bold = True
        st_run.font.color.rgb = NAVY
        sp.add_run(desc)

    # SECTION 5: BUILT-IN DEMO
    h5 = doc.add_heading(level=1)
    h5.paragraph_format.space_before = Pt(14)
    h5.paragraph_format.space_after = Pt(6)
    r5 = h5.add_run("5. Interactive Highway Simulator Demo (No ATS Needed!)")
    r5.font.color.rgb = NAVY

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.2
    p.paragraph_format.space_after = Pt(6)
    p.add_run("Want to test your hand driving skills before installing ATS? We built a full standalone highway simulator directly into the app!\n\n"
              "1. Double-click ")
    r_bat = p.add_run("play_demo.bat")
    r_bat.font.bold = True
    p.add_run(".\n"
              "2. A realistic highway appears with road perspective, speed lines, 12-speed truck transmission, dashboard gauges, and dynamic steering response.\n"
              "3. Steer, pinch to accelerate to 70 MPH, brake, honk the horn with [H], and signal lane changes with [ [ ] and [ ] ]!")

    # SECTION 6: HOTKEYS TABLE
    h6 = doc.add_heading(level=1)
    h6.paragraph_format.space_before = Pt(14)
    h6.paragraph_format.space_after = Pt(6)
    r6 = h6.add_run("6. Complete Controls & Hotkey Quick Reference")
    r6.font.color.rgb = NAVY

    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Widths: 1.5 in, 2.0 in, 1.8 in, 1.5 in
    col_widths = [Inches(1.4), Inches(2.1), Inches(1.8), Inches(1.5)]

    headers = ["Action", "Hand Gesture", "In-Game Binding", "Screen Indicator"]
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].width = col_widths[i]
        set_cell_background(hdr_cells[i], "1B365D")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p_hdr = hdr_cells[i].paragraphs[0]
        p_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p_hdr.runs[0]
        run.font.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    data_rows = [
        ("Steer Left / Right", "Tilt hands or rotate hand-over-hand (900°)", "Xbox Left Joystick X", "Anti-Twitch Progressive S-Curve (+/-0.0%)"),
        ("Accelerate (Gas)", "Right hand Thumb + Index Pinch (or physical RT)", "Xbox Right Trigger (RT)", "GAS: 0% -> 100% green gauge"),
        ("Brake / Stop", "Left hand Thumb + Index Pinch (or physical LT)", "Xbox Left Trigger (LT)", "BRAKE: 0% -> 100% red gauge"),
        ("Shift to DRIVE (D)", "Push right hand forward toward screen", "Xbox Button A / Shift Up", "Green [D] indicator & HUD banner"),
        ("Shift to REVERSE (R)", "Pull left hand downward", "Xbox Button X / Shift Down", "Red [R] indicator & HUD banner"),
        ("Shift to NEUTRAL (N)", "Press keyboard key [N]", "Xbox Button Y / Neutral", "Yellow [N] indicator"),
        ("Physical Xbox Gamepad", "Plug in Xbox 360 / One controller anytime", "Simultaneous Pass-Through", "Physical RT/LT/Right-Stick pass seamlessly"),
        ("Mini PiP Overlay", "Press keyboard key [O]", "Window Toggle", "Shrinks / Expands Always-on-Top HUD"),
        ("Calibrate Wheel Center", "Press keyboard key [C]", "Calibrate Center", "Re-centers zero angle to current hand pose"),
        ("Switch Gamepad / Keyboard", "Press keyboard key [M]", "Input Mode Toggle", "Gamepad (Analog) <-> Keyboard (DirectInput)"),
        ("Quit Application", "Press keyboard key [Q] or [ESC]", "Exit", "Gracefully closes tracking")
    ]

    for row_idx, rdata in enumerate(data_rows):
        row = table.add_row()
        bg_color = "F7F9FC" if (row_idx % 2 == 1) else "FFFFFF"
        for col_idx, text in enumerate(rdata):
            cell = row.cells[col_idx]
            cell.text = text
            cell.width = col_widths[col_idx]
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.runs[0].font.size = Pt(9.5)
            if col_idx == 0:
                p.runs[0].font.bold = True

    # Spacing after table
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(8)

    # SECTION 7: TROUBLESHOOTING & FAQ
    h7 = doc.add_heading(level=1)
    h7.paragraph_format.space_before = Pt(14)
    h7.paragraph_format.space_after = Pt(6)
    r7 = h7.add_run("7. Troubleshooting & FAQs")
    r7.font.color.rgb = NAVY

    faqs = [
        ("Q: The camera doesn't detect my hands or loses them frequently.",
         "A: Make sure your room has good lighting in front of you. Avoid having a bright window directly behind your back. Sit 1.5 to 3 feet from the lens with your hands clearly visible in the camera frame."),
        
        ("Q: ATS does not turn when I move my hands.",
         "A: In American Truck Simulator -> Options -> Controls, check that the top input box says 'Keyboard + Controller (Xbox 360 For Windows)'. If you don't see it, run 'install_gamepad_driver.bat' inside the folder and restart ATS."),
        
        ("Q: Steering feels too fast or too slow.",
         "A: You can adjust steering sensitivity in two ways:\n"
         "1. Inside ATS: Go to Options -> Controls -> adjust 'Steering Sensitivity' and 'Steering Non-Linearity' sliders.\n"
         "2. In config.py: Open 'config.py' with Notepad and change STEERING_SENSITIVITY = 1.0 (higher = faster, lower = slower)."),
         
        ("Q: How do I switch camera if I have multiple webcams?",
         "A: Open 'config.py' in Notepad and set CAMERA_INDEX = 1 (or 2). If using an IP Webcam stream, paste your phone's URL into PHONE_STREAM_URL = 'http://192.168.1.XX:8080/video'.")
    ]

    for q, a in faqs:
        p_faq = doc.add_paragraph()
        p_faq.paragraph_format.space_before = Pt(4)
        p_faq.paragraph_format.space_after = Pt(4)
        r_q = p_faq.add_run(f"{q}\n")
        r_q.font.bold = True
        r_q.font.color.rgb = NAVY
        p_faq.add_run(a)

    # Footer note
    doc.add_paragraph().paragraph_format.space_after = Pt(10)
    p_end = doc.add_paragraph()
    p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_end = p_end.add_run("Happy Trucking & Safe Hauling on American Highways! Enjoy your new hand-tracking steering wheel!")
    r_end.font.bold = True
    r_end.font.size = Pt(10.5)
    r_end.font.color.rgb = SLATE

    doc.save(DOCX_OUTPUT_PATH)
    print(f"User manual successfully generated at: {DOCX_OUTPUT_PATH}")

if __name__ == "__main__":
    build_user_manual()

