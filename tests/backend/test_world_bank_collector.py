from app.collectors.world_bank import (
    _current_account_stress,
    _imports_share_stress,
    _latest_country_score,
)


def test_current_account_stress_penalizes_deficits_more_than_surpluses() -> None:
    assert _current_account_stress(-4.0) > _current_account_stress(4.0)
    assert _current_account_stress(6.0) < 20.0


def test_imports_share_stress_rises_with_open_import_exposure() -> None:
    assert _imports_share_stress(35.0) > _imports_share_stress(15.0)


def test_latest_country_score_combines_current_account_and_import_share() -> None:
    score = _latest_country_score(
        current_account=[(2023, 2.5), (2024, -1.0)],
        imports_share=[(2023, 22.0), (2024, 30.0)],
    )
    assert score is not None
    latest_score, latest_year = score
    assert latest_year == 2024
    assert latest_score > 40.0
