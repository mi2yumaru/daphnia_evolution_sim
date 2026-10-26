"""STEP3の系譜関係評価を小規模な人工記録で検証。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_gene_flow import (
    analyze_gene_flow, save_gene_flow_seed, aggregate_gene_flow_experiment,
)


def rec(org, parent, founder, step, event=False, donor=None, donor_founder=None, selected=0, changed=0):
    return {
        "organism_id": org, "parent_id": parent, "founder_id": founder,
        "birth_step": step, "gene_exchange_occurred": event,
        "gene_exchange_donor_id": donor,
        "gene_exchange_donor_founder_id": donor_founder,
        "gene_exchange_selected_loci_count": selected,
        "gene_exchange_changed_bit_count": changed,
    }


def case_data():
    # Founder 1&2. Parent is always primary inherited lineage; donor can cross Founder.
    return pd.DataFrame([
        rec(1, None, 1, 0), rec(2, None, 2, 0),
        rec(3, 1, 1, 1),
        rec(4, 1, 1, 2, True, 2, 2, 3, 2),    # donor2 -> founder1, effective
        rec(5, 4, 1, 3, True, 3, 1, 2, 0),    # same-founder, no change
        rec(6, 2, 2, 4, True, 4, 1, 3, 1),    # donor4 -> founder2, effective
        rec(7, 4, 1, 5, True, 2, 2, 0, 0),    # cross-founder selected 0 (no change)
    ])


def test_summary_donor_and_founder_edges():
    out = analyze_gene_flow(case_data(), last_logged_step=5, window_steps=2)
    s = out["summary"].iloc[0]
    assert s.total_births == 5
    assert s.exchange_events == 4
    assert s.effective_exchanges == 2
    assert s.cross_founder_events == 3
    assert s.cross_founder_effective_exchanges == 2
    assert s.selected_loci_total == 8
    assert s.changed_bits_total == 3
    assert s.distinct_donors == 3
    assert s.donor_founder_edges == 3
    assert s.cross_founder_share_of_effective == 1.0
    edges = out["edges"].set_index(["donor_founder_id", "recipient_founder_id"])
    assert edges.loc[(2, 1), "exchange_events"] == 2
    assert edges.loc[(2, 1), "effective_exchanges"] == 1
    assert edges.loc[(1, 2), "effective_exchanges"] == 1
    assert edges.loc[(1, 1), "effective_exchanges"] == 0


def test_direct_born_versus_donor_event_not_conflated():
    out = analyze_gene_flow(case_data(), last_logged_step=5, window_steps=2)
    donors = out["donors"].set_index("donor_id")
    # donor2 has one directly born child (6) but was a gene donor twice (4,7).
    assert donors.loc[2, "direct_offspring_count"] == 1
    assert donors.loc[2, "donor_event_count"] == 2
    assert donors.loc[2, "donor_effective_count"] == 1
    assert donors.loc[4, "direct_offspring_count"] == 2
    assert donors.loc[4, "donor_event_count"] == 1
    assert donors.loc[4, "donor_cross_founder_effective_count"] == 1
    founders = out["founders"].set_index("founder_id")
    assert founders.loc[1, "lineage_births"] == 4
    assert founders.loc[2, "lineage_births"] == 1
    assert founders.loc[1, "provided_cross_founder_effective"] == 1
    assert founders.loc[2, "provided_cross_founder_effective"] == 1
    assert founders.loc[1, "received_cross_founder_effective"] == 1


def test_window_coverage_and_zero_denominators():
    out = analyze_gene_flow(case_data(), last_logged_step=7, window_steps=2)
    w = out["windows"]
    assert list(w.window_start) == [0, 2, 4, 6]
    assert list(w.births) == [1, 2, 2, 0]
    assert list(w.exchange_events) == [0, 2, 2, 0]
    assert np.isnan(w.iloc[0].cross_founder_share_of_effective)
    assert np.isnan(w.iloc[3].effective_per_birth)
    assert int(w.effective_exchanges.sum()) == 2
    assert int(w.cross_founder_effective_exchanges.sum()) == 2


def test_no_exchange_has_empty_edges_donors_and_nan_share():
    d = case_data().iloc[:3].copy()
    out = analyze_gene_flow(d, last_logged_step=3)
    assert out["donors"].empty
    assert list(out["donors"].columns)[0] == "donor_id"
    assert out["edges"].empty
    assert out["summary"].iloc[0]["total_births"] == 1
    assert np.isnan(out["summary"].iloc[0]["cross_founder_share_of_effective"])


def test_invalid_donor_link_is_rejected():
    d = case_data()
    d.loc[d.organism_id == 4, "gene_exchange_donor_founder_id"] = 999
    with pytest.raises(ValueError, match="提供個体ID"):
        analyze_gene_flow(d, last_logged_step=5)


def test_invalid_bitcounts_rejected():
    d = case_data()
    d.loc[d.organism_id == 6, "gene_exchange_changed_bit_count"] = 10
    with pytest.raises(ValueError, match="変化bit数"):
        analyze_gene_flow(d, last_logged_step=5)


def test_csv_and_aggregate_across_seeds(tmp_path):
    exp = tmp_path / "experiment"
    for seed in (0, 1):
        save_gene_flow_seed(case_data(), exp / f"seed_{seed}", 5, window_steps=2, save_plots=False)
    agg = aggregate_gene_flow_experiment(exp, [0, 1], save_plots=True)
    assert len(agg["by_seed"]) == 2
    assert agg["windows"].iloc[1].effective_exchanges_mean == 1.0
    assert agg["windows"].iloc[1].effective_exchanges_std == 0.0
    assert len(agg["across_seeds"]) >= 10
    assert (exp / "gene_flow_rates_mean_std.png").is_file()
    assert (exp / "gene_flow_cross_share_mean_std.png").is_file()


def test_window_too_short_rejected():
    with pytest.raises(ValueError, match="window_steps"):
        analyze_gene_flow(case_data(), last_logged_step=5, window_steps=0)


def test_source_ignores_lineage_phenotypes_and_mortality():
    d = case_data()
    d["death_step"] = np.nan
    d["birth_energy"] = 999
    assert analyze_gene_flow(d, 5)["summary"].iloc[0]["exchange_events"] == 4
