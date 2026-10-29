# Pik-drishti AI: research notes

Problem statement 1 for the Seva Innovation Challenge 2026:
**Agriculture → Farmer income protection, market access and digital crop-loss assessment.**

Working name: **Pik-drishti AI** ("pik" = crop in Marathi; same family as Van-drishti AI).

## The problem, with sources

| Fact | Source |
|---|---|
| Jun–Sep 2025 rain and floods damaged crops on 60–68 lakh ha in Maharashtra (figures differ by date and source: 60, 65, 68.8 lakh ha) | [Scroll, 7 Oct 2025](https://scroll.in/latest/1087420/maharashtra-announces-rs-31628-crore-package-for-farmers-hit-by-heavy-rains-floods); [The Week, 7 Oct 2025](https://www.theweek.in/news/india/2025/10/07/maharashtra-cm-devendra-fadnavis-unveils-rs-31-628-crore-flood-relief-package-for-maharashtra-farmers.amp.html); [Free Press Journal](https://www.freepressjournal.in/amp/mumbai/maharashtra-floods-cm-devendra-fadnavis-announces-31628-crore-relief-package-for-rain-hit-farmers-heres-what-he-said) |
| ₹31,628 crore relief package, ₹17,675 crore of it for crops; 29 of 36 districts and 253 of 358 talukas affected | same as above |
| First tranche: ₹3,258 crore for 33.65 lakh farmers in 23 districts (Oct 2025) | [The Hitavada, 19 Oct 2025](https://www.thehitavada.com/Encyc/2025/10/19/mah-govt-approves-rs-3258-cr-aid-for-rain-affected-farmers.html) |
| Aug–Sep 2025 floods: 14.44 lakh ha across 29 districts (agriculture minister, early estimate) | [All India Radio, 5 Sep 2025](https://www.newsonair.gov.in/heavy-rains-wreck-14-36-lakh-hectares-of-crops-in-maharashtra-says-state-agriculture-minister) |
| Banana storms May–Jun 2026: drone survey ordered ~3 weeks after the damage; farmers expect 1.5–2 months before it reaches Solapur; "no farmer can afford to leave fields vacant for so long while waiting for a survey" | [Rural Voice, 27 Jun 2026](https://eng.ruralvoice.in/maharashtra-farmers-upset-over-delay-in-survey-of-banana-crop-damage-say-fields-cannot-be-left-vacant) |
| The State itself proposed satellite-based damage assessment linked to payouts ("game changer", "autopilot mode") | [PTI via Outlook India, updated Jan 2024](https://www.outlookindia.com/amp/story/national/maharashtra-government-eyes-to-make-use-of-satellites-for-crop-damage-assessment-and-payout-to-farmers-news-231398) |
| Current process: revenue officials visit farms on a written order; report goes tehsil → district → state | same PTI article |
| SDRF input subsidy needs ≥33% crop loss; ₹8,500/ha rainfed, ₹17,000/ha irrigated, ₹22,500/ha perennial (2022 norms, max 2 ha) | [Akola district disaster management page](https://akola.gov.in/disaster-management-department) (check the latest MHA order before quoting) |
| YES-TECH (2023): remote-sensing yields get 30% weight in PMFBY claims for paddy and wheat (soybean from Kharif 2024). Season-end yield, not event damage | [ICRISAT ISSCA](https://issca.icrisat.org/scalable-solutions/yield-estimation-using-technology-yes-tech); [Down To Earth](https://www.downtoearth.org.in/agriculture/beyond-the-lens) |
| PMFBY claims held up when the state premium share was unpaid (₹1,015 crore pending, Jul 2025) | [The Week, 8 Jul 2025](https://www.theweek.in/wire-updates/business/2025/07/08/bes31-mh-council-crop-insurance.html) |
| e-Pik Pahani app: farmers register crops and can photograph damage; depends on the farmer's phone and network | [Tata Trusts Horizons](https://horizons.tatatrusts.org/2022/july/tata-trusts-horizons-peek-pahani.html) |

Not used on the slides (unverified or too indirect): farmer counts per holding size, IIM claim-delay study, farmer suicide figures.

## What already exists (and what we do differently)

- **Manual panchanama**: field by field, weeks, surveyor-dependent.
- **Drone surveys** (2026 banana case): accurate, but staged district by district and costly.
- **YES-TECH / CROPIC**: season-end yield models and crop photos for insurance. Not an immediate, per-farm damage map after an event.
- **Commercial** (e.g. EOSDA flood crop insurance): paid, not built around panchanama or Indian relief norms.

**Our angle:** within days of an event, a per-farm (or per-village) damage map and list that ranks farms by damage %, flags those above the 33% relief threshold, and tells officials which farms to verify first. Officials still sign off; the satellite does the first pass.

## Methods and code to build on

- **Sentinel-1 radar flood mapping in Earth Engine** (sees through monsoon cloud):
  - UN-SPIDER recommended practice (change detection before/after): [in detail](https://un-spider.org/advisory-support/recommended-practices/recommended-practice-google-earth-engine-flood-mapping/in-detail), [step by step](https://un-spider.org/advisory-support/recommended-practices/recommended-practice-google-earth-engine-flood-mapping/step-by-step)
  - Backscatter anomaly (Z-score) method, DeVries et al. 2020, packaged as [s1flood](https://pypi.org/project/s1flood)
  - [Global Flood Mapper](https://iihs.co.in/knowledge-gateway/global-flood-mapper-a-novel-google-earth-engine-application-for-rapid-flood-mapping-using-sentinel-1-sar/) (IIHS, GEE app)
  - [MapAction flood-mapping-tool](https://github.com/mapaction/flood-mapping-tool) (Streamlit + GEE)
  - NASA ARSET [SAR for Landcover Applications](https://www.earthdata.nasa.gov/learn/trainings/sar-landcover-applications) (flood + agriculture in GEE)
- **Caution from the literature**: C-band misses flooding under dense canopy; double bounce in crops and towns can be mistaken for water; flood extent alone is a weak proxy for loss, so combine with crop stage and post-event greenness ([MDPI 2026](https://mdpi-res.com/d_attachment/remotesensing/remotesensing-18-02481/article_deploy/remotesensing-18-02481.pdf), [UAF lecture](https://radar.community.uaf.edu/wp-content/uploads/sites/667/2023/04/2023-Lectures17-SurfaceWaterMapping-handouts.pdf)).
- **Optical damage**: pre/post NDVI change with Sentinel-2 ([Pakistan 2022 floods study](https://research.uaeu.ac.ae/en/publications/assessing-agrometeorological-damage-after-the-2022-pakistan-flood/), [ACRS 2024](https://acrs-aars.org/proceeding/ACRS2024/AB0250.pdf), [FLNet 2026](https://arxiv.org/html/2601.03884v1)).
- **Foundation models**: [Prithvi-EO-2.0](https://arxiv.org/pdf/2412.02732) with a [Sen1Floods11 fine-tune](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL-Sen1Floods11) (TerraTorch). Later upgrade, not needed for the first prototype.
- **Field boundaries**: Google Agricultural Understanding has field boundaries for India, but API access needs allowlisting ([docs](https://developers.google.com/agricultural-understanding/api)). Prototype: user uploads village or farm boundaries (KML), like Van-drishti.

## Prototype plan (reuses Van-drishti)

1. **Input**: event date + village/farm boundaries (KML), or a taluka.
2. **Crop mask**: ESA WorldCover cropland plus Dynamic World crop probability (both in Earth Engine).
3. **Flood**: Sentinel-1 VV/VH after the event vs the same season in earlier years (Z-score), so normally flooded paddy is not counted.
4. **Crop damage**: Sentinel-2 NDVI after the event vs the field's own normal for that week (earlier years), plus rainfall (CHIRPS / GPM) to confirm the event.
5. **Per farm**: % area flooded, NDVI loss %, a damage class, and whether it crosses the 33% relief threshold.
6. **Output**: damage map, ranked farm list for field verification, PDF / CSV / KML for the panchanama file.
7. **Demo**: Marathwada floods, Sept 2025.

## Drought 2026 (added 28 Oct 2026)

### The situation
- 25 Sep 2026: the Relief & Rehabilitation Department declared drought (Trigger-1) in **265 of 358 talukas**.
  - Statewide rainfall was ~18% below normal (1 Jun–25 Sep).
  - District deficits: Solapur 57%, Beed 49%, Hingoli 48%, Jalna 46%, Dharashiv 45%, Akola 41%.
  - A ~45-day dry spell; at least a quarter of Marathwada's standing crops were reported damaged.
  - Collectors were told to start field assessments: panchanamas, photos, GPS-tagged records.
  - Direct crop-loss compensation was to be announced separately, after the assessment.
  - Sources: [Down To Earth, 26 Sep 2026](https://www.downtoearth.org.in/natural-disasters/maharashtra-declares-drought-in-265-talukas-as-crop-losses-mount-after-weak-monsoon), [All India Radio](https://newsonair.gov.in/maharashtra-declares-265-talukas-drought-affected/).
- 14 Oct 2026: reported expansion to **305 talukas** ([GKToday](https://www.gktoday.in/maharashtra-declares-drought-in-305-talukas/); single source, not confirmed against the GR).
- The manual says Kharif drought must be declared by **30 October**, and the memorandum for central (NDRF) help needs village-wise field verification data.

### Method (Manual for Drought Management 2016, pp. 32-45)
- **Trigger-1 (Table 3.10):** rainfall deficient (≤ -20%) plus a dry spell; or scanty (≤ -60%); or a dry spell alone. A dry spell is 3-4 consecutive weeks each under 50% of normal.
- **Impact indicators:**
  - NDVI / NDWI deviation: -20 to -30% moderate, below -30% severe (3.2.2).
  - MAI: ≤25 severe, 26-50 moderate (Table 3.5).
  - Sown area.
- **Trigger-2:** severe if all three chosen indicators are severe; moderate if two of three are moderate or severe.
- **Our adaptations (shown in the app):**
  - MAI uses MODIS PET, so it is compared with each unit's own normal years.
  - Cropped area is a satellite estimate (cropland with season-peak NDVI > 0.6).
  - "Normal years" are each unit's years with rainfall within ±19% of normal, as the manual asks.

### Validation against the official declaration
- **Statewide:** our Trigger-1 fires in **287 of 365** talukas (2001 boundaries), against 265 declared on 25 Sep and a reported 305 on 14 Oct.
- **District counts published so far:**

| District | Declared | Ours (Trigger-1) |
|---|---|---|
| Jalgaon | 15 | 15 of 15 |
| Buldhana | 13 | 13 of 13 |
| Yavatmal | 16 | 17 of 17 |
| Nanded | 14 | 16 of 16 |
| Amravati | 14 | 11 of 14 |
| Pune | 8 | 13 of 14 (7 of the 8 named talukas included) |
| Chandrapur | 12 | 4 of 15 |
| Nagpur | 14 | 0 of 14 |

- **Where we differ:** Nagpur and Chandrapur. CHIRPS shows near-normal seasonal rain there (-5 to -15%), with weekly falls mostly 50-75% of normal rather than below 50%. The state used IMD data "and other factors".
- **Tried and rejected:** a 21-consecutive-day dry-spell rule on daily CHIRPS taluka means matched worse, because averaging smooths out dry days.

### What the satellites add (the product insight)
- Rainfall alone (Trigger-1) flags ~3/4 of the state. The impact indicators show where crops are actually suffering:
  - At 8 Oct 2026, **7 talukas are moderate**, mostly in Solapur and Sangli, which matches Solapur's 57% deficit.
  - Crops elsewhere held up through the Aug-Sep dry spell, but **early browning is appearing** in places. Beed taluka: NDVI -17%, NDWI -38% on the 8 Oct composite.
- The 2018 drought (declared in 151 talukas) is clearly visible in the same indicators: NDWI 26-45% below normal, cropped area down. So the method can detect a real drought.

### Crop damage demo (Sept 2025 floods)
- **Event:** 26-27 Sep 2025 (40-63 mm/day on top of a wet September).
- **Coverage:** Sentinel-1 passes on 18 Sep (before), 30 Sep and 5 Oct (after); clear Sentinel-2 views on 7-17 Oct.
- **Madha (Solapur):** the radar shows the Sina river flood channel. Wakav village has 19.5% of its cropland flooded and is flagged "verify first".
- **Village validation not yet possible:** village-level flood reports were not found in English news.
- **Limitations:**
  - Excess rain often damages soybean pods while the canopy stays green, so NDVI under-counts that kind of loss.
  - Radar misses water under tall crops.
