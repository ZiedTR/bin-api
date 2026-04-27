from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Base de données BIN étendue
BANQUES = {
    # France
    "453998": {"bank": "BNP Paribas", "country": "FR", "country_name": "France"},
    "491652": {"bank": "Société Générale", "country": "FR", "country_name": "France"},
    "492920": {"bank": "Crédit Agricole", "country": "FR", "country_name": "France"},
    "498458": {"bank": "La Banque Postale", "country": "FR", "country_name": "France"},
    "455400": {"bank": "CIC", "country": "FR", "country_name": "France"},
    "451212": {"bank": "LCL", "country": "FR", "country_name": "France"},
    "497010": {"bank": "Caisse d'Epargne", "country": "FR", "country_name": "France"},
    "543004": {"bank": "BNP Paribas Business", "country": "FR", "country_name": "France"},
    "516100": {"bank": "LCL Gold", "country": "FR", "country_name": "France"},
    "524157": {"bank": "CIC Gold", "country": "FR", "country_name": "France"},
    "533300": {"bank": "Caisse d'Epargne Platinum", "country": "FR", "country_name": "France"},
    "539245": {"bank": "Prepaid Solutions", "country": "GB", "country_name": "United Kingdom"},
    "501800": {"bank": "Prepaid Card Services", "country": "GB", "country_name": "United Kingdom"},
    # UK
    "453201": {"bank": "Barclays", "country": "GB", "country_name": "United Kingdom"},
    "411743": {"bank": "HSBC UK", "country": "GB", "country_name": "United Kingdom"},
    "476935": {"bank": "Lloyds Bank", "country": "GB", "country_name": "United Kingdom"},
    "462066": {"bank": "NatWest", "country": "GB", "country_name": "United Kingdom"},
    # Germany
    "400115": {"bank": "Deutsche Bank", "country": "DE", "country_name": "Germany"},
    "462803": {"bank": "Commerzbank", "country": "DE", "country_name": "Germany"},
    "518774": {"bank": "Sparkasse", "country": "DE", "country_name": "Germany"},
    # Belgium
    "453269": {"bank": "BNP Paribas Fortis", "country": "BE", "country_name": "Belgium"},
    "476200": {"bank": "KBC Bank", "country": "BE", "country_name": "Belgium"},
    # Spain
    "454881": {"bank": "BBVA", "country": "ES", "country_name": "Spain"},
    "400491": {"bank": "Santander", "country": "ES", "country_name": "Spain"},
    # Italy
    "432917": {"bank": "UniCredit", "country": "IT", "country_name": "Italy"},
    "476464": {"bank": "Intesa Sanpaolo", "country": "IT", "country_name": "Italy"},
    # Netherlands
    "453978": {"bank": "ING Bank", "country": "NL", "country_name": "Netherlands"},
    "476101": {"bank": "Rabobank", "country": "NL", "country_name": "Netherlands"},
    # US
    "453210": {"bank": "Chase Bank", "country": "US", "country_name": "United States"},
    "411111": {"bank": "Test Bank Virtual", "country": "US", "country_name": "United States"},
    "424242": {"bank": "Stripe Test", "country": "US", "country_name": "United States"},
    "400000": {"bank": "Bank of America", "country": "US", "country_name": "United States"},
    "453300": {"bank": "Wells Fargo", "country": "US", "country_name": "United States"},
    "471700": {"bank": "Citibank", "country": "US", "country_name": "United States"},
    # Singapore
    "453985": {"bank": "DBS Bank", "country": "SG", "country_name": "Singapore"},
    "476543": {"bank": "OCBC Bank", "country": "SG", "country_name": "Singapore"},
    "453001": {"bank": "UOB Bank", "country": "SG", "country_name": "Singapore"},
}

PAYS_RISQUE_ELEVE = ["NG", "GH", "RO", "UA", "RU", "VN", "ID", "PK", "BD", "KE"]
PAYS_RISQUE_MOYEN = ["CN", "IN", "BR", "MX", "TR", "EG", "ZA"]
PAYS_FAIBLE_RISQUE = ["FR", "DE", "GB", "NL", "BE", "SE", "CH", "AT", "DK", "NO", "FI", "SG", "JP", "AU", "CA", "US"]

PREFIXES_PREPAYEE = ["4840", "4754", "4261", "5392", "5018", "6304", "6759"]
PREFIXES_VIRTUELLE = ["4111", "4242", "5100", "5200", "4000"]
PREFIXES_BUSINESS = ["4485", "4716", "5499", "5411", "5543", "4924"]
PREFIXES_CORPORATE = ["4532", "5411", "4716", "5543"]
PREFIXES_GOLD = ["4539", "4916", "5424", "5161", "4551"]
PREFIXES_PLATINUM = ["4929", "5457", "5331", "4917", "5420"]
PREFIXES_INFINITE = ["4903", "5420", "4026"]

def luhn_check(card_number):
    """Algorithme de Luhn corrigé et optimisé"""
    digits = [int(d) for d in card_number if d.isdigit()]
    total = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0

def get_network(bin_number):
    if bin_number.startswith("4"):
        return "Visa"
    elif bin_number[:2] in ["51","52","53","54","55"] or (2221 <= int(bin_number[:4]) <= 2720):
        return "Mastercard"
    elif bin_number[:2] in ["34","37"]:
        return "American Express"
    elif bin_number[:4] in ["6011"] or bin_number[:2] in ["65"] or bin_number[:6] in ["622126", "622925"]:
        return "Discover"
    elif bin_number[:2] == "36" or bin_number[:4] in ["3095", "3096"]:
        return "Diners Club"
    elif bin_number[:4] in ["3528", "3529"] or bin_number[:2] == "35":
        return "JCB"
    elif bin_number[:4] in ["6304", "6759", "6761", "6762", "6763"]:
        return "Maestro"
    elif bin_number[:4] in ["6304", "6771"]:
        return "UnionPay"
    return "Unknown"

def get_card_level(bin_number):
    for prefix in PREFIXES_INFINITE:
        if bin_number.startswith(prefix):
            return "Infinite"
    for prefix in PREFIXES_PLATINUM:
        if bin_number.startswith(prefix):
            return "Platinum"
    for prefix in PREFIXES_GOLD:
        if bin_number.startswith(prefix):
            return "Gold"
    for prefix in PREFIXES_CORPORATE:
        if bin_number.startswith(prefix):
            return "Corporate"
    for prefix in PREFIXES_BUSINESS:
        if bin_number.startswith(prefix):
            return "Business"
    return "Classic"

def is_prepaid(bin_number):
    return any(bin_number.startswith(p) for p in PREFIXES_PREPAYEE)

def is_virtual(bin_number):
    return any(bin_number.startswith(p) for p in PREFIXES_VIRTUELLE)

def get_country_risk(country_code):
    if country_code in PAYS_RISQUE_ELEVE:
        return "ÉLEVÉ"
    elif country_code in PAYS_RISQUE_MOYEN:
        return "MOYEN"
    elif country_code in PAYS_FAIBLE_RISQUE:
        return "FAIBLE"
    return "INCONNU"

def get_bank_info(bin_number):
    # Cherche d'abord sur 6 chiffres puis 4 chiffres
    for length in [6, 5, 4]:
        prefix = bin_number[:length]
        if prefix in BANQUES:
            return BANQUES[prefix]
    return {"bank": "Unknown Bank", "country": "XX", "country_name": "Unknown"}

def calculate_fraud_score(bin_number, bank_info):
    score = 0
    reasons = []

    if is_prepaid(bin_number):
        score += 25
        reasons.append("Carte prépayée détectée")
    if is_virtual(bin_number):
        score += 20
        reasons.append("Carte virtuelle détectée")
    
    country_risk = get_country_risk(bank_info["country"])
    if country_risk == "ÉLEVÉ":
        score += 40
        reasons.append(f"Pays à risque élevé: {bank_info['country_name']}")
    elif country_risk == "MOYEN":
        score += 20
        reasons.append(f"Pays à risque moyen: {bank_info['country_name']}")
    
    if bank_info["bank"] == "Unknown Bank":
        score += 20
        reasons.append("Banque inconnue")
    
    if bin_number.startswith("4111") or bin_number.startswith("4242"):
        score += 50
        reasons.append("Numéro de test détecté")

    if score >= 70:
        risk_level = "ÉLEVÉ"
        recommendation = "Bloquer"
    elif score >= 40:
        risk_level = "MOYEN"
        recommendation = "Vérification 3DS obligatoire"
    elif score >= 20:
        risk_level = "FAIBLE"
        recommendation = "Accepter avec surveillance"
    else:
        risk_level = "MINIMAL"
        recommendation = "Accepter"

    return {
        "score": min(score, 100),
        "niveau": risk_level,
        "recommendation": recommendation,
        "raisons": reasons
    }

def analyze_bin(bin_number):
    bank_info = get_bank_info(bin_number)
    fraud = calculate_fraud_score(bin_number, bank_info)
    network = get_network(bin_number)
    level = get_card_level(bin_number)
    prepaid = is_prepaid(bin_number)
    virtual = is_virtual(bin_number)
    country_risk = get_country_risk(bank_info["country"])

    return {
        "bin": bin_number[:6],
        "reseau": network,
        "banque": bank_info["bank"],
        "pays": bank_info["country"],
        "pays_nom": bank_info["country_name"],
        "risque_pays": country_risk,
        "niveau_carte": level,
        "prepayee": prepaid,
        "virtuelle": virtual,
        "3ds_recommande": fraud["score"] >= 40,
        "fraude": fraud,
        "statut": "valide"
    }

# GET - Vérifier 1 BIN
@app.route('/bin', methods=['GET'])
def check_bin():
    bin_number = request.args.get('numero', '').strip()
    
    if not bin_number or len(bin_number) < 6:
        return jsonify({"erreur": "Numéro BIN invalide - minimum 6 chiffres"}), 400
    if not bin_number.isdigit():
        return jsonify({"erreur": "Le BIN doit contenir uniquement des chiffres"}), 400

    return jsonify(analyze_bin(bin_number))

# POST - Vérifier plusieurs BINs
@app.route('/bin/batch', methods=['POST'])
def check_bin_batch():
    data = request.get_json()
    if not data or 'bins' not in data:
        return jsonify({"erreur": "Paramètre bins manquant"}), 400
    
    bins = data['bins']
    if len(bins) > 50:
        return jsonify({"erreur": "Maximum 50 BINs par requête"}), 400

    results = []
    for bin_number in bins:
        bin_str = str(bin_number).strip()
        if len(bin_str) >= 6 and bin_str.isdigit():
            results.append(analyze_bin(bin_str))
        else:
            results.append({"bin": bin_number, "erreur": "BIN invalide"})

    high_risk = sum(1 for r in results if r.get('fraude', {}).get('niveau') == 'ÉLEVÉ')
    
    return jsonify({
        "total": len(results),
        "resume": {
            "risque_eleve": high_risk,
            "risque_faible": len(results) - high_risk
        },
        "resultats": results
    })

# POST - Valider numéro carte complet
@app.route('/bin/validate', methods=['POST'])
def validate_card():
    data = request.get_json()
    if not data:
        return jsonify({"erreur": "Body JSON manquant"}), 400
    
    numero = str(data.get('numero', '')).strip().replace(' ', '').replace('-', '')
    expiry = data.get('expiry', '')
    
    if not numero or len(numero) < 13:
        return jsonify({"erreur": "Numéro de carte invalide - minimum 13 chiffres"}), 400
    if not numero.isdigit():
        return jsonify({"erreur": "Le numéro doit contenir uniquement des chiffres"}), 400

    luhn_valid = luhn_check(numero)
    bin_info = analyze_bin(numero)
    
    # Vérification expiry si fournie
    expiry_valid = None
    expiry_info = {}
    if expiry:
        try:
            parts = expiry.replace('/', '').replace('-', '')
            if len(parts) == 4:
                month = int(parts[:2])
                year = int("20" + parts[2:])
            elif len(parts) == 6:
                month = int(parts[:2])
                year = int(parts[2:])
            else:
                month, year = 0, 0
            
            now = datetime.now()
            expiry_valid = (year > now.year) or (year == now.year and month >= now.month)
            expiry_info = {
                "mois": month,
                "annee": year,
                "expire": not expiry_valid
            }
        except:
            expiry_valid = None

    # Masquage du numéro
    masked = numero[:4] + " **** " * ((len(numero) - 8) // 4) + " " + numero[-4:]

    return jsonify({
        "numero_masque": masked.strip(),
        "luhn_valide": luhn_valid,
        "longueur_valide": len(numero) in [13, 15, 16, 19],
        "expiry": expiry_info if expiry else None,
        "expiry_valide": expiry_valid,
        "bin_info": bin_info,
        "carte_valide": luhn_valid and len(numero) in [13, 15, 16, 19]
    })

# GET - Score risque uniquement
@app.route('/bin/risk', methods=['GET'])
def risk_score():
    bin_number = request.args.get('numero', '').strip()
    
    if not bin_number or len(bin_number) < 6:
        return jsonify({"erreur": "Numéro BIN invalide"}), 400

    bank_info = get_bank_info(bin_number)
    fraud = calculate_fraud_score(bin_number, bank_info)
    
    return jsonify({
        "bin": bin_number[:6],
        "fraude": fraud,
        "prepayee": is_prepaid(bin_number),
        "virtuelle": is_virtual(bin_number),
        "risque_pays": get_country_risk(bank_info["country"]),
        "pays": bank_info["country"],
        "banque": bank_info["bank"]
    })

# GET - Informations réseau carte
@app.route('/bin/network', methods=['GET'])
def network_info():
    bin_number = request.args.get('numero', '').strip()
    
    if not bin_number or len(bin_number) < 6:
        return jsonify({"erreur": "Numéro BIN invalide"}), 400

    network = get_network(bin_number)
    level = get_card_level(bin_number)
    
    network_limits = {
        "Visa": {"transaction_max": 10000, "contactless_max": 50, "3ds_supported": True},
        "Mastercard": {"transaction_max": 10000, "contactless_max": 50, "3ds_supported": True},
        "American Express": {"transaction_max": 25000, "contactless_max": 50, "3ds_supported": True},
        "Discover": {"transaction_max": 8000, "contactless_max": 25, "3ds_supported": True},
        "Diners Club": {"transaction_max": 15000, "contactless_max": 25, "3ds_supported": False},
    }
    
    limits = network_limits.get(network, {"transaction_max": 5000, "contactless_max": 25, "3ds_supported": False})
    
    return jsonify({
        "bin": bin_number[:6],
        "reseau": network,
        "niveau_carte": level,
        "limites": limits
    })

if __name__ == '__main__':
    app.run(debug=True, port=5003)
