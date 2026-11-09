"""Register lookup on a 16-row hand-made fixture. No network."""
from pathlib import Path

from sponsor_scout.register import load_register, lookup, normalise

IDX = load_register(Path(__file__).parent / "fixtures" / "register_sample.csv")


def test_normalise_drops_company_forms_punctuation_and_ampersands():
    assert normalise("  Smith & Jones (Leeds) LIMITED ") == "smith and jones leeds"
    assert normalise("The Brightco Partnership LLP") == "brightco partnership"


def test_exact_match_ignores_case_and_company_form_and_merges_routes():
    r = lookup("revolut limited", IDX)
    assert r["match"] == "exact" and r["organisations"][0]["name"] == "Revolut Ltd"
    assert r["organisations"][0]["skilled_worker"] is True
    assert r["organisations"][0]["towns"] == ["London"]


def test_licence_without_skilled_worker_route_is_reported_as_such():
    assert lookup("Creative Co", IDX)["organisations"][0]["skilled_worker"] is False


def test_close_match_is_listed_as_a_possibility_not_an_exact_match():
    r = lookup("Ravenstone Analytic Ltd", IDX)
    assert r["match"] == "close" and r["organisations"][0]["name"] == "Ravenstone Analytics Limited"


def test_a_shorter_name_is_not_matched_to_a_longer_organisation():
    # "Apple" must not claim "Apple & Way Limited"; "Computershare UK" must not claim "... Investor Services"
    assert lookup("Apple", IDX)["match"] == "none"
    assert lookup("Computershare UK", IDX)["match"] == "none"


def test_missing_or_hidden_employer_gives_none():
    assert lookup(None, IDX) == {"match": "none", "organisations": []}
    assert lookup("", IDX)["match"] == "none"


def test_cli_extract_prints_the_register_lookup(tmp_path, monkeypatch, capsys):
    from sponsor_scout import cli

    advert = tmp_path / "a.txt"
    advert.write_text("Analyst at Revolut Ltd", encoding="utf-8")
    record = '{"title": "Analyst", "employer": "Revolut", "location": null, "salary_min": null, "salary_max": null, ' \
             '"work_pattern": null, "skills": [], "years_experience_min": null, "closing_date": null, "sponsorship": "not_stated"}'
    monkeypatch.setattr(cli, "build_generator", lambda arm, cfg, adapter: lambda messages: (record, 1.0))
    code = cli.main(["extract", "--file", str(advert), "--arm", "zero_shot", "--register",
                     str(Path(__file__).parent / "fixtures" / "register_sample.csv")])
    out = capsys.readouterr().out
    assert code == 0 and '"match": "exact"' in out and "Revolut Ltd" in out
