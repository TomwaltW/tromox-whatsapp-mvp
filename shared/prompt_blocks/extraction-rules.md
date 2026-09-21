### Extraction rules (shared block)

1. **segment**
   - `B2B`: the person represents, or wants to start, a business that would resell, import, rent out or operate Tromox vehicles - dealers, distributors, importers, fleet / rental / delivery operators, shop owners, purchasing agents. Typical signals: "dealer", "distributor", "reseller", "wholesale", "importer", "MOQ", "price list", "exclusive", "container", "our shop / company / store", "fleet", "rental", a company name, a business website, quantities above 2.
   - `B2C`: an individual rider, owner or prospective buyer - retail price, where to buy one vehicle, test ride, specs for personal use, after-sales help, parts or warranty for their own vehicle.
   - `unknown`: greeting only, unclear, spam, job seekers, suppliers selling to Tromox, media / influencer requests, anything unrelated to Tromox. For a greeting-only, spam or clearly unrelated message, `unknown` is the confident answer (see rule 8) and nothing is escalated - the flow simply asks its next question.
   - A button choice made by the customer wins over your inference, unless the free text clearly contradicts it (pressed "Rider or Customer" but writes "I own three shops and want to distribute"). Then follow the text and lower `ai_confidence`.
   - **Asymmetric cost**: missing a real dealer or distributor is far worse than sending an individual to sales. When B2B vs B2C is genuinely ambiguous, choose `B2B` and set `ai_confidence` below 0.6.
2. **b2b_type** (only when `segment` = `B2B`, otherwise null)
   - `dealer`: retail shop, wants to sell to end customers in a city or region.
   - `distributor`: wants regional or national distribution, a sub-dealer network, exclusivity.
   - `importer`: talks about importing, containers, homologation, customs.
   - `fleet`: rental, sharing, delivery, corporate or government fleet purchase.
   - `other`: B2B but none of the above (OEM / ODM, corporate gifts, online reseller).
3. **b2c_intent** (only when `segment` = `B2C`, otherwise null)
   - `buy`: price, availability, where to buy, financing. `test_ride`: try or see the vehicle, showroom. `support`: how-to, app, charging, troubleshooting, manuals. `parts`: spare parts, accessories, batteries. `warranty`: warranty coverage questions or claims. `other`: anything else.
4. **country_stated**: never infer a country from language, currency or a city name. Fill it ONLY when the customer explicitly names a country or national market (ISO 3166-1 alpha-2). A city alone goes into `city_region` and `country_stated` stays null - the phone prefix rule and a follow-up question cover the rest.
5. **product_interest**: catalogue codes only. Map variants to the family ("Ukko S+" -> `UKKO`, "MC10 StreetX" -> `MC10`). Unknown or competitor models are omitted. A generic "electric motorcycle" gives `[]`.
6. **volume**: quote briefly what was said ("20 units / quarter", "1 container", "2 bikes"). Never estimate.
7. **Escalation** - set `escalation_flag` = true with exactly one `escalation_reason`, first match in this order:
   1. `complaint_warranty_legal_safety`: complaint, accident, injury, battery fire or smoke, legal threat, refund dispute, warranty claim or dispute, personal-data request.
   2. `human_requested`: explicitly asks for a human, agent, salesperson or a call.
   3. `price_negotiation`: asks for a discount, dealer or wholesale price, a quotation, payment or exclusivity terms.
   4. `not_understood_twice`: the assistant failed to understand two consecutive customer messages (conversation mode only).
   5. `low_confidence`: `ai_confidence` below 0.6 - an uncertain lead must reach a human labelled as uncertain, even when its fields are complete.
   6. `b2b_qualified`: `segment` = `B2B` and business type + who (company or contact name) + market are all known.
   Otherwise `escalation_flag` = false and `escalation_reason` = null.
8. **ai_confidence**: confidence in the `segment` decision. 0.9 and above = explicit (button or clear statement, and also a greeting-only, spam or clearly unrelated message, where `unknown` is certain); 0.6 to 0.9 = inferred from strong signals; below 0.6 = the message has business content but B2B vs B2C is genuinely unclear. Never use a value below 0.6 just because a message is short.
9. **ai_summary**: one or two sentences in Simplified Chinese for the sales team - who, where, what they want, quantity if stated, suggested next step. No speculation.
10. **No invention**: extract only what the customer wrote. Never invent names, companies, quantities or countries. Missing values are null (`[]` for `product_interest`).
11. **Output format**: exactly one JSON object with exactly the keys below - no markdown fences, no comments, no text before or after.
