import xml.etree.ElementTree as ET
import ast
import sys
import os
from pathlib import Path
import argparse
import re
import json
import csv

from applications.bug_finding.diff import (
    load_generator_registers as parse_output_registers_from_json,
    parse_svd_registers,
)

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import RegisterInfo, BitField, BitNumber, CoverageInfo

def strip_bracket_suffix(s):
    if isinstance(s, str):
        idx = s.find('[')
        if idx != -1:
            return s[:idx]
    return s

def convert_hex_string_to_int(hex_str):
    if isinstance(hex_str, str) and hex_str.strip().startswith('0x'):
        try:
            return int(hex_str.strip().replace(' ', ''), 16)
        except Exception as e:
            # print(f"Error converting hex string to int: {hex_str} ({e})")
            return hex_str
    return hex_str

def convert_int_to_hex_string(int_val):
    if isinstance(int_val, int):
        return f"0x{int_val:X}"
    return int_val



def compare_registers_to_get_coverage(svd_peripherals, out_peripherals):
    coverage_info = CoverageInfo (
        peripheral_coverage=0,
        register_coverage=0,
        field_coverage=0,
        peripherals_only_in_svd=[],
        peripherals_only_in_agent_output=[],
        peripherals_present_in_both=[],
        registers_only_in_svd={},
        registers_only_in_agent_output={},
        registers_present_in_both={},
        fields_only_in_svd={},
        fields_only_in_agent_output={},
        fields_present_in_both={},
    )

    svd_keys = set(svd_peripherals.keys())
    out_keys = set(out_peripherals.keys())
    peripherals_missing_in_output = len(svd_keys - out_keys)
    peripherals_missing_in_svd = len(out_keys - svd_keys)
    peripherals_present_in_both = len(svd_keys & out_keys)

    peripheral_summary = {
        'just svd': peripherals_missing_in_output,
        'just output': peripherals_missing_in_svd,
        'both': peripherals_present_in_both
    }

    coverage_info.peripherals_only_in_svd = list(svd_keys - out_keys)
    coverage_info.peripherals_only_in_agent_output = list(out_keys - svd_keys)
    coverage_info.peripherals_present_in_both = list(svd_keys & out_keys)

    register_summary = {}
    subfield_summary = {}
    
    for peripheral in svd_keys & out_keys:
        svd_registers = svd_peripherals[peripheral]
        out_registers = out_peripherals[peripheral]
        registers_missing_in_output = len(svd_registers.keys() - out_registers.keys())
        registers_missing_in_svd = len(out_registers.keys() - svd_registers.keys())
        registers_present_in_both = len(svd_registers.keys() & out_registers.keys())
        register_summary[peripheral] = {
            'just svd': registers_missing_in_output,
            'just output': registers_missing_in_svd,
            'both': registers_present_in_both,
        }
        subfield_summary[peripheral] = {} # initialize subfield_summary for this peripheral

        coverage_info.registers_only_in_svd[peripheral] = list(svd_registers.keys() - out_registers.keys())
        coverage_info.registers_only_in_agent_output[peripheral] = list(out_registers.keys() - svd_registers.keys())
        coverage_info.registers_present_in_both[peripheral] = list(svd_registers.keys() & out_registers.keys())

        coverage_info.fields_only_in_svd[peripheral] = {}
        coverage_info.fields_only_in_agent_output[peripheral] = {}
        coverage_info.fields_present_in_both[peripheral] = {}

        for register in svd_registers.keys() & out_registers.keys():
            svd_register = svd_registers[register]
            out_register = out_registers[register]
            # Compare all fields except description
            fields_svd = {f['name']: f for f in svd_register.get('fields', [])}
            fields_out = {f['name']: f for f in out_register.get('fields', [])}

            fields_svd_names = set(fields_svd.keys())
            fields_out_names = set(fields_out.keys())

            missing_fields = fields_svd_names - fields_out_names
            extra_fields = fields_out_names - fields_svd_names
            common_fields = fields_svd_names & fields_out_names

            fields_missing_in_output = len(missing_fields)
            fields_missing_in_svd = len(extra_fields)
            fields_present_in_both = len(common_fields)

            subfield_summary[peripheral][register] = {
                'just svd': fields_missing_in_output,
                'just output': fields_missing_in_svd,
                'both': fields_present_in_both
            }

            coverage_info.fields_only_in_svd[peripheral][register] = list(missing_fields)
            coverage_info.fields_only_in_agent_output[peripheral][register] = list(extra_fields)
            coverage_info.fields_present_in_both[peripheral][register] = list(common_fields)

    return peripheral_summary, register_summary, subfield_summary, coverage_info

def calculate_generator_coverage(svd_path, agent_output_folder) -> CoverageInfo:
    svd_regs = parse_svd_registers(svd_path)
    print(f"Parsed {len(svd_regs)} peripherals from SVD file")
    out_regs = parse_output_registers_from_json(agent_output_folder)
    print(f"Parsed {len(out_regs)} peripherals from agent output folder")
    peripheral_summary, register_summary, subfield_summary, coverage_info = compare_registers_to_get_coverage(svd_regs, out_regs)

    # Stats
    total_peripherals = 0
    present_peripherals = 0

    total_registers_in_present_peripherals = 0
    present_registers = 0

    total_fields_in_present_registers = 0
    present_fields = 0

    total_peripherals += peripheral_summary['just svd'] + peripheral_summary['both'] + peripheral_summary['just output']
    present_peripherals += peripheral_summary['both']
    
    for peripheral in register_summary.keys():
        total_registers_in_present_peripherals += register_summary[peripheral]['just svd'] + register_summary[peripheral]['both']
        present_registers += register_summary[peripheral]['both']
    
    for peripheral in subfield_summary.keys():
        for register in subfield_summary[peripheral].keys():
            total_fields_in_present_registers += subfield_summary[peripheral][register]['just svd'] + subfield_summary[peripheral][register]['both']
            present_fields += subfield_summary[peripheral][register]['both']
    
    coverage_info.peripheral_coverage = present_peripherals / total_peripherals * 100
    coverage_info.register_coverage = present_registers / total_registers_in_present_peripherals * 100
    coverage_info.field_coverage = present_fields / total_fields_in_present_registers * 100

    return coverage_info


