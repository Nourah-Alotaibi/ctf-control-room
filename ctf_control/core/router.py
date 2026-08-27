
from __future__ import annotations

ROLE_MAP = {
    "web": "Web Security Specialist",
    "reverse": "Reverse Engineering Specialist",
    "pwn": "Binary Exploitation Specialist",
    "crypto": "Cryptography Specialist",
    "forensics": "Digital Forensics Specialist",
    "network": "Network Security Specialist",
    "stego": "Steganography Specialist",
    "malware": "Malware Analysis Specialist",
    "mobile": "Mobile Security Specialist",
    "osint": "OSINT Specialist",
    "cloud": "Cloud Security Specialist",
    "hardware-iot": "Hardware / IoT Specialist",
    "ai-ml": "AI / ML Challenge Specialist",
    "misc": "General CTF Specialist",
}

def route_role(category: str, context_text: str="") -> dict:
    role = ROLE_MAP.get(category, "General CTF Specialist")
    hints = []
    low = context_text.lower()

    # Deterministic hints only: no extra model call.
    if "elf" in low or "checksec" in low:
        hints.append("binary")
    if "dns" in low or "pcap" in low or "tshark" in low:
        hints.append("network")
    if "zip" in low or "archive" in low:
        hints.append("embedded/archive")
    if "rsa" in low:
        hints.append("rsa")
    if "png" in low or "jpeg" in low:
        hints.append("image")
    return {
        "role": role,
        "category": category,
        "hints": hints,
    }
