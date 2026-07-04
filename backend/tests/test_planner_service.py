from app.services.planner_service import (
    build_weekly_plan,
    get_cuisine_profiles,
    get_delivery_partners,
    get_household_profile,
)


def test_build_weekly_plan_returns_seven_days_and_summary():
    pantry = [
        {"name": "rice"},
        {"name": "carrot"},
        {"name": "tomato"},
    ]

    result = build_weekly_plan(pantry, region="asian", household_size=3, days=7)

    assert len(result["days"]) == 7
    assert result["profile"]["id"] == "asian"
    assert result["household"]["defaultServings"] == 3
    assert result["nutritionalSummary"]["dailyAverage"]["calories"] > 0
    assert result["days"][0]["servings"] == 3
    assert "rice" in result["days"][0]["usesPantryItems"]


def test_build_weekly_plan_clamps_days_and_household_size():
    result = build_weekly_plan([], region="mediterranean", household_size=99, days=99)

    assert len(result["days"]) == 14
    assert result["household"]["defaultServings"] == 12


def test_cuisine_profiles_include_requested_regions():
    profile_ids = {profile["id"] for profile in get_cuisine_profiles()}

    assert {"belgian", "mediterranean", "asian"}.issubset(profile_ids)


def test_household_profile_supports_multiple_members():
    household = get_household_profile()

    assert len(household["members"]) >= 2
    assert household["defaultServings"] >= 2


def test_delivery_partners_create_collectandgo_link():
    partners = get_delivery_partners(["rice", "pasta"])

    partner_ids = {partner["id"] for partner in partners}

    assert partner_ids == {"collectandgo"}
    assert all("cartUrl" in partner for partner in partners)
