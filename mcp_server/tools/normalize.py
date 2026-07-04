import re


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone.strip())


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def normalize_identification_number(identification_number: str) -> str:
    return identification_number.strip().upper()
