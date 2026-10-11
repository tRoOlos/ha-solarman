# Registerspecificatie SG05LP3

Scope: SUN-15K-SG05LP3-EU-SM2, 15 000 W, gemelde firmware HMI 1001-C05F,
MAIN 2107-1184-1809, ARC D20A. Firmware-identiteit moet vóór een live test
opnieuw gecontroleerd worden. Geen universeel profiel voor alle Deye-modellen.
Alle adressen zijn decimaal; geen +/-1 adrescorrectie toepassen.

## Bronnen

- S1: Deye `MODBUS RTU V105.4-20240814`, sectie Customized register.
  SHA256: `0f091a6b45099ff827d4d07ad9da483e7c10b0b116f60c025ce90605a397bb00`.
- S2: Deye `ems control English version`, DC-/AC-control-tabellen.
  SHA256: `88d3da985dda968ce84c73ebc00279b1c9e6da23745b5806d4f0090a17e17ceb`.
- S3: Deye `RS-485-Remote mode(1)`, tabel en Modbus Poll-afbeeldingen.
  SHA256: `cc5eb36b4d72e3eb2072e04147ac76bedfc9d92f504715daeb2dd111ae821f16`.
- S4: Deye-mailantwoord op firmware-/implementatievragen; privé origineel lokaal
  gecontroleerd. Geen mailadressen, serienummer of volledige mail gepubliceerd.
- S5: [PR #978](https://github.com/davidrapan/ha-solarman/pull/978) en de oorspronkelijke
  bijlage `wiki_remote_control_deye_p3.md`; vergelijking, geen uitvoeringsbewijs.

## Mapping

| Adres | Deye-definitie | Schaal / grenzen | Status |
| --- | --- | --- | --- |
| 1100 | Remote Mode-commandowaarde | 0 enter, 1 exit volgens S2 en firmwarebevestiging S4 | LEVERANCIER BEVESTIGD; nog niet fysiek getest |
| 1101 | Watchdog | configuratie 10–18000 s; 65535 = uit | refreshmechanisme ONBEKEND |
| 1104 | Control side | 0 AC, 1 batterij, 2 net; range-kolom S1 noemt alleen 0/1 | batterijwaarde 1 bevestigd S4 |
| 1105 | Battery strategy | 2 vermogen; 3 SOC; 4/5 genoemd buiten range-kolom | 2 bevestigd S4; andere modes niet testen |
| 1106 | AC combined/per-phase | 0 gecombineerd, 1 afzonderlijk | S1/S2; observe-only |
| 1107 | Batterijspanningsdoel | 0.1 V; 0–10000 raw | S1; geen schrijffunctie |
| 1108 | Batterijstroomdoel | 0.1 A; 0–2000 raw | S1; geen schrijffunctie |
| 1109 | Batterijvermogensdoel | signed -1200..1200; 0.1% nominaal | S1/S2/S4; + ontladen, - laden |
| 1110 | Batterij-SOC-doel | 0.1%; 0–1000 raw | S1/S2; geen schrijffunctie |
| 1111 | Totaal AC-vermogensdoel | signed 0.1%; -1200..1200 | S1/S2; observe-only |
| 1112–1114 | AC-fase A/B/C | signed 0.1%; fasevoorbeeld gebruikt nominaal/3 | S1/S2; geen AC-controller |
| 1115 | Maximaal PV-vermogensdoel | 0.1%; 0–2000 raw | S1; observe-only |

1102/1103 en 1116+ worden niet aangevraagd of geschreven in deze proef.
Er worden geen statusbits afgeleid uit 1121: S1 noemt daar reactieve fase-C-data.
S1/S3 noemen voor 1100 de tegengestelde aan/uit-definitie. S4 bevestigt expliciet
de S2-interpretatie voor C05F/1184: schrijven van 0 betekent enter, 1 betekent exit.
Die leveranciersbevestiging is de gekozen commandospecificatie voor deze scope;
1100 is dus geen onbeantwoorde documentatievraag meer. Niet generaliseren naar
andere modellen/firmware. Een raw read van 0/1 is op zichzelf nog geen bewezen
actief/inactief-status: daarvoor ontbreken testrespons en een bevestigd statusmodel.
Een watchdog-read kan een aftelling of instelling zijn; ruwe waarde bewaren.
65535 herkennen als watchdog uit, niet als geldige timeout.

## Codering en schrijfprotocol

S4 bevestigt 1100 enter=0/exit=1, 1104=1, 1105=2, signed 1109 en FC16 (0x10).
Niet aaneengesloten adressen niet samenvoegen door tussenliggende velden te
overschrijven. De volledige volgorde inclusief watchdog-initialisatie en
refreshhandeling is nog niet gespecificeerd; dit verandert niets aan de al
bevestigde afzonderlijke commandowaarden.

1109: raw = vermogen_W / nominaal_W * 1000. Afronden naar nul.
15 kW: +300 W -> +20; -300 W -> -20; signed -20 -> unsigned wire 65516.
Alleen codering, geen verstuurinstructie. Een signed waarde kan niet letterlijk
negatief naar de generieke unsigned HA-service.

PR-entiteiten gebruiken procenten; raw -150 is -15%, niet -150%.
Batterijspanning (V), stroom (A), vermogen (W) en SOC (%) zijn niet uitwisselbaar.

## Bewijsstatus en vragen

S4 bevestigt voor 1100 de S2-definitie, volatile commands, CAN-BMS-bescherming en
TOU-terugval bij communicatie-/watchdogverlies. Dit zijn leveranciersantwoorden,
geen gemeten testresultaten.

S4 zegt over transport: uitsluitend RS485-adapter ondersteund. Dit is geen bewijs
van een fysieke blokkade in de LSW-5, maar ook geen toezegging dat deze route werkt.
Een fork kan deze onzekerheid niet wegprogrammeren.

Nog aan Deye/Bram te verduidelijken: exacte refreshhandeling (1101 opnieuw
schrijven of andere handeling), timeout versus
aftelwaarde, betekenis van de genoemde één seconde, aanbevolen commandovolgorde,
FC16 readback en veilige nul-/laagvermogentest op de gekozen verbinding.
1100 entry=0/exit=1 hoeft voor de genoemde firmware niet opnieuw als open vraag
gesteld te worden; de fysieke uitvoering wordt later afzonderlijk getest.
