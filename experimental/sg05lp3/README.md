# SG05LP3 Remote Mode testproject

Status op 11 oktober 2026: offline implementatie en eerste handmatige FC03-read geslaagd.
Niet geïnstalleerd in Home Assistant. Geen Remote Mode-schrijfpad of scheduler.
Geen fysieke test uitgevoerd. Dit is geen productieversie.

Doel: een model-/firmwarespecifieke aanvulling op ha-solarman voorbereiden,
zonder het zes-regelige productie-TOU-plan te veranderen. Eerst bewijs
verzamelen, daarna afzonderlijk goedgekeurde schrijftests.

## Inhoud

- `remote_observe.yaml`: 14 read-only registerdefinities volgens Deye V105.4
  en EMS-documentatie. Dit is een fragment, geen vervangend basisprofiel.
- `../../custom_components/solarman/remote_shadow.py`: pure codecs, offline
  vermogenspreview, strikte snapshotdecoder en expliciete FC03-read-only probe.
  Niet vanuit de integratie-entrypoint geïmporteerd.
- `register-spec.md`: bronnen, mapping, onzekerheden en herkomst.
- `acceptance.md`: gefaseerd testplan met afzonderlijke go/no-go beslissingen.
- `../../tests/test_remote_shadow.py`: codec-, fout- en schrijfblokkadetests.
- `../../tests/test_remote_profile.py`: read-only profielcontrole.
- `../../tools/remote_shadow_preview.py`: uitsluitend offline rekenvoorbeeld.

## Offline uitvoeren

Python 3.11+ en PyYAML 6.x voor profieltests. Maak een eigen virtualenv en
installeer eerst `requirements-remote-test.txt`. Daarna:

```sh
python3 -m unittest discover -s tests -p 'test_remote_*.py' -v
python3 tools/remote_shadow_preview.py --power-w -300
```

Positief vermogen betekent ontladen; negatief laden. Op 15 kW is één raw stap
15 W. Een preview geeft nooit toestemming tot sturing. Deze tools lezen geen
HA-configuratie, credentials of live apparaten en openen geen netwerkverbinding.

## Veiligheidsgrenzen

Alle nieuwe Remote Mode-entiteiten zijn sensoren. Er zijn geen nieuwe HA-actions,
geen `number`/`select`/`switch` controls, geen mode-entrycommando en geen FC16-
executor. `ReadOnlyProbe.write()` weigert onvoorwaardelijk, ook bij nul vermogen.
Er is geen instelling om deze blokkade op te heffen.

De bestaande generieke ha-solarman-schrijfacties blijven upstream ongewijzigd.
Deze testfork blokkeert die bestaande acties NIET; het is geen globale write-lock
voor de gehele integratie. Installeer hem niet als productie-update.

Voor observatie moet een later goedgekeurde HA-wrapper de bestaande
Solarman-device-interface gebruiken, niet een tweede verbinding/command owner.
Het YAML-fragment vervangt de bestaande telemetrie niet automatisch.
Via de reeds geïnstalleerde integratie zijn 1100–1101 en 1104–1115 eenmalig
succesvol gelezen. Dat bewijst bereikbaarheid op die bestaande verbinding,
niet HA-runtimecompatibiliteit van deze fork of Remote Mode-writeondersteuning.

Geen automatische grid charging of batterij-export wordt toegevoegd. Een
eventuele toekomstige controller moet beide ook fysiek bewaken: alleen een
toggle of een voorspelde PV-/loadwaarde is geen garantie.

## Open blokkades

1. Tegengestelde betekenis van 1100 in Deye-bronnen; mail wijst op EMS-variant,
   maar gedrag op de actuele firmware is niet vastgesteld.
2. Watchdog: exact te verversen register, volgorde en deadline ontbreken.
3. Deye bevestigt uitsluitend adapterondersteuning; LSW-5 schrijftests niet bewezen.
4. TOU-terugval en actuele BMS-/fase-/eigenaar-gates niet fysiek getest.

Upstreambasis: `ac1d88b8` (main, 3 mei 2026). PR #978 is niet overgenomen.
Productiebestanden, helpers, bestaande registerwaarden en apparaatinstellingen
blijven ongemoeid. Originele mails en documenten worden niet mee gepubliceerd.

## Bestandswijzigingen in deze branch

| Bestand | Wijziging |
| --- | --- |
| `.gitignore` | Alleen lokale test-virtualenv uitsluiten |
| `custom_components/solarman/remote_shadow.py` | Nieuwe offline codecs en expliciete read-only probe |
| `experimental/sg05lp3/remote_observe.yaml` | Nieuw inactief fragment met 14 sensoren |
| `experimental/sg05lp3/register-spec.md` | Nieuwe brongebonden specificatie en conflicten |
| `experimental/sg05lp3/acceptance.md` | Nieuw gefaseerd acceptatieplan |
| `experimental/sg05lp3/README.md` | Scope, gebruik, veiligheidsgrenzen en deze inventaris |
| `tests/test_remote_shadow.py` | Nieuwe offline codec- en probe-tests |
| `tests/test_remote_profile.py` | Nieuwe YAML- en mappingtests |
| `tools/remote_shadow_preview.py` | Nieuwe offline CLI, geen HA/netwerkverbinding |
| `requirements-remote-test.txt` | Alleen PyYAML voor offline testvalidatie |

Offline validatie: 23 tests geslaagd op Python 3.12. Geen HA-runtime-importtest,
geen live writes, geen fysieke watchdog-/TOU-terugvaltest. Het bestaande
productieprofiel en de bestaande service-implementatie zijn niet gewijzigd.
De handmatige FC03-read gebruikte de bestaande HA-action; de nieuwe probe en
het YAML-fragment zijn daarbij niet in HA geïnstalleerd of live uitgevoerd.
