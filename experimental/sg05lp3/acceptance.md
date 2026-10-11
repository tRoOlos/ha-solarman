# Acceptatieplan

Elke fase krijgt een eigen expliciete go/no-go. Geen fase wordt vanzelf actief.
Readback, fysieke vermogensrespons en watchdog-terugval zijn afzonderlijk bewijs.

## Fase 0 Offline

- Registerspecificatie en firmwareafbakening gereed.
- Codec-, profiel-, incomplete-response- en permanente schrijfblokkadetests groen.
- Geen HA-registratie, geen socket, geen credentials, geen actuator.
- Productie-TOU en bestaande integratie blijven ongewijzigd.

## Fase 1 Alleen lezen

Op 11 oktober 2026 zijn via de bestaande HA-action `solarman.read_holding_registers`
de twee FC03-blokken 1100–1101 en 1104–1115 succesvol gelezen. Geen writes.
De antwoorden blijven privé; dit bewijst alleen registerbereikbaarheid.
De nieuwe probe/YAML zijn niet in HA uitgevoerd. Fase 1 is dus nog niet volledig
afgerond: gelijktijdige firmware-/TOU-baseline, responstijdmeting en herhaalde
freshnessvalidatie ontbreken nog. Na keuze en toestemming voor exacte bestanden:

- Bestaande HA Solarman-device-interface gebruiken, geen parallelle Modbus-master.
- Eerst één expliciete FC03-meting: 1100–1101 en 1104–1115.
- Adreslijst, raw antwoorden, foutcodes, responstijden en ontvangsttijd vastleggen.
- Geen oude/retained response als actueel bewijs. Incomplete/met fout beantwoorde
  requests geven geen geldige snapshot.
- Werkelijke firmware en bestaande TOU-tabel op hetzelfde moment vastleggen.
- Nog geen LSW-5-writeondersteuning concluderen uit succesvolle reads.
- Geen tweede HACS-repository met hetzelfde domain naast de bestaande integratie.

## Fase 2 Handmatige nul- en laagvermogentest

GEBLOKKEERD totdat 1100 en watchdogmechanisme eenduidig zijn en gebruiker
de exacte commando's, verbinding, duur en maximale vermogens apart heeft goedgekeurd.
Er is nog geen executor voor deze fase.

- Een actieve command owner; bestaande TOU-productieschrijver en herstelwrites
  mogen tijdens de gecontroleerde proef niet concurreren.
- Actuele gegevens van alle drie packs, SOC, cellen, alarmen, BMS-limieten,
  AC-fasen en inverterstatus. Actuele grenzen live vaststellen, niet uit historie.
- Volledige veilige TOU-baseline exact teruglezen vóór de proef.
- Netladen/export uitsluiten met gemeten PV-surplus, eigen load en werkelijke
  netrichting; kortdurende regeling kan afwijkingen niet absoluut voorkomen.
- Eerst nulvermogen, daarna hoogstens 300 W testvermogen indien de actuele
  BMS-/fase-/SOC-grenzen dat toestaan. Bij onvoldoende PV geen laadtest.
- Elk geschreven register teruglezen én fysieke richting/vermogensrespons
  controleren; die zaken niet gelijkstellen.
- Timeout nooit uitschakelen. Geen foutieve control-side/AC/PV/reactieve writes.
- Geen blind herhalen na timeout: mogelijk is een write uitgevoerd zonder antwoord.
- Stopcondities: onverwachte grid charge/export, alarm, oude/ontbrekende telemetrie,
  fasebelasting, verkeerde vermogensrichting of readbackmismatch.

## Fase 3 Communicatieverlies en herstart

- Vastgestelde, korte watchdog-timeout en refreshhandeling gebruiken.
- Refresh doelbewust stoppen tijdens bewaakte nul-/laagvermogentest.
- Aantonen wanneer Remote Mode stopt en welke TOU-regel fysiek terugkomt.
- Procescrash, netwerkverlies en handmatige stop testen; geen automatisch hervatten
  na reboot of na een alarm.
- Latentie inclusief polling meten; bewezen deadline nodig. Geen onbewezen
  één-secondegarantie op basis van een HA automation of sensor-update_interval.

## Fase 4 EMHASS shadow en mogelijke productie

- CHARGE/HOLD/DISCHARGE vergelijken met kwartierplan; nog geen apparaatsturing.
- Pas na duurtest, write/readback/response/fallback-bewijs een afzonderlijke
  productiebeslissing nemen. Geen eis dat de batterij onnodig maximaal ontlaadt.
- Eenzelfde gevalideerde controller blijft eigenaar; SolarAssistant monitoring
  en Seplos-telemetrie worden geen concurrerende inverterstuurpaden.

## Resultaten per test

Noteer tijdzone en tijd, firmware, verbinding, command owner, gates, raw request,
response en readback, gemeten batterij-/netvermogen, SOC/cellen/BMS-alarmen,
watchdogverloop en teruggevallen TOU. Houd verwachte en gemeten resultaten apart.
Geen credentials, IP-adressen, serienummers of volledige privé-mails publiceren.
