from flask import Flask, request, jsonify

app = Flask(__name__)

# Base de données BIN simplifiée
BIN_DATABASE = {
    "4": {"network": "Visa", "type": "debit"},
    "51": {"network": "Mastercard", "type": "credit"},
    "52": {"network": "Mastercard", "type": "credit"},
    "53": {"network": "Mastercard", "type": "credit"},
    "54": {"network": "Mastercard", "type": "credit"},
    "55": {"network": "Mastercard", "type": "credit"},
    "34": {"network": "American Express", "type": "credit"},
    "37": {"network": "American Express", "type": "credit"},
    "6011": {"network": "Discover", "type": "credit"},
    "36": {"network": "Diners Club", "type": "credit"},
}

PAYS_RISQUE_ELEVE = ["NG", "GH", "RO", "UA", "RU", "VN", "ID"]

PREFIXES_PREPAYEE = ["4840", "4754", "4261", "5392", "5018"]
PREFIXES_VIRTUELLE = ["4111", "4242", "5100", "5200"]
PREFIXES_BUSINESS = ["4485", "4716", "5499", "5411"]
PREFIXES_GOLD = ["4539", "4916", "5424", "5161"]
PREFIXES_PLATINUM = ["4532", "4929", "5457", "5331"]

BANQUES = {
    "4532": {"bank": "Visa Classic", "country": "US", "country_name": "United States"},
    "4539": {"bank": "BNP Paribas", "country": "FR", "country_name": "France"},
    "4916": {"bank": "Société Générale", "country": "FR", "country_name": "France"},
    "4929": {"bank": "Crédit Agricole", "country": "FR", "country_name": "France"},
    "4111": {"bank": "Test Bank Virtual", "country": "US", "country_name": "United States"},
    "4242": {"bank": "Stripe Test", "country": "US", "country_name": "United States"},
    "5499": {"bank": "BNP Business", "country": "FR", "country_name": "France"},
    "5411": {"bank": "Amex Business FR", "country": "FR", "country_name": "France"},
    "5161": {"bank": "LCL Gold", "country": "FR", "country_name": "France"},
    "5457": {"bank": "CIC Gold", "country": "FR", "country_name": "France"},
    "5331": {"bank": "Caisse d'Epargne Platinum", "country": "FR", "country_name": "France"},
    "5392": {"bank": "Prepaid Solutions", "country": "GB", "country_name": "United Kingdom"},
    "5018": {"bank": "Prepaid Card Services", "country": "GB", "country_name": "United Kingdom"},
}

def get_network(bin_number):
    if bin_number.startswith("4"):
        return "Visa"
    elif bin_number[:2] in ["51","52","53","54","55"]:
        return "Mastercard"
    elif bin_number[:2] in ["34","37"]:
        return "American Express"
    elif bin_number[:4] == "6011":
        return "Discover"
    elif bin_number[:2] == "36":
        return "Diners Club"
    return "Unknown"

def get_card_level(bin_number):
    for prefix in PREFIXES_PLATINUM:
        if bin_number.startswith(prefix):
            return "Platinum"
    for prefix in PREFIXES_GOLD:
        if bin_number.startswith(prefix):
            return "Gold"
    for prefix in PREFIXES_BUSINESS:
        if bin_number.startswith(prefix):
            return "Business"
    return "Classic"

def is_prepaid(bin_number):
    for prefix in PREFIXES_PREPAYEE:
        if bin_number.startswith(prefix):
            return True
    return False

def is_virtual(bin_number):
    for prefix in PREFIXES_VIRTUELLE:
        if bin_number.startswith(prefix):
            return True
    return False

def get_bank_info(bin_number):
    for prefix in sorted(BANQUES.keys(), key=len, reverse=True):
        if bin_number.startswith(prefix):
            return BANQUES[prefix]
    return {"bank": "Unknown Bank", "country": "XX", "country_name": "Unknown"}

def calculate_fraud_score(bin_number, bank_info):
    score = 0
    
    if is_prepaid(bin_number):
        score += 30
    if is_virtual(bin_number):
        score += 20
    if bank_info["country"] in PAYS_RISQUE_ELEVE:
        score += 40
    if bank_info["bank"] == "Unknown Bank":
        score += 20
    if bin_number.startswith("4111") or bin_number.startswith("4242"):
        score += 50

    if score >= 70:
        risk_level = "ÉLEVÉ"
        recommendation = "Bloquer"
    elif score >= 40:
        risk_level = "MOYEN"
        recommendation = "Vérification 3DS obligatoire"
    else:
        risk_level = "FAIBLE"
        recommendation = "Accepter"

    return {
        "score": min(score, 100),
        "niveau": risk_level,
        "recommendation": recommendation
    }

def analyze_bin(bin_number):
    bank_info = get_bank_info(bin_number)
    fraud = calculate_fraud_score(bin_number, bank_info)
    network = get_network(bin_number)
    level = get_card_level(bin_number)
    prepaid = is_prepaid(bin_number)
    virtual = is_virtual(bin_number)

    return {
        "bin": bin_number[:6],
        "reseau": network,
        "banque": bank_info["bank"],
        "pays": bank_info["country"],
        "pays_nom": bank_info["country_name"],
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
    bin_number = request.args.get('numero', '')
    
    if not bin_number or len(bin_number) < 6:
        return jsonify({"erreur": "Numéro BIN invalide - minimum 6 chiffres"}), 400
    
    if not bin_number.isdigit():
        return jsonify({"erreur": "Le BIN doit contenir uniquement des chiffres"}), 400

    result = analyze_bin(bin_number)
    return jsonify(result)

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
        if len(str(bin_number)) >= 6 and str(bin_number).isdigit():
            results.append(analyze_bin(str(bin_number)))
        else:
            results.append({"bin": bin_number, "erreur": "BIN invalide"})

    return jsonify({
        "total": len(results),
        "resultats": results
    })

# POST - Valider numéro carte complet
@app.route('/bin/validate', methods=['POST'])
def validate_card():
    data = request.get_json()
    numero = str(data.get('numero', ''))
    
    if not numero or len(numero) < 13:
        return jsonify({"erreur": "Numéro de carte invalide"}), 400

    # Algorithme de Luhn
    def luhn_check(card_number):
        digits = [int(d) for d in card_number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        total = sum(odd_digits)
        for d in even_digits:
            total += sum(divmod(d * 2, 10))
        return total % 10 == 0

    luhn_valid = luhn_check(numero)
    bin_info = analyze_bin(numero)

    return jsonify({
        "numero_masque": numero[:4] + "****" * ((len(numero)-8)//4) + numero[-4:],
        "luhn_valide": luhn_valid,
        "longueur_valide": len(numero) in [13, 15, 16, 19],
        "bin_info": bin_info,
        "carte_valide": luhn_valid and len(numero) in [13, 15, 16, 19]
    })

# GET - Score risque uniquement
@app.route('/bin/risk', methods=['GET'])
def risk_score():
    bin_number = request.args.get('numero', '')
    
    if not bin_number or len(bin_number) < 6:
        return jsonify({"erreur": "Numéro BIN invalide"}), 400

    bank_info = get_bank_info(bin_number)
    fraud = calculate_fraud_score(bin_number, bank_info)
    
    return jsonify({
        "bin": bin_number[:6],
        "fraude": fraud,
        "prepayee": is_prepaid(bin_number),
        "virtuelle": is_virtual(bin_number),
        "pays_risque": bank_info["country"] in PAYS_RISQUE_ELEVE
    })

if __name__ == '__main__':
    app.run(debug=True, port=5003)
