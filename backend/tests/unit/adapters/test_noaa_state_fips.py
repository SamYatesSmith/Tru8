"""NOAA CDO US-state location resolution.

Storm/hurricane claims name a US state (e.g. "Hurricane Ida struck Louisiana").
Before this fix only ~6 states were in _COUNTRY_FIPS, so "Louisiana" resolved to
no locationid and NOAA got a locationless query that 500s (chronic storm 0-yield).
These tests are network-free: they assert the state→FIPS map only.
"""

import pytest

from app.services.api_adapters.climate import NOAAAdapter


@pytest.fixture
def noaa():
    return NOAAAdapter()


@pytest.mark.parametrize(
    "state,fips",
    [
        ("Louisiana", "FIPS:22"),
        ("Texas", "FIPS:48"),
        ("Florida", "FIPS:12"),
        ("California", "FIPS:06"),
        ("New York", "FIPS:36"),
        ("Mississippi", "FIPS:28"),
        ("North Carolina", "FIPS:37"),
        ("Washington", "FIPS:53"),
    ],
)
def test_us_state_resolves_to_fips(noaa, state, fips):
    ents = [{"text": state, "label": "LOCATION"}]
    assert noaa._extract_location_id(ents) == fips


def test_all_50_states_present(noaa):
    # 50 states + DC-style entries; assert no US state is missing (the bug class).
    missing = [
        s
        for s in [
            "ALABAMA",
            "ALASKA",
            "ARIZONA",
            "ARKANSAS",
            "CALIFORNIA",
            "COLORADO",
            "CONNECTICUT",
            "DELAWARE",
            "FLORIDA",
            "GEORGIA",
            "HAWAII",
            "IDAHO",
            "ILLINOIS",
            "INDIANA",
            "IOWA",
            "KANSAS",
            "KENTUCKY",
            "LOUISIANA",
            "MAINE",
            "MARYLAND",
            "MASSACHUSETTS",
            "MICHIGAN",
            "MINNESOTA",
            "MISSISSIPPI",
            "MISSOURI",
            "MONTANA",
            "NEBRASKA",
            "NEVADA",
            "NEW HAMPSHIRE",
            "NEW JERSEY",
            "NEW MEXICO",
            "NEW YORK",
            "NORTH CAROLINA",
            "NORTH DAKOTA",
            "OHIO",
            "OKLAHOMA",
            "OREGON",
            "PENNSYLVANIA",
            "RHODE ISLAND",
            "SOUTH CAROLINA",
            "SOUTH DAKOTA",
            "TENNESSEE",
            "TEXAS",
            "UTAH",
            "VERMONT",
            "VIRGINIA",
            "WASHINGTON",
            "WEST VIRGINIA",
            "WISCONSIN",
            "WYOMING",
        ]
        if s not in noaa._COUNTRY_FIPS
    ]
    assert not missing, f"US states missing from _COUNTRY_FIPS: {missing}"
