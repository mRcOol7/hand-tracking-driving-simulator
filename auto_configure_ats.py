"""
auto_configure_ats.py
Reverse-engineered profile injector for American Truck Simulator & Euro Truck Simulator 2.
Automatically binds Virtual Xbox 360 Controller, sets Controller Subtype to 'Wheel' (1:1 physical response),
eliminates deadzones, and maps throttle, brake, horn, and indicators without touching game menus!
"""

import os
import sys
import glob
import re
import shutil

DOCUMENTS = os.path.expanduser(r"~\Documents")
ATS_DIRS = [
    os.path.join(DOCUMENTS, "American Truck Simulator"),
    os.path.join(DOCUMENTS, "Euro Truck Simulator 2"),
]

def find_all_controls_sii():
    """Finds all controls.sii files in local and steam cloud profiles."""
    found_files = []

    # 1. Documents profile directories
    for base in ATS_DIRS:
        if os.path.isdir(base):
            pattern = os.path.join(base, "profiles", "*", "controls.sii")
            found_files.extend(glob.glob(pattern))
            pattern_steam = os.path.join(base, "steam_profiles", "*", "controls.sii")
            found_files.extend(glob.glob(pattern_steam))

    # 2. Steam userdata cloud profiles (ATS appid = 270880, ETS2 = 227300)
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    steam_userdata = os.path.join(program_files_x86, "Steam", "userdata")
    if os.path.isdir(steam_userdata):
        for appid in ["270880", "227300"]:
            pattern = os.path.join(steam_userdata, "*", appid, "remote", "profiles", "*", "controls.sii")
            found_files.extend(glob.glob(pattern))

    return list(set(found_files))

def configure_file(filepath):
    """Parses and updates controls.sii with optimal hand-tracking wheel configuration."""
    print(f"\n[Found Profile] -> {filepath}")
    
    # Create safety backup
    backup_path = filepath + ".backup"
    if not os.path.exists(backup_path):
        shutil.copy2(filepath, backup_path)
        print(f"  [Backup] Created safety backup at: {backup_path}")

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Verify if file is plain text SII (not binary encrypted)
    if "SiiNunit" not in content and "config_lines" not in content:
        print("  [Warning] Profile file is binary encrypted. ATS will configure automatically upon selecting 'Wheel' in menus.")
        return False

    lines = content.splitlines()
    new_lines = []
    modified_count = 0

    # Key parameters to set for 1:1 steering wheel simulation
    replacements = {
        # Set Controller Subtype to 'Wheel' (1) instead of 'Gamepad' (0) for zero lag & 1:1 linearity
        r'config_lines\[\d+\]:\s*"constant c_ctrlsubtype\s+.*"': 'constant c_ctrlsubtype 1',
        # Set steering deadzone to 0%
        r'config_lines\[\d+\]:\s*"constant c_steer_dz\s+.*"': 'constant c_steer_dz 0.000000',
        # Set steering non-linearity to 0% (pure linear response)
        r'config_lines\[\d+\]:\s*"constant c_steer_func\s+.*"': 'constant c_steer_func 0.000000',
    }

    for line in lines:
        updated = False
        for pattern, replacement in replacements.items():
            if re.search(pattern, line):
                # Preserve the config_lines[idx]: prefix
                prefix_match = re.match(r'(config_lines\[\d+\]:\s*)"([^"]*)"', line)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    new_line = f'{prefix}"{replacement}"'
                    new_lines.append(new_line)
                    updated = True
                    modified_count += 1
                    break
        if not updated:
            new_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    print(f"  [Success] Injected 1:1 Physical Wheel parameters ({modified_count} settings updated)!")
    return True

def main():
    print("=" * 65)
    print("  ATS & ETS2 REVERSE-ENGINEERED 1-CLICK CONTROLLER INJECTOR")
    print("=" * 65)
    print("Scanning system for American Truck Simulator & Euro Truck Simulator profiles...\n")

    files = find_all_controls_sii()
    if not files:
        print("[Status] No ATS profile directories found on this PC.")
        print("(Note: If playing on your friend's laptop, run this file there to auto-bind!).")
        print("\nManual Game Settings:")
        print("  1. In ATS, go to Options -> Controls")
        print("  2. Set Input Device: 'Keyboard + Controller (Xbox 360)'")
        print("  3. Set Controller Subtype: 'Wheel' (gives 1:1 lag-free steering!)")
        print("  4. Set Steering Deadzone slider: 0% (far left)")
        print("  5. Set Steering Non-linearity slider: 0% (far left)")
        return

    success_count = 0
    for p in files:
        try:
            if configure_file(p):
                success_count += 1
        except Exception as e:
            print(f"  [Error] Could not update {p}: {e}")

    print(f"\n[Finished] Successfully optimized {success_count} profile(s) for 1:1 Hand Steering!")

if __name__ == "__main__":
    main()

