"""
Skrypt do analizy i porównania plików wynikowych (JSON).

Grupuje pliki wg zbioru danych (demagog / liar), ekstrapoluje nazwę modelu
z nazwy pliku i generuje wykresy porównujące wszystkie modele w obrębie
każdego zbioru danych.

Uruchomienie (PowerShell):
  python .\\src\\research_first_step\\analyze_results.py `
         -i .\\src\\research_first_step\\results `
         -o .\\src\\research_first_step\\results_summary_manip.csv `
         --plots-dir .\\src\\research_first_step\\plots
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ---------------------------------------------------------------------------
# Stałe
# ---------------------------------------------------------------------------
MANIP_KEYS = {"manipulacja", "manipulation"}
METRICS = ("precision", "recall", "f1")
COLORS = {
    "manipulation": "#e15759",   # czerwony
    "macro":        "#4e79a7",   # niebieski
    "best_other":   "#59a14f",   # zielony
    "delta":        "#f28e2b",   # pomarańczowy
}


# ---------------------------------------------------------------------------
# Parsowanie nazwy pliku
# ---------------------------------------------------------------------------
def parse_filename(stem: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Wzorzec: results_{dataset}_{model...}_{YYYYMMDD}_{HHMMSS}
    Zwraca (dataset_type, model_name) lub (None, None) przy błędzie.
    """
    parts = stem.split("_")
    # Minimum: results + dataset + model_part + date + time = 5 parts
    if len(parts) < 5 or parts[0] != "results":
        return None, None
    # Dwie ostatnie części to timestamp
    if not (re.fullmatch(r"\d{8}", parts[-2]) and re.fullmatch(r"\d{6}", parts[-1])):
        return None, None
    dataset = parts[1]
    model = "_".join(parts[2:-2])
    return dataset, model


# ---------------------------------------------------------------------------
# Wczytywanie i parsowanie metryk z JSON
# ---------------------------------------------------------------------------
def try_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def find_per_class(metrics: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
    if not isinstance(metrics, dict):
        return None
    if "per_class" in metrics and isinstance(metrics["per_class"], dict):
        return metrics["per_class"]
    # Heurystyka: szukaj zagnieżdżonych dictów z polami precision/recall/f1
    candidates = {}
    for k, v in metrics.items():
        if isinstance(v, dict) and any(f in v for f in ("precision", "recall", "f1")):
            candidates[k] = v
    return candidates if candidates else None


def extract_macro(metrics: Dict[str, Any], per_class: Optional[Dict]) -> Dict[str, Optional[float]]:
    macro: Dict[str, Optional[float]] = {m: None for m in METRICS}

    # Warianty nazw kluczy makro
    key_map = [
        ("macro_precision", "precision"),
        ("macro_recall", "recall"),
        ("macro_f1", "f1"),
    ]
    for key, target in key_map:
        if key in metrics:
            macro[target] = try_float(metrics[key])

    for alt in ("macro", "macro avg", "macro_avg", "macro-average"):
        if alt in metrics and isinstance(metrics[alt], dict):
            for m in METRICS:
                if macro[m] is None:
                    macro[m] = try_float(metrics[alt].get(m))

    # Jeśli nadal brak — policz prostą średnią z klas
    if per_class and any(macro[m] is None for m in METRICS):
        buckets: Dict[str, List[float]] = {m: [] for m in METRICS}
        for vals in per_class.values():
            for m in METRICS:
                v = try_float(vals.get(m))
                if v is not None:
                    buckets[m].append(v)
        for m in METRICS:
            if buckets[m] and macro[m] is None:
                macro[m] = float(sum(buckets[m]) / len(buckets[m]))
    return macro


def find_manipulation_key(per_class: Dict[str, Any]) -> Optional[str]:
    for k in per_class:
        if k.lower().strip() in MANIP_KEYS:
            return k
    for k in per_class:
        if "manip" in k.lower():
            return k
    return None


def extract_metrics_from_file(path: Path, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """Wczytuje plik JSON i zwraca słownik z wyekstrahowanymi metrykami."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        if verbose:
            print(f"[ERR] Nie udało się wczytać {path.name}: {e}")
        return None

    dataset, model = parse_filename(path.stem)
    if dataset is None:
        if verbose:
            print(f"[WARN] Nie rozpoznano wzorca nazwy: {path.name}")
        return None

    # Wyodrębnij sekcję metrics
    raw_metrics = None
    if isinstance(data, dict) and "metrics" in data:
        raw_metrics = data["metrics"]
    elif isinstance(data, dict):
        raw_metrics = data

    if not raw_metrics:
        if verbose:
            print(f"[WARN] Brak metrics w: {path.name}")
        return None

    per_class = find_per_class(raw_metrics)
    macro = extract_macro(raw_metrics, per_class)
    total_support = (
        raw_metrics.get("total_samples")
        or raw_metrics.get("total")
        or raw_metrics.get("classified")
    )

    if not per_class:
        if verbose:
            print(f"[WARN] Brak per_class w: {path.name}")
        return {
            "filename": path.name,
            "dataset": dataset,
            "model": model,
            "per_class": {},
            "macro": macro,
            "total_support": total_support,
            "manip_key": None,
        }

    manip_key = find_manipulation_key(per_class)

    # Oblicz total_support jeśli brak
    if total_support is None:
        s = sum(
            int(v.get("support", 0))
            for v in per_class.values()
            if isinstance(v, dict) and v.get("support") is not None
        )
        total_support = s if s > 0 else None

    return {
        "filename": path.name,
        "dataset": dataset,
        "model": model,
        "per_class": per_class,
        "macro": macro,
        "total_support": total_support,
        "manip_key": manip_key,
    }


# ---------------------------------------------------------------------------
# Budowanie DataFrame z wynikami
# ---------------------------------------------------------------------------
def build_rows(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    per_class = entry["per_class"]
    macro = entry["macro"]
    manip_key = entry["manip_key"]

    for metric in METRICS:
        manip_val = None
        if manip_key and manip_key in per_class:
            manip_val = try_float(per_class[manip_key].get(metric))
        macro_val = macro.get(metric)

        delta = None
        rel = None
        if manip_val is not None and macro_val is not None:
            delta = manip_val - macro_val
            rel = (100.0 * delta / macro_val) if macro_val != 0 else None

        # Najlepsza inna klasa
        others = [
            (c, try_float(v.get(metric)))
            for c, v in per_class.items()
            if c != manip_key and isinstance(v, dict)
        ]
        others = [(c, v) for c, v in others if v is not None]
        others_sorted = sorted(others, key=lambda x: x[1], reverse=True)
        best_other_class = others_sorted[0][0] if others_sorted else None
        best_other_value = others_sorted[0][1] if others_sorted else None

        # Ranga manipulacji (1 = najlepsza)
        all_vals = [
            (c, try_float(v.get(metric)))
            for c, v in per_class.items()
            if isinstance(v, dict)
        ]
        all_vals_filtered = [(c, v) for c, v in all_vals if v is not None]
        all_vals_sorted = sorted(all_vals_filtered, key=lambda x: x[1], reverse=True)
        rank = None
        if manip_val is not None:
            rank = 1 + sum(1 for _, v in all_vals_sorted if v is not None and v > manip_val)

        # Per-class values dla wszystkich klas (do CSV szczegółowego)
        all_class_vals = {
            c: try_float(v.get(metric))
            for c, v in per_class.items()
            if isinstance(v, dict)
        }

        manip_support = None
        if manip_key and manip_key in per_class:
            try:
                manip_support = int(per_class[manip_key].get("support", 0))
            except Exception:
                pass

        rows.append({
            "filename": entry["filename"],
            "dataset": entry["dataset"],
            "model": entry["model"],
            "metric": metric,
            "manipulation_value": manip_val,
            "macro_value": macro_val,
            "delta": delta,
            "relative_delta%": rel,
            "best_other_class": best_other_class,
            "best_other_value": best_other_value,
            "rank_of_manipulation": rank,
            "support_of_manipulation": manip_support,
            "support_total": entry["total_support"],
            "all_class_values": all_class_vals,
        })
    return rows


# ---------------------------------------------------------------------------
# Generowanie wykresów
# ---------------------------------------------------------------------------
def short_model_name(model: str) -> str:
    """Skraca nazwę modelu do rozsądnej długości na wykresie."""
    replacements = [
        ("meta-llama_", ""),
        ("openai_", ""),
        ("openrouter_", ""),
        ("moonshotai_", ""),
        ("qwen_", ""),
        ("-instruct", ""),
        ("-versatile", ""),
    ]
    name = model
    for old, new in replacements:
        name = name.replace(old, new)
    return name


def plot_dataset_comparison(
    df_group: pd.DataFrame,
    dataset: str,
    plots_dir: Path,
) -> None:
    """
    Dla danego zbioru danych (demagog/liar) generuje:
    1. Wykres porównania precision/recall/f1 – manipulation vs macro (per model)
    2. Wykres delta (manipulation – macro) per model i metrykę
    3. Wykres porównania wszystkich klas (grouped bar) dla każdej metryki
    """
    models = df_group["model"].unique().tolist()
    short_names = [short_model_name(m) for m in models]
    x = np.arange(len(models))

    # ── 1. Manipulation vs Macro (3 subploty – precision, recall, f1) ────────
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
    fig.suptitle(f"Manipulacja vs Makro — zbiór: {dataset}", fontsize=14, fontweight="bold")

    for ax, metric in zip(axes, METRICS):
        sub = df_group[df_group["metric"] == metric].set_index("model")
        manip_vals = [sub.loc[m, "manipulation_value"] if m in sub.index else np.nan for m in models]
        macro_vals = [sub.loc[m, "macro_value"] if m in sub.index else np.nan for m in models]

        w = 0.35
        ax.bar(x - w / 2, manip_vals, w, label="Manipulacja", color=COLORS["manipulation"], zorder=3)
        ax.bar(x + w / 2, macro_vals, w, label="Makro avg", color=COLORS["macro"], zorder=3)
        ax.set_title(metric.capitalize(), fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(short_names, rotation=35, ha="right", fontsize=8)
        ax.set_ylim(0, 1)
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
        ax.grid(axis="y", alpha=0.4, zorder=0)
        ax.legend(fontsize=8)

    plt.tight_layout()
    out = plots_dir / f"{dataset}_manip_vs_macro.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Zapisano: {out}")

    # ── 2. Delta (manipulation – macro) ──────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.suptitle(f"Delta (Manipulacja − Makro) — zbiór: {dataset}", fontsize=14, fontweight="bold")

    bar_w = 0.25
    for i, metric in enumerate(METRICS):
        sub = df_group[df_group["metric"] == metric].set_index("model")
        deltas = [sub.loc[m, "delta"] if m in sub.index else np.nan for m in models]
        offset = (i - 1) * bar_w
        bars = ax.bar(x + offset, deltas, bar_w, label=metric.capitalize(), zorder=3)
        # Etykiety wartości
        for bar, val in zip(bars, deltas):
            if val is not None and not np.isnan(float(val)):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (0.01 if val >= 0 else -0.03),
                    f"{val:.2f}",
                    ha="center", va="bottom", fontsize=6,
                )

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(short_names, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("Delta")
    ax.legend()
    ax.grid(axis="y", alpha=0.4, zorder=0)
    plt.tight_layout()
    out = plots_dir / f"{dataset}_delta.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Zapisano: {out}")

    # ── 3. Wszystkie klasy per metryka (per model) ────────────────────────────
    for model in models:
        sub_model = df_group[df_group["model"] == model]
        if sub_model.empty:
            continue

        # Zbierz wszystkie klasy ze słownika all_class_values
        all_classes: set = set()
        for _, row in sub_model.iterrows():
            all_classes.update(row["all_class_values"].keys())
        all_classes_sorted = sorted(all_classes)

        fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
        fig.suptitle(
            f"Wszystkie klasy — {dataset} / {short_model_name(model)}",
            fontsize=12, fontweight="bold"
        )

        for ax, metric in zip(axes, METRICS):
            row = sub_model[sub_model["metric"] == metric]
            if row.empty:
                ax.set_title(metric.capitalize())
                continue
            row = row.iloc[0]
            vals = [row["all_class_values"].get(c) for c in all_classes_sorted]
            macro_val = row["macro_value"]

            colors = []
            for c in all_classes_sorted:
                if c == row.get("manip_key") or c.lower() in MANIP_KEYS or "manip" in c.lower():
                    colors.append(COLORS["manipulation"])
                else:
                    colors.append("#aecbfa")

            xc = np.arange(len(all_classes_sorted))
            ax.bar(xc, [v if v is not None else 0 for v in vals], color=colors, zorder=3)
            if macro_val is not None:
                ax.axhline(macro_val, color=COLORS["macro"], linewidth=1.5,
                           linestyle="--", label=f"Makro={macro_val:.2f}", zorder=4)
            ax.set_title(metric.capitalize(), fontsize=11)
            ax.set_xticks(xc)
            ax.set_xticklabels(all_classes_sorted, rotation=30, ha="right", fontsize=8)
            ax.set_ylim(0, 1)
            ax.grid(axis="y", alpha=0.4, zorder=0)
            ax.legend(fontsize=7)

        plt.tight_layout()
        safe_model = re.sub(r"[^\w\-]", "_", model)
        out = plots_dir / f"{dataset}_{safe_model}_all_classes.png"
        plt.savefig(out, dpi=150)
        plt.close()
        print(f"  Zapisano: {out}")

    # ── 4. Porównanie relative_delta% ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.suptitle(f"Względna różnica (Manipulacja − Makro) [%] — zbiór: {dataset}",
                 fontsize=13, fontweight="bold")
    bar_w = 0.25
    for i, metric in enumerate(METRICS):
        sub = df_group[df_group["metric"] == metric].set_index("model")
        rel_deltas = [sub.loc[m, "relative_delta%"] if m in sub.index else np.nan for m in models]
        offset = (i - 1) * bar_w
        ax.bar(x + offset, rel_deltas, bar_w, label=metric.capitalize(), zorder=3)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(short_names, rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("Względna delta [%]")
    ax.legend()
    ax.grid(axis="y", alpha=0.4, zorder=0)
    plt.tight_layout()
    out = plots_dir / f"{dataset}_relative_delta.png"
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  Zapisano: {out}")


def plot_cross_dataset(df: pd.DataFrame, plots_dir: Path) -> None:
    """
    Porównuje modele wspólne dla obu zbiorów (demagog i liar).
    """
    datasets = df["dataset"].unique().tolist()
    if len(datasets) < 2:
        return

    # Modele wspólne
    common_models = set(df[df["dataset"] == "demagog"]["model"]) & set(df[df["dataset"] == "liar"]["model"])
    if not common_models:
        return

    common_sorted = sorted(common_models)
    short_names = [short_model_name(m) for m in common_sorted]
    x = np.arange(len(common_sorted))

    for metric in METRICS:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.set_title(
            f"Manipulacja {metric.capitalize()} — demagog vs liar (modele wspólne)",
            fontsize=12, fontweight="bold"
        )
        w = 0.35
        for j, ds in enumerate(["demagog", "liar"]):
            sub = df[(df["dataset"] == ds) & (df["metric"] == metric)].set_index("model")
            vals = [sub.loc[m, "manipulation_value"] if m in sub.index else np.nan for m in common_sorted]
            offset = (j - 0.5) * w
            ax.bar(x + offset, vals, w, label=ds, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(short_names, rotation=35, ha="right", fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_ylabel(metric)
        ax.legend()
        ax.grid(axis="y", alpha=0.4, zorder=0)
        plt.tight_layout()
        out = plots_dir / f"cross_dataset_manip_{metric}.png"
        plt.savefig(out, dpi=150)
        plt.close()
        print(f"  Zapisano: {out}")


# ---------------------------------------------------------------------------
# Główna funkcja
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Analiza metryk Manipulacja w wynikach JSON")
    parser.add_argument("-i", "--input-dir", required=True)
    parser.add_argument("-o", "--output-csv", required=True)
    parser.add_argument("--plots-dir", default=None, help="Katalog docelowy wykresów (domyślnie: input-dir/plots)")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    plots_dir = Path(args.plots_dir) if args.plots_dir else input_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Zbierz pliki
    pattern = "**/*.json" if args.recursive else "*.json"
    files = sorted([p for p in input_dir.glob(pattern) if "backup" not in p.parts and p.is_file()])
    print(f"Znaleziono {len(files)} plików JSON w {input_dir}")

    # Wczytaj i sparsuj
    all_rows: List[Dict] = []
    for p in files:
        entry = extract_metrics_from_file(p, verbose=args.verbose)
        if entry is None:
            continue
        rows = build_rows(entry)
        # Dodaj manip_key do każdego wiersza (potrzebne w plot_dataset_comparison)
        for r in rows:
            r["manip_key"] = entry["manip_key"]
        all_rows.extend(rows)

    if not all_rows:
        print("Brak danych do analizy.")
        return

    df_full = pd.DataFrame(all_rows)

    # ── Zapis CSV (bez kolumny all_class_values) ──────────────────────────────
    csv_cols = [
        "filename", "dataset", "model", "metric",
        "manipulation_value", "macro_value", "delta", "relative_delta%",
        "best_other_class", "best_other_value",
        "rank_of_manipulation", "support_of_manipulation", "support_total",
    ]
    df_full[csv_cols].to_csv(args.output_csv, index=False, float_format="%.6f")
    print(f"Zapisano CSV: {args.output_csv}")

    # ── Wykresy per dataset ───────────────────────────────────────────────────
    for dataset in df_full["dataset"].unique():
        df_grp = df_full[df_full["dataset"] == dataset].copy()
        print(f"\nGeneruję wykresy dla zbioru: {dataset} ({df_grp['model'].nunique()} modeli)")
        plot_dataset_comparison(df_grp, dataset, plots_dir)

    # ── Wykresy porównawcze demagog vs liar ───────────────────────────────────
    print("\nGeneruję wykresy porównawcze demagog vs liar...")
    plot_cross_dataset(df_full, plots_dir)

    print(f"\nGotowe! Wykresy zapisane w: {plots_dir}")


if __name__ == "__main__":
    main()

