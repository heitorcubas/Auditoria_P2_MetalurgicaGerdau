"""Gera base_imobilizado_gerdau_2025.csv (505.000 linhas) calibrada por categoria (Nota 10.a).
Uso: python gerar_base_v6.py   |   Dependências: numpy, pandas
Todos os valores são tratados em CENTAVOS (int64) para cravar os saldos sem erro de arredondamento.
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(2025)

# Categoria: (linhas, custo alvo, depreciação alvo) em centavos
CATS = [
    ('Terrenos, prédios e construções',      100_000, 1_050_000_000_000,   480_641_300_000),
    ('Máquinas, equipamentos e instalações', 285_000, 4_500_000_000_000, 3_052_963_600_000),
    ('Equipamento eletrônico de dados',       50_000,   120_000_000_000,   100_477_500_000),
    ('Imobilizado em construção',             40_000,   866_048_800_000,                 0),
    ('Outros',                                30_000,   823_030_900_000,   660_891_500_000),
]
N = sum(c[1] for c in CATS)                       # 505.000
CUSTO_F1 = 4_205_047_408                          # R$ 42.050.474,08 (200 máquinas)
CUSTO_F2 = 5_878_744_894                          # R$ 58.787.448,94 (500 TI)
DIV_F1 = 16_820_189_633                           # R$ 168.201.896,33 (divergência Fraude 1)
DIV_F2 = 2_939_372_447                            # R$ 29.393.724,47 (divergência Fraude 2)
# Calibração blindada: os itens normais de Máquinas e TI absorvem o efeito das fraudes na depreciação,
# para que a coluna Valor_Liquido_BRL (com fraudes) feche exatamente com a DFP.
ABSORVE = {1: DIV_F1, 2: DIV_F2}
ALVO_CUSTO = 7_359_079_700_000                    # R$ 73.590.797.000,00
ALVO_DEPREC = 4_314_733_462_080                   # R$ 43.147.334.620,80
ALVO_LIQ = 3_064_105_800_000                      # R$ 30.641.058.000,00 (DFP)


def distribuir(total, pesos):
    """Rateio proporcional em centavos; resíduo ajustado na PRIMEIRA linha."""
    v = np.floor(pesos / pesos.sum() * total).astype(np.int64)
    v[0] += total - v.sum()
    return v


def depreciar(custo, total, ratio_base):
    """Depreciação ~ custo * taxa aleatória, escalada iterativamente para bater o total e nunca exceder o custo."""
    if total == 0 or len(custo) == 0:
        return np.zeros(len(custo), np.int64)
    r = np.clip(rng.normal(ratio_base, 0.12, len(custo)), 0.02, 0.98)
    for _ in range(50):
        r = np.clip(r * total / (custo * r).sum(), 0.0, 1.0)
    d = np.minimum(np.floor(custo * r).astype(np.int64), custo)
    falta = total - d.sum()
    folga = custo - d
    for i in np.argsort(-folga):                   # distribui o resíduo de centavos onde há folga
        if falta <= 0:
            break
        a = min(falta, folga[i]); d[i] += a; falta -= a
    assert d.sum() == total and (d <= custo).all()
    return d


cat = np.repeat(np.arange(5), [c[1] for c in CATS])
custo = np.zeros(N, np.int64)
deprec = np.zeros(N, np.int64)

# Datas de aquisição 2010-11/2025 (viés para ativos antigos)
inicio = np.datetime64('2010-01-01')
limite = (np.datetime64('2025-11-30') - inicio).astype(int)
data = inicio + (np.clip(np.abs(rng.normal(0, .45, N)), 0, 1) * limite).astype(int).astype('timedelta64[D]')

idx = {k: np.where(cat == k)[0] for k in range(5)}

# Máquinas: 3.060 em dez/2025 (sem depreciação); 200 delas = Fraude 1
dez = rng.choice(idx[1], 3060, replace=False)
data[dez] = np.datetime64('2025-12-01') + rng.integers(0, 31, 3060).astype('timedelta64[D]')
f1 = np.sort(rng.choice(dez, 200, replace=False))
# TI: 500 linhas = Fraude 2
f2 = np.sort(rng.choice(idx[2], 500, replace=False))
# Terrenos: 25.000 linhas com depreciação zero
terrenos = rng.choice(idx[0], 25_000, replace=False)

for k, (nome, n, c_alvo, d_nota) in enumerate(CATS):
    d_alvo = d_nota + ABSORVE.get(k, 0)
    linhas = idx[k]
    fixos = {1: f1, 2: f2}.get(k, np.array([], int))
    livres = np.setdiff1d(linhas, fixos)
    c_fix = {1: CUSTO_F1, 2: CUSTO_F2}.get(k, 0)
    if len(fixos):
        custo[fixos] = distribuir(c_fix, rng.lognormal(0, .5, len(fixos)))
    custo[livres] = distribuir(c_alvo - c_fix, rng.lognormal(11, 1.2, len(livres)))

    sem_dep = {0: terrenos, 1: dez}.get(k, np.array([], int))
    d_fix = 0
    if k == 2:                                     # Fraude 2: TI 100% depreciado
        deprec[f2] = custo[f2]; d_fix = custo[f2].sum()
    dep_idx = np.setdiff1d(livres, sem_dep) if k != 3 else np.array([], int)
    if k == 1:
        dep_idx = np.setdiff1d(linhas, dez)
    deprec[dep_idx] = depreciar(custo[dep_idx], d_alvo - d_fix, (d_alvo - d_fix) / max(custo[dep_idx].sum(), 1))
    assert custo[linhas].sum() == c_alvo and deprec[linhas].sum() == d_alvo, nome

# Valor líquido contábil e sobrescrita das fraudes (após calibração)
liq_correto = custo - deprec
liquido = liq_correto.copy()
liquido[f1] = custo[f1] * 5                         # Fraude 1: 5,0x o custo
liquido[f1[0]] += DIV_F1 - (liquido[f1] - liq_correto[f1]).sum()   # crava R$ 168.201.896,33
liquido[f2] = np.round(custo[f2] * 0.5).astype(np.int64)   # Fraude 2: 50% do custo
liquido[f2[0]] += DIV_F2 - (liquido[f2] - liq_correto[f2]).sum()   # crava R$ 29.393.724,47

assert custo.sum() == ALVO_CUSTO and deprec.sum() == ALVO_DEPREC and liquido.sum() == ALVO_LIQ
assert (deprec <= custo).all()

pd.DataFrame({
    'Plaqueta': [f'ATV-{100000 + i}' for i in range(N)],
    'Categoria': np.array([c[0] for c in CATS])[cat],
    'Data_Aquisicao': pd.to_datetime(data).strftime('%Y-%m-%d'),
    'Custo_Bruto_BRL': custo / 100,
    'Depreciacao_Acumulada_BRL': deprec / 100,
    'Valor_Liquido_BRL': liquido / 100,
}).to_csv('base_imobilizado_gerdau_2025.csv', index=False, float_format='%.2f')

R = lambda c: f"R$ {c / 100:>22,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
print("=== CONFERÊNCIA POR CATEGORIA (Máq. e TI incluem a depreciação que absorve as fraudes) ===")
for k, (nome, n, *_ ) in enumerate(CATS):
    m = cat == k
    print(f"{nome:<38} n={m.sum():>7,} Custo {R(custo[m].sum())} Deprec {R(deprec[m].sum())} Líquido(C−D) {R(liq_correto[m].sum())}")
print(f"{'TOTAL':<38} n={N:>7,} Custo {R(custo.sum())} Deprec {R(deprec.sum())} Líquido {R(liq_correto.sum())}")
print(f"Terrenos com depreciação zero: {(deprec[idx[0]] == 0).sum():,}")

print("\n=== FRAUDES ===")
print(f"Fraude 1: n={len(f1)} Custo {R(custo[f1].sum())} Divergência {R((liquido - liq_correto)[f1].sum())}")
print(f"Fraude 2: n={len(f2)} Custo {R(custo[f2].sum())} Divergência {R((liquido - liq_correto)[f2].sum())}")
print(f"Divergência total: {R((liquido - liq_correto).sum())}")

e2a = np.setdiff1d(idx[2], f2)
e3 = np.setdiff1d(np.arange(N), np.concatenate([dez, idx[2]]))
print("\n=== ESTRATOS (para o PT 530) ===")
print(f"{'Estrato':<30}{'Tamanho':>10}{'Líquido Contábil (C−D)':>28}{'Líquido Registrado na Base':>30}")
for nome, ix in [('Estrato 1 (Máq. dez/2025)', dez), ('Estrato 2A (TI restante)', e2a),
                 ('Estrato 2B (Fraude TI)', f2), ('Estrato 3 (Restante)', e3)]:
    print(f"{nome:<30}{len(ix):>10,}{R(liq_correto[ix].sum()):>28}{R(liquido[ix].sum()):>30}")
print(f"{'TOTAL':<30}{N:>10,}{R(liq_correto.sum()):>28}{R(liquido.sum()):>30}")

print("\n=== MACROSALDOS DA BASE ===")
print(f"Soma Custo_Bruto_BRL:            {R(custo.sum())}")
print(f"Soma Depreciacao_Acumulada_BRL:  {R(deprec.sum())}")
print(f"Soma Valor_Liquido_BRL:          {R(liquido.sum())}")
print("\n=== PROVA REAL ===")
print(f"Soma(Custo) - Soma(Depreciação) = {R(custo.sum() - deprec.sum())}  (recálculo do auditor)")
print(f"Soma(Valor_Liquido_BRL)         = {R(liquido.sum())}  (valor registrado = DFP)")
print(f"Diferença                       = {R(liquido.sum() - (custo.sum() - deprec.sum()))}  (fraude)")
