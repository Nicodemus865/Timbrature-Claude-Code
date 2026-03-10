"""
Parser per i PDF delle timbrature SOMEtime
Formato: CART_YYYY-MM-DD_YYYY-MM-DD_XXXX_Nome Cognome.pdf
"""

import pdfplumber
import re
import io
from datetime import datetime
from typing import List, Dict, Any, Optional

# Mapping giorni settimana italiano -> numero
GIORNI_MAP = {
    'lun': 0, 'mar': 1, 'mer': 2, 'gio': 3, 'ven': 4, 'sab': 5, 'dom': 6
}

def parse_sometime_pdf(pdf_content: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Parse a SOMEtime PDF and extract timbrature data.
    
    Args:
        pdf_content: PDF file content as bytes
        filename: Original filename for reference
        
    Returns:
        Dictionary with parsed data and metadata
    """
    result = {
        "success": False,
        "filename": filename,
        "dipendente": None,
        "azienda": None,
        "periodo": None,
        "mese": None,
        "anno": None,
        "timbrature": [],
        "totali": {},
        "errors": []
    }
    
    try:
        # Extract month/year from filename
        # Format: CART_YYYY-MM-DD_YYYY-MM-DD_XXXX_Nome Cognome.pdf
        filename_match = re.search(r'CART_(\d{4})-(\d{2})-\d{2}_(\d{4})-(\d{2})-\d{2}', filename)
        if filename_match:
            result["anno"] = int(filename_match.group(1))
            result["mese"] = int(filename_match.group(2))
        
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            all_text = ""
            all_tables = []
            
            for page in pdf.pages:
                # Extract text
                text = page.extract_text() or ""
                all_text += text + "\n"
                
                # Extract tables
                tables = page.extract_tables()
                all_tables.extend(tables)
            
            # Parse header info
            result["dipendente"] = extract_dipendente(all_text)
            result["azienda"] = extract_azienda(all_text)
            result["periodo"] = extract_periodo(all_text)
            
            # Parse timbrature from tables
            timbrature = parse_timbrature_tables(all_tables, all_text, result["anno"], result["mese"])
            result["timbrature"] = timbrature
            
            # Parse totals
            result["totali"] = extract_totali(all_text)
            
            result["success"] = True
            
    except Exception as e:
        result["errors"].append(str(e))
        
    return result


def extract_dipendente(text: str) -> Optional[str]:
    """Extract employee name from text"""
    # Look for pattern after "Dipendente:" or similar
    patterns = [
        r'Dipendente:\s*(\d+)\s*[-–]\s*([A-Za-z\s]+)',
        r'(\d{4,})\s*[-–]\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(2).strip()
    return None


def extract_azienda(text: str) -> Optional[str]:
    """Extract company name from text"""
    patterns = [
        r'Azienda:\s*(.+?)(?:\n|$)',
        r'(Plastiape\s*S\.p\.A\.)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_periodo(text: str) -> Optional[str]:
    """Extract period from text"""
    match = re.search(r'Periodo:\s*(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})', text)
    if match:
        return f"{match.group(1)} - {match.group(2)}"
    return None


def extract_totali(text: str) -> Dict[str, Any]:
    """Extract totals from text"""
    totali = {}
    
    patterns = {
        "giorni_lavorativi": r'Totale\s+Giorni\s+Lavorativi:\s*(\d+)',
        "giorni_lavorati": r'Totale\s+Giorni\s+Lavorati:\s*(\d+)',
        "ore_lavorative": r'Totale\s+Ore\s+Lavorative:\s*(\d+:\d+)',
        "ore_lavorate": r'Totale\s+Ore\s+Lavorate:\s*(\d+:\d+)',
        "ore_ordinarie": r'Totale\s+Ore\s+Ordinarie:\s*(\d+:\d+)',
        "ore_straordinarie": r'Totale\s+Ore\s+Straordinarie:\s*(\d+:\d+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            if ':' in value:
                # Convert HH:MM to float hours
                parts = value.split(':')
                totali[key] = float(parts[0]) + float(parts[1]) / 60
                totali[f"{key}_str"] = value
            else:
                totali[key] = int(value)
                
    return totali


def parse_timbrature_tables(tables: List, text: str, anno: int, mese: int) -> List[Dict[str, Any]]:
    """Parse timbrature from extracted tables and text"""
    timbrature = []
    
    # Pattern per identificare le righe con date
    # Formato: "Gio 01/01/2026" o "Lun 06/01/2026"
    date_pattern = r'([A-Za-z]{3})\s+(\d{2})/(\d{2})/(\d{4})'
    time_pattern = r'(\d{2}:\d{2})'
    
    lines = text.split('\n')
    
    for line in lines:
        # Check if line contains a date
        date_match = re.search(date_pattern, line)
        if date_match:
            giorno_sett = date_match.group(1).lower()
            giorno = int(date_match.group(2))
            mese_doc = int(date_match.group(3))
            anno_doc = int(date_match.group(4))
            
            # Format date as YYYY-MM-DD
            data = f"{anno_doc}-{mese_doc:02d}-{giorno:02d}"
            
            # Extract times from the line
            times = re.findall(time_pattern, line)
            
            # Parse the line for entry/exit times
            ora_entrata = None
            ora_uscita = None
            ore_lavorate = 0.0
            descrizione = None
            
            # Times typically appear in order: entry1, exit1, entry2, exit2, ... then calculated hours
            # We need to identify which times are entry/exit vs calculated
            
            # Look for Ferie or other justifications
            ferie_match = re.search(r'(\d{2}:\d{2})\s*Ferie', line)
            tkt_match = re.search(r'(\d+)\s*Tkt\s*Mensa', line)
            
            if ferie_match:
                descrizione = f"Ferie {ferie_match.group(1)}"
                # Check if there's also entry/exit
                if len(times) >= 3:
                    # First two might be entry/exit
                    potential_entry = times[0]
                    potential_exit = times[1]
                    # Validate they look like reasonable work times
                    entry_h = int(potential_entry.split(':')[0])
                    exit_h = int(potential_exit.split(':')[0])
                    if 6 <= entry_h <= 12 and 14 <= exit_h <= 22:
                        ora_entrata = potential_entry
                        ora_uscita = potential_exit
            elif tkt_match:
                descrizione = f"Tkt Mensa"
                # Extract entry/exit times
                if len(times) >= 2:
                    # Find the last time which is usually the worked hours
                    # Entry/exit are usually the first two distinct times
                    potential_times = []
                    for t in times:
                        h = int(t.split(':')[0])
                        # Entry times are typically 7-11, exit 15-21
                        potential_times.append((t, h))
                    
                    # Try to identify entry/exit based on hour ranges
                    for t, h in potential_times:
                        if ora_entrata is None and 6 <= h <= 12:
                            ora_entrata = t
                        elif ora_uscita is None and 14 <= h <= 22 and ora_entrata is not None:
                            ora_uscita = t
                            break
            else:
                # Standard day - look for entry/exit
                if len(times) >= 2:
                    for t in times:
                        h = int(t.split(':')[0])
                        if ora_entrata is None and 6 <= h <= 12:
                            ora_entrata = t
                        elif ora_uscita is None and 14 <= h <= 22 and ora_entrata is not None:
                            ora_uscita = t
                            break
            
            # Calculate worked hours if we have entry/exit
            if ora_entrata and ora_uscita:
                entry_parts = ora_entrata.split(':')
                exit_parts = ora_uscita.split(':')
                entry_mins = int(entry_parts[0]) * 60 + int(entry_parts[1])
                exit_mins = int(exit_parts[0]) * 60 + int(exit_parts[1])
                diff_mins = exit_mins - entry_mins
                if diff_mins > 0:
                    ore_lavorate = round(diff_mins / 60, 2)
            
            # Look for explicit worked hours in the line (usually last HH:MM before end)
            ore_match = re.search(r'(\d{2}:\d{2})\s*$', line.strip())
            if not ore_match:
                # Try to find hours at end of data portion
                last_times = re.findall(r'(\d{2}:\d{2})', line[-30:])
                if last_times:
                    last_time = last_times[-1]
                    h = int(last_time.split(':')[0])
                    if h <= 12:  # Likely hours worked, not a time
                        ore_lavorate = h + int(last_time.split(':')[1]) / 60
            
            timbratura = {
                "data": data,
                "giorno_settimana": giorno_sett,
                "ora_entrata": ora_entrata,
                "ora_uscita": ora_uscita,
                "ore_lavorate": ore_lavorate,
                "descrizione": descrizione,
                "raw_line": line.strip()[:100]  # Keep first 100 chars for reference
            }
            
            # Only add if it's a work day (has entry/exit or justification)
            if ora_entrata or ora_uscita or descrizione:
                timbrature.append(timbratura)
    
    return timbrature


def parse_sometime_from_url(url: str) -> Dict[str, Any]:
    """
    Download and parse a SOMEtime PDF from URL.
    """
    import requests
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Extract filename from URL
        filename = url.split('/')[-1]
        if '%20' in filename:
            filename = filename.replace('%20', ' ')
        
        return parse_sometime_pdf(response.content, filename)
    except Exception as e:
        return {
            "success": False,
            "errors": [f"Failed to download PDF: {str(e)}"]
        }
