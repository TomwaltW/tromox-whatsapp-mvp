#!/usr/bin/env python3
"""Generate 04-eval/synthetic-samples.csv (80 synthetic multilingual enquiries).

SYNTHETIC DATA - written by hand for this repository, not taken from any real customer.
It exists only to run the tool end to end; acceptance needs real labelled enquiries.
Phone numbers use reserved / zero-padded ranges and are never contacted.

Gold labels follow shared/prompt_blocks/extraction-rules.md. Escalation is derived here in
the same priority order as the rules so the labels stay consistent:
  explicit reason (complaint > human > price) > low_confidence (genuinely ambiguous B2B/B2C,
  labelled B2B by the asymmetric-cost rule) > b2b_qualified (type + who + market).

    python 04-eval/tools/make_synthetic.py            # rewrite the CSV
    python 04-eval/tools/make_synthetic.py --check    # exit 1 if the CSV is stale
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from tromox_lead import LABEL_COLUMNS, country_from_phone, normalize_e164

OUT = Path(__file__).resolve().parents[1] / "synthetic-samples.csv"

COMPLAINT, HUMAN, PRICE = "complaint_warranty_legal_safety", "human_requested", "price_negotiation"


def row(lang, phone, phone_country, text, segment, *, b2b=None, b2c=None, stated=None, products=(),
        who=False, esc=None, ambiguous=False, note=""):
    return dict(lang=lang, phone=phone, phone_country=phone_country, text=text, segment=segment, b2b=b2b,
                b2c=b2c, stated=stated, products=products, who=who, esc=esc, ambiguous=ambiguous, note=note)


ROWS = [
    # ---------------------------------------------------------------- English (28)
    row("en", "+447700900101", "GB", "Hi Tromox! [IG-2609] We are Northline Motors Ltd, a motorcycle dealership in Manchester, UK. We'd like to become a Tromox dealer. Interested in the MC10 and Ukko, around 20 units a year. I'm Daniel Reeves, owner.", "B2B", b2b="dealer", stated="GB", products=("MC10", "UKKO"), who=True),
    row("en", "+61491570156", "AU", "Hello, we are an e-mobility distributor covering all of Australia with 14 sub-dealers. We would like to add Tromox to our portfolio. Which models are available for our market?", "B2B", b2b="distributor", stated="AU"),
    row("en", "+971500000101", "AE", "We operate a food delivery fleet in Dubai with about 120 riders and want to switch to electric. Is the M05 suitable for delivery use, and how do fleet orders work?", "B2B", b2b="fleet", products=("M05",), note="仅城市无国家：国家取号码国家码"),
    row("en", "+27820000101", "ZA", "Good day. My company imports motorcycles into South Africa, we handle homologation and customs ourselves. We are interested in importing Tromox, starting with one container of mixed models.", "B2B", b2b="importer", stated="ZA"),
    row("en", "+6580000101", "SG", "Hi, we're a corporate gifting company in Singapore and want to buy 30 Mino scooters as employee rewards for a client. Can a sales representative contact me about a bulk order?", "B2B", b2b="other", stated="SG", products=("MINO",), esc=HUMAN),
    row("en", "+16135550101", "CA", "Hello, I own two scooter shops in Toronto, Canada. Please send me your dealer price list and MOQ for the Ukko and MC10.", "B2B", b2b="dealer", stated="CA", products=("MC10", "UKKO"), esc=PRICE),
    row("en", "+12025550101", "US", "Hi, I'm interested in buying a few of your bikes, maybe 3 or 4. Can you send me some info?", "B2B", b2b="other", ambiguous=True, note="歧义：3 到 4 台，个人或小商家都可能；按不对称原则标 B2B"),
    row("en", "+12025550102", "US", "Hi, I'm based in Mexico City, Mexico and run a small dealership called MotoVerde. We'd love to sell Tromox here. Which models can you ship to Mexico?", "B2B", b2b="dealer", stated="MX", who=True, note="自述国家与号码国家不同"),
    row("en", "+6281200000101", "ID", "Hello from Bali! We run a scooter rental business for tourists with 60 scooters. Thinking about going electric next season. Do you work with rental companies?", "B2B", b2b="fleet", note="仅地区无国家：国家取号码国家码"),
    row("en", "+12025550103", "US", "Hi Tromox! [FB-2609] How much does the MC10 cost and can I order it online in the US?", "B2C", b2c="buy", stated="US", products=("MC10",)),
    row("en", "+447700900102", "GB", "Hi, is there somewhere in London where I can test ride the Ukko?", "B2C", b2c="test_ride", products=("UKKO",)),
    row("en", "+12025550104", "US", "My Mino won't connect to the app after the last update. How do I pair it again?", "B2C", b2c="support", products=("MINO",)),
    row("en", "+61491570157", "AU", "Hi Tromox! [QR-2610] I need a replacement rear mirror and a spare charger for my M03. Where can I buy parts?", "B2C", b2c="parts", products=("M03",)),
    row("en", "+447700900103", "GB", "Hi, I bought an Ukko S+ four months ago. Does the warranty cover the display if it stops working?", "B2C", b2c="warranty", products=("UKKO",), note="质保范围提问，不是索赔，不升级"),
    row("en", "+12025550105", "US", "I've been waiting six weeks for my warranty repair and nobody answers my emails. This is unacceptable. I want a refund or I will take legal action.", "B2C", b2c="warranty", esc=COMPLAINT),
    row("en", "+14165550102", "CA", "Can I please speak to a real person? I have questions about buying an MC10.", "B2C", b2c="buy", products=("MC10",), esc=HUMAN),
    row("en", "+12025550106", "US", "Hey, I'm a student. Any chance of a discount on the Mino if I buy this week?", "B2C", b2c="buy", products=("MINO",), esc=PRICE),
    row("en", "+447700900104", "GB", "Urgent: the battery of my M05 got very hot and started smoking while charging. What should I do?", "B2C", b2c="warranty", products=("M05",), esc=COMPLAINT, note="安全事故：必须升级"),
    row("en", "+12025550107", "US", "Do you have any owner clubs or community rides for Tromox riders in California?", "B2C", b2c="other"),
    row("en", "+12025550108", "US", "Hi Tromox! [AD-2610A] Do you offer financing for the M05? I live in Austin.", "B2C", b2c="buy", products=("M05",)),
    row("en", "+447700900105", "GB", "Do I need a motorcycle license to ride the Mino in the UK?", "B2C", b2c="other", stated="GB", products=("MINO",)),
    row("en", "+61491570158", "AU", "Looking for a replacement battery for my MC10 StreetX. I'm in Melbourne. Do you ship batteries?", "B2C", b2c="parts", products=("MC10",)),
    row("en", "+12025550109", "US", "How long should I charge the Ukko before the first ride? The manual isn't clear.", "B2C", b2c="support", products=("UKKO",)),
    row("en", "+447700900106", "GB", "Hi, I'm moving to Ireland next month. Are there any Tromox dealers in Dublin where I can see the M05?", "B2C", b2c="test_ride", stated="IE", products=("M05",), note="自述国家与号码国家不同"),
    row("en", "+12025550110", "US", "Hi Tromox! [IG-2609]", "unknown", note="仅问候：等待客户按按钮"),
    row("en", "+2348030000101", "NG", "Congratulations! You have been selected for a free crypto bonus. Click here to claim now!!!", "unknown", note="垃圾消息"),
    row("en", "+31600000101", "NL", "Hello, I am a mechanical engineer with 5 years of experience. Are there any job openings at Tromox Europe?", "unknown", note="求职"),
    row("en", "+8613800000101", "CN", "Dear Sir/Madam, we are a manufacturer of lithium battery packs and brake systems. We would like to be your supplier. Please find our catalog.", "unknown", note="供应商推销：看似 B 端，实际不是客户"),
    # ---------------------------------------------------------------- German (12)
    row("de", "+4917604069011", "DE", "Hallo Tromox! [IG-2609] Wir sind das Zweiradhaus Lindner in Leipzig, Deutschland, und möchten Tromox-Händler werden. Interesse an MC10 und Ukko, ca. 15 Fahrzeuge pro Jahr. Ansprechpartner: Markus Lindner, Inhaber.", "B2B", b2b="dealer", stated="DE", products=("MC10", "UKKO"), who=True),
    row("de", "+4917604069012", "DE", "Guten Tag, wir sind ein E-Mobility-Großhändler mit Sitz in Österreich und beliefern rund 40 Fachhändler. Wir möchten den Vertrieb von Tromox für Österreich übernehmen. Firma: AlpenVolt Handels GmbH.", "B2B", b2b="distributor", stated="AT", who=True, note="自述国家与号码国家不同"),
    row("de", "+41760000101", "CH", "Wir betreiben einen Lieferdienst in Zürich mit 35 Fahrern und suchen elektrische Roller für die Flotte. Ist der M05 dafür geeignet?", "B2B", b2b="fleet", products=("M05",)),
    row("de", "+4917604069013", "DE", "Guten Tag, ich habe ein Motorradgeschäft in Köln. Bitte senden Sie mir Ihre Händlerpreisliste und die Zahlungsbedingungen.", "B2B", b2b="dealer", esc=PRICE),
    row("de", "+4917604069014", "DE", "Hallo, was kostet die Mino und wo kann ich sie in Deutschland kaufen?", "B2C", b2c="buy", stated="DE", products=("MINO",)),
    row("de", "+4917604069015", "DE", "Kann ich den Ukko irgendwo in München Probe fahren?", "B2C", b2c="test_ride", products=("UKKO",)),
    row("de", "+4917604069016", "DE", "Meine MC10 lädt nicht mehr vollständig, die Anzeige bleibt bei 80 % stehen. Was kann ich tun?", "B2C", b2c="support", products=("MC10",), note="故障排查提问，未提出保修要求"),
    row("de", "+4917604069017", "DE", "Guten Tag, das Display meines Ukko ist nach drei Monaten ausgefallen. Ich möchte das als Garantiefall melden. Wie gehe ich vor?", "B2C", b2c="warranty", products=("UKKO",), esc=COMPLAINT, note="明确提出质保索赔"),
    row("de", "+436600000101", "AT", "Wo bekomme ich Ersatzteile für die M03, konkret einen neuen Seitenständer?", "B2C", b2c="parts", products=("M03",)),
    row("de", "+4917604069018", "DE", "Gibt es die MC10 auch in anderen Farben als auf eurer Website?", "B2C", b2c="buy", products=("MC10",)),
    row("de", "+4917604069019", "DE", "Ich möchte bitte mit einem Mitarbeiter sprechen, nicht mit einem Bot.", "unknown", esc=HUMAN, note="类型未知但明确要求真人"),
    row("de", "+4917604069020", "DE", "Hi, ich bin Content Creator mit 80k Followern auf Instagram und würde gerne eine Kooperation mit Tromox machen. Habt ihr ein Influencer-Programm?", "unknown", note="媒体/达人合作"),
    # ---------------------------------------------------------------- Spanish (12)
    row("es", "+573000000101", "CO", "Hola Tromox! [TT-2610] Somos Movilidad Andina S.A.S., distribuidores de motos eléctricas en Colombia con una red de 12 puntos de venta. Queremos distribuir Tromox en el país. Soy Camila Rojas, gerente comercial.", "B2B", b2b="distributor", stated="CO", who=True),
    row("es", "+34600000101", "ES", "Buenas tardes, tengo una tienda de motos en Sevilla y me interesa vender la Mino y la MC10. ¿Qué requisitos piden para ser concesionario?", "B2B", b2b="dealer", products=("MC10", "MINO")),
    row("es", "+34600000102", "ES", "Hola, somos una empresa importadora y queremos llevar Tromox a Chile. Manejamos homologación y aduanas, y pensamos empezar con un contenedor. ¿Qué documentación necesitan?", "B2B", b2b="importer", stated="CL", note="自述国家与号码国家不同"),
    row("es", "+525500000101", "MX", "Hola, me interesan unas 3 motos, ¿hacen envíos a Guadalajara?", "B2B", b2b="other", ambiguous=True, note="歧义：数量 3，用途不明；按不对称原则标 B2B"),
    row("es", "+34600000103", "ES", "Hola, ¿cuánto cuesta la Ukko y dónde la puedo comprar en España?", "B2C", b2c="buy", stated="ES", products=("UKKO",)),
    row("es", "+34600000104", "ES", "Hola Tromox! [IG-2609] Vi la Mino en Instagram. ¿Dónde puedo probarla en Valencia?", "B2C", b2c="test_ride", products=("MINO",)),
    row("es", "+5491100000101", "AR", "Mi M05 no enciende después de la lluvia de ayer. ¿Qué puedo revisar?", "B2C", b2c="support", products=("M05",)),
    row("es", "+34600000105", "ES", "Quiero poner una queja: los frenos de mi MC10 fallaron y tuve un accidente. Necesito que alguien me llame hoy mismo.", "B2C", b2c="warranty", products=("MC10",), esc=COMPLAINT, note="事故与投诉优先于要求真人"),
    row("es", "+525500000102", "MX", "¿Venden baterías de repuesto para la Mino B? Vivo en Monterrey.", "B2C", b2c="parts", products=("MINO",)),
    row("es", "+34600000106", "ES", "Quiero comprar dos Ukko, una para mi esposa y otra para mí. ¿Tienen stock ahora?", "B2C", b2c="buy", products=("UKKO",), note="两台自用，明确是个人"),
    row("es", "+56900000101", "CL", "¿La garantía cubre la batería si la moto se usa todos los días para ir al trabajo?", "B2C", b2c="warranty"),
    row("es", "+573000000102", "CO", "Hola", "unknown", note="仅问候"),
    # ---------------------------------------------------------------- French (10)
    row("fr", "+33639980101", "FR", "Bonjour Tromox ! [FB-2609] Nous sommes Cycles & Motos Lemaire, concession deux-roues à Lyon, France. Nous souhaitons devenir revendeur Tromox. Intérêt pour la MC10, environ 10 unités par an. Julien Lemaire, gérant.", "B2B", b2b="dealer", stated="FR", products=("MC10",), who=True),
    row("fr", "+33639980102", "FR", "Bonjour, notre société distribue des scooters électriques en Belgique auprès d'une trentaine de revendeurs. Nous aimerions représenter Tromox en Belgique.", "B2B", b2b="distributor", stated="BE", note="自述国家与号码国家不同"),
    row("fr", "+212600000101", "MA", "Nous gérons un service de livraison à Casablanca avec 50 livreurs. Vos modèles conviennent-ils à un usage intensif de livraison ?", "B2B", b2b="fleet"),
    row("fr", "+33639980103", "FR", "Bonjour, quel est le prix de l'Ukko et où puis-je l'acheter en France ?", "B2C", b2c="buy", stated="FR", products=("UKKO",)),
    row("fr", "+33639980104", "FR", "Est-il possible d'essayer la Mino à Bordeaux ?", "B2C", b2c="test_ride", products=("MINO",)),
    row("fr", "+32470000101", "BE", "Comment réinitialiser l'application après avoir changé de téléphone ? Mon M05 n'apparaît plus.", "B2C", b2c="support", products=("M05",)),
    row("fr", "+33639980105", "FR", "Cela fait deux mois que ma MC10 est en panne sous garantie et le revendeur refuse de la réparer. Je vais saisir une association de consommateurs.", "B2C", b2c="warranty", products=("MC10",), esc=COMPLAINT),
    row("fr", "+33639980106", "FR", "Bonjour, la M03 est-elle homologuée pour transporter un passager en France ?", "B2C", b2c="other", stated="FR", products=("M03",)),
    row("fr", "+33639980107", "FR", "Bonjour, je suis étudiant en commerce international et je cherche un stage. Recrutez-vous chez Tromox Europe ?", "unknown", note="求职"),
    row("fr", "+15145550101", "CA", "Bonjour Tromox ! [YT-2609]", "unknown", note="仅问候"),
    # ---------------------------------------------------------------- Portuguese (9)
    row("pt", "+5511900000101", "BR", "Olá Tromox! [IG-2609] Somos distribuidores de veículos elétricos em São Paulo, Brasil, com 25 lojas parceiras. Queremos distribuir a Tromox no Brasil. Quais modelos estão disponíveis?", "B2B", b2b="distributor", stated="BR"),
    row("pt", "+351910000101", "PT", "Boa tarde, tenho uma loja de motas em Lisboa, Portugal. Podem enviar a tabela de preços para revendedores?", "B2B", b2b="dealer", stated="PT", esc=PRICE),
    row("pt", "+351910000102", "PT", "Olá, quanto custa a MC10 e vocês entregam em Portugal?", "B2C", b2c="buy", stated="PT", products=("MC10",)),
    row("pt", "+351910000103", "PT", "Onde posso fazer um test ride da Ukko no Porto?", "B2C", b2c="test_ride", products=("UKKO",)),
    row("pt", "+5511900000102", "BR", "A minha Mino não carrega até 100%. Há algum procedimento para calibrar a bateria?", "B2C", b2c="support", products=("MINO",)),
    row("pt", "+5511900000103", "BR", "Preciso de um carregador novo para a M03. Onde encontro peças em Curitiba?", "B2C", b2c="parts", products=("M03",)),
    row("pt", "+5511900000104", "BR", "Quero falar com um atendente, por favor. É sobre a compra de uma M05.", "B2C", b2c="buy", products=("M05",), esc=HUMAN),
    row("pt", "+5511900000105", "BR", "Ganhe dinheiro rápido trabalhando de casa! Clique no link e saiba mais.", "unknown", note="垃圾消息"),
    row("pt", "+5511900000106", "BR", "Oi, tudo bem?", "unknown", note="仅问候"),
    # ---------------------------------------------------------------- Italian (9)
    row("it", "+393330000101", "IT", "Ciao Tromox! [WEB-2610] Siamo Moto Elettra Srl, concessionaria a Bologna, Italia. Vorremmo diventare rivenditori Tromox: ci interessano Ukko e Mino, circa 12 pezzi l'anno. Sono Giulia Ferri, titolare.", "B2B", b2b="dealer", stated="IT", products=("MINO", "UKKO"), who=True),
    row("it", "+393330000102", "IT", "Buongiorno, gestiamo un e-commerce di mobilità elettrica e vorremmo vendere i vostri modelli online in Italia. È possibile?", "B2B", b2b="other", stated="IT", note="线上转售：B 端 other"),
    row("it", "+393330000103", "IT", "Buongiorno, quanto costa la MC10 e dove posso acquistarla in Italia?", "B2C", b2c="buy", stated="IT", products=("MC10",)),
    row("it", "+393330000104", "IT", "È possibile provare la Ukko a Milano?", "B2C", b2c="test_ride", products=("UKKO",)),
    row("it", "+393330000105", "IT", "Come si aggiorna il firmware della M05? L'app mi dà errore.", "B2C", b2c="support", products=("M05",)),
    row("it", "+393330000106", "IT", "Il motore della mia Mino fa un rumore strano dopo due mesi. È normale?", "B2C", b2c="support", products=("MINO",), note="故障排查提问，未提出保修要求"),
    row("it", "+393330000107", "IT", "Vivo in Svizzera, a Lugano. Spedite ricambi per la MC10 anche in Svizzera?", "B2C", b2c="parts", stated="CH", products=("MC10",), note="自述国家与号码国家不同"),
    row("it", "+393330000108", "IT", "Avete in programma nuovi modelli per il prossimo anno?", "B2C", b2c="other"),
    row("it", "+393330000109", "IT", "Gentili signori, produciamo caschi e accessori per moto e vorremmo proporvi una collaborazione come fornitori.", "unknown", note="供应商推销"),
]


def gold_escalation(spec: dict) -> tuple[bool, str]:
    if spec["esc"]:
        return True, spec["esc"]
    if spec["ambiguous"]:
        return True, "low_confidence"
    if spec["segment"] == "B2B" and spec["b2b"] and spec["who"]:
        return True, "b2b_qualified"   # market is always known here: every row has a phone
    return False, ""


def build_rows() -> list[dict[str, str]]:
    assert len(ROWS) == 80, len(ROWS)
    rows: list[dict[str, str]] = []
    for index, spec in enumerate(ROWS, start=1):
        phone = normalize_e164(spec["phone"])
        assert phone, f"row {index}: phone {spec['phone']} is not a possible number"
        detected = country_from_phone(phone)
        assert detected == spec["phone_country"], f"row {index}: {phone} -> {detected}, expected {spec['phone_country']}"
        flag, reason = gold_escalation(spec)
        if spec["segment"] == "B2B":
            valid = "" if spec["ambiguous"] else "yes"
        else:
            valid = "no"
        rows.append({
            "sample_id": f"SYN-{index:03d}",
            "data_origin": "synthetic",
            "phone": phone,
            "conversation_text": spec["text"],
            "language": spec["lang"],
            "segment": spec["segment"],
            "b2b_type": spec["b2b"] or "",
            "b2c_intent": spec["b2c"] or "",
            "country_gold": spec["stated"] or spec["phone_country"],
            "product_interest": ";".join(sorted(spec["products"])),
            "escalation_flag": "true" if flag else "false",
            "escalation_reason": reason,
            "is_valid_lead": valid,
            "annotator": "synthetic-generator",
            "label_notes": spec["note"],
        })
    return rows


def render() -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(LABEL_COLUMNS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(build_rows())
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = render()
    if args.check:
        stale = not OUT.exists() or OUT.read_text(encoding="utf-8") != content
        print("STALE: synthetic-samples.csv" if stale else "synthetic-samples.csv is up to date")
        return 1 if stale else 0
    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(ROWS)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
