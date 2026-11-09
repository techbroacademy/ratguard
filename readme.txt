# Techbro Academy RAT Guard V2.0

**A Windows Defensive Security Scanner by Techbro Academy**

Techbro Academy RAT Guard is a Python-based Windows security utility designed to identify suspicious Remote Access Trojan (RAT) indicators and unusual persistence mechanisms.

## Features

- Running process inspection
- Active network connection inspection
- Windows Registry autorun inspection
- Startup folder inspection
- Windows services inspection
- Scheduled task inspection
- PowerShell profile inspection
- SHA-256 file fingerprinting
- Permission-based process termination
- Reversible startup file quarantine
- Registry autorun disabling and restoration
- Security report generation

## Requirements

- Windows 10 or Windows 11
- Python 3.9 or later
- Administrator privileges recommended
- psutil

## Installation

Clone the repository:

```bash
https://github.com/techbroacademy/ratguard.git
```

Enter the project directory:

```bash
cd ratguard
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python ratguard.py
```

## Disclaimer

This project is intended for authorized defensive cybersecurity testing and educational purposes.

Detection is based on heuristic indicators and does not guarantee identification of all malware. False positives are possible.

Always review findings before taking action. Use Microsoft Defender or another reputable antivirus solution alongside this tool.

**Developed by Techbro Academy Technologies**

Website: https://www.techbroacademy.com/

