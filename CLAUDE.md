# Real Estate Investment Analyzer

## Účel
Scraping realitných portálov + STR revenue analýza pre investičné rozhodnutia na trhu Costa del Sol.

## MCP nástroje
- `apify` → Idealista scraper, Sreality scraper (Apify Actors)
- AirROI API → priame REST volania (nie MCP), endpoint: `/api/v1/calculator`

## Workflow
1. **Scraping** – Apify Actor → JSON listings (Idealista / Sreality)
2. **STR data** – AirROI Calculator API (`/api/v1/calculator`)
3. **ROI výpočet** – `gross_yield = (annual_revenue / purchase_price) * 100`
4. **Export** – Google Sheets alebo JSON

## Investičné kritériá (Costa del Sol)
| Parameter | Hodnota |
|---|---|
| Max kúpna cena | 320 000 € |
| Min plocha | 70 m² + terasa |
| Min čistý yield | 5 % |
| VFT licencia | required |
| Prízemie | zakázané |

## API Keys
Všetky kľúče sa načítavajú **výhradne z env premenných** – nikdy ich nevkladaj priamo do kódu.

```
APIFY_TOKEN=...
AIRROI_API_KEY=...
```

## Konvencie
- Výstupy vždy obsahujú: `address`, `price_eur`, `size_m2`, `annual_revenue_eur`, `gross_yield_pct`
- Filtruj nehnuteľnosti pred exportom – exportuj len tie, ktoré spĺňajú všetky kritériá
- Chyby API loguj s kontextom (actor ID, URL, status kód), nemlčky preskočiť
