from datetime import date

from pikdrishti import drought
from pikdrishti.drought import Season


def test_trigger_1_follows_manual_table_3_10():
    assert drought.trigger_1(-30, False, True)          # deficient + dry spell
    assert not drought.trigger_1(-30, False, False)     # deficient, no dry spell, not scanty
    assert drought.trigger_1(-65, True, False)          # scanty without dry spell
    assert drought.trigger_1(-5, False, True)           # normal rain but a dry spell
    assert not drought.trigger_1(-5, False, False)


def test_dry_spell_counts_consecutive_weeks_below_half_normal():
    assert drought.longest_dry_spell([1.2, 0.4, 0.3, 0.1, 0.9, 0.2]) == (3, 1)
    assert drought.longest_dry_spell([None, 0.6, 0.7]) == (0, None)


def test_rain_and_mai_classes():
    assert drought.rain_category(-25) == "deficient"
    assert drought.rain_category(-70) == "large deficient"
    assert drought.rain_category(5) == "normal"
    assert drought.mai_class(20) == "severe" and drought.mai_class(40) == "moderate"
    assert drought.mai_class(60) == "mild" and drought.mai_class(90) == "normal"
    assert drought.dev_class(-35) == "severe" and drought.dev_class(-25) == "moderate"
    assert drought.dev_class(-10) == "normal"


def _row(**over):
    """A unit with a 40% rain deficit, 4 dry weeks and normal-year history 2017-2025."""
    row = {"rain_cur": 360, "rain_norm": 600}
    for i, r in enumerate([1.0, 0.3, 0.2, 0.1, 0.4, 1.0], start=1):
        row[f"w{i:02d}_cur"], row[f"w{i:02d}_norm"] = r * 50, 50
    for y in drought.RECENT_YEARS:
        row.update({f"rain_{y}": 600, f"ndvi_{y}": 0.6, f"ndwi_{y}": 0.2, f"crop_{y}": 0.8,
                    f"aet_{y}": 200, f"pet_{y}": 400})
    row.update(ndvi_cur=0.6, ndwi_cur=0.2, crop_cur=0.8, aet_cur=200, pet_cur=400, vci=55)
    row.update(over)
    return row


SEASON = Season(2026, date(2026, 6, 1), date(2026, 9, 30), date(2026, 10, 8), date(2026, 10, 8))


def test_classify_normal_crops_after_trigger_1():
    r = drought.classify(_row(), SEASON, 6)
    assert r["trigger_1"] and r["dry_spell_weeks"] == 4 and r["rain_dev_pct"] == -40
    assert r["category"] == "normal"


def test_classify_severe_when_all_three_impacts_severe():
    r = drought.classify(_row(ndvi_cur=0.36, ndwi_cur=0.1, crop_cur=0.4, aet_cur=40), SEASON, 6)
    assert r["remote_sensing_class"] == r["agriculture_class"] == r["soil_moisture_class"] == "severe"
    assert r["category"] == "severe"


def test_classify_moderate_when_two_of_three():
    r = drought.classify(_row(ndvi_cur=0.46, crop_cur=0.6), SEASON, 6)
    assert r["category"] == "moderate"


def test_normal_years_skip_drought_and_flood_years():
    row = _row(rain_2018=380, rain_2020=900)
    years = drought.normal_years(row)
    assert 2018 not in years and 2020 not in years and len(years) >= 3


def test_no_trigger_means_no_category():
    row = _row(rain_cur=590)
    for i in range(1, 7):
        row[f"w{i:02d}_cur"] = 50
    assert drought.classify(row, SEASON, 6)["category"] == "no trigger"
