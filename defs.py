from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel

class Manufacturer(Enum):
    INTEL = "Intel"
    STM = "STM"

@dataclass
class UserContext:
    device_name: str
    peripheral_name: str
    manufacturer: Manufacturer
    driver_path: str
    datasheet_path: str
    datasheet_sections_directory: str
    svd_path: list[str]
    run: int
    file_id: str
    vs_id: str

class BitNumber(BaseModel):
    start_bit: int
    end_bit: int

class EnumValue(BaseModel):
    value: str
    name: str

class BitField(BaseModel):
    name: str
    description: str
    bit_number: BitNumber
    enumerated_values: list[EnumValue]

class RegisterInfo(BaseModel):
    datasheet_register_abbreviation: str
    address_offset: str
    reset_value: str
    size: int
    readonly_bits: list[BitNumber]
    write_only_bits: list[BitNumber]
    read_write_bits: list[BitNumber]
    subfields: list[BitField]

class RegisterList(BaseModel):
    registers: list[RegisterInfo]

class RegisterName(BaseModel):
    driver_register_name: str
    datasheet_register_name: str
    datasheet_register_abbreviation: str

class RegisterNameList(BaseModel):
    registers: list[RegisterName]