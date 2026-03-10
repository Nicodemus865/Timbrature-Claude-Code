"""
Parser per i PDF delle buste paga Zucchetti
"""

import pdfplumber
import re
import io
from datetime import datetime
from typing import Dict, Any, Optional, List

# Mapping mesi italiano -> numero
MESI_MAP = {
    'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
    'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
    'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
}

def parse_zucchetti_pdf(pdf_content: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Parse a Zucchetti payslip PDF and extract key data.
    
    Args:
        pdf_content: PDF file content as bytes
        filename: Original filename for reference
        
    Returns:
        Dictionary with parsed payslip data
    """
    result = {
        "success": False,
        "filename": filename,
        "mese": None,
        "anno": None,
        "dipendente": {},
        "azienda": {},
        "elementi_retributivi": {},
        "ore": {},
        "straordinari": [],
        "trattenute": [],
        "totali": {},
        "tfr": {},
        "netto": 0.0,
        "raw_text": "",
        "errors": []
    }
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            all_text = ""
            
            for page in pdf.pages:
                text = page.extract_text() or ""
                all_text += text + "\n"
            
            result["raw_text"] = all_text[:2000]  # Keep first 2000 chars for reference
            
            # Parse periodo di retribuzione (mese/anno)
            periodo = extract_periodo(all_text)
            if periodo:
                result["mese"] = periodo.get("mese")
                result["anno"] = periodo.get("anno")
            
            # Parse dati dipendente
            result["dipendente"] = extract_dipendente(all_text)
            
            # Parse dati azienda
            result["azienda"] = extract_azienda(all_text)
            
            # Parse elementi retributivi
            result["elementi_retributivi"] = extract_elementi_retributivi(all_text)
            
            # Parse ore lavorate
            result["ore"] = extract_ore(all_text)
            
            # Parse straordinari
            result["straordinari"] = extract_straordinari(all_text)
            
            # Parse trattenute
            result["trattenute"] = extract_trattenute(all_text)
            
            # Parse totali
            result["totali"] = extract_totali(all_text)
            
            # Parse TFR
            result["tfr"] = extract_tfr(all_text)
            
            # Parse netto
            result["netto"] = extract_netto(all_text)
            
            result["success"] = True
            
    except Exception as e:
        result["errors"].append(str(e))
        
    return result


def extract_periodo(text: str) -> Optional[Dict[str, int]]:
    """Extract reference month and year"""
    # Pattern: "PERIODO DI RETRIBUZIONE: Gennaio 2026" or similar
    patterns = [
        r'PERIODO\s+DI\s+RETRIBUZIONE[:\s]+(\w+)\s+(\d{4})',
        r'Retribuzione[:\s]+(\w+)\s+(\d{4})',
        r'Mese[:\s]+(\w+)\s+(\d{4})',
        r'(\w+)\s+(\d{4})\s+Variabili',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            mese_str = match.group(1).lower()
            anno = int(match.group(2))
            mese = MESI_MAP.get(mese_str)
            if mese:
                return {"mese": mese, "anno": anno}
    
    # Try to find month/year from context
    for mese_nome, mese_num in MESI_MAP.items():
        pattern = rf'\b{mese_nome}\s+(\d{{4}})\b'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {"mese": mese_num, "anno": int(match.group(1))}
    
    return None


def extract_dipendente(text: str) -> Dict[str, Any]:
    """Extract employee data"""
    dipendente = {}
    
    # Nome
    match = re.search(r'COGNOMEENOME[:\s]+([A-Z\s]+)', text)
    if not match:
        match = re.search(r'([A-Z]{2,}\s+[A-Z]{2,})\s+\(', text)
    if match:
        dipendente["nome"] = match.group(1).strip().title()
    
    # Codice fiscale
    match = re.search(r'Codice\s+Fiscale[:\s]+([A-Z0-9]{16})', text, re.IGNORECASE)
    if not match:
        match = re.search(r'\(([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])', text)
    if match:
        dipendente["codice_fiscale"] = match.group(1)
    
    # Matricola
    match = re.search(r'Matricola[:\s]+(\d+)', text, re.IGNORECASE)
    if match:
        dipendente["matricola"] = match.group(1)
    
    # Data assunzione
    match = re.search(r'Data\s+Assunzione[:\s]+(\d{2}-\d{2}-\d{4})', text, re.IGNORECASE)
    if match:
        dipendente["data_assunzione"] = match.group(1)
    
    # Livello
    match = re.search(r'Livello[:\s]+(\d+)', text, re.IGNORECASE)
    if match:
        dipendente["livello"] = int(match.group(1))
    
    # Data nascita
    match = re.search(r'Data\s+di\s+Nascita[:\s]+(\d{2}-\d{2}-\d{4})', text, re.IGNORECASE)
    if match:
        dipendente["data_nascita"] = match.group(1)
    
    return dipendente


def extract_azienda(text: str) -> Dict[str, Any]:
    """Extract company data"""
    azienda = {}
    
    # Nome azienda
    patterns = [
        r'PLASTI[-\s]?APE\s*S\.?P\.?A\.?',
        r'Plastiape\s*S\.?p\.?A\.?',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            azienda["nome"] = "Plastiape S.p.A."
            break
    
    # Codice azienda
    match = re.search(r'Codice\s+Azienda[:\s]+(\d+)', text, re.IGNORECASE)
    if match:
        azienda["codice"] = match.group(1)
    
    # Posizione INPS
    match = re.search(r'Posizione\s+Inps[:\s]+([\d/]+)', text, re.IGNORECASE)
    if match:
        azienda["posizione_inps"] = match.group(1)
    
    return azienda


def extract_elementi_retributivi(text: str) -> Dict[str, float]:
    """Extract salary elements"""
    elementi = {}
    
    # Paga base - look for "PAGA BASE" followed by number
    match = re.search(r'PAGA\s+BASE\s+([\d.]+[,][\d]+)', text)
    if match:
        value = match.group(1).replace('.', '').replace(',', '.')
        try:
            elementi["paga_base"] = float(value)
        except:
            pass
    
    # Scatti anzianità
    match = re.search(r'SCATTI\s+N\.?[\d,]+\s+([\d.]+[,][\d]+)', text)
    if match:
        value = match.group(1).replace('.', '').replace(',', '.')
        try:
            elementi["scatti_anzianita"] = float(value)
        except:
            pass
    
    # Superminimo / SUP.ASS.
    match = re.search(r'SUP\.?\s*ASS\.?\s+([\d.]+[,][\d]+)', text)
    if match:
        value = match.group(1).replace('.', '').replace(',', '.')
        try:
            elementi["superminimo"] = float(value)
        except:
            pass
    
    # Premio incarico / Pr.Inc.
    match = re.search(r'Pr\.?\s*Inc\.?\s+([\d.]+[,][\d]+)', text)
    if match:
        value = match.group(1).replace('.', '').replace(',', '.')
        try:
            elementi["premio_incarico"] = float(value)
        except:
            pass
    
    return elementi


def extract_ore(text: str) -> Dict[str, float]:
    """Extract worked hours"""
    ore = {}
    
    # Ore ordinarie
    match = re.search(r'Ore\s+ordinarie[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'ordinarie[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if match:
        value = match.group(1).replace(',', '.')
        try:
            ore["ordinarie"] = float(value)
        except:
            pass
    
    # Ore straordinarie totali
    match = re.search(r'Ore\s+straordinarie[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if not match:
        match = re.search(r'straordinarie[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if match:
        value = match.group(1).replace(',', '.')
        try:
            ore["straordinarie"] = float(value)
        except:
            pass
    
    return ore


def extract_straordinari(text: str) -> List[Dict[str, Any]]:
    """Extract overtime details"""
    straordinari = []
    
    # Pattern: Straordinario XX% - ore - importo
    patterns = [
        r'Straordinario\s+(\d+)%.*?([\d.,]+)\s*ORE.*?COMPETENZE[:\s]+([\d.,]+)',
        r'(\d{6})\s+Straordinario\s*(\d+)%.*?([\d.,]+)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                straord = {
                    "percentuale": int(match.group(1)) if match.group(1).isdigit() else int(match.group(2)),
                    "importo": float(match.group(3).replace('.', '').replace(',', '.'))
                }
                straordinari.append(straord)
            except:
                pass
    
    return straordinari


def extract_trattenute(text: str) -> List[Dict[str, Any]]:
    """Extract deductions"""
    trattenute = []
    
    deduction_patterns = {
        "contributo_ivs": r'Contributo\s+IVS.*?TRATTENUTE[:\s]+([\d.,]+)',
        "irpef": r'Ritenute\s+IRPEF.*?([\d.,]+)',
        "addizionale_regionale": r'Addizionale\s+regionale.*?([\d.,]+)',
        "addizionale_comunale": r'Addizionale\s+comunale.*?TRATTENUTE[:\s]+([\d.,]+)',
        "trattenuta_sindacale": r'Trattenuta\s+sindacale.*?TRATTENUTE[:\s]+([\d.,]+)',
        "contributo_cigs": r'Contributo\s+CIGS.*?TRATTENUTE[:\s]+([\d.,]+)',
    }
    
    for key, pattern in deduction_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1).replace('.', '').replace(',', '.'))
                trattenute.append({
                    "tipo": key,
                    "importo": value
                })
            except:
                pass
    
    return trattenute


def extract_totali(text: str) -> Dict[str, float]:
    """Extract totals"""
    totali = {}
    
    # Totale competenze
    match = re.search(r'TOTALE\s+COMPETENZE[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if match:
        try:
            totali["competenze"] = float(match.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    
    # Totale trattenute
    match = re.search(r'TOTALE\s+TRATTENUTE[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if match:
        try:
            totali["trattenute"] = float(match.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    
    return totali


def extract_tfr(text: str) -> Dict[str, float]:
    """Extract TFR (severance pay) data"""
    tfr = {}
    
    # Retribuzione utile TFR
    match = re.search(r'Retribuzione\s+utile\s+T\.?F\.?R\.?[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if match:
        try:
            tfr["retribuzione_utile"] = float(match.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    
    # Quota TFR
    match = re.search(r'Quota\s+T\.?F\.?R\.?[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if match:
        try:
            tfr["quota"] = float(match.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    
    # TFR a fondi
    match = re.search(r'TFR\s+a\s+fondi[:\s]+([\d.,]+)', text, re.IGNORECASE)
    if match:
        try:
            tfr["a_fondi"] = float(match.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    
    return tfr


def extract_netto(text: str) -> float:
    """Extract net pay"""
    patterns = [
        r'NETTO\s*DEL\s*MESE[:\s]*([\d.]+[,][\d]+)',
        r'NETTOsDELsMESE[:\s]*([\d.]+[,][\d]+)',  # Zucchetti uses 's' as separator
        r'NETTO[:\s]*([\d.]+[,][\d]+)\s*€',
        r'Netto\s+in\s+busta[:\s]*([\d.]+[,][\d]+)',
        r'NETTO\s+([\d.]+[,][\d]+)',
        r'([\d.]+[,][\d]+)\s*€\s*$',  # Amount followed by € at end
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            try:
                value = match.group(1).replace('.', '').replace(',', '.')
                net = float(value)
                if net > 0:
                    return net
            except:
                pass
    
    # Try to find the pattern with newline between label and value
    match = re.search(r'NETTOsDELsMESE\s*\n?\s*([\d.]+[,][\d]+)', text, re.IGNORECASE | re.MULTILINE)
    if match:
        try:
            value = match.group(1).replace('.', '').replace(',', '.')
            return float(value)
        except:
            pass
    
    return 0.0


def parse_zucchetti_from_url(url: str) -> Dict[str, Any]:
    """
    Download and parse a Zucchetti payslip PDF from URL.
    """
    import requests
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Extract filename from URL
        filename = url.split('/')[-1]
        if '%20' in filename:
            filename = filename.replace('%20', ' ')
        
        return parse_zucchetti_pdf(response.content, filename)
    except Exception as e:
        return {
            "success": False,
            "errors": [f"Failed to download PDF: {str(e)}"]
        }
