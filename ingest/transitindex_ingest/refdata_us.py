"""US agency reference data — GENERATED, do not hand-edit.

Produced by `python ingest/scripts/generate_ntd_agencies.py` from the
committed NTD snapshots under db/seeds/ntd/. Mirrors
db/seeds/08_agencies_us.sql exactly; re-running the generator preserves
the existing slug of every ntd_id it has seen before (slugs are
permanent URLs).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

# slug -> {subdivision (2-letter state), fiscal_year_end_month (NTD fy_end_date),
#          country, ntd_id, primary_modes}. Same shape as refdata.AGENCIES
#          plus country/currency/ntd_id.
US_AGENCIES: Mapping[str, Mapping] = MappingProxyType(
    {
        "academy-lines-inc-dba-academy-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20122",
             "primary_modes": ("bus",)}
        ),
        "access-services-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90157",
             "primary_modes": ("paratransit",)}
        ),
        "ada-county-highway-district-dba-achd-commuteride-id": MappingProxyType(
            {"subdivision": "ID", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "00415",
             "primary_modes": ("on_demand",)}
        ),
        "adirondack-transit-lines-inc-dba-adirondack-trailways-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20177",
             "primary_modes": ("bus",)}
        ),
        "alameda-contra-costa-transit-district-dba-ac-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90014",
             "primary_modes": ("bus", "brt", "paratransit")}
        ),
        "alaska-railroad-corporation-ak": MappingProxyType(
            {"subdivision": "AK", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00041",
             "primary_modes": ("commuter_rail",)}
        ),
        "altamont-corridor-express-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90182",
             "primary_modes": ("commuter_rail",)}
        ),
        "alternativa-de-transporte-integrado-dba-autoridad-de-transporte-integrado-pr": MappingProxyType(
            {"subdivision": "PR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40094",
             "primary_modes": ("bus", "subway", "paratransit")}
        ),
        "altoona-metro-transit-dba-amtran-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30011",
             "primary_modes": ("bus", "paratransit")}
        ),
        "ames-transit-agency-dba-cyride-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70041",
             "primary_modes": ("bus",)}
        ),
        "anaheim-transportation-network-dba-anaheim-regional-transportation-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90211",
             "primary_modes": ("bus", "paratransit")}
        ),
        "ann-arbor-area-transportation-authority-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50040",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "anne-arundel-county-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30129",
             "primary_modes": ("bus", "paratransit")}
        ),
        "antelope-valley-transit-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90121",
             "primary_modes": ("bus", "paratransit")}
        ),
        "arlington-county-virginia-dba-arlington-transit-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30080",
             "primary_modes": ("bus", "paratransit")}
        ),
        "athens-clarke-county-unified-government-dba-athens-clarke-county-transit-department-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40047",
             "primary_modes": ("bus", "paratransit")}
        ),
        "atlanta-region-transit-link-authority-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "42000",
             "primary_modes": ("bus", "on_demand")}
        ),
        "augusta-richmond-county-transit-department-dba-augusta-transit-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "40023",
             "primary_modes": ("bus", "paratransit")}
        ),
        "baldwin-county-commission-dba-baldwin-regional-area-transit-system-al": MappingProxyType(
            {"subdivision": "AL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40928",
             "primary_modes": ("paratransit",)}
        ),
        "bay-area-transportation-authority-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50413",
             "primary_modes": ("bus", "paratransit")}
        ),
        "bay-county-transportation-planning-organization-dba-bayway-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40185",
             "primary_modes": ("bus", "paratransit")}
        ),
        "bay-metropolitan-transit-authority-dba-bay-metro-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50029",
             "primary_modes": ("bus", "paratransit")}
        ),
        "beaver-county-transit-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30023",
             "primary_modes": ("bus", "paratransit")}
        ),
        "ben-franklin-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00018",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "berkshire-regional-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10007",
             "primary_modes": ("bus", "paratransit")}
        ),
        "bi-state-development-agency-of-the-missouri-illinois-metropolitan-district-dba-st-louis-metro-mo": MappingProxyType(
            {"subdivision": "MO", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70006",
             "primary_modes": ("bus", "light_rail", "paratransit")}
        ),
        "birmingham-jefferson-county-transit-authority-al": MappingProxyType(
            {"subdivision": "AL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40042",
             "primary_modes": ("bus", "brt", "paratransit")}
        ),
        "bloomington-normal-public-transit-system-dba-connect-transit-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50047",
             "primary_modes": ("bus", "paratransit")}
        ),
        "bloomington-public-transportation-corporation-dba-bloomington-transit-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50110",
             "primary_modes": ("bus", "paratransit")}
        ),
        "blue-water-area-transportation-commission-dba-blue-water-area-transit-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50148",
             "primary_modes": ("bus", "paratransit")}
        ),
        "board-of-county-commissioners-of-st-lucie-county-dba-area-regional-transit-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "41199",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "board-of-county-commissioners-palm-beach-county-dba-palm-tran-inc-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40037",
             "primary_modes": ("bus", "paratransit")}
        ),
        "borough-of-pottstown-dba-pottstown-area-rapid-transit-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30077",
             "primary_modes": ("bus", "paratransit")}
        ),
        "brazos-transit-district-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60059",
             "primary_modes": ("bus", "paratransit")}
        ),
        "brevard-board-of-county-commissioners-dba-space-coast-area-transit-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40063",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "brockton-area-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10004",
             "primary_modes": ("bus", "paratransit")}
        ),
        "broome-county-dba-bc-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20003",
             "primary_modes": ("bus", "paratransit")}
        ),
        "broward-county-board-of-county-commissioners-dba-broward-county-transit-division-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40029",
             "primary_modes": ("bus", "paratransit")}
        ),
        "buncombe-county-dba-mountain-mobility-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40224",
             "primary_modes": ("bus", "paratransit")}
        ),
        "butler-county-regional-transit-authority-dba-bcrta-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50157",
             "primary_modes": ("bus", "paratransit")}
        ),
        "butte-county-association-of-governments-dba-butte-regional-transit-b-line-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90208",
             "primary_modes": ("bus", "paratransit")}
        ),
        "cache-valley-transit-district-dba-connect-transit-ut": MappingProxyType(
            {"subdivision": "UT", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80028",
             "primary_modes": ("bus", "paratransit")}
        ),
        "california-vanpool-authority-dba-calvans-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90230",
             "primary_modes": ("on_demand",)}
        ),
        "cambria-county-transit-authority-dba-camtran-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30012",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "cape-ann-transportation-authority-dba-cata-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10053",
             "primary_modes": ("bus", "paratransit")}
        ),
        "cape-cod-regional-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10105",
             "primary_modes": ("bus", "paratransit")}
        ),
        "cape-fear-public-transportation-authority-dba-wave-transit-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40006",
             "primary_modes": ("bus", "paratransit")}
        ),
        "cape-may-lewes-ferry-de": MappingProxyType(
            {"subdivision": "DE", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20223",
             "primary_modes": ("ferry",)}
        ),
        "capital-area-transit-system-la": MappingProxyType(
            {"subdivision": "LA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60022",
             "primary_modes": ("bus", "paratransit")}
        ),
        "capital-area-transportation-authority-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50036",
             "primary_modes": ("bus", "paratransit")}
        ),
        "capital-district-transportation-authority-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 3,
             "currency": "USD", "country": "US", "ntd_id": "20002",
             "primary_modes": ("bus", "paratransit")}
        ),
        "capital-metropolitan-transportation-authority-dba-capital-metro-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60048",
             "primary_modes": ("bus", "commuter_rail", "paratransit", "on_demand")}
        ),
        "casco-bay-island-transit-district-dba-casco-bay-lines-me": MappingProxyType(
            {"subdivision": "ME", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "10088",
             "primary_modes": ("ferry",)}
        ),
        "central-arkansas-development-council-dba-south-central-arkansas-transit-ar": MappingProxyType(
            {"subdivision": "AR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "60246",
             "primary_modes": ("paratransit",)}
        ),
        "central-contra-costa-transit-authority-dba-county-connection-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90078",
             "primary_modes": ("bus", "paratransit")}
        ),
        "central-county-transportation-authority-dba-metro-transit-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50035",
             "primary_modes": ("bus", "paratransit")}
        ),
        "central-florida-commuter-rail-dba-sunrail-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40232",
             "primary_modes": ("commuter_rail",)}
        ),
        "central-florida-regional-transportation-authority-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40035",
             "primary_modes": ("bus", "brt", "paratransit", "on_demand")}
        ),
        "central-indiana-regional-transportation-authority-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50209",
             "primary_modes": ("bus", "on_demand")}
        ),
        "central-midlands-regional-transportation-authority-dba-the-comet-sc": MappingProxyType(
            {"subdivision": "SC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40141",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "central-new-york-regional-transportation-authority-dba-new-york-regional-transportation-authority-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 3,
             "currency": "USD", "country": "US", "ntd_id": "20018",
             "primary_modes": ("bus", "paratransit")}
        ),
        "central-ohio-transit-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50016",
             "primary_modes": ("bus", "paratransit")}
        ),
        "central-oklahoma-transportation-and-parking-authority-dba-embark-ok": MappingProxyType(
            {"subdivision": "OK", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "60017",
             "primary_modes": ("bus", "streetcar", "brt", "ferry", "paratransit")}
        ),
        "central-oregon-intergovernmental-council-dba-cascades-east-transit-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00057",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "central-puget-sound-regional-transit-authority-dba-sound-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00040",
             "primary_modes": ("bus", "light_rail", "commuter_rail", "streetcar")}
        ),
        "centre-area-transportation-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30054",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "champaign-urbana-mass-transit-district-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50060",
             "primary_modes": ("bus", "paratransit")}
        ),
        "charleston-area-regional-transportation-authority-sc": MappingProxyType(
            {"subdivision": "SC", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40110",
             "primary_modes": ("bus", "paratransit")}
        ),
        "charlotte-county-government-dba-charlotte-county-transit-division-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40129",
             "primary_modes": ("paratransit",)}
        ),
        "chatham-area-transit-authority-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40025",
             "primary_modes": ("bus", "ferry", "paratransit")}
        ),
        "chattanooga-area-regional-transportation-authority-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40001",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "chelan-douglas-ptba-dba-link-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00043",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "chicago-transit-authority-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50066",
             "primary_modes": ("bus", "subway")}
        ),
        "chicago-water-taxi-wendella-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50521",
             "primary_modes": ("ferry",)}
        ),
        "city-and-county-of-honolulu-hi": MappingProxyType(
            {"subdivision": "HI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90002",
             "primary_modes": ("bus", "subway", "paratransit")}
        ),
        "city-and-county-of-san-francisco-dba-san-francisco-municipal-transportation-agency-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90015",
             "primary_modes": ("bus", "light_rail", "streetcar", "trolleybus", "paratransit")}
        ),
        "city-of-albany-dba-albany-transit-system-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40021",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-albuquerque-dba-abqride-nm": MappingProxyType(
            {"subdivision": "NM", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "60019",
             "primary_modes": ("bus", "brt", "paratransit")}
        ),
        "city-of-alexandria-dba-dash-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30071",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-appleton-dba-valley-transit-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50001",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-arlington-dba-arlington-transportation-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60041",
             "primary_modes": ("paratransit",)}
        ),
        "city-of-asheville-dba-art-asheville-rides-transit-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40005",
             "primary_modes": ("bus",)}
        ),
        "city-of-baltimore-dba-charm-city-circulator-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30201",
             "primary_modes": ("bus", "ferry")}
        ),
        "city-of-beaumont-dba-beaumont-municipal-transit-system-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60016",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-billings-dba-billings-metropolitan-transit-system-mt": MappingProxyType(
            {"subdivision": "MT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "80004",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-brownsville-dba-brownsville-metro-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60014",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-cedar-rapids-dba-cedar-rapids-transit-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70008",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-charlotte-north-carolina-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40008",
             "primary_modes": ("bus", "light_rail", "streetcar", "paratransit", "on_demand")}
        ),
        "city-of-cincinnati-dba-the-connector-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "55311",
             "primary_modes": ("streetcar",)}
        ),
        "city-of-clovis-dba-clovis-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90313",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-colorado-springs-dba-mountain-metropolitan-transit-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80005",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "city-of-columbia-dba-gocomo-mo": MappingProxyType(
            {"subdivision": "MO", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "70016",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-commerce-dba-city-of-commerce-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90043",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-coralville-dba-coralville-transit-system-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70030",
             "primary_modes": ("bus",)}
        ),
        "city-of-culver-city-dba-culver-citybus-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90039",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-davenport-dba-davenport-citibus-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70009",
             "primary_modes": ("bus",)}
        ),
        "city-of-decatur-il-dba-decatur-public-transit-system-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50061",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-dekalb-dba-city-of-dekalb-public-transit-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50176",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-detroit-dba-detroit-department-of-transportation-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50119",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-durham-dba-godurham-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40087",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-eau-claire-dba-eau-claire-transit-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50099",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-el-paso-dba-sun-metro-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 8,
             "currency": "USD", "country": "US", "ntd_id": "60006",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "city-of-evansville-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50043",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-everett-dba-everett-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00005",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-fairfax-dba-cue-bus-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30058",
             "primary_modes": ("bus",)}
        ),
        "city-of-fairfield-california-dba-fast-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90092",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-fargo-dba-metropolitan-area-transit-nd": MappingProxyType(
            {"subdivision": "ND", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80003",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-fayetteville-dba-fayetteville-area-system-of-transit-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40009",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-fort-collins-dba-transfort-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80011",
             "primary_modes": ("bus", "brt", "paratransit")}
        ),
        "city-of-fort-lauderdale-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "44929",
             "primary_modes": ("bus", "ferry")}
        ),
        "city-of-fresno-dba-fresno-area-express-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90027",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-gainesville-fl-dba-regional-transit-system-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40030",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-galveston-dba-galveston-island-transit-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60015",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "city-of-gardena-dba-gtrans-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90042",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-glendale-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90034",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-glendale-dba-beeline-bus-dial-a-ride-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "99423",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-grand-forks-nd": MappingProxyType(
            {"subdivision": "ND", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80008",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-green-bay-dba-green-bay-metro-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50002",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-greensboro-dba-greensboro-transit-agency-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40093",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-harrisonburg-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30094",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-huntsville-alabama-dba-huntsville-transit-al": MappingProxyType(
            {"subdivision": "AL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40071",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-iowa-city-dba-iowa-city-transit-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70018",
             "primary_modes": ("bus",)}
        ),
        "city-of-jackson-ms-ms": MappingProxyType(
            {"subdivision": "MS", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40015",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-jackson-transportation-authority-dba-jackson-area-transportation-authority-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50034",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-kenosha-dba-kenosha-area-transit-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50003",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "city-of-knoxville-dba-knoxville-area-transit-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40002",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-kokomo-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50145",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-la-crosse-dba-city-of-la-crosse-mtu-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50004",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-la-mirada-dba-la-mirada-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90024",
             "primary_modes": ("paratransit",)}
        ),
        "city-of-laredo-dba-laredo-transit-management-inc-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60009",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-lathrop-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "99479",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-lawrence-dba-lawrence-transit-ks": MappingProxyType(
            {"subdivision": "KS", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "70048",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-lincoln-dba-startran-ne": MappingProxyType(
            {"subdivision": "NE", "fiscal_year_end_month": 8,
             "currency": "USD", "country": "US", "ntd_id": "70001",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-long-beach-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "20006",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-longview-dba-rivercities-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00016",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-los-angeles-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90147",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-loveland-colorado-dba-city-of-loveland-transit-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80025",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-lubbock-dba-citibus-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60010",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-madison-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50005",
             "primary_modes": ("bus", "brt", "paratransit")}
        ),
        "city-of-maple-grove-dba-maple-grove-transit-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50517",
             "primary_modes": ("paratransit",)}
        ),
        "city-of-mckinney-dba-collin-county-transit-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60270",
             "primary_modes": ("paratransit",)}
        ),
        "city-of-memphis-dba-memphis-area-transit-authority-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40003",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "city-of-milwaukee-dba-milwaukee-streetcar-system-the-hop-streetcar-mke-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "55312",
             "primary_modes": ("streetcar",)}
        ),
        "city-of-mobile-dba-the-wave-transit-system-al": MappingProxyType(
            {"subdivision": "AL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40043",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-montebello-dba-montebello-bus-lines-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90041",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-montgomery-dba-the-m-transit-al": MappingProxyType(
            {"subdivision": "AL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40044",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-moorhead-dba-matbus-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50026",
             "primary_modes": ("paratransit",)}
        ),
        "city-of-nashua-dba-nashua-transit-system-nh": MappingProxyType(
            {"subdivision": "NH", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10087",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-norwalk-dba-norwalk-transit-system-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90022",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-pasadena-dba-pasadena-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "99424",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-peoria-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90140",
             "primary_modes": ("paratransit",)}
        ),
        "city-of-petaluma-dba-petaluma-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90213",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-phoenix-dba-valley-metro-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90032",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-plymouth-dba-plymouth-metrolink-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50516",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-portland-dba-portland-streetcar-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00058",
             "primary_modes": ("streetcar",)}
        ),
        "city-of-pueblo-dba-pueblo-transit-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80007",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "city-of-racine-wisconsin-dba-ryde-racine-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50006",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-raleigh-dba-goraleigh-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40007",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-redondo-beach-dba-beach-cities-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90214",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-riverside-dba-riverside-connect-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90086",
             "primary_modes": ("paratransit",)}
        ),
        "city-of-rochester-minnesota-dba-rochester-public-transit-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50092",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-rome-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "40058",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-san-luis-obispo-dba-slo-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90156",
             "primary_modes": ("bus",)}
        ),
        "city-of-santa-clarita-dba-santa-clarita-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90171",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-santa-fe-dba-santa-fe-trails-nm": MappingProxyType(
            {"subdivision": "NM", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "60077",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-santa-maria-dba-santa-maria-regional-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90087",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-santa-monica-dba-big-blue-bus-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90008",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-santa-rosa-dba-santa-rosa-citybus-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90017",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-scottsdale-dba-scottsdale-trolley-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90131",
             "primary_modes": ("bus",)}
        ),
        "city-of-seattle-dba-seattle-center-monorail-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00023",
             "primary_modes": ("light_rail",)}
        ),
        "city-of-shreveport-dba-sportran-la": MappingProxyType(
            {"subdivision": "LA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60024",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-sioux-city-dba-sioux-city-transit-system-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70012",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-sioux-falls-dba-sioux-area-metro-sd": MappingProxyType(
            {"subdivision": "SD", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80002",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-springfield-dba-city-utilities-of-springfield-mo-mo": MappingProxyType(
            {"subdivision": "MO", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "70003",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-tallahassee-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40036",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-terre-haute-dba-terre-haute-transit-utility-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50053",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-torrance-dba-torrance-transit-system-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90010",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-tucson-dba-sun-tran-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90033",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "city-of-turlock-dba-turlock-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90201",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-visalia-dba-visalia-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90091",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-waco-dba-waco-transit-system-inc-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60012",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-waukesha-dba-waukesha-metro-transit-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50096",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-wichita-dba-wichita-transit-ks": MappingProxyType(
            {"subdivision": "KS", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "70015",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-wilsonville-dba-south-metro-area-regional-transit-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00046",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "city-of-winston-salem-dba-winston-salem-transit-authority-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40012",
             "primary_modes": ("bus", "paratransit")}
        ),
        "city-of-yakima-dba-yakima-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00006",
             "primary_modes": ("bus", "paratransit")}
        ),
        "clark-county-public-transportation-benefit-area-authority-dba-c-tran-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00024",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "clermont-county-ohio-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50166",
             "primary_modes": ("bus", "paratransit")}
        ),
        "clinton-area-transit-system-dba-my-blue-bus-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50314",
             "primary_modes": ("paratransit",)}
        ),
        "cobb-county-dba-cobblinc-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40078",
             "primary_modes": ("bus", "paratransit")}
        ),
        "collier-county-dba-collier-area-transit-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40140",
             "primary_modes": ("bus", "paratransit")}
        ),
        "concho-valley-transit-district-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60102",
             "primary_modes": ("bus", "paratransit")}
        ),
        "connecticut-department-of-transportation-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10102",
             "primary_modes": ("bus", "commuter_rail")}
        ),
        "connecticut-department-of-transportation-cttransit-hartford-division-dba-cttransit-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10048",
             "primary_modes": ("bus", "brt")}
        ),
        "connecticut-department-of-transportation-cttransit-new-britain-dattco-dba-dattco-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10045",
             "primary_modes": ("bus",)}
        ),
        "connecticut-department-of-transportation-cttransit-new-britain-dba-cttransit-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10130",
             "primary_modes": ("bus",)}
        ),
        "connecticut-department-of-transportation-cttransit-new-haven-division-dba-cttransit-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10055",
             "primary_modes": ("bus",)}
        ),
        "connecticut-department-of-transportation-cttransit-stamford-division-dba-cttransit-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10056",
             "primary_modes": ("bus",)}
        ),
        "connecticut-department-of-transportation-cttransit-waterbury-net-dba-cttransit-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10128",
             "primary_modes": ("bus", "paratransit")}
        ),
        "cooperative-alliance-for-seacoast-transportation-nh": MappingProxyType(
            {"subdivision": "NH", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "10086",
             "primary_modes": ("bus", "paratransit")}
        ),
        "corpus-christi-regional-transportation-authority-dba-the-b-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60051",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "county-commissioners-of-charles-county-md-dba-pgm-vango-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30088",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-atlantic-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20199",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-douglas-dba-connect-douglas-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "40082",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-fayette-dba-fayette-area-coordinated-transportation-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30087",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-johnson-iowa-dba-johnson-county-seats-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70045",
             "primary_modes": ("paratransit",)}
        ),
        "county-of-lackawanna-transit-system-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30025",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-lebanon-transit-authority-dba-lebanon-transit-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30095",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-maui-hi": MappingProxyType(
            {"subdivision": "HI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90241",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-miami-dade-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40034",
             "primary_modes": ("bus", "subway", "light_rail", "brt", "paratransit", "on_demand")}
        ),
        "county-of-nassau-dba-nassau-inter-county-express-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20206",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-pierce-dba-pierce-county-ferry-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00028",
             "primary_modes": ("ferry",)}
        ),
        "county-of-placer-dba-placer-county-transit-tart-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90196",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "county-of-rockland-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20084",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-sonoma-dba-sonoma-county-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90089",
             "primary_modes": ("bus", "paratransit")}
        ),
        "county-of-volusia-dba-votran-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40032",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "dallas-area-rapid-transit-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60056",
             "primary_modes": ("bus", "light_rail", "commuter_rail", "streetcar", "paratransit")}
        ),
        "delaware-county-transit-board-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50199",
             "primary_modes": ("paratransit",)}
        ),
        "delaware-transit-corporation-de": MappingProxyType(
            {"subdivision": "DE", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30075",
             "primary_modes": ("bus", "paratransit")}
        ),
        "denton-county-transportation-authority-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60101",
             "primary_modes": ("bus", "commuter_rail", "paratransit", "on_demand")}
        ),
        "denver-regional-council-of-governments-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80109",
             "primary_modes": ("on_demand",)}
        ),
        "denver-regional-transportation-district-dba-rtd-denver-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80006",
             "primary_modes": ("bus", "light_rail", "commuter_rail", "paratransit")}
        ),
        "des-moines-area-regional-transit-authority-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70010",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "detroit-transportation-corporation-dba-detroit-people-mover-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50141",
             "primary_modes": ("light_rail",)}
        ),
        "district-department-of-transportation-dba-dc-circulator-dc-streetcar-dc": MappingProxyType(
            {"subdivision": "DC", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "30112",
             "primary_modes": ("streetcar",)}
        ),
        "duluth-transit-authority-dba-dta-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50025",
             "primary_modes": ("bus", "paratransit")}
        ),
        "dutchess-county-dba-dutchess-county-public-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20010",
             "primary_modes": ("bus", "paratransit")}
        ),
        "el-paso-county-dba-el-paso-transportation-authority-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60179",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "erie-metropolitan-transit-authority-dba-the-e-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30013",
             "primary_modes": ("bus", "paratransit")}
        ),
        "escambia-county-board-of-county-commissioners-fl-dba-escambia-county-area-transit-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40038",
             "primary_modes": ("bus", "paratransit")}
        ),
        "fairfax-county-va-dba-fairfax-connector-bus-system-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30068",
             "primary_modes": ("bus",)}
        ),
        "florida-department-of-transportation-district-1-office-dba-commute-connector-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40271",
             "primary_modes": ("on_demand",)}
        ),
        "foothill-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90146",
             "primary_modes": ("bus",)}
        ),
        "fort-bend-county-texas-dba-fort-bend-transit-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60103",
             "primary_modes": ("bus", "paratransit")}
        ),
        "fort-wayne-public-transportation-corporation-dba-citilink-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50044",
             "primary_modes": ("bus", "paratransit")}
        ),
        "fort-worth-transportation-authority-dba-trinity-metro-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60007",
             "primary_modes": ("bus", "commuter_rail", "paratransit", "on_demand")}
        ),
        "frederick-county-maryland-dba-transit-services-of-frederick-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30072",
             "primary_modes": ("bus", "paratransit")}
        ),
        "gary-public-transportation-corporation-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50045",
             "primary_modes": ("bus", "paratransit")}
        ),
        "gold-coast-transit-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90035",
             "primary_modes": ("bus", "paratransit")}
        ),
        "golden-crescent-regional-planning-commission-dba-victoria-transit-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 8,
             "currency": "USD", "country": "US", "ntd_id": "60095",
             "primary_modes": ("bus", "paratransit")}
        ),
        "golden-empire-transit-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90004",
             "primary_modes": ("bus", "paratransit")}
        ),
        "golden-gate-bridge-highway-and-transportation-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90016",
             "primary_modes": ("bus", "ferry", "paratransit")}
        ),
        "great-falls-transit-district-mt": MappingProxyType(
            {"subdivision": "MT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "80012",
             "primary_modes": ("bus", "paratransit")}
        ),
        "greater-attleboro-taunton-regional-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10064",
             "primary_modes": ("bus", "paratransit")}
        ),
        "greater-bridgeport-transit-authority-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10050",
             "primary_modes": ("bus", "paratransit")}
        ),
        "greater-dayton-regional-transit-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50017",
             "primary_modes": ("bus", "trolleybus", "paratransit")}
        ),
        "greater-hartford-transit-district-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10017",
             "primary_modes": ("paratransit",)}
        ),
        "greater-lafayette-public-transportation-corporation-dba-citybus-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50051",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "greater-lynchburg-transit-company-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30008",
             "primary_modes": ("bus", "paratransit")}
        ),
        "greater-new-haven-transit-district-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10049",
             "primary_modes": ("paratransit",)}
        ),
        "greater-peoria-mass-transit-district-dba-citylink-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50056",
             "primary_modes": ("bus", "paratransit")}
        ),
        "greater-portland-transit-district-dba-metro-me": MappingProxyType(
            {"subdivision": "ME", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "10016",
             "primary_modes": ("bus", "paratransit")}
        ),
        "greater-richmond-transit-company-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30006",
             "primary_modes": ("bus", "brt", "paratransit", "on_demand")}
        ),
        "greater-roanoke-transit-company-dba-valley-metro-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30007",
             "primary_modes": ("bus", "paratransit")}
        ),
        "green-mountain-transit-authority-vt": MappingProxyType(
            {"subdivision": "VT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10066",
             "primary_modes": ("bus", "paratransit")}
        ),
        "greene-county-transit-board-dba-greene-cats-public-transit-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50165",
             "primary_modes": ("paratransit",)}
        ),
        "greenville-transit-authority-dba-greenlink-sc": MappingProxyType(
            {"subdivision": "SC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40053",
             "primary_modes": ("bus", "paratransit")}
        ),
        "gwinnett-county-board-of-commissioners-dba-ride-gwinnett-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "40138",
             "primary_modes": ("bus", "paratransit")}
        ),
        "hampton-jitney-inc-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20217",
             "primary_modes": ("bus",)}
        ),
        "harris-county-dba-harris-county-transit-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60108",
             "primary_modes": ("bus", "paratransit")}
        ),
        "heart-of-iowa-regional-transit-agency-dba-hirta-public-transit-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70066",
             "primary_modes": ("paratransit", "on_demand")}
        ),
        "hendricks-county-sycamore-services-dba-link-hendricks-county-morgan-county-connect-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50342",
             "primary_modes": ("paratransit",)}
        ),
        "hill-country-transit-district-dba-the-hop-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60091",
             "primary_modes": ("bus", "paratransit")}
        ),
        "hillsborough-area-regional-transit-authority-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40041",
             "primary_modes": ("bus", "streetcar", "paratransit")}
        ),
        "housatonic-area-regional-transit-dba-hartransit-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10051",
             "primary_modes": ("bus", "paratransit")}
        ),
        "hyannis-harbor-tours-inc-dba-hy-line-cruises-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 2,
             "currency": "USD", "country": "US", "ntd_id": "11239",
             "primary_modes": ("ferry",)}
        ),
        "imperial-county-transportation-commission-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90226",
             "primary_modes": ("bus", "paratransit")}
        ),
        "indian-river-county-dba-goline-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40104",
             "primary_modes": ("bus", "paratransit")}
        ),
        "indianapolis-and-marion-county-public-transportation-dba-indygo-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50050",
             "primary_modes": ("bus", "brt", "paratransit")}
        ),
        "intercity-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00019",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "interurban-transit-partnership-dba-the-rapid-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50033",
             "primary_modes": ("bus", "brt", "paratransit")}
        ),
        "jackson-transit-authority-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40057",
             "primary_modes": ("bus", "paratransit")}
        ),
        "jacksonville-transportation-authority-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40040",
             "primary_modes": ("bus", "light_rail", "ferry", "paratransit")}
        ),
        "jaunt-inc-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30045",
             "primary_modes": ("bus", "paratransit")}
        ),
        "jefferson-parish-dba-jefferson-transit-la": MappingProxyType(
            {"subdivision": "LA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60088",
             "primary_modes": ("bus", "paratransit")}
        ),
        "johnson-county-kansas-dba-johnson-county-transit-ks": MappingProxyType(
            {"subdivision": "KS", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "70035",
             "primary_modes": ("bus", "paratransit")}
        ),
        "kanawha-valley-regional-transportation-authority-wv": MappingProxyType(
            {"subdivision": "WV", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30001",
             "primary_modes": ("bus", "paratransit")}
        ),
        "kansas-city-area-transportation-authority-mo": MappingProxyType(
            {"subdivision": "MO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "70005",
             "primary_modes": ("bus", "brt", "paratransit", "on_demand")}
        ),
        "kansas-city-city-of-missouri-dba-kansas-city-streetcar-mo": MappingProxyType(
            {"subdivision": "MO", "fiscal_year_end_month": 4,
             "currency": "USD", "country": "US", "ntd_id": "70271",
             "primary_modes": ("streetcar",)}
        ),
        "king-county-dba-king-county-metro-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00001",
             "primary_modes": ("bus", "streetcar", "trolleybus", "ferry", "paratransit", "on_demand")}
        ),
        "kings-county-area-public-transit-agency-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90200",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "kitsap-county-public-transportation-benefit-area-authority-dba-kitsap-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00020",
             "primary_modes": ("bus", "ferry", "paratransit", "on_demand")}
        ),
        "knoxville-knox-county-community-action-committee-dba-knox-county-cac-transit-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40171",
             "primary_modes": ("paratransit",)}
        ),
        "lafayette-city-parish-consolidated-government-dba-lafayette-transit-system-la": MappingProxyType(
            {"subdivision": "LA", "fiscal_year_end_month": 10,
             "currency": "USD", "country": "US", "ntd_id": "60038",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lake-county-board-of-county-commissioners-dba-lakexpress-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40158",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lake-erie-transportation-commission-dba-lake-erie-transit-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50522",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lakeland-area-mass-transit-district-dba-citrus-connection-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40031",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lakeland-bus-lines-inc-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20163",
             "primary_modes": ("bus",)}
        ),
        "laketran-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50117",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lane-transit-district-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00007",
             "primary_modes": ("bus", "brt", "paratransit", "on_demand")}
        ),
        "lee-county-dba-leetran-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40028",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lehigh-and-northampton-transportation-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30010",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lexington-transit-authority-dba-lextran-ky": MappingProxyType(
            {"subdivision": "KY", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40017",
             "primary_modes": ("bus", "paratransit")}
        ),
        "licking-county-ohio-dba-licking-county-transit-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50163",
             "primary_modes": ("bus", "paratransit")}
        ),
        "livermore-amador-valley-transit-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90144",
             "primary_modes": ("bus",)}
        ),
        "long-beach-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90023",
             "primary_modes": ("bus", "paratransit")}
        ),
        "loop-trolley-transportation-development-district-mo": MappingProxyType(
            {"subdivision": "MO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "70057",
             "primary_modes": ("streetcar",)}
        ),
        "los-angeles-county-metropolitan-transportation-authority-dba-metro-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90154",
             "primary_modes": ("bus", "subway", "light_rail", "brt", "paratransit", "on_demand")}
        ),
        "loudoun-county-dba-loudoun-county-transit-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30081",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lowell-regional-transit-authority-dba-lrta-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10005",
             "primary_modes": ("bus", "paratransit")}
        ),
        "lower-rio-grande-valley-development-council-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60090",
             "primary_modes": ("bus", "paratransit")}
        ),
        "luzerne-county-transportation-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30015",
             "primary_modes": ("bus", "paratransit")}
        ),
        "macatawa-area-express-transportation-authority-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50184",
             "primary_modes": ("bus", "paratransit")}
        ),
        "madison-county-transit-district-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50146",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "manatee-county-board-of-county-commissioners-dba-manatee-county-area-transit-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40026",
             "primary_modes": ("bus", "paratransit")}
        ),
        "marin-county-transit-district-dba-marin-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90234",
             "primary_modes": ("bus", "paratransit")}
        ),
        "martin-county-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40192",
             "primary_modes": ("bus", "paratransit")}
        ),
        "maryland-transit-administration-dba-mta-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30034",
             "primary_modes": ("bus", "subway", "light_rail", "commuter_rail", "paratransit")}
        ),
        "mass-transportation-authority-dba-mta-flint-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50032",
             "primary_modes": ("bus", "paratransit")}
        ),
        "massachusetts-bay-transportation-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10003",
             "primary_modes": ("bus", "subway", "light_rail", "commuter_rail", "brt", "ferry", "paratransit")}
        ),
        "mckinney-avenue-transit-authority-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60133",
             "primary_modes": ("streetcar",)}
        ),
        "mecklenburg-county-dba-mecklenburg-transportation-system-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40228",
             "primary_modes": ("paratransit",)}
        ),
        "medina-county-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50198",
             "primary_modes": ("paratransit",)}
        ),
        "merrimack-valley-regional-transit-authority-dba-merrimack-valley-transit-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10013",
             "primary_modes": ("bus", "paratransit")}
        ),
        "metro-north-commuter-railroad-company-dba-mta-metro-north-railroad-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20078",
             "primary_modes": ("bus", "commuter_rail", "ferry")}
        ),
        "metro-regional-transit-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50010",
             "primary_modes": ("bus", "paratransit")}
        ),
        "metro-transit-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50027",
             "primary_modes": ("bus", "light_rail", "commuter_rail", "brt")}
        ),
        "metropolitan-atlanta-rapid-transit-authority-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40022",
             "primary_modes": ("bus", "subway", "streetcar", "brt", "paratransit")}
        ),
        "metropolitan-bus-authority-pr": MappingProxyType(
            {"subdivision": "PR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40086",
             "primary_modes": ("bus", "paratransit")}
        ),
        "metropolitan-council-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50154",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "metropolitan-transit-authority-dba-wego-public-transit-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40004",
             "primary_modes": ("bus", "paratransit")}
        ),
        "metropolitan-transit-authority-of-harris-county-texas-dba-metro-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60008",
             "primary_modes": ("bus", "light_rail", "paratransit", "on_demand")}
        ),
        "metropolitan-transportation-commission-dba-mtc-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90094",
             "primary_modes": ("on_demand",)}
        ),
        "metropolitan-tulsa-transit-authority-dba-tulsa-transit-metrolink-tulsa-ok": MappingProxyType(
            {"subdivision": "OK", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "60018",
             "primary_modes": ("bus", "paratransit")}
        ),
        "metrowest-regional-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10118",
             "primary_modes": ("bus", "paratransit")}
        ),
        "michiana-area-council-of-governments-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50149",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "michigan-department-of-transportation-dba-michivan-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50193",
             "primary_modes": ("on_demand",)}
        ),
        "mid-mon-valley-transit-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30061",
             "primary_modes": ("bus",)}
        ),
        "mid-ohio-regional-planning-commission-dba-morpc-gohio-commute-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50191",
             "primary_modes": ("on_demand",)}
        ),
        "milford-transit-district-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10107",
             "primary_modes": ("bus", "paratransit")}
        ),
        "milwaukee-county-dba-milwaukee-county-transit-system-wi": MappingProxyType(
            {"subdivision": "WI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50008",
             "primary_modes": ("bus", "paratransit")}
        ),
        "minnesota-valley-transit-authority-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50519",
             "primary_modes": ("bus", "paratransit")}
        ),
        "missoula-urban-transportation-district-dba-mountain-line-mt": MappingProxyType(
            {"subdivision": "MT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "80009",
             "primary_modes": ("bus", "paratransit")}
        ),
        "montachusett-regional-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10061",
             "primary_modes": ("bus", "paratransit")}
        ),
        "monterey-salinas-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90062",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "montgomery-county-maryland-dba-ride-on-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30051",
             "primary_modes": ("bus", "paratransit")}
        ),
        "ms-coast-transportation-authority-dba-coast-transit-authority-ms": MappingProxyType(
            {"subdivision": "MS", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40014",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "mta-bus-company-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20188",
             "primary_modes": ("bus",)}
        ),
        "mta-long-island-rail-road-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20100",
             "primary_modes": ("commuter_rail",)}
        ),
        "mta-new-york-city-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20008",
             "primary_modes": ("bus", "subway", "brt", "paratransit")}
        ),
        "muncie-indiana-transit-system-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50054",
             "primary_modes": ("bus", "paratransit")}
        ),
        "municipality-of-anchorage-ak": MappingProxyType(
            {"subdivision": "AK", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00012",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "napa-valley-transportation-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90088",
             "primary_modes": ("bus", "paratransit")}
        ),
        "nebraska-department-of-transportation-ne": MappingProxyType(
            {"subdivision": "NE", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70275",
             "primary_modes": ("on_demand",)}
        ),
        "new-jersey-transit-corporation-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "20080",
             "primary_modes": ("bus", "light_rail", "commuter_rail", "paratransit", "on_demand")}
        ),
        "new-mexico-department-of-transportation-dba-nmgo-nm": MappingProxyType(
            {"subdivision": "NM", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "66339",
             "primary_modes": ("on_demand",)}
        ),
        "new-orleans-regional-transit-authority-la": MappingProxyType(
            {"subdivision": "LA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60032",
             "primary_modes": ("bus", "streetcar", "ferry", "paratransit")}
        ),
        "new-york-city-department-of-transportation-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "20082",
             "primary_modes": ("ferry",)}
        ),
        "new-york-city-economic-development-corporation-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "22930",
             "primary_modes": ("bus", "ferry")}
        ),
        "niagara-frontier-transportation-authority-dba-nfta-metro-bus-rail-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 3,
             "currency": "USD", "country": "US", "ntd_id": "20004",
             "primary_modes": ("bus", "light_rail", "paratransit")}
        ),
        "north-carolina-state-university-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40147",
             "primary_modes": ("bus",)}
        ),
        "north-county-transit-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90030",
             "primary_modes": ("bus", "commuter_rail", "paratransit")}
        ),
        "north-front-range-transportation-and-air-quality-planning-council-dba-north-front-range-mpo-vango-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80106",
             "primary_modes": ("on_demand",)}
        ),
        "northeast-illinois-regional-commuter-railroad-corporation-dba-metra-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50118",
             "primary_modes": ("commuter_rail",)}
        ),
        "northern-arizona-intergovernmental-public-transportation-authority-dba-mountain-line-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90219",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "northern-indiana-commuter-transportation-district-dba-south-shore-line-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50104",
             "primary_modes": ("commuter_rail",)}
        ),
        "northern-new-england-passenger-rail-authority-dba-amtrak-downeaster-me": MappingProxyType(
            {"subdivision": "ME", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10115",
             "primary_modes": ("commuter_rail",)}
        ),
        "norwalk-transit-district-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10057",
             "primary_modes": ("bus", "paratransit")}
        ),
        "ohio-valley-regional-transportation-authority-wv": MappingProxyType(
            {"subdivision": "WV", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "30035",
             "primary_modes": ("bus", "paratransit")}
        ),
        "okaloosa-county-board-of-county-commissioners-dba-ec-rider-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40128",
             "primary_modes": ("bus", "paratransit")}
        ),
        "omnitrans-dba-omni-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90029",
             "primary_modes": ("bus", "paratransit")}
        ),
        "orange-county-transportation-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90036",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "pace-the-suburban-bus-division-of-the-regional-transportation-authority-dba-pace-suburban-bus-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50113",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "pace-the-suburban-bus-division-of-the-regional-transportation-authority-dba-pace-suburban-bus-il-50182": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50182",
             "primary_modes": ("paratransit",)}
        ),
        "paratransit-inc-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90223",
             "primary_modes": ("bus", "paratransit")}
        ),
        "pasco-county-board-of-county-commissioners-dba-gopasco-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40074",
             "primary_modes": ("bus", "paratransit")}
        ),
        "pee-dee-regional-transportation-authority-sc": MappingProxyType(
            {"subdivision": "SC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40056",
             "primary_modes": ("bus", "paratransit")}
        ),
        "peninsula-corridor-joint-powers-board-dba-caltrain-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90134",
             "primary_modes": ("commuter_rail",)}
        ),
        "pennsylvania-department-of-transportation-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30057",
             "primary_modes": ("commuter_rail",)}
        ),
        "piedmont-authority-for-regional-transportation-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40173",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "pierce-county-transportation-benefit-area-authority-dba-pierce-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00003",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "pima-association-of-governments-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90222",
             "primary_modes": ("on_demand",)}
        ),
        "pinellas-suncoast-transit-authority-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40027",
             "primary_modes": ("bus", "brt", "ferry", "paratransit", "on_demand")}
        ),
        "pioneer-valley-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10008",
             "primary_modes": ("bus", "paratransit")}
        ),
        "pittsburgh-regional-transit-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30022",
             "primary_modes": ("bus", "light_rail", "streetcar", "paratransit")}
        ),
        "plaquemines-port-harbor-and-terminal-district-la": MappingProxyType(
            {"subdivision": "LA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60276",
             "primary_modes": ("ferry",)}
        ),
        "pomona-valley-transportation-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "99425",
             "primary_modes": ("paratransit",)}
        ),
        "port-authority-trans-hudson-corporation-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20098",
             "primary_modes": ("subway",)}
        ),
        "port-authority-transit-corporation-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20075",
             "primary_modes": ("subway",)}
        ),
        "port-imperial-ferry-corporation-dba-ny-waterway-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20190",
             "primary_modes": ("bus", "ferry")}
        ),
        "portage-area-regional-transportation-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50021",
             "primary_modes": ("bus", "paratransit")}
        ),
        "potomac-and-rappahannock-transportation-commission-dba-omniride-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30070",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "prince-george-s-county-maryland-dba-prince-george-s-county-transit-thebus-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30085",
             "primary_modes": ("bus", "paratransit")}
        ),
        "private-transportation-corporation-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20175",
             "primary_modes": ("bus",)}
        ),
        "puerto-rico-highway-and-transportation-authority-pr": MappingProxyType(
            {"subdivision": "PR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40105",
             "primary_modes": ("bus",)}
        ),
        "puerto-rico-maritime-transport-authority-pr": MappingProxyType(
            {"subdivision": "PR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40175",
             "primary_modes": ("ferry",)}
        ),
        "putnam-county-dba-putnam-area-rapid-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20096",
             "primary_modes": ("bus", "paratransit")}
        ),
        "regional-planning-commission-of-greater-birmingham-dba-commutesmart-al": MappingProxyType(
            {"subdivision": "AL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40169",
             "primary_modes": ("on_demand",)}
        ),
        "regional-public-transportation-authority-dba-valley-metro-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90136",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "regional-transit-authority-of-southeast-michigan-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50571",
             "primary_modes": ("bus", "streetcar")}
        ),
        "regional-transit-service-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 3,
             "currency": "USD", "country": "US", "ntd_id": "20113",
             "primary_modes": ("bus", "paratransit")}
        ),
        "regional-transportation-authority-dba-wego-public-transit-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40159",
             "primary_modes": ("bus", "commuter_rail", "on_demand")}
        ),
        "regional-transportation-authority-of-pima-county-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "91122",
             "primary_modes": ("bus", "paratransit")}
        ),
        "regional-transportation-commission-of-southern-nevada-nv": MappingProxyType(
            {"subdivision": "NV", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90045",
             "primary_modes": ("bus", "paratransit")}
        ),
        "regional-transportation-commission-of-washoe-county-nv": MappingProxyType(
            {"subdivision": "NV", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90001",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "research-triangle-regional-public-transportation-authority-dba-gotriangle-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40108",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "rhode-island-department-of-transportation-ri": MappingProxyType(
            {"subdivision": "RI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "11147",
             "primary_modes": ("ferry",)}
        ),
        "rhode-island-public-transit-authority-dba-ripta-ri": MappingProxyType(
            {"subdivision": "RI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10001",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "ride-connection-inc-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00376",
             "primary_modes": ("bus", "paratransit")}
        ),
        "rio-metro-regional-transit-district-nm": MappingProxyType(
            {"subdivision": "NM", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "60111",
             "primary_modes": ("bus", "commuter_rail", "paratransit")}
        ),
        "river-bend-transit-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70049",
             "primary_modes": ("bus", "paratransit")}
        ),
        "river-valley-metro-mass-transit-district-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50159",
             "primary_modes": ("bus", "paratransit")}
        ),
        "river-valley-transit-authority-dba-river-valley-transit-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30207",
             "primary_modes": ("bus", "paratransit")}
        ),
        "riverside-county-transportation-commission-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90218",
             "primary_modes": ("on_demand",)}
        ),
        "riverside-transit-agency-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90031",
             "primary_modes": ("bus", "paratransit")}
        ),
        "rock-island-county-metropolitan-mass-transit-district-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50057",
             "primary_modes": ("bus", "ferry", "paratransit")}
        ),
        "rock-region-metropolitan-transit-authority-dba-rock-region-metro-ar": MappingProxyType(
            {"subdivision": "AR", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60033",
             "primary_modes": ("bus", "streetcar", "paratransit", "on_demand")}
        ),
        "rockford-mass-transit-district-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50058",
             "primary_modes": ("bus", "paratransit")}
        ),
        "rockland-coaches-inc-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20149",
             "primary_modes": ("bus",)}
        ),
        "rogue-valley-transportation-district-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00034",
             "primary_modes": ("bus", "paratransit")}
        ),
        "sacramento-regional-transit-district-dba-sacramento-rt-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90019",
             "primary_modes": ("bus", "light_rail", "paratransit")}
        ),
        "saginaw-transit-authority-regional-service-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50039",
             "primary_modes": ("bus", "paratransit")}
        ),
        "salem-area-mass-transit-district-dba-salem-keizer-transit-or-cherriots-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00025",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "san-bernardino-county-transportation-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90302",
             "primary_modes": ("on_demand",)}
        ),
        "san-diego-association-of-governments-dba-sandag-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90095",
             "primary_modes": ("on_demand",)}
        ),
        "san-diego-metropolitan-transit-system-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90026",
             "primary_modes": ("bus", "light_rail", "paratransit")}
        ),
        "san-francisco-bay-area-rapid-transit-district-dba-sf-bart-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90003",
             "primary_modes": ("subway", "light_rail", "commuter_rail")}
        ),
        "san-francisco-bay-area-water-emergency-transportation-authority-dba-san-francisco-bay-ferry-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90225",
             "primary_modes": ("ferry",)}
        ),
        "san-joaquin-council-dba-dibs-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "99422",
             "primary_modes": ("on_demand",)}
        ),
        "san-joaquin-regional-transit-district-dba-san-joaquin-rtd-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90012",
             "primary_modes": ("bus", "paratransit")}
        ),
        "san-luis-obispo-regional-transit-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90206",
             "primary_modes": ("bus", "paratransit")}
        ),
        "san-mateo-county-transit-district-dba-samtrans-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90009",
             "primary_modes": ("bus", "paratransit")}
        ),
        "santa-barbara-county-association-of-governments-dba-clean-air-express-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90303",
             "primary_modes": ("bus",)}
        ),
        "santa-barbara-metropolitan-transit-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90020",
             "primary_modes": ("bus", "paratransit")}
        ),
        "santa-clara-valley-transportation-authority-dba-valley-transportation-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90013",
             "primary_modes": ("bus", "light_rail", "paratransit")}
        ),
        "santa-cruz-metropolitan-transit-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90006",
             "primary_modes": ("bus", "paratransit")}
        ),
        "santee-wateree-regional-transportation-authority-dba-santee-wateree-rta-sc": MappingProxyType(
            {"subdivision": "SC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40100",
             "primary_modes": ("bus", "paratransit")}
        ),
        "sarasota-county-dba-breeze-transit-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40046",
             "primary_modes": ("bus", "paratransit")}
        ),
        "seastreak-llc-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20226",
             "primary_modes": ("ferry",)}
        ),
        "shortline-transit-llc-dba-short-line-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20126",
             "primary_modes": ("bus",)}
        ),
        "skagit-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00044",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "snohomish-county-public-transportation-benefit-area-corporation-dba-community-transit-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00029",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "solano-county-transit-dba-soltrans-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90232",
             "primary_modes": ("bus", "paratransit")}
        ),
        "somerset-county-dba-somerset-county-transportation-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20209",
             "primary_modes": ("bus", "paratransit")}
        ),
        "sonoma-marin-area-rail-transit-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90299",
             "primary_modes": ("commuter_rail", "paratransit")}
        ),
        "south-bend-public-transportation-corporation-dba-transpo-in": MappingProxyType(
            {"subdivision": "IN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50052",
             "primary_modes": ("bus", "paratransit")}
        ),
        "south-central-transit-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30202",
             "primary_modes": ("bus", "paratransit")}
        ),
        "south-florida-regional-transportation-authority-dba-tri-rail-fl": MappingProxyType(
            {"subdivision": "FL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40077",
             "primary_modes": ("bus", "commuter_rail")}
        ),
        "southeast-area-transit-district-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10040",
             "primary_modes": ("bus", "paratransit")}
        ),
        "southeastern-pennsylvania-transportation-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30019",
             "primary_modes": ("bus", "subway", "commuter_rail", "streetcar", "trolleybus", "paratransit")}
        ),
        "southeastern-regional-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10006",
             "primary_modes": ("bus", "paratransit")}
        ),
        "southern-california-regional-rail-authority-dba-metrolink-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90151",
             "primary_modes": ("commuter_rail",)}
        ),
        "southwest-ohio-regional-transit-authority-dba-metro-access-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50012",
             "primary_modes": ("bus", "paratransit")}
        ),
        "southwest-transit-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50518",
             "primary_modes": ("bus", "paratransit")}
        ),
        "southwestern-pennsylvania-commission-dba-commuteinfo-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30078",
             "primary_modes": ("on_demand",)}
        ),
        "spartanburg-regional-health-services-inc-sc": MappingProxyType(
            {"subdivision": "SC", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40244",
             "primary_modes": ("paratransit",)}
        ),
        "spokane-transit-authority-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00002",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "springfield-mass-transit-district-dba-sangamon-mass-transit-district-il": MappingProxyType(
            {"subdivision": "IL", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50059",
             "primary_modes": ("bus", "paratransit")}
        ),
        "st-cloud-metropolitan-transit-commission-dba-metro-bus-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "50028",
             "primary_modes": ("bus", "paratransit")}
        ),
        "stanislaus-council-of-governments-dba-staniscruise-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90311",
             "primary_modes": ("on_demand",)}
        ),
        "stanislaus-regional-transit-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90306",
             "primary_modes": ("bus", "paratransit")}
        ),
        "star-transit-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 8,
             "currency": "USD", "country": "US", "ntd_id": "60114",
             "primary_modes": ("bus", "paratransit")}
        ),
        "stark-area-regional-transit-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50011",
             "primary_modes": ("bus", "paratransit")}
        ),
        "staten-island-rapid-transit-operating-authority-dba-mta-staten-island-railway-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20099",
             "primary_modes": ("subway",)}
        ),
        "step-inc-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "31036",
             "primary_modes": ("paratransit",)}
        ),
        "suburban-mobility-authority-for-regional-transportation-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50031",
             "primary_modes": ("bus", "paratransit")}
        ),
        "suburban-transit-lines-llc-dba-suburban-transit-nj": MappingProxyType(
            {"subdivision": "NJ", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20128",
             "primary_modes": ("bus",)}
        ),
        "suffolk-county-dba-suffolk-county-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20072",
             "primary_modes": ("bus", "paratransit")}
        ),
        "sunline-transit-agency-dba-sunline-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90079",
             "primary_modes": ("bus", "paratransit")}
        ),
        "susquehanna-regional-transportation-authority-dba-rabbittransit-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30206",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "tahoe-transportation-district-nv": MappingProxyType(
            {"subdivision": "NV", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "91092",
             "primary_modes": ("bus", "paratransit")}
        ),
        "texas-a-m-university-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60278",
             "primary_modes": ("bus",)}
        ),
        "texas-state-university-dba-bobcat-shuttle-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 8,
             "currency": "USD", "country": "US", "ntd_id": "60269",
             "primary_modes": ("bus",)}
        ),
        "texoma-area-paratransit-system-inc-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60107",
             "primary_modes": ("paratransit",)}
        ),
        "the-eastern-contra-costa-transit-authority-dba-tri-delta-transit-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90162",
             "primary_modes": ("bus", "paratransit")}
        ),
        "the-greater-cleveland-regional-transit-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50015",
             "primary_modes": ("bus", "subway", "light_rail", "brt", "paratransit")}
        ),
        "the-transportation-management-association-group-dba-the-tma-group-tn": MappingProxyType(
            {"subdivision": "TN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40178",
             "primary_modes": ("on_demand",)}
        ),
        "the-tri-county-council-for-the-lower-eastern-shore-of-maryland-dba-shore-transit-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30096",
             "primary_modes": ("bus", "paratransit")}
        ),
        "the-tri-state-transit-authority-wv": MappingProxyType(
            {"subdivision": "WV", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30002",
             "primary_modes": ("bus", "paratransit")}
        ),
        "the-woodlands-township-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "60134",
             "primary_modes": ("bus",)}
        ),
        "toledo-area-regional-transit-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50022",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "tompkins-consolidated-area-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20145",
             "primary_modes": ("bus",)}
        ),
        "topeka-metropolitan-transit-authority-dba-topeka-metro-ks": MappingProxyType(
            {"subdivision": "KS", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70014",
             "primary_modes": ("bus", "paratransit")}
        ),
        "town-of-blacksburg-dba-blacksburg-transit-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30091",
             "primary_modes": ("bus", "paratransit")}
        ),
        "town-of-chapel-hill-dba-chapel-hill-transit-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40051",
             "primary_modes": ("bus", "paratransit")}
        ),
        "town-of-huntington-dba-huntington-area-rapid-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20071",
             "primary_modes": ("bus", "paratransit")}
        ),
        "trans-bridge-lines-inc-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20169",
             "primary_modes": ("bus",)}
        ),
        "transit-authority-of-central-kentucky-dba-tack-ky": MappingProxyType(
            {"subdivision": "KY", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40191",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "transit-authority-of-northern-kentucky-ky": MappingProxyType(
            {"subdivision": "KY", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40019",
             "primary_modes": ("bus", "paratransit")}
        ),
        "transit-authority-of-omaha-dba-metro-ne": MappingProxyType(
            {"subdivision": "NE", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "70002",
             "primary_modes": ("bus", "paratransit")}
        ),
        "transit-authority-of-river-city-ky": MappingProxyType(
            {"subdivision": "KY", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40018",
             "primary_modes": ("bus", "paratransit")}
        ),
        "transit-joint-powers-authority-for-merced-county-dba-merced-the-bus-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90173",
             "primary_modes": ("bus", "paratransit")}
        ),
        "transit-management-of-central-maryland-inc-dba-regional-transportation-agency-of-central-maryland-md": MappingProxyType(
            {"subdivision": "MD", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30205",
             "primary_modes": ("bus", "paratransit")}
        ),
        "transportation-district-commission-of-hampton-roads-dba-hampton-roads-transit-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30083",
             "primary_modes": ("bus", "light_rail", "ferry", "paratransit", "on_demand")}
        ),
        "tri-county-metropolitan-transportation-district-of-oregon-dba-trimet-or": MappingProxyType(
            {"subdivision": "OR", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00008",
             "primary_modes": ("bus", "light_rail", "commuter_rail", "paratransit")}
        ),
        "tulare-county-regional-transit-agency-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90310",
             "primary_modes": ("bus", "paratransit")}
        ),
        "ulster-county-dba-ulster-county-area-transit-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20178",
             "primary_modes": ("bus", "paratransit")}
        ),
        "university-of-california-davis-dba-unitrans-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90142",
             "primary_modes": ("bus",)}
        ),
        "university-of-georgia-dba-transportation-and-parking-services-ga": MappingProxyType(
            {"subdivision": "GA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40180",
             "primary_modes": ("bus", "paratransit")}
        ),
        "university-of-iowa-ia": MappingProxyType(
            {"subdivision": "IA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70019",
             "primary_modes": ("bus", "paratransit")}
        ),
        "university-of-kansas-dba-ku-transportation-services-ks": MappingProxyType(
            {"subdivision": "KS", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "70044",
             "primary_modes": ("bus",)}
        ),
        "university-of-michigan-parking-and-transportation-services-mi": MappingProxyType(
            {"subdivision": "MI", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50158",
             "primary_modes": ("bus",)}
        ),
        "university-of-minnesota-mn": MappingProxyType(
            {"subdivision": "MN", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "50515",
             "primary_modes": ("bus",)}
        ),
        "university-of-montana-dba-asum-transportation-mt": MappingProxyType(
            {"subdivision": "MT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "80107",
             "primary_modes": ("bus",)}
        ),
        "university-of-texas-rio-grande-valley-nm": MappingProxyType(
            {"subdivision": "NM", "fiscal_year_end_month": 8,
             "currency": "USD", "country": "US", "ntd_id": "60273",
             "primary_modes": ("bus",)}
        ),
        "utah-transit-authority-ut": MappingProxyType(
            {"subdivision": "UT", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80001",
             "primary_modes": ("bus", "light_rail", "commuter_rail", "paratransit", "on_demand")}
        ),
        "valley-metro-rail-inc-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90209",
             "primary_modes": ("light_rail", "streetcar")}
        ),
        "valley-regional-transit-id": MappingProxyType(
            {"subdivision": "ID", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00011",
             "primary_modes": ("bus", "paratransit")}
        ),
        "valley-transit-district-ct": MappingProxyType(
            {"subdivision": "CT", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10042",
             "primary_modes": ("paratransit",)}
        ),
        "ventura-county-transportation-commission-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90164",
             "primary_modes": ("bus", "paratransit")}
        ),
        "via-metropolitan-transit-dba-via-tx": MappingProxyType(
            {"subdivision": "TX", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "60011",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "via-mobility-services-dba-via-co": MappingProxyType(
            {"subdivision": "CO", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "80285",
             "primary_modes": ("paratransit",)}
        ),
        "victor-valley-transit-authority-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90148",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "virginia-railway-express-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30073",
             "primary_modes": ("commuter_rail",)}
        ),
        "waccamaw-regional-transportation-authority-dba-coast-rta-sc": MappingProxyType(
            {"subdivision": "SC", "fiscal_year_end_month": 9,
             "currency": "USD", "country": "US", "ntd_id": "40102",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "wake-county-dba-gowake-access-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40222",
             "primary_modes": ("paratransit",)}
        ),
        "washington-county-transportation-authority-dba-freedom-transit-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30111",
             "primary_modes": ("bus", "paratransit")}
        ),
        "washington-metropolitan-area-transit-authority-dba-washington-metro-dc": MappingProxyType(
            {"subdivision": "DC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30030",
             "primary_modes": ("bus", "subway", "paratransit")}
        ),
        "washington-state-ferries-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "00035",
             "primary_modes": ("ferry",)}
        ),
        "west-virginia-university-dba-personal-rapid-transit-wv": MappingProxyType(
            {"subdivision": "WV", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30107",
             "primary_modes": ("light_rail",)}
        ),
        "westchester-county-dba-westchester-county-bee-line-ny": MappingProxyType(
            {"subdivision": "NY", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "20076",
             "primary_modes": ("bus", "paratransit")}
        ),
        "western-contra-costa-transit-authority-dba-westcat-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90159",
             "primary_modes": ("bus", "paratransit")}
        ),
        "western-piedmont-regional-transit-authority-dba-greenway-public-transportation-nc": MappingProxyType(
            {"subdivision": "NC", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "40172",
             "primary_modes": ("bus", "paratransit")}
        ),
        "western-reserve-transit-authority-oh": MappingProxyType(
            {"subdivision": "OH", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "50024",
             "primary_modes": ("bus", "paratransit")}
        ),
        "westmoreland-county-transit-authority-pa": MappingProxyType(
            {"subdivision": "PA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30044",
             "primary_modes": ("bus", "paratransit")}
        ),
        "whatcom-transportation-authority-wa": MappingProxyType(
            {"subdivision": "WA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "00021",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
        "williamsburg-area-transit-authority-va": MappingProxyType(
            {"subdivision": "VA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "30076",
             "primary_modes": ("bus", "paratransit")}
        ),
        "woods-hole-martha-s-vineyard-and-nantucket-steamship-authority-dba-the-steamship-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 12,
             "currency": "USD", "country": "US", "ntd_id": "10183",
             "primary_modes": ("bus", "ferry")}
        ),
        "worcester-regional-transit-authority-ma": MappingProxyType(
            {"subdivision": "MA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "10014",
             "primary_modes": ("bus", "paratransit")}
        ),
        "yolo-county-transportation-district-ca": MappingProxyType(
            {"subdivision": "CA", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90090",
             "primary_modes": ("bus", "paratransit")}
        ),
        "yuma-county-intergovernmental-public-transportation-authority-dba-yuma-county-area-transit-az": MappingProxyType(
            {"subdivision": "AZ", "fiscal_year_end_month": 6,
             "currency": "USD", "country": "US", "ntd_id": "90233",
             "primary_modes": ("bus", "paratransit", "on_demand")}
        ),
    }
)

# NTD ID (5-digit zero-padded string, e.g. "00001") -> agency slug.
NTD_AGENCY_MAP: Mapping[str, str] = MappingProxyType(
    {
        "00001": "king-county-dba-king-county-metro-wa",
        "00002": "spokane-transit-authority-wa",
        "00003": "pierce-county-transportation-benefit-area-authority-dba-pierce-transit-wa",
        "00005": "city-of-everett-dba-everett-transit-wa",
        "00006": "city-of-yakima-dba-yakima-transit-wa",
        "00007": "lane-transit-district-or",
        "00008": "tri-county-metropolitan-transportation-district-of-oregon-dba-trimet-or",
        "00011": "valley-regional-transit-id",
        "00012": "municipality-of-anchorage-ak",
        "00016": "city-of-longview-dba-rivercities-transit-wa",
        "00018": "ben-franklin-transit-wa",
        "00019": "intercity-transit-wa",
        "00020": "kitsap-county-public-transportation-benefit-area-authority-dba-kitsap-transit-wa",
        "00021": "whatcom-transportation-authority-wa",
        "00023": "city-of-seattle-dba-seattle-center-monorail-wa",
        "00024": "clark-county-public-transportation-benefit-area-authority-dba-c-tran-wa",
        "00025": "salem-area-mass-transit-district-dba-salem-keizer-transit-or-cherriots-or",
        "00028": "county-of-pierce-dba-pierce-county-ferry-wa",
        "00029": "snohomish-county-public-transportation-benefit-area-corporation-dba-community-transit-wa",
        "00034": "rogue-valley-transportation-district-or",
        "00035": "washington-state-ferries-wa",
        "00040": "central-puget-sound-regional-transit-authority-dba-sound-transit-wa",
        "00041": "alaska-railroad-corporation-ak",
        "00043": "chelan-douglas-ptba-dba-link-transit-wa",
        "00044": "skagit-transit-wa",
        "00046": "city-of-wilsonville-dba-south-metro-area-regional-transit-or",
        "00057": "central-oregon-intergovernmental-council-dba-cascades-east-transit-or",
        "00058": "city-of-portland-dba-portland-streetcar-or",
        "00376": "ride-connection-inc-or",
        "00415": "ada-county-highway-district-dba-achd-commuteride-id",
        "10001": "rhode-island-public-transit-authority-dba-ripta-ri",
        "10003": "massachusetts-bay-transportation-authority-ma",
        "10004": "brockton-area-transit-authority-ma",
        "10005": "lowell-regional-transit-authority-dba-lrta-ma",
        "10006": "southeastern-regional-transit-authority-ma",
        "10007": "berkshire-regional-transit-authority-ma",
        "10008": "pioneer-valley-transit-authority-ma",
        "10013": "merrimack-valley-regional-transit-authority-dba-merrimack-valley-transit-ma",
        "10014": "worcester-regional-transit-authority-ma",
        "10016": "greater-portland-transit-district-dba-metro-me",
        "10017": "greater-hartford-transit-district-ct",
        "10040": "southeast-area-transit-district-ct",
        "10042": "valley-transit-district-ct",
        "10045": "connecticut-department-of-transportation-cttransit-new-britain-dattco-dba-dattco-ct",
        "10048": "connecticut-department-of-transportation-cttransit-hartford-division-dba-cttransit-ct",
        "10049": "greater-new-haven-transit-district-ct",
        "10050": "greater-bridgeport-transit-authority-ct",
        "10051": "housatonic-area-regional-transit-dba-hartransit-ct",
        "10053": "cape-ann-transportation-authority-dba-cata-ma",
        "10055": "connecticut-department-of-transportation-cttransit-new-haven-division-dba-cttransit-ct",
        "10056": "connecticut-department-of-transportation-cttransit-stamford-division-dba-cttransit-ct",
        "10057": "norwalk-transit-district-ct",
        "10061": "montachusett-regional-transit-authority-ma",
        "10064": "greater-attleboro-taunton-regional-transit-authority-ma",
        "10066": "green-mountain-transit-authority-vt",
        "10086": "cooperative-alliance-for-seacoast-transportation-nh",
        "10087": "city-of-nashua-dba-nashua-transit-system-nh",
        "10088": "casco-bay-island-transit-district-dba-casco-bay-lines-me",
        "10102": "connecticut-department-of-transportation-ct",
        "10105": "cape-cod-regional-transit-authority-ma",
        "10107": "milford-transit-district-ct",
        "10115": "northern-new-england-passenger-rail-authority-dba-amtrak-downeaster-me",
        "10118": "metrowest-regional-transit-authority-ma",
        "10128": "connecticut-department-of-transportation-cttransit-waterbury-net-dba-cttransit-ct",
        "10130": "connecticut-department-of-transportation-cttransit-new-britain-dba-cttransit-ct",
        "10183": "woods-hole-martha-s-vineyard-and-nantucket-steamship-authority-dba-the-steamship-authority-ma",
        "11147": "rhode-island-department-of-transportation-ri",
        "11239": "hyannis-harbor-tours-inc-dba-hy-line-cruises-ma",
        "20002": "capital-district-transportation-authority-ny",
        "20003": "broome-county-dba-bc-transit-ny",
        "20004": "niagara-frontier-transportation-authority-dba-nfta-metro-bus-rail-ny",
        "20006": "city-of-long-beach-ny",
        "20008": "mta-new-york-city-transit-ny",
        "20010": "dutchess-county-dba-dutchess-county-public-transit-ny",
        "20018": "central-new-york-regional-transportation-authority-dba-new-york-regional-transportation-authority-ny",
        "20071": "town-of-huntington-dba-huntington-area-rapid-transit-ny",
        "20072": "suffolk-county-dba-suffolk-county-transit-ny",
        "20075": "port-authority-transit-corporation-nj",
        "20076": "westchester-county-dba-westchester-county-bee-line-ny",
        "20078": "metro-north-commuter-railroad-company-dba-mta-metro-north-railroad-ny",
        "20080": "new-jersey-transit-corporation-nj",
        "20082": "new-york-city-department-of-transportation-ny",
        "20084": "county-of-rockland-ny",
        "20096": "putnam-county-dba-putnam-area-rapid-transit-ny",
        "20098": "port-authority-trans-hudson-corporation-ny",
        "20099": "staten-island-rapid-transit-operating-authority-dba-mta-staten-island-railway-ny",
        "20100": "mta-long-island-rail-road-ny",
        "20113": "regional-transit-service-ny",
        "20122": "academy-lines-inc-dba-academy-nj",
        "20126": "shortline-transit-llc-dba-short-line-nj",
        "20128": "suburban-transit-lines-llc-dba-suburban-transit-nj",
        "20145": "tompkins-consolidated-area-transit-ny",
        "20149": "rockland-coaches-inc-nj",
        "20163": "lakeland-bus-lines-inc-nj",
        "20169": "trans-bridge-lines-inc-pa",
        "20175": "private-transportation-corporation-ny",
        "20177": "adirondack-transit-lines-inc-dba-adirondack-trailways-ny",
        "20178": "ulster-county-dba-ulster-county-area-transit-ny",
        "20188": "mta-bus-company-ny",
        "20190": "port-imperial-ferry-corporation-dba-ny-waterway-nj",
        "20199": "county-of-atlantic-nj",
        "20206": "county-of-nassau-dba-nassau-inter-county-express-ny",
        "20209": "somerset-county-dba-somerset-county-transportation-nj",
        "20217": "hampton-jitney-inc-ny",
        "20223": "cape-may-lewes-ferry-de",
        "20226": "seastreak-llc-nj",
        "22930": "new-york-city-economic-development-corporation-ny",
        "30001": "kanawha-valley-regional-transportation-authority-wv",
        "30002": "the-tri-state-transit-authority-wv",
        "30006": "greater-richmond-transit-company-va",
        "30007": "greater-roanoke-transit-company-dba-valley-metro-va",
        "30008": "greater-lynchburg-transit-company-va",
        "30010": "lehigh-and-northampton-transportation-authority-pa",
        "30011": "altoona-metro-transit-dba-amtran-pa",
        "30012": "cambria-county-transit-authority-dba-camtran-pa",
        "30013": "erie-metropolitan-transit-authority-dba-the-e-pa",
        "30015": "luzerne-county-transportation-authority-pa",
        "30019": "southeastern-pennsylvania-transportation-authority-pa",
        "30022": "pittsburgh-regional-transit-pa",
        "30023": "beaver-county-transit-authority-pa",
        "30025": "county-of-lackawanna-transit-system-pa",
        "30030": "washington-metropolitan-area-transit-authority-dba-washington-metro-dc",
        "30034": "maryland-transit-administration-dba-mta-md",
        "30035": "ohio-valley-regional-transportation-authority-wv",
        "30044": "westmoreland-county-transit-authority-pa",
        "30045": "jaunt-inc-va",
        "30051": "montgomery-county-maryland-dba-ride-on-md",
        "30054": "centre-area-transportation-authority-pa",
        "30057": "pennsylvania-department-of-transportation-pa",
        "30058": "city-of-fairfax-dba-cue-bus-va",
        "30061": "mid-mon-valley-transit-authority-pa",
        "30068": "fairfax-county-va-dba-fairfax-connector-bus-system-va",
        "30070": "potomac-and-rappahannock-transportation-commission-dba-omniride-va",
        "30071": "city-of-alexandria-dba-dash-va",
        "30072": "frederick-county-maryland-dba-transit-services-of-frederick-md",
        "30073": "virginia-railway-express-va",
        "30075": "delaware-transit-corporation-de",
        "30076": "williamsburg-area-transit-authority-va",
        "30077": "borough-of-pottstown-dba-pottstown-area-rapid-transit-pa",
        "30078": "southwestern-pennsylvania-commission-dba-commuteinfo-pa",
        "30080": "arlington-county-virginia-dba-arlington-transit-va",
        "30081": "loudoun-county-dba-loudoun-county-transit-va",
        "30083": "transportation-district-commission-of-hampton-roads-dba-hampton-roads-transit-va",
        "30085": "prince-george-s-county-maryland-dba-prince-george-s-county-transit-thebus-md",
        "30087": "county-of-fayette-dba-fayette-area-coordinated-transportation-pa",
        "30088": "county-commissioners-of-charles-county-md-dba-pgm-vango-md",
        "30091": "town-of-blacksburg-dba-blacksburg-transit-va",
        "30094": "city-of-harrisonburg-va",
        "30095": "county-of-lebanon-transit-authority-dba-lebanon-transit-pa",
        "30096": "the-tri-county-council-for-the-lower-eastern-shore-of-maryland-dba-shore-transit-md",
        "30107": "west-virginia-university-dba-personal-rapid-transit-wv",
        "30111": "washington-county-transportation-authority-dba-freedom-transit-pa",
        "30112": "district-department-of-transportation-dba-dc-circulator-dc-streetcar-dc",
        "30129": "anne-arundel-county-md",
        "30201": "city-of-baltimore-dba-charm-city-circulator-md",
        "30202": "south-central-transit-authority-pa",
        "30205": "transit-management-of-central-maryland-inc-dba-regional-transportation-agency-of-central-maryland-md",
        "30206": "susquehanna-regional-transportation-authority-dba-rabbittransit-pa",
        "30207": "river-valley-transit-authority-dba-river-valley-transit-pa",
        "31036": "step-inc-pa",
        "40001": "chattanooga-area-regional-transportation-authority-tn",
        "40002": "city-of-knoxville-dba-knoxville-area-transit-tn",
        "40003": "city-of-memphis-dba-memphis-area-transit-authority-tn",
        "40004": "metropolitan-transit-authority-dba-wego-public-transit-tn",
        "40005": "city-of-asheville-dba-art-asheville-rides-transit-nc",
        "40006": "cape-fear-public-transportation-authority-dba-wave-transit-nc",
        "40007": "city-of-raleigh-dba-goraleigh-nc",
        "40008": "city-of-charlotte-north-carolina-nc",
        "40009": "city-of-fayetteville-dba-fayetteville-area-system-of-transit-nc",
        "40012": "city-of-winston-salem-dba-winston-salem-transit-authority-nc",
        "40014": "ms-coast-transportation-authority-dba-coast-transit-authority-ms",
        "40015": "city-of-jackson-ms-ms",
        "40017": "lexington-transit-authority-dba-lextran-ky",
        "40018": "transit-authority-of-river-city-ky",
        "40019": "transit-authority-of-northern-kentucky-ky",
        "40021": "city-of-albany-dba-albany-transit-system-ga",
        "40022": "metropolitan-atlanta-rapid-transit-authority-ga",
        "40023": "augusta-richmond-county-transit-department-dba-augusta-transit-ga",
        "40025": "chatham-area-transit-authority-ga",
        "40026": "manatee-county-board-of-county-commissioners-dba-manatee-county-area-transit-fl",
        "40027": "pinellas-suncoast-transit-authority-fl",
        "40028": "lee-county-dba-leetran-fl",
        "40029": "broward-county-board-of-county-commissioners-dba-broward-county-transit-division-fl",
        "40030": "city-of-gainesville-fl-dba-regional-transit-system-fl",
        "40031": "lakeland-area-mass-transit-district-dba-citrus-connection-fl",
        "40032": "county-of-volusia-dba-votran-fl",
        "40034": "county-of-miami-dade-fl",
        "40035": "central-florida-regional-transportation-authority-fl",
        "40036": "city-of-tallahassee-fl",
        "40037": "board-of-county-commissioners-palm-beach-county-dba-palm-tran-inc-fl",
        "40038": "escambia-county-board-of-county-commissioners-fl-dba-escambia-county-area-transit-fl",
        "40040": "jacksonville-transportation-authority-fl",
        "40041": "hillsborough-area-regional-transit-authority-fl",
        "40042": "birmingham-jefferson-county-transit-authority-al",
        "40043": "city-of-mobile-dba-the-wave-transit-system-al",
        "40044": "city-of-montgomery-dba-the-m-transit-al",
        "40046": "sarasota-county-dba-breeze-transit-fl",
        "40047": "athens-clarke-county-unified-government-dba-athens-clarke-county-transit-department-ga",
        "40051": "town-of-chapel-hill-dba-chapel-hill-transit-nc",
        "40053": "greenville-transit-authority-dba-greenlink-sc",
        "40056": "pee-dee-regional-transportation-authority-sc",
        "40057": "jackson-transit-authority-tn",
        "40058": "city-of-rome-ga",
        "40063": "brevard-board-of-county-commissioners-dba-space-coast-area-transit-fl",
        "40071": "city-of-huntsville-alabama-dba-huntsville-transit-al",
        "40074": "pasco-county-board-of-county-commissioners-dba-gopasco-fl",
        "40077": "south-florida-regional-transportation-authority-dba-tri-rail-fl",
        "40078": "cobb-county-dba-cobblinc-ga",
        "40082": "county-of-douglas-dba-connect-douglas-ga",
        "40086": "metropolitan-bus-authority-pr",
        "40087": "city-of-durham-dba-godurham-nc",
        "40093": "city-of-greensboro-dba-greensboro-transit-agency-nc",
        "40094": "alternativa-de-transporte-integrado-dba-autoridad-de-transporte-integrado-pr",
        "40100": "santee-wateree-regional-transportation-authority-dba-santee-wateree-rta-sc",
        "40102": "waccamaw-regional-transportation-authority-dba-coast-rta-sc",
        "40104": "indian-river-county-dba-goline-fl",
        "40105": "puerto-rico-highway-and-transportation-authority-pr",
        "40108": "research-triangle-regional-public-transportation-authority-dba-gotriangle-nc",
        "40110": "charleston-area-regional-transportation-authority-sc",
        "40128": "okaloosa-county-board-of-county-commissioners-dba-ec-rider-fl",
        "40129": "charlotte-county-government-dba-charlotte-county-transit-division-fl",
        "40138": "gwinnett-county-board-of-commissioners-dba-ride-gwinnett-ga",
        "40140": "collier-county-dba-collier-area-transit-fl",
        "40141": "central-midlands-regional-transportation-authority-dba-the-comet-sc",
        "40147": "north-carolina-state-university-nc",
        "40158": "lake-county-board-of-county-commissioners-dba-lakexpress-fl",
        "40159": "regional-transportation-authority-dba-wego-public-transit-tn",
        "40169": "regional-planning-commission-of-greater-birmingham-dba-commutesmart-al",
        "40171": "knoxville-knox-county-community-action-committee-dba-knox-county-cac-transit-tn",
        "40172": "western-piedmont-regional-transit-authority-dba-greenway-public-transportation-nc",
        "40173": "piedmont-authority-for-regional-transportation-nc",
        "40175": "puerto-rico-maritime-transport-authority-pr",
        "40178": "the-transportation-management-association-group-dba-the-tma-group-tn",
        "40180": "university-of-georgia-dba-transportation-and-parking-services-ga",
        "40185": "bay-county-transportation-planning-organization-dba-bayway-fl",
        "40191": "transit-authority-of-central-kentucky-dba-tack-ky",
        "40192": "martin-county-fl",
        "40222": "wake-county-dba-gowake-access-nc",
        "40224": "buncombe-county-dba-mountain-mobility-nc",
        "40228": "mecklenburg-county-dba-mecklenburg-transportation-system-nc",
        "40232": "central-florida-commuter-rail-dba-sunrail-fl",
        "40244": "spartanburg-regional-health-services-inc-sc",
        "40271": "florida-department-of-transportation-district-1-office-dba-commute-connector-ga",
        "40928": "baldwin-county-commission-dba-baldwin-regional-area-transit-system-al",
        "41199": "board-of-county-commissioners-of-st-lucie-county-dba-area-regional-transit-fl",
        "42000": "atlanta-region-transit-link-authority-ga",
        "44929": "city-of-fort-lauderdale-fl",
        "50001": "city-of-appleton-dba-valley-transit-wi",
        "50002": "city-of-green-bay-dba-green-bay-metro-wi",
        "50003": "city-of-kenosha-dba-kenosha-area-transit-wi",
        "50004": "city-of-la-crosse-dba-city-of-la-crosse-mtu-wi",
        "50005": "city-of-madison-wi",
        "50006": "city-of-racine-wisconsin-dba-ryde-racine-wi",
        "50008": "milwaukee-county-dba-milwaukee-county-transit-system-wi",
        "50010": "metro-regional-transit-authority-oh",
        "50011": "stark-area-regional-transit-authority-oh",
        "50012": "southwest-ohio-regional-transit-authority-dba-metro-access-oh",
        "50015": "the-greater-cleveland-regional-transit-authority-oh",
        "50016": "central-ohio-transit-authority-oh",
        "50017": "greater-dayton-regional-transit-authority-oh",
        "50021": "portage-area-regional-transportation-authority-oh",
        "50022": "toledo-area-regional-transit-authority-oh",
        "50024": "western-reserve-transit-authority-oh",
        "50025": "duluth-transit-authority-dba-dta-mn",
        "50026": "city-of-moorhead-dba-matbus-mn",
        "50027": "metro-transit-mn",
        "50028": "st-cloud-metropolitan-transit-commission-dba-metro-bus-mn",
        "50029": "bay-metropolitan-transit-authority-dba-bay-metro-mi",
        "50031": "suburban-mobility-authority-for-regional-transportation-mi",
        "50032": "mass-transportation-authority-dba-mta-flint-mi",
        "50033": "interurban-transit-partnership-dba-the-rapid-mi",
        "50034": "city-of-jackson-transportation-authority-dba-jackson-area-transportation-authority-mi",
        "50035": "central-county-transportation-authority-dba-metro-transit-mi",
        "50036": "capital-area-transportation-authority-mi",
        "50039": "saginaw-transit-authority-regional-service-mi",
        "50040": "ann-arbor-area-transportation-authority-mi",
        "50043": "city-of-evansville-in",
        "50044": "fort-wayne-public-transportation-corporation-dba-citilink-in",
        "50045": "gary-public-transportation-corporation-in",
        "50047": "bloomington-normal-public-transit-system-dba-connect-transit-il",
        "50050": "indianapolis-and-marion-county-public-transportation-dba-indygo-in",
        "50051": "greater-lafayette-public-transportation-corporation-dba-citybus-in",
        "50052": "south-bend-public-transportation-corporation-dba-transpo-in",
        "50053": "city-of-terre-haute-dba-terre-haute-transit-utility-in",
        "50054": "muncie-indiana-transit-system-in",
        "50056": "greater-peoria-mass-transit-district-dba-citylink-il",
        "50057": "rock-island-county-metropolitan-mass-transit-district-il",
        "50058": "rockford-mass-transit-district-il",
        "50059": "springfield-mass-transit-district-dba-sangamon-mass-transit-district-il",
        "50060": "champaign-urbana-mass-transit-district-il",
        "50061": "city-of-decatur-il-dba-decatur-public-transit-system-il",
        "50066": "chicago-transit-authority-il",
        "50092": "city-of-rochester-minnesota-dba-rochester-public-transit-mn",
        "50096": "city-of-waukesha-dba-waukesha-metro-transit-wi",
        "50099": "city-of-eau-claire-dba-eau-claire-transit-wi",
        "50104": "northern-indiana-commuter-transportation-district-dba-south-shore-line-in",
        "50110": "bloomington-public-transportation-corporation-dba-bloomington-transit-in",
        "50113": "pace-the-suburban-bus-division-of-the-regional-transportation-authority-dba-pace-suburban-bus-il",
        "50117": "laketran-oh",
        "50118": "northeast-illinois-regional-commuter-railroad-corporation-dba-metra-il",
        "50119": "city-of-detroit-dba-detroit-department-of-transportation-mi",
        "50141": "detroit-transportation-corporation-dba-detroit-people-mover-mi",
        "50145": "city-of-kokomo-in",
        "50146": "madison-county-transit-district-il",
        "50148": "blue-water-area-transportation-commission-dba-blue-water-area-transit-mi",
        "50149": "michiana-area-council-of-governments-in",
        "50154": "metropolitan-council-mn",
        "50157": "butler-county-regional-transit-authority-dba-bcrta-oh",
        "50158": "university-of-michigan-parking-and-transportation-services-mi",
        "50159": "river-valley-metro-mass-transit-district-il",
        "50163": "licking-county-ohio-dba-licking-county-transit-oh",
        "50165": "greene-county-transit-board-dba-greene-cats-public-transit-oh",
        "50166": "clermont-county-ohio-oh",
        "50176": "city-of-dekalb-dba-city-of-dekalb-public-transit-il",
        "50182": "pace-the-suburban-bus-division-of-the-regional-transportation-authority-dba-pace-suburban-bus-il-50182",
        "50184": "macatawa-area-express-transportation-authority-mi",
        "50191": "mid-ohio-regional-planning-commission-dba-morpc-gohio-commute-oh",
        "50193": "michigan-department-of-transportation-dba-michivan-mi",
        "50198": "medina-county-oh",
        "50199": "delaware-county-transit-board-oh",
        "50209": "central-indiana-regional-transportation-authority-in",
        "50314": "clinton-area-transit-system-dba-my-blue-bus-mi",
        "50342": "hendricks-county-sycamore-services-dba-link-hendricks-county-morgan-county-connect-in",
        "50413": "bay-area-transportation-authority-mi",
        "50515": "university-of-minnesota-mn",
        "50516": "city-of-plymouth-dba-plymouth-metrolink-mn",
        "50517": "city-of-maple-grove-dba-maple-grove-transit-mn",
        "50518": "southwest-transit-mn",
        "50519": "minnesota-valley-transit-authority-mn",
        "50521": "chicago-water-taxi-wendella-il",
        "50522": "lake-erie-transportation-commission-dba-lake-erie-transit-mi",
        "50571": "regional-transit-authority-of-southeast-michigan-mi",
        "55311": "city-of-cincinnati-dba-the-connector-oh",
        "55312": "city-of-milwaukee-dba-milwaukee-streetcar-system-the-hop-streetcar-mke-wi",
        "60006": "city-of-el-paso-dba-sun-metro-tx",
        "60007": "fort-worth-transportation-authority-dba-trinity-metro-tx",
        "60008": "metropolitan-transit-authority-of-harris-county-texas-dba-metro-tx",
        "60009": "city-of-laredo-dba-laredo-transit-management-inc-tx",
        "60010": "city-of-lubbock-dba-citibus-tx",
        "60011": "via-metropolitan-transit-dba-via-tx",
        "60012": "city-of-waco-dba-waco-transit-system-inc-tx",
        "60014": "city-of-brownsville-dba-brownsville-metro-tx",
        "60015": "city-of-galveston-dba-galveston-island-transit-tx",
        "60016": "city-of-beaumont-dba-beaumont-municipal-transit-system-tx",
        "60017": "central-oklahoma-transportation-and-parking-authority-dba-embark-ok",
        "60018": "metropolitan-tulsa-transit-authority-dba-tulsa-transit-metrolink-tulsa-ok",
        "60019": "city-of-albuquerque-dba-abqride-nm",
        "60022": "capital-area-transit-system-la",
        "60024": "city-of-shreveport-dba-sportran-la",
        "60032": "new-orleans-regional-transit-authority-la",
        "60033": "rock-region-metropolitan-transit-authority-dba-rock-region-metro-ar",
        "60038": "lafayette-city-parish-consolidated-government-dba-lafayette-transit-system-la",
        "60041": "city-of-arlington-dba-arlington-transportation-tx",
        "60048": "capital-metropolitan-transportation-authority-dba-capital-metro-tx",
        "60051": "corpus-christi-regional-transportation-authority-dba-the-b-tx",
        "60056": "dallas-area-rapid-transit-tx",
        "60059": "brazos-transit-district-tx",
        "60077": "city-of-santa-fe-dba-santa-fe-trails-nm",
        "60088": "jefferson-parish-dba-jefferson-transit-la",
        "60090": "lower-rio-grande-valley-development-council-tx",
        "60091": "hill-country-transit-district-dba-the-hop-tx",
        "60095": "golden-crescent-regional-planning-commission-dba-victoria-transit-tx",
        "60101": "denton-county-transportation-authority-tx",
        "60102": "concho-valley-transit-district-tx",
        "60103": "fort-bend-county-texas-dba-fort-bend-transit-tx",
        "60107": "texoma-area-paratransit-system-inc-tx",
        "60108": "harris-county-dba-harris-county-transit-tx",
        "60111": "rio-metro-regional-transit-district-nm",
        "60114": "star-transit-tx",
        "60133": "mckinney-avenue-transit-authority-tx",
        "60134": "the-woodlands-township-tx",
        "60179": "el-paso-county-dba-el-paso-transportation-authority-tx",
        "60246": "central-arkansas-development-council-dba-south-central-arkansas-transit-ar",
        "60269": "texas-state-university-dba-bobcat-shuttle-tx",
        "60270": "city-of-mckinney-dba-collin-county-transit-tx",
        "60273": "university-of-texas-rio-grande-valley-nm",
        "60276": "plaquemines-port-harbor-and-terminal-district-la",
        "60278": "texas-a-m-university-tx",
        "66339": "new-mexico-department-of-transportation-dba-nmgo-nm",
        "70001": "city-of-lincoln-dba-startran-ne",
        "70002": "transit-authority-of-omaha-dba-metro-ne",
        "70003": "city-of-springfield-dba-city-utilities-of-springfield-mo-mo",
        "70005": "kansas-city-area-transportation-authority-mo",
        "70006": "bi-state-development-agency-of-the-missouri-illinois-metropolitan-district-dba-st-louis-metro-mo",
        "70008": "city-of-cedar-rapids-dba-cedar-rapids-transit-ia",
        "70009": "city-of-davenport-dba-davenport-citibus-ia",
        "70010": "des-moines-area-regional-transit-authority-ia",
        "70012": "city-of-sioux-city-dba-sioux-city-transit-system-ia",
        "70014": "topeka-metropolitan-transit-authority-dba-topeka-metro-ks",
        "70015": "city-of-wichita-dba-wichita-transit-ks",
        "70016": "city-of-columbia-dba-gocomo-mo",
        "70018": "city-of-iowa-city-dba-iowa-city-transit-ia",
        "70019": "university-of-iowa-ia",
        "70030": "city-of-coralville-dba-coralville-transit-system-ia",
        "70035": "johnson-county-kansas-dba-johnson-county-transit-ks",
        "70041": "ames-transit-agency-dba-cyride-ia",
        "70044": "university-of-kansas-dba-ku-transportation-services-ks",
        "70045": "county-of-johnson-iowa-dba-johnson-county-seats-ia",
        "70048": "city-of-lawrence-dba-lawrence-transit-ks",
        "70049": "river-bend-transit-ia",
        "70057": "loop-trolley-transportation-development-district-mo",
        "70066": "heart-of-iowa-regional-transit-agency-dba-hirta-public-transit-ia",
        "70271": "kansas-city-city-of-missouri-dba-kansas-city-streetcar-mo",
        "70275": "nebraska-department-of-transportation-ne",
        "80001": "utah-transit-authority-ut",
        "80002": "city-of-sioux-falls-dba-sioux-area-metro-sd",
        "80003": "city-of-fargo-dba-metropolitan-area-transit-nd",
        "80004": "city-of-billings-dba-billings-metropolitan-transit-system-mt",
        "80005": "city-of-colorado-springs-dba-mountain-metropolitan-transit-co",
        "80006": "denver-regional-transportation-district-dba-rtd-denver-co",
        "80007": "city-of-pueblo-dba-pueblo-transit-co",
        "80008": "city-of-grand-forks-nd",
        "80009": "missoula-urban-transportation-district-dba-mountain-line-mt",
        "80011": "city-of-fort-collins-dba-transfort-co",
        "80012": "great-falls-transit-district-mt",
        "80025": "city-of-loveland-colorado-dba-city-of-loveland-transit-co",
        "80028": "cache-valley-transit-district-dba-connect-transit-ut",
        "80106": "north-front-range-transportation-and-air-quality-planning-council-dba-north-front-range-mpo-vango-co",
        "80107": "university-of-montana-dba-asum-transportation-mt",
        "80109": "denver-regional-council-of-governments-co",
        "80285": "via-mobility-services-dba-via-co",
        "90001": "regional-transportation-commission-of-washoe-county-nv",
        "90002": "city-and-county-of-honolulu-hi",
        "90003": "san-francisco-bay-area-rapid-transit-district-dba-sf-bart-ca",
        "90004": "golden-empire-transit-district-ca",
        "90006": "santa-cruz-metropolitan-transit-district-ca",
        "90008": "city-of-santa-monica-dba-big-blue-bus-ca",
        "90009": "san-mateo-county-transit-district-dba-samtrans-ca",
        "90010": "city-of-torrance-dba-torrance-transit-system-ca",
        "90012": "san-joaquin-regional-transit-district-dba-san-joaquin-rtd-ca",
        "90013": "santa-clara-valley-transportation-authority-dba-valley-transportation-authority-ca",
        "90014": "alameda-contra-costa-transit-district-dba-ac-transit-ca",
        "90015": "city-and-county-of-san-francisco-dba-san-francisco-municipal-transportation-agency-ca",
        "90016": "golden-gate-bridge-highway-and-transportation-district-ca",
        "90017": "city-of-santa-rosa-dba-santa-rosa-citybus-ca",
        "90019": "sacramento-regional-transit-district-dba-sacramento-rt-ca",
        "90020": "santa-barbara-metropolitan-transit-district-ca",
        "90022": "city-of-norwalk-dba-norwalk-transit-system-ca",
        "90023": "long-beach-transit-ca",
        "90024": "city-of-la-mirada-dba-la-mirada-transit-ca",
        "90026": "san-diego-metropolitan-transit-system-ca",
        "90027": "city-of-fresno-dba-fresno-area-express-ca",
        "90029": "omnitrans-dba-omni-ca",
        "90030": "north-county-transit-district-ca",
        "90031": "riverside-transit-agency-ca",
        "90032": "city-of-phoenix-dba-valley-metro-az",
        "90033": "city-of-tucson-dba-sun-tran-az",
        "90034": "city-of-glendale-az",
        "90035": "gold-coast-transit-district-ca",
        "90036": "orange-county-transportation-authority-ca",
        "90039": "city-of-culver-city-dba-culver-citybus-ca",
        "90041": "city-of-montebello-dba-montebello-bus-lines-ca",
        "90042": "city-of-gardena-dba-gtrans-ca",
        "90043": "city-of-commerce-dba-city-of-commerce-transit-ca",
        "90045": "regional-transportation-commission-of-southern-nevada-nv",
        "90062": "monterey-salinas-transit-ca",
        "90078": "central-contra-costa-transit-authority-dba-county-connection-ca",
        "90079": "sunline-transit-agency-dba-sunline-ca",
        "90086": "city-of-riverside-dba-riverside-connect-ca",
        "90087": "city-of-santa-maria-dba-santa-maria-regional-transit-ca",
        "90088": "napa-valley-transportation-authority-ca",
        "90089": "county-of-sonoma-dba-sonoma-county-transit-ca",
        "90090": "yolo-county-transportation-district-ca",
        "90091": "city-of-visalia-dba-visalia-transit-ca",
        "90092": "city-of-fairfield-california-dba-fast-transit-ca",
        "90094": "metropolitan-transportation-commission-dba-mtc-ca",
        "90095": "san-diego-association-of-governments-dba-sandag-ca",
        "90121": "antelope-valley-transit-authority-ca",
        "90131": "city-of-scottsdale-dba-scottsdale-trolley-az",
        "90134": "peninsula-corridor-joint-powers-board-dba-caltrain-ca",
        "90136": "regional-public-transportation-authority-dba-valley-metro-az",
        "90140": "city-of-peoria-az",
        "90142": "university-of-california-davis-dba-unitrans-ca",
        "90144": "livermore-amador-valley-transit-authority-ca",
        "90146": "foothill-transit-ca",
        "90147": "city-of-los-angeles-ca",
        "90148": "victor-valley-transit-authority-ca",
        "90151": "southern-california-regional-rail-authority-dba-metrolink-ca",
        "90154": "los-angeles-county-metropolitan-transportation-authority-dba-metro-ca",
        "90156": "city-of-san-luis-obispo-dba-slo-transit-ca",
        "90157": "access-services-ca",
        "90159": "western-contra-costa-transit-authority-dba-westcat-ca",
        "90162": "the-eastern-contra-costa-transit-authority-dba-tri-delta-transit-ca",
        "90164": "ventura-county-transportation-commission-ca",
        "90171": "city-of-santa-clarita-dba-santa-clarita-transit-ca",
        "90173": "transit-joint-powers-authority-for-merced-county-dba-merced-the-bus-ca",
        "90182": "altamont-corridor-express-ca",
        "90196": "county-of-placer-dba-placer-county-transit-tart-ca",
        "90200": "kings-county-area-public-transit-agency-ca",
        "90201": "city-of-turlock-dba-turlock-transit-ca",
        "90206": "san-luis-obispo-regional-transit-authority-ca",
        "90208": "butte-county-association-of-governments-dba-butte-regional-transit-b-line-ca",
        "90209": "valley-metro-rail-inc-az",
        "90211": "anaheim-transportation-network-dba-anaheim-regional-transportation-ca",
        "90213": "city-of-petaluma-dba-petaluma-transit-ca",
        "90214": "city-of-redondo-beach-dba-beach-cities-transit-ca",
        "90218": "riverside-county-transportation-commission-ca",
        "90219": "northern-arizona-intergovernmental-public-transportation-authority-dba-mountain-line-az",
        "90222": "pima-association-of-governments-az",
        "90223": "paratransit-inc-ca",
        "90225": "san-francisco-bay-area-water-emergency-transportation-authority-dba-san-francisco-bay-ferry-ca",
        "90226": "imperial-county-transportation-commission-ca",
        "90230": "california-vanpool-authority-dba-calvans-ca",
        "90232": "solano-county-transit-dba-soltrans-ca",
        "90233": "yuma-county-intergovernmental-public-transportation-authority-dba-yuma-county-area-transit-az",
        "90234": "marin-county-transit-district-dba-marin-transit-ca",
        "90241": "county-of-maui-hi",
        "90299": "sonoma-marin-area-rail-transit-district-ca",
        "90302": "san-bernardino-county-transportation-authority-ca",
        "90303": "santa-barbara-county-association-of-governments-dba-clean-air-express-ca",
        "90306": "stanislaus-regional-transit-authority-ca",
        "90310": "tulare-county-regional-transit-agency-ca",
        "90311": "stanislaus-council-of-governments-dba-staniscruise-ca",
        "90313": "city-of-clovis-dba-clovis-transit-ca",
        "91092": "tahoe-transportation-district-nv",
        "91122": "regional-transportation-authority-of-pima-county-az",
        "99422": "san-joaquin-council-dba-dibs-ca",
        "99423": "city-of-glendale-dba-beeline-bus-dial-a-ride-ca",
        "99424": "city-of-pasadena-dba-pasadena-transit-ca",
        "99425": "pomona-valley-transportation-authority-ca",
        "99479": "city-of-lathrop-ca",
    }
)
