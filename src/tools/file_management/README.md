# file_management — Folder README

This folder contains neutral, non-destructive tools for inspecting and analyzing files. Tools here never modify user data. They operate only on structure, metadata, and safe read-only scanning. All tools are user-agnostic and GitHub-safe.

---

## 1. Purpose and Scope

This folder provides structural utilities for:

- scanning files for keyword patterns  
- validating directory layouts  
- performing batch checks before maintenance tasks  
- supporting agents that need safe file inspection  

This folder is part of the tools layer of the system architecture.

Appropriate contents:

- standalone Python tools  
- structural validators  
- scanners  
- batch-processing helpers  

Out of scope:

- tools that edit or transform file contents  
- tools that manipulate images or media  
- agent-specific or user-specific logic  

---

## 2. Contents Overview

keyword_scan.py  
A read-only scanner that:

- loads exact paths from config.local.json  
- loads keyword rules from the `keyword_scan` block of config.local.json  
- walks the configured runtime directory  
- records all matching lines into a CSV file inside the configured logs folder  

This tool is safe for any agent to call and does not modify files.

config.local.json → `keyword_scan`  
The scanner's rules live in this block of the single config file:

- keyword variants to search for  
- suffixes and prefixes to exclude from scanning  

All paths also come from config.local.json.

---

## 3. System Relationships

This folder interacts with:

- the project `src/` tree as the source of files to scan  
- `config/config.local.json` as the provider of configuration  
- `data/<instance>/system/logs/` as the destination for output logs  

It is part of the toolchain used by maintenance playbooks and structural audits.  
It does not depend on agent memory or user-specific logic.

---

## 4. Human Audit Checklist

- Confirm config.local.json contains the exact literal path for keyword_scan_results.  
- Review the `keyword_scan` block of config.local.json periodically to ensure keyword lists remain correct.  
- Ensure no personal data appears in this folder.  
- Remove obsolete tools if replaced by newer structural utilities.  
- Verify that tools do not derive or construct paths; all paths must come from config.local.json.

---

## Usage

Run the scanner from any terminal:

python3 keyword_scan.py

The tool:

- reads the scan root from config.local.json  
- reads the output directory from config.local.json  
- writes keyword_scan_results.csv into the exact folder specified there  

No arguments are required.
