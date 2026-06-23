"""Testes de sanidade — rodam offline, garantem que o build não regrida."""
from pathlib import Path
import pytest
import yaml
from pipeline.sources import ibge, snis
from pipeline import transform, model

ROOT = Path(__file__).resolve().parents[1]
COEF = yaml.safe_load((ROOT / "config/coefficients.yml").read_text())
REGIONS = yaml.safe_load((ROOT / "config/regions.yml").read_text())


def test_rms_tem_27_municipios():
    assert len(REGIONS["rms"]["municipios"]) == 27


def test_build_offline_gera_dados():
    import os
    os.chdir(ROOT)
    df = transform.build_region(REGIONS["rms"]["municipios"], ibge.load(ROOT), snis.load(ROOT), COEF)
    assert df.height == 27
    # Sorocaba tem dado real
    soro = df.filter(df["key"] == "sorocaba").to_dicts()[0]
    assert soro["flag"] == "real"
    assert soro["rsu_t_ano"] == 228000
    assert soro["organico_t_ano"] == pytest.approx(228000 * 0.48, rel=1e-3)  # gravimetria local 0.48, per D-12
    # Baseline real da RMS: SNIS-RS 2022 raspado da Série Histórica oficial
    # cobre os 25 municípios restantes; com Sorocaba+Porto Feliz, os 27 têm dado.
    real = df.filter(df["flag"] == "real")
    assert real.height >= 25
    # Invariante sagrado (D-11): município pendente nunca inventa número.
    pend = df.filter(df["flag"] == "pendente")
    assert pend["rsu_t_ano"].null_count() == pend.height


def test_modelo_break_even_coerente():
    d = model.defaults(COEF)
    r = model.project(d["clientes"], d["kg_dia"], d["partilha_pct"], d["gate_fee"], COEF, 116280)
    assert r["desviado_t_ano"] > 0
    assert 0 < r["pct_organico_municipal"] < 5   # Fase 1 é foothold, não bala de prata
    assert r["catadores_sustentados"] > 0
