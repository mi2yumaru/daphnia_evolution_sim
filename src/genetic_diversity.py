"""集団内の二値ゲノムに対する遺伝的多様性の評価（STEP2）。

population = 0 のとき指標は未定義 (NaN)。population = 1 なら 0。
これらは集団の断面指標であり、遺伝子交換の適応的利益を示すものではない。
"""

from __future__ import annotations

import numpy as np

METRIC_NAMES = (
    "genetic_diversity_all",       # 120 loci
    "genetic_diversity_behavior",  # 80 loci
    "genetic_diversity_exchange",  # 40 loci
    "genotype_diversity",          # 120 loci の異なるゲノムの Simpson 多様度
    "unique_genotype_ratio",      # 異なるゲノム数 / 集団サイズ（個体数依存）
)


def calculate_genetic_diversity(organisms: list) -> dict[str, float]:
    """全生存個体から遺伝的多様性を算出する（ステップ末・新生児追加後）。

    各 locus の 1 の割合を p_i とし、H = mean(2 p_i (1-p_i))。
    個体は二値（半数体相当）のため、この H は集団の遺伝子座多様度。
    一個体のヘテロ接合性ではない。

    120bit をゲノムとして扱い、Organism の6形質×20bitの順序を確認。
    ゲノム型の多様度は 1-Σ(freq(genotype)^2) で算出する。
    """
    if not organisms:
        return {metric: float("nan") for metric in METRIC_NAMES}

    first = organisms[0]
    trait_labels = list(type(first).TRAIT_LABELS)
    loci_per_trait = int(type(first).LOCI_PER_TRAIT)
    expected_labels = [
        "exploration_tendency", "site_fidelity", "risk_tolerance",
        "reproduction_timing", "gene_exchange_probability", "gene_exchange_fraction",
    ]
    if trait_labels != expected_labels:
        raise ValueError("形質の順序が変わっています。遺伝的多様性の集計範囲を再確認してください。")

    genomes = np.stack([org.genome for org in organisms], axis=0)
    if genomes.shape[1] != len(trait_labels) * loci_per_trait:
        raise ValueError("ゲノム長が形質定義と一致しません")
    if np.any((genomes != 0) & (genomes != 1)):
        raise ValueError("遺伝的多様性の指標は0/1ゲノムを前提とします")

    allele_freqs = genomes.mean(axis=0)
    diversity_by_locus = 2.0 * allele_freqs * (1.0 - allele_freqs)
    split = 4 * loci_per_trait

    # 120 bitをpackして重複ゲノムの頻度を数える（計算負荷を抑える）
    packed = np.packbits(genomes.astype(np.uint8, copy=False), axis=1)
    _, counts = np.unique(packed, axis=0, return_counts=True)
    genotype_freqs = counts / genomes.shape[0]

    return {
        "genetic_diversity_all": float(diversity_by_locus.mean()),
        "genetic_diversity_behavior": float(diversity_by_locus[:split].mean()),
        "genetic_diversity_exchange": float(diversity_by_locus[split:].mean()),
        "genotype_diversity": float(1.0 - np.sum(genotype_freqs ** 2)),
        "unique_genotype_ratio": float(len(counts) / genomes.shape[0]),
    }
