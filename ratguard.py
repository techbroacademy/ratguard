
import os
import sys
import json
import psutil
import shutil
import hashlib
import ctypes
import subprocess
import winreg
from pathlib import Path
from datetime import datetime

# ==========================================================
# TECHBRO ACADEMY RAT GUARD V2.0
# ADVANCED WINDOWS DEFENSIVE SECURITY SCANNER
# ==========================================================

APP = "TECHBRO ACADEMY RAT GUARD"
VERSION = "2.0"

BASE_DIR = Path(os.environ["LOCALAPPDATA"]) / "TechbroAcademy" / "RATGuard"
QUARANTINE_DIR = BASE_DIR / "Quarantine"
REPORT_DIR = BASE_DIR / "Reports"
MANIFEST = BASE_DIR / "quarantine.json"

for folder in (BASE_DIR, QUARANTINE_DIR, REPORT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

RAT_INDICATORS = [
    "njrat", "darkcomet", "asyncrat", "quasarrat",
    "nanocore", "remcos", "netwire", "orcus",
    "warzone", "luminosity", "blackshades",
    "dcrat", "xworm", "venomrat", "pandorahvnc",
    "poisonivy", "sality"
]

SUSPICIOUS_PATHS = [
    "\\appdata\\local\\temp\\",
    "\\appdata\\roaming\\",
    "\\users\\public\\",
    "\\windows\\temp\\"
]

SUSPICIOUS_COMMANDS = [
    "-encodedcommand",
    "-enc ",
    "frombase64string",
    "downloadstring",
    "invoke-expression",
    "iex(",
    "hidden",
    "windowstyle hidden"
]

findings = []
process_objects = {}


# ==========================================================
# GENERAL UTILITIES
# ==========================================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def banner():
    os.system("cls")

    print("=" * 70)
    print(r"""
  _______ ______ _____ _    _ ____  _____   ____  
 |__   __|  ____/ ____| |  | |  _ \|  __ \ / __ \ 
    | |  | |__ | |    | |__| | |_) | |__) | |  | |
    | |  |  __|| |    |  __  |  _ <|  _  /| |  | |
    | |  | |___| |____| |  | | |_) | | \ \| |__| |
    |_|  |______\_____|_|  |_|____/|_|  \_\\____/ 
    """)
    print("              TECHBRO ACADEMY")
    print("          ADVANCED RAT GUARD V2.0")
    print("       WINDOWS SECURITY & RESPONSE")
    print("=" * 70)
    print("Administrator:", "YES" if is_admin() else "NO")
    print("Quarantine:", QUARANTINE_DIR)
    print("=" * 70)


def confirm(message):
    answer = input(
        "\n" + message + "\nType YES to continue: "
    )
    return answer.strip().upper() == "YES"


def sha256_file(filepath):
    try:
        digest = hashlib.sha256()

        with open(filepath, "rb") as file:
            for block in iter(
                lambda: file.read(1024 * 1024), b""
            ):
                digest.update(block)

        return digest.hexdigest()

    except OSError:
        return "Unavailable"


def indicators(name, path="", command=""):
    text = (
        str(name) + " " +
        str(path) + " " +
        str(command)
    ).lower()

    reasons = []

    for indicator in RAT_INDICATORS:
        if indicator in text:
            reasons.append(
                "Known RAT-family name indicator: " + indicator
            )

    for location in SUSPICIOUS_PATHS:
        if location in text:
            reasons.append(
                "Execution from commonly abused location"
            )
            break

    for pattern in SUSPICIOUS_COMMANDS:
        if pattern in text:
            reasons.append(
                "Suspicious command-line indicator: " + pattern
            )

    return list(dict.fromkeys(reasons))


def add_finding(category, name, details, reasons=None, data=None):
    item = {
        "category": category,
        "name": str(name),
        "details": str(details),
        "reasons": reasons or [],
        "data": data or {}
    }

    findings.append(item)
    return item


def run_command(command, timeout=30):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace"
        )

        return result.stdout

    except Exception as error:
        return "Command failed: " + str(error)


def load_manifest():
    if MANIFEST.exists():
        try:
            with open(MANIFEST, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            print("[!] Could not read quarantine manifest.")

    return []


def save_manifest(items):
    temporary = MANIFEST.with_suffix(".tmp")

    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(items, file, indent=4)

    temporary.replace(MANIFEST)


# ==========================================================
# 1. PROCESS SCANNER
# ==========================================================

def scan_processes():
    print("\n[1] RUNNING PROCESS SCAN")
    print("-" * 60)

    for process in psutil.process_iter(
        ["pid", "name", "exe", "username", "cmdline"]
    ):
        try:
            info = process.info

            pid = info["pid"]
            name = info["name"] or "Unknown"
            path = info["exe"] or ""
            command = " ".join(info["cmdline"] or [])

            process_objects[pid] = process

            reasons = indicators(name, path, command)

            if reasons:
                digest = (
                    sha256_file(path)
                    if path and os.path.isfile(path)
                    else "Unavailable"
                )

                add_finding(
                    "process",
                    name,
                    f"PID: {pid} | Path: {path}",
                    reasons,
                    {
                        "pid": pid,
                        "path": path,
                        "sha256": digest
                    }
                )

                print("\n[!] PROCESS FLAGGED")
                print("Name:", name)
                print("PID:", pid)
                print("Path:", path)

                for reason in reasons:
                    print("Reason:", reason)

                print("SHA256:", digest)

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess
        ):
            continue


# ==========================================================
# 2. NETWORK CONNECTION SCANNER
# ==========================================================

def scan_network():
    print("\n[2] NETWORK CONNECTION SCAN")
    print("-" * 60)

    try:
        for connection in psutil.net_connections(kind="inet"):

            if not connection.raddr:
                continue

            try:
                process = (
                    psutil.Process(connection.pid)
                    if connection.pid else None
                )

                name = process.name() if process else "Unknown"

                print(
                    f"PID: {connection.pid} | "
                    f"Process: {name} | "
                    f"Remote: {connection.raddr.ip}:"
                    f"{connection.raddr.port} | "
                    f"State: {connection.status}"
                )

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):
                continue

    except psutil.AccessDenied:
        print("[!] Run as Administrator for a more complete scan.")

    print("\nNetwork scan complete.")
    print("An unusual connection is not proof of a RAT.")


# ==========================================================
# 3. REGISTRY AUTORUN SCANNER - CORRECTED
# ==========================================================

REGISTRY_KEYS = [
    (
        "HKCU",
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run"
    ),
    (
        "HKLM",
        winreg.HKEY_LOCAL_MACHINE,
        r"Software\Microsoft\Windows\CurrentVersion\Run"
    ),
    (
        "HKCU",
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
    ),
    (
        "HKLM",
        winreg.HKEY_LOCAL_MACHINE,
        r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
    )
]


def scan_registry():
    print("\n[3] REGISTRY AUTORUN SCAN")
    print("-" * 60)

    total_entries = 0
    suspicious_entries = 0

    for hive_name, hive, key_path in REGISTRY_KEYS:

        try:
            with winreg.OpenKey(
                hive,
                key_path,
                0,
                winreg.KEY_READ
            ) as key:

                index = 0

                while True:
                    try:
                        name, value, value_type = (
                            winreg.EnumValue(key, index)
                        )

                        index += 1
                        total_entries += 1

                        command = str(value)

                        # CORRECTION:
                        # Only entries with suspicious indicators
                        # are added to the findings list.

                        reasons = indicators(name, command)

                        if reasons:

                            suspicious_entries += 1

                            add_finding(
                                "registry",
                                name,
                                command,
                                reasons,
                                {
                                    "hive": hive_name,
                                    "key": key_path,
                                    "value": value,
                                    "value_type": value_type
                                }
                            )

                            print("\n[!] SUSPICIOUS AUTORUN:", name)
                            print("Registry:", hive_name)
                            print("Command:", command)

                            for reason in reasons:
                                print("Reason:", reason)

                    except OSError:
                        break

        except OSError:
            continue

    print("\nRegistry scan completed.")
    print("Total startup entries inspected:", total_entries)
    print("Suspicious entries flagged:", suspicious_entries)
    print("Legitimate-looking entries were not added to findings.")


# ==========================================================
# 4. STARTUP FOLDER SCANNER
# ==========================================================

def scan_startup():
    print("\n[4] STARTUP FOLDER SCAN")
    print("-" * 60)

    folders = [
        Path(os.environ.get("APPDATA", "")) /
        "Microsoft/Windows/Start Menu/Programs/Startup",

        Path(os.environ.get("PROGRAMDATA", "")) /
        "Microsoft/Windows/Start Menu/Programs/Startup"
    ]

    for folder in folders:

        if not folder.exists():
            continue

        for file in folder.iterdir():

            if not file.is_file():
                continue

            reasons = indicators(file.name, str(file))

            # Only flag startup files that match an indicator.
            if not reasons:
                continue

            digest = sha256_file(file)

            add_finding(
                "startup_file",
                file.name,
                str(file),
                reasons,
                {
                    "path": str(file),
                    "sha256": digest
                }
            )

            print("\n[!] STARTUP ITEM FLAGGED:", file.name)
            print("Location:", file)
            print("SHA256:", digest)

            for reason in reasons:
                print("Reason:", reason)

    print("\nStartup folder scan completed.")


# ==========================================================
# 5. WINDOWS SERVICES SCANNER
# ==========================================================

def scan_services():
    print("\n[5] WINDOWS SERVICES SCAN")
    print("-" * 60)

    try:
        for service in psutil.win_service_iter():

            try:
                info = service.as_dict()

                name = info.get("name", "")
                display = info.get("display_name", "")
                path = info.get("binpath", "")
                start_type = info.get("start_type", "")

                reasons = indicators(name, path, display)

                if reasons:

                    add_finding(
                        "service",
                        name,
                        f"{display} | {path}",
                        reasons,
                        {
                            "service_name": name,
                            "binpath": path,
                            "start_type": start_type
                        }
                    )

                    print("\n[!] SERVICE FLAGGED")
                    print("Name:", name)
                    print("Display:", display)
                    print("Path:", path)

                    for reason in reasons:
                        print("Reason:", reason)

            except (
                psutil.AccessDenied,
                psutil.NoSuchProcess
            ):
                continue

    except Exception as error:
        print("Service scan error:", error)


# ==========================================================
# 6. SCHEDULED TASK SCANNER
# ==========================================================

def scan_scheduled_tasks():
    print("\n[6] SCHEDULED TASK SCAN")
    print("-" * 60)

    script = r"""
    Get-ScheduledTask | ForEach-Object {
        $task = $_
        foreach ($action in $task.Actions) {
            [PSCustomObject]@{
                TaskName = $task.TaskName
                TaskPath = $task.TaskPath
                State = [string]$task.State
                Execute = $action.Execute
                Arguments = $action.Arguments
            }
        }
    } | ConvertTo-Json -Depth 4 -Compress
    """

    output = run_command(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script
        ],
        timeout=60
    )

    try:
        tasks = json.loads(output)

        if isinstance(tasks, dict):
            tasks = [tasks]

        if not isinstance(tasks, list):
            tasks = []

        for task in tasks:

            name = task.get("TaskName", "")
            task_path = task.get("TaskPath", "")
            executable = task.get("Execute", "") or ""
            arguments = task.get("Arguments", "") or ""

            command = executable + " " + arguments

            reasons = indicators(name, command)

            if reasons:

                add_finding(
                    "scheduled_task",
                    name,
                    command,
                    reasons,
                    {
                        "task_name": name,
                        "task_path": task_path
                    }
                )

                print("\n[!] SCHEDULED TASK FLAGGED")
                print("Name:", name)
                print("Task path:", task_path)
                print("Command:", command)

                for reason in reasons:
                    print("Reason:", reason)

    except (json.JSONDecodeError, TypeError):
        print("Could not parse scheduled task results.")
        print(output[:1500])


# ==========================================================
# 7. POWERSHELL PERSISTENCE SCANNER
# ==========================================================

def scan_powershell():
    print("\n[7] POWERSHELL PERSISTENCE SCAN")
    print("-" * 60)

    profile_paths = [
        Path(os.environ.get("USERPROFILE", "")) /
        "Documents/WindowsPowerShell/profile.ps1",

        Path(os.environ.get("USERPROFILE", "")) /
        "Documents/PowerShell/profile.ps1",

        Path(os.environ.get("WINDIR", "C:\\Windows")) /
        "System32/WindowsPowerShell/v1.0/profile.ps1"
    ]

    for profile in profile_paths:

        if not profile.is_file():
            continue

        try:
            content = profile.read_text(
                encoding="utf-8",
                errors="replace"
            )

            reasons = indicators(
                profile.name,
                str(profile),
                content
            )

            if reasons:

                add_finding(
                    "powershell_profile",
                    profile.name,
                    str(profile),
                    reasons,
                    {"path": str(profile)}
                )

                print("\n[!] POWERSHELL PROFILE FLAGGED")
                print("File:", profile)

                for reason in reasons:
                    print("Reason:", reason)

        except OSError:
            continue

    print("PowerShell profile inspection complete.")


# ==========================================================
# 8. PROCESS TERMINATION
# ==========================================================

def stop_process(item):
    pid = item["data"].get("pid")

    process = process_objects.get(pid)

    if not process:
        print("Process is unavailable.")
        return

    try:
        print("\nPROCESS TERMINATION")
        print("Name:", item["name"])
        print("PID:", pid)

        if process.pid == os.getpid():
            print("Cannot terminate the security scanner.")
            return

        if process.username().upper() in (
            "SYSTEM",
            "NT AUTHORITY\\SYSTEM"
        ):
            print("Protected SYSTEM process. No action taken.")
            return

        if not confirm("Authorize process termination?"):
            print("No changes made.")
            return

        process.terminate()

        try:
            process.wait(timeout=5)
            print("[SUCCESS] Process terminated.")

        except psutil.TimeoutExpired:
            print("Process did not exit normally.")
            print("Force termination is intentionally disabled.")

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied
    ) as error:
        print("Could not stop process:", error)


# ==========================================================
# 9. REVERSIBLE REGISTRY AUTORUN DISABLING
# ==========================================================

def disable_registry(item):
    data = item["data"]

    hive = (
        winreg.HKEY_CURRENT_USER
        if data["hive"] == "HKCU"
        else winreg.HKEY_LOCAL_MACHINE
    )

    print("\nREGISTRY AUTORUN ENTRY")
    print("Name:", item["name"])
    print("Command:", data["value"])

    if not confirm("Disable this exact autorun entry?"):
        print("Entry unchanged.")
        return

    original_name = item["name"]

    disabled_name = (
        "TBA_DISABLED_" +
        datetime.now().strftime("%Y%m%d%H%M%S%f") +
        "_" + original_name
    )

    try:
        access = winreg.KEY_READ | winreg.KEY_SET_VALUE

        with winreg.OpenKey(
            hive,
            data["key"],
            0,
            access
        ) as key:

            winreg.SetValueEx(
                key,
                disabled_name,
                0,
                data["value_type"],
                data["value"]
            )

            winreg.DeleteValue(key, original_name)

        manifest = load_manifest()

        manifest.append({
            "type": "registry",
            "hive": data["hive"],
            "key": data["key"],
            "original_name": original_name,
            "disabled_name": disabled_name,
            "value": data["value"],
            "value_type": data["value_type"]
        })

        save_manifest(manifest)

        print("[SUCCESS] Autorun entry disabled.")
        print("Original command preserved for restoration.")

    except OSError as error:
        print("Registry operation failed:", error)


# ==========================================================
# 10. STARTUP FILE QUARANTINE
# ==========================================================

def quarantine_startup(item):
    source = Path(item["data"]["path"])

    if not source.is_file():
        print("Startup file no longer exists.")
        return

    print("\nSTARTUP FILE QUARANTINE")
    print("File:", source)
    print("SHA256:", item["data"]["sha256"])

    if not confirm("Move this file into quarantine?"):
        print("File unchanged.")
        return

    destination = (
        QUARANTINE_DIR /
        (
            datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            + "_" + source.name
        )
    )

    try:
        # Check that the file has not changed since scanning.
        if sha256_file(source) != item["data"]["sha256"]:
            print("Quarantine cancelled: file hash has changed.")
            return

        shutil.move(str(source), str(destination))

        manifest = load_manifest()

        manifest.append({
            "type": "file",
            "original_path": str(source),
            "quarantine_path": str(destination),
            "sha256": item["data"]["sha256"]
        })

        save_manifest(manifest)

        print("[SUCCESS] File quarantined.")
        print("Quarantine location:", destination)

    except OSError as error:
        print("Quarantine failed:", error)


# ==========================================================
# 11. SCHEDULED TASK DISABLING
# ==========================================================

def disable_task(item):
    data = item["data"]

    full_name = data["task_path"] + data["task_name"]

    print("\nSCHEDULED TASK")
    print("Task:", full_name)
    print("Command:", item["details"])

    if not confirm("Disable this scheduled task?"):
        print("Task unchanged.")
        return

    result = subprocess.run(
        [
            "schtasks.exe",
            "/Change",
            "/TN",
            full_name,
            "/Disable"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("[SUCCESS] Scheduled task disabled.")
        print("It can be re-enabled through Windows Task Scheduler.")

    else:
        print("[FAILED]", result.stderr or result.stdout)


# ==========================================================
# 12. REVIEW FINDINGS
# ==========================================================

def review_findings():
    print("\n" + "=" * 70)
    print("TECHBRO ACADEMY - FINDINGS REVIEW")
    print("=" * 70)

    if not findings:
        print("No matching suspicious indicators found.")
        return

    print("Total flagged items:", len(findings))

    for index, item in enumerate(findings, 1):

        print("\n" + "-" * 60)
        print(f"[{index}] {item['category'].upper()}")
        print("Name:", item["name"])
        print("Details:", item["details"])

        print("Indicators:")
        for reason in item["reasons"]:
            print(" -", reason)

        if item["category"] == "process":

            if confirm("Review termination of this process?"):
                stop_process(item)

        elif item["category"] == "registry":

            if confirm("Review disabling this registry entry?"):
                disable_registry(item)

        elif item["category"] == "startup_file":

            if confirm("Review quarantining this startup file?"):
                quarantine_startup(item)

        elif item["category"] == "scheduled_task":

            if confirm("Review disabling this scheduled task?"):
                disable_task(item)

        elif item["category"] == "service":

            print(
                "[INFO] Service flagged for investigation. "
                "No automatic service changes."
            )

        elif item["category"] == "powershell_profile":

            print(
                "[INFO] Inspect the profile manually. "
                "No automatic file changes."
            )


# ==========================================================
# 13. RESTORE QUARANTINED ITEMS
# ==========================================================

def restore_quarantine():
    print("\n" + "=" * 65)
    print("TECHBRO ACADEMY - QUARANTINE RESTORE")
    print("=" * 65)

    manifest = load_manifest()

    if not manifest:
        print("No quarantined items recorded.")
        return

    for index, item in enumerate(manifest, 1):

        print(f"\n[{index}] {item['type'].upper()}")

        if item["type"] == "file":

            print("Original:", item["original_path"])
            print("Quarantine:", item["quarantine_path"])

        else:

            print("Registry:", item["key"])
            print("Original name:", item["original_name"])

    selection = input(
        "\nEnter item number to restore, or ALL: "
    ).strip().upper()

    if selection == "ALL":

        selected = list(range(len(manifest)))

    else:

        try:
            selected = [int(selection) - 1]

            if selected[0] < 0 or selected[0] >= len(manifest):
                print("Invalid selection.")
                return

        except ValueError:
            print("Invalid selection.")
            return

    if not confirm("Authorize restoration of selected items?"):
        print("No changes made.")
        return

    for index in sorted(selected, reverse=True):

        item = manifest[index]

        try:

            if item["type"] == "file":

                source = Path(item["quarantine_path"])
                destination = Path(item["original_path"])

                if not source.is_file():
                    print("Quarantined file unavailable:", source)
                    continue

                if destination.exists():
                    print("Restore skipped: destination already exists.")
                    continue

                if sha256_file(source) != item["sha256"]:
                    print("Restore skipped: hash mismatch.")
                    continue

                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                shutil.move(str(source), str(destination))

                print("[RESTORED]", destination)

            elif item["type"] == "registry":

                hive = (
                    winreg.HKEY_CURRENT_USER
                    if item["hive"] == "HKCU"
                    else winreg.HKEY_LOCAL_MACHINE
                )

                with winreg.OpenKey(
                    hive,
                    item["key"],
                    0,
                    winreg.KEY_READ | winreg.KEY_SET_VALUE
                ) as key:

                    try:
                        winreg.QueryValueEx(
                            key,
                            item["original_name"]
                        )

                        print(
                            "Restore skipped: original registry "
                            "entry already exists."
                        )
                        continue

                    except FileNotFoundError:
                        pass

                    winreg.SetValueEx(
                        key,
                        item["original_name"],
                        0,
                        item["value_type"],
                        item["value"]
                    )

                    winreg.DeleteValue(
                        key,
                        item["disabled_name"]
                    )

                print(
                    "[RESTORED] Registry entry:",
                    item["original_name"]
                )

            manifest.pop(index)

        except OSError as error:
            print("Restore failed:", error)

    save_manifest(manifest)


# ==========================================================
# 14. SECURITY REPORT
# ==========================================================

def save_report():
    filename = (
        REPORT_DIR /
        (
            "Techbro_RAT_Report_" +
            datetime.now().strftime("%Y%m%d_%H%M%S") +
            ".txt"
        )
    )

    with open(filename, "w", encoding="utf-8") as report:

        report.write(APP + " V" + VERSION + "\n")
        report.write("Scan time: " + str(datetime.now()) + "\n")
        report.write("=" * 70 + "\n")

        report.write(
            "Total findings: " + str(len(findings)) + "\n"
        )

        for index, item in enumerate(findings, 1):

            report.write(
                f"\n[{index}] {item['category'].upper()}\n"
            )

            report.write("Name: " + item["name"] + "\n")
            report.write("Details: " + item["details"] + "\n")

            for reason in item["reasons"]:
                report.write("Indicator: " + reason + "\n")

            if item["data"].get("sha256"):
                report.write(
                    "SHA256: " + item["data"]["sha256"] + "\n"
                )

        report.write(
            "\nNOTE: Findings are heuristic indicators, "
            "not confirmed malware diagnoses.\n"
        )

    print("\n[SUCCESS] Security report saved:")
    print(filename)


# ==========================================================
# 15. MAIN MENU
# ==========================================================

def full_scan():

    findings.clear()
    process_objects.clear()

    print("\nStarting Techbro Academy security scan...")
    print("This may take a few minutes.")

    scan_processes()
    scan_network()
    scan_registry()
    scan_startup()
    scan_services()
    scan_scheduled_tasks()
    scan_powershell()

    print("\n" + "=" * 70)
    print("SCAN COMPLETED")
    print("Reviewable findings:", len(findings))
    print("=" * 70)

    review_findings()
    save_report()


def main():

    if os.name != "nt":
        print("This application supports Windows only.")
        return

    while True:

        banner()

        print("\n[1] Start Full Security Scan")
        print("[2] View Current Scan Findings")
        print("[3] Review / Remove Selected Findings")
        print("[4] Restore Quarantined Files and Registry Entries")
        print("[5] View Quarantine Location")
        print("[6] Exit")

        choice = input("\nSelect an option: ").strip()

        if choice == "1":

            full_scan()

        elif choice == "2":

            if findings:

                for item in findings:

                    print(
                        f"\n{item['category']} | "
                        f"{item['name']} | {item['details']}"
                    )

            else:

                print("No scan findings available.")

        elif choice == "3":

            review_findings()
            save_report()

        elif choice == "4":

            restore_quarantine()

        elif choice == "5":

            print("\nQuarantine folder:")
            print(QUARANTINE_DIR)
            os.startfile(str(QUARANTINE_DIR))

        elif choice == "6":

            print(
                "\nThank you for using "
                "Techbro Academy RAT Guard."
            )
            break

        else:

            print("Invalid selection.")

        input("\nPress ENTER to return to the main menu...")


if __name__ == "__main__":
    main()
