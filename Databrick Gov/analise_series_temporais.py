"""
Análise Exploratória de Séries Temporais — Licitações do Exército Brasileiro
Executar ANTES de escolher qualquer modelo de previsão.

Dependências:
    pip install pandas numpy matplotlib statsmodels scipy databricks-sql-connector prophet
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import STL
from statsmodels.stats.diagnostic import acorr_ljungbox
import warnings
warnings.filterwarnings("ignore")

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#F9FAFB",
    "axes.grid": True,
    "grid.color": "#E4E4E7",
    "grid.linewidth": 0.6,
    "font.family": "sans-serif",
})

# ── 1. CARREGAR DADOS ─────────────────────────────────────────────────────────
# Escolha UMA das opções abaixo:

# OPÇÃO A — CSV exportado do Databricks / Power BI
# Exportar com: SELECT DATE_TRUNC('month', `mes/ano`) AS mes, SUM(valor) AS valor_total ...
# df_raw = pd.read_csv("licitacoes_mensal.csv", parse_dates=["mes"])

# OPÇÃO B — Databricks SQL Connector (requer token pessoal)
import os
from dotenv import load_dotenv
from databricks import sql

load_dotenv()  # carrega variáveis do arquivo .env

DATABRICKS_HOST  = os.environ["DATABRICKS_HOST"]
DATABRICKS_PATH  = os.environ["DATABRICKS_PATH"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]

conn = sql.connect(
    server_hostname=DATABRICKS_HOST,
    http_path=DATABRICKS_PATH,
    access_token=DATABRICKS_TOKEN,
)

QUERY = """
SELECT
    to_date(`mes/ano`, 'MM/yyyy')         AS mes,
    SUM(CAST(REPLACE(REPLACE(valor, '.', ''), ',', '.') AS DOUBLE)) AS valor_total,
    COUNT(DISTINCT id)                    AS qtd_licitacoes,
    COUNT(DISTINCT cpfCnpjVencedor)       AS qtd_fornecedores
FROM workspace.default.licitacoes_2019_2024
GROUP BY 1
ORDER BY 1
"""

with conn.cursor() as cur:
    cur.execute(QUERY)
    df_raw = pd.DataFrame(cur.fetchall(), columns=["mes", "valor_total", "qtd_licitacoes", "qtd_fornecedores"])

conn.close()

# ── 2. PREPARAR SÉRIE TEMPORAL ────────────────────────────────────────────────
df_raw["mes"] = pd.to_datetime(df_raw["mes"])
df = df_raw.set_index("mes").sort_index()
ts = df["valor_total"].astype(float)

# Garantir frequência mensal sem lacunas
ts = ts.asfreq("MS")
n_missing = ts.isna().sum()
if n_missing > 0:
    print(f"⚠ {n_missing} meses sem dados — interpolando linearmente")
    ts = ts.interpolate(method="linear")

print(f"Período     : {ts.index.min().strftime('%b/%Y')} → {ts.index.max().strftime('%b/%Y')}")
print(f"Observações : {len(ts)}")
print(f"Média mensal: R$ {ts.mean():,.0f}")
print(f"Desvio pad. : R$ {ts.std():,.0f}")
print(f"CV          : {ts.std() / ts.mean():.1%}  (coef. de variação)")


# ── 3. VISUALIZAÇÃO INICIAL ───────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(15, 11))
fig.suptitle("Análise Exploratória — Valor Mensal Licitado", fontsize=14, fontweight="bold", y=0.98)

# 3a. Série completa
axes[0].plot(ts.index, ts / 1e6, color="#3B82F6", linewidth=1.5)
axes[0].fill_between(ts.index, ts / 1e6, alpha=0.08, color="#3B82F6")
axes[0].set_title("Série Temporal Completa")
axes[0].set_ylabel("R$ Milhões")
axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45, ha="right")

# 3b. Média por mês do ano (sazonalidade intra-anual)
monthly_means = ts.groupby(ts.index.month).mean() / 1e6
meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
cores = ["#EF4444" if v == monthly_means.max() else "#3B82F6" for v in monthly_means.values]
bars = axes[1].bar(meses, monthly_means.values, color=cores, edgecolor="white", linewidth=0.5)
axes[1].axhline(monthly_means.mean(), color="#F59E0B", linestyle="--", linewidth=1.2, label=f"Média geral: R$ {monthly_means.mean():.1f}M")
axes[1].set_title("Média por Mês (padrão sazonal intra-anual)")
axes[1].set_ylabel("R$ Milhões")
axes[1].legend(fontsize=9)

# Rótulo no pico
pico_idx = monthly_means.values.argmax()
axes[1].annotate(f"Pico: {meses[pico_idx]}\nR$ {monthly_means.values[pico_idx]:.1f}M",
                 xy=(pico_idx, monthly_means.values[pico_idx]),
                 xytext=(pico_idx + 0.5, monthly_means.values[pico_idx] * 1.05),
                 fontsize=8, color="#EF4444",
                 arrowprops=dict(arrowstyle="->", color="#EF4444", lw=0.8))

# 3c. Boxplot por ano
ts_df = ts.rename("valor").to_frame()
ts_df["ano"] = ts_df.index.year
anos = sorted(ts_df["ano"].unique())
data_by_year = [ts_df[ts_df["ano"] == a]["valor"].values / 1e6 for a in anos]
bp = axes[2].boxplot(data_by_year, labels=anos, patch_artist=True,
                     medianprops=dict(color="#F59E0B", linewidth=2))
for patch in bp["boxes"]:
    patch.set_facecolor("#DBEAFE")
    patch.set_edgecolor("#3B82F6")
axes[2].set_title("Distribuição por Ano (variabilidade e outliers)")
axes[2].set_ylabel("R$ Milhões")
axes[2].set_xlabel("")

plt.tight_layout()
plt.savefig("01_exploracao.png", dpi=150, bbox_inches="tight")
plt.show()
print("→ 01_exploracao.png salvo")


# ── 4. DECOMPOSIÇÃO STL ───────────────────────────────────────────────────────
stl = STL(ts, period=12, robust=True)
stl_fit = stl.fit()

fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)
fig.suptitle("Decomposição STL — período = 12 meses", fontsize=14, fontweight="bold")

stl_fit.observed.plot(ax=axes[0], color="#3B82F6")
axes[0].set_title("Original"); axes[0].set_ylabel("R$")

stl_fit.trend.plot(ax=axes[1], color="#F59E0B", linewidth=2)
axes[1].set_title("Tendência"); axes[1].set_ylabel("R$")

stl_fit.seasonal.plot(ax=axes[2], color="#10B981")
axes[2].set_title("Componente Sazonal"); axes[2].set_ylabel("R$")

stl_fit.resid.plot(ax=axes[3], color="#EF4444", style="o", markersize=3, linewidth=0)
axes[3].axhline(0, color="black", linewidth=0.8, linestyle="--")
axes[3].set_title("Resíduos"); axes[3].set_ylabel("R$")

plt.tight_layout()
plt.savefig("02_decomposicao_stl.png", dpi=150, bbox_inches="tight")
plt.show()
print("→ 02_decomposicao_stl.png salvo")

# Força da sazonalidade e tendência (Hyndman & Athanasopoulos, 2021)
Fs = max(0, 1 - np.var(stl_fit.resid) / np.var(stl_fit.seasonal + stl_fit.resid))
Ft = max(0, 1 - np.var(stl_fit.resid) / np.var(stl_fit.trend   + stl_fit.resid))

print(f"\n── STL ──────────────────────────────────────────────────────")
print(f"Força da Sazonalidade Fs = {Fs:.3f}  {'★ FORTE (>0.64)' if Fs > 0.64 else '(fraca)'}")
print(f"Força da Tendência    Ft = {Ft:.3f}  {'★ FORTE (>0.64)' if Ft > 0.64 else '(fraca)'}")


# ── 5. ESTACIONARIDADE — ADF + KPSS ──────────────────────────────────────────
print(f"\n── ADF  (H₀: série NÃO estacionária) ───────────────────────────────────")
adf = adfuller(ts, autolag="AIC")
print(f"Estatística : {adf[0]:.4f}")
print(f"p-valor     : {adf[1]:.4f}  →  {'✓ ESTACIONÁRIA' if adf[1] < 0.05 else '✗ NÃO ESTACIONÁRIA'}")
print(f"Valores crít: 1%={adf[4]['1%']:.3f}  5%={adf[4]['5%']:.3f}  10%={adf[4]['10%']:.3f}")

print(f"\n── KPSS (H₀: série É estacionária) ─────────────────────────────────────")
kpss_stat, kpss_p, kpss_lags, kpss_crit = kpss(ts, regression="ct", nlags="auto")
print(f"Estatística : {kpss_stat:.4f}")
print(f"p-valor     : {kpss_p:.4f}  →  {'✗ NÃO ESTACIONÁRIA' if kpss_p < 0.05 else '✓ ESTACIONÁRIA'}")

# Determinar d
if adf[1] >= 0.05:
    ts_d1 = ts.diff().dropna()
    adf_d1 = adfuller(ts_d1, autolag="AIC")
    print(f"\n── ADF após 1ª diferenciação ────────────────────────────────────────────")
    print(f"p-valor: {adf_d1[1]:.4f}  →  {'✓ estacionária com d=1' if adf_d1[1] < 0.05 else 'considerar d=2'}")
    d = 1
else:
    d = 0

print(f"\n→ Ordem de integração: d = {d}")


# ── 6. ACF / PACF ─────────────────────────────────────────────────────────────
ts_acf = ts.diff().dropna() if d == 1 else ts

# PACF aceita no máximo 50% da amostra - 1
max_lags_pacf = len(ts_acf) // 2 - 1
max_lags_acf  = min(36, len(ts_acf) // 2 - 1)

fig, axes = plt.subplots(2, 1, figsize=(15, 8))
fig.suptitle(f"ACF e PACF {'(após 1ª diferenciação)' if d == 1 else '(série original)'}  [max lags={max_lags_acf}]", fontsize=14, fontweight="bold")

plot_acf(ts_acf, lags=max_lags_acf, ax=axes[0], color="#3B82F6", vlines_kwargs={"colors": "#3B82F6"})
axes[0].set_title("ACF — lags além das bandas indicam q (MA) e Q (SMA)")
if max_lags_acf >= 12:
    axes[0].axvline(12, color="#F59E0B", linestyle=":", linewidth=1.2, label="lag 12 (1 ano)")
if max_lags_acf >= 24:
    axes[0].axvline(24, color="#F59E0B", linestyle=":", linewidth=1.2, label="lag 24 (2 anos)")
axes[0].legend(fontsize=8)

plot_pacf(ts_acf, lags=max_lags_pacf, ax=axes[1], color="#10B981",
          vlines_kwargs={"colors": "#10B981"}, method="ywm")
axes[1].set_title("PACF — lags significativos indicam p (AR) e P (SAR)")
if max_lags_pacf >= 12:
    axes[1].axvline(12, color="#F59E0B", linestyle=":", linewidth=1.2)
if max_lags_pacf >= 24:
    axes[1].axvline(24, color="#F59E0B", linestyle=":", linewidth=1.2)

plt.tight_layout()
plt.savefig("03_acf_pacf.png", dpi=150, bbox_inches="tight")
plt.show()
print("→ 03_acf_pacf.png salvo")


# ── 7. TESTE DE INDEPENDÊNCIA DOS RESÍDUOS STL (Ljung-Box) ───────────────────
lb = acorr_ljungbox(stl_fit.resid.dropna(), lags=[12, 24], return_df=True)
print(f"\n── Ljung-Box nos resíduos STL ───────────────────────────────────────────")
print(lb.to_string())
print("(p > 0.05 = resíduos independentes = STL capturou bem a estrutura)")


# ── 8. DIAGNÓSTICO FINAL ──────────────────────────────────────────────────────
sazonal_forte = Fs > 0.4
tendencia_forte = Ft > 0.64

print(f"""
{'='*65}
DIAGNÓSTICO DA SÉRIE TEMPORAL
{'='*65}
Período analisado : {ts.index.min().strftime('%b/%Y')} → {ts.index.max().strftime('%b/%Y')}
Observações       : {len(ts)} meses
Estacionaridade   : {'Sim' if d == 0 else f'Não — requer d={d} diferenciação(ões)'}
Sazonalidade (Fs) : {Fs:.3f}  →  {'FORTE — componente sazonal dominante' if Fs > 0.64 else 'MODERADA' if Fs > 0.4 else 'FRACA'}
Tendência    (Ft) : {Ft:.3f}  →  {'FORTE' if Ft > 0.64 else 'MODERADA' if Ft > 0.4 else 'FRACA'}

MODELOS RECOMENDADOS (validar com train/test split — últimos 12 meses):
""")

if sazonal_forte:
    print("  1. SARIMA(p,d,q)(P,D,Q)₁₂  ← principal candidato")
    print("     → escolher p,q via PACF/ACF; testar P=1,Q=1,D=1")
    print("  2. ETS Holt-Winters multiplicativo (auto_arima ou statsmodels)")
    print("  3. Prophet com regressores de calendário fiscal")
    print("     (feriados nacionais, virada de exercício dez/jan)")
else:
    print(f"  1. ARIMA(p,{d},q)  — sem sazonalidade forte")
    print("  2. ETS simples com tendência")

print(f"""
PRÓXIMOS PASSOS:
  1. Analisar graficamente ACF/PACF para determinar p, q, P, Q
  2. Ajustar modelos e comparar: AIC, BIC, MAPE (holdout 12 meses)
  3. Verificar resíduos do modelo final: Ljung-Box + QQ-plot
  4. Implementar no Power BI:
     - Modelo simples (ETS) → DAX com Holt-Winters manual
     - Modelo complexo     → Python visual (statsmodels / Prophet)
{'='*65}
""")


# ── 9. TRATAMENTO DE OUTLIER + SÉRIE LIMPA ───────────────────────────────────
print("\n" + "="*65)
print("SÉRIE TRATADA — LIMPEZA ANTES DA MODELAGEM")
print("="*65)

ts_clean = ts.copy()

# Substituir Jul/2019 pela mediana de julho dos demais anos
jul_outros = ts_clean[(ts_clean.index.month == 7) & (ts_clean.index.year != 2019)]
jul_mediana = jul_outros.median()
outlier_valor = ts_clean["2019-07-01"]
ts_clean["2019-07-01"] = jul_mediana
print(f"Outlier jul/2019: R$ {outlier_valor/1e6:.1f}M → substituído por mediana R$ {jul_mediana/1e6:.1f}M")

# Excluir 2024 (dados incompletos que enviesam tendência)
ts_train_full = ts_clean[ts_clean.index.year < 2024]
print(f"Série para modelagem: {ts_train_full.index.min().strftime('%b/%Y')} → {ts_train_full.index.max().strftime('%b/%Y')}  ({len(ts_train_full)} obs)")

# STL na série limpa
stl_clean = STL(ts_train_full, period=12, robust=True).fit()
Fs_c = max(0, 1 - np.var(stl_clean.resid) / np.var(stl_clean.seasonal + stl_clean.resid))
Ft_c = max(0, 1 - np.var(stl_clean.resid) / np.var(stl_clean.trend   + stl_clean.resid))
print(f"Fs (sazonalidade) = {Fs_c:.3f}  {'★ FORTE' if Fs_c > 0.64 else 'moderada' if Fs_c > 0.4 else 'fraca'}")
print(f"Ft (tendência)    = {Ft_c:.3f}  {'★ FORTE' if Ft_c > 0.64 else 'moderada' if Ft_c > 0.4 else 'fraca'}")

# ADF na série limpa
adf_c = adfuller(ts_train_full, autolag="AIC")
print(f"ADF p-valor       = {adf_c[1]:.4f}  {'✓ estacionária' if adf_c[1] < 0.05 else '✗ não estacionária (tendência presente)'}")

# Plot comparativo: série bruta vs. limpa
fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=False)
fig.suptitle("Série Bruta vs. Série Tratada (sem outlier, sem 2024)", fontsize=13, fontweight="bold")

axes[0].plot(ts.index, ts / 1e6, color="#EF4444", linewidth=1.2, label="Bruta")
axes[0].set_title("Bruta (com outlier jul/2019 e 2024 parcial)")
axes[0].set_ylabel("R$ Milhões"); axes[0].legend()
axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45, ha="right")

axes[1].plot(ts_train_full.index, ts_train_full / 1e6, color="#3B82F6", linewidth=1.5, label="Tratada")
axes[1].set_title("Tratada — usada para modelagem")
axes[1].set_ylabel("R$ Milhões"); axes[1].legend()
axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45, ha="right")

plt.tight_layout()
plt.savefig("04_serie_tratada.png", dpi=150, bbox_inches="tight")
plt.show()
print("→ 04_serie_tratada.png salvo")


# ── 10. PROPHET — TREINO / TESTE / FORECAST ──────────────────────────────────
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error

print("\n" + "="*65)
print("PROPHET — VALIDAÇÃO E FORECAST")
print("="*65)

# Split: treinar em 2019-2022, testar em 2023
CUTOFF = "2022-12-01"
df_prophet = ts_train_full.reset_index().rename(columns={"mes": "ds", "valor_total": "y"})

df_treino = df_prophet[df_prophet["ds"] <= CUTOFF].copy()
df_teste  = df_prophet[df_prophet["ds"] >  CUTOFF].copy()

print(f"Treino : {df_treino['ds'].min().strftime('%b/%Y')} → {df_treino['ds'].max().strftime('%b/%Y')}  ({len(df_treino)} obs)")
print(f"Teste  : {df_teste['ds'].min().strftime('%b/%Y')}  → {df_teste['ds'].max().strftime('%b/%Y')}  ({len(df_teste)} obs)")

# Ajustar modelo
model = Prophet(
    seasonality_mode="multiplicative",   # sazonalidade proporcional ao nível
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    changepoint_prior_scale=0.1,         # rigidez na tendência (evita overfit com poucos dados)
    seasonality_prior_scale=10,
    interval_width=0.90,                 # intervalo de confiança 90%
)
model.add_country_holidays(country_name="BR")
model.fit(df_treino)

# Previsão no período de teste
future_test = model.make_future_dataframe(periods=len(df_teste), freq="MS")
forecast_test = model.predict(future_test)
pred_teste = forecast_test[forecast_test["ds"] > CUTOFF][["ds", "yhat", "yhat_lower", "yhat_upper"]]

# Métricas de validação
y_real = df_teste["y"].values
y_pred = pred_teste["yhat"].values[:len(y_real)]

mape = mean_absolute_percentage_error(y_real, y_pred) * 100
mae  = np.mean(np.abs(y_real - y_pred))
rmse = np.sqrt(np.mean((y_real - y_pred) ** 2))

print(f"\nMétricas no período de teste (2023):")
print(f"  MAPE : {mape:.1f}%   (erro percentual médio absoluto)")
print(f"  MAE  : R$ {mae/1e6:.1f}M  (erro absoluto médio)")
print(f"  RMSE : R$ {rmse/1e6:.1f}M  (raiz do erro quadrático médio)")

if mape < 20:
    print(f"  → Acurácia BOA para dados de licitações (MAPE < 20%)")
elif mape < 35:
    print(f"  → Acurácia RAZOÁVEL — útil para direção de tendência")
else:
    print(f"  → Acurácia LIMITADA — usar como indicativo qualitativo")

# Plot validação
fig, ax = plt.subplots(figsize=(15, 6))
fig.suptitle("Prophet — Validação: Real vs. Previsto (2023)", fontsize=13, fontweight="bold")

ax.plot(df_treino["ds"], df_treino["y"] / 1e6, color="#94A3B8", linewidth=1.2, label="Treino (histórico)")
ax.plot(df_teste["ds"],  df_teste["y"]  / 1e6, color="#3B82F6", linewidth=2, marker="o", markersize=5, label="Real 2023")
ax.plot(pred_teste["ds"], pred_teste["yhat"] / 1e6, color="#F59E0B", linewidth=2, linestyle="--", label=f"Previsto (MAPE={mape:.1f}%)")
ax.fill_between(pred_teste["ds"],
                pred_teste["yhat_lower"] / 1e6,
                pred_teste["yhat_upper"] / 1e6,
                alpha=0.15, color="#F59E0B", label="IC 90%")

ax.set_ylabel("R$ Milhões")
ax.legend(fontsize=9)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

plt.tight_layout()
plt.savefig("05_validacao_prophet.png", dpi=150, bbox_inches="tight")
plt.show()
print("→ 05_validacao_prophet.png salvo")


# ── 11. FORECAST 12 MESES À FRENTE ───────────────────────────────────────────
print("\n" + "="*65)
print("FORECAST — 12 MESES")
print("="*65)

# Re-treinar com todos os dados (2019-2023 tratados)
model_final = Prophet(
    seasonality_mode="multiplicative",
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    changepoint_prior_scale=0.1,
    seasonality_prior_scale=10,
    interval_width=0.90,
)
model_final.add_country_holidays(country_name="BR")
model_final.fit(df_prophet)

future = model_final.make_future_dataframe(periods=12, freq="MS")
forecast = model_final.predict(future)

forecast_futuro = forecast[forecast["ds"] > ts_train_full.index.max()][["ds", "yhat", "yhat_lower", "yhat_upper"]]
print("\nPrevisão mensal (próximos 12 meses):")
print(f"{'Mês':<12} {'Previsto':>14} {'IC Inferior':>14} {'IC Superior':>14}")
print("-" * 56)
for _, row in forecast_futuro.iterrows():
    print(f"{row['ds'].strftime('%b/%Y'):<12} R$ {row['yhat']/1e6:>8.1f}M  R$ {row['yhat_lower']/1e6:>7.1f}M  R$ {row['yhat_upper']/1e6:>7.1f}M")

# Plot forecast final
fig, ax = plt.subplots(figsize=(15, 6))
fig.suptitle("Forecast 12 Meses — Prophet (IC 90%)", fontsize=13, fontweight="bold")

hist = forecast[forecast["ds"] <= ts_train_full.index.max()]
fut  = forecast[forecast["ds"] >  ts_train_full.index.max()]

ax.plot(ts_train_full.index, ts_train_full / 1e6, color="#3B82F6", linewidth=1.5, label="Histórico tratado")
ax.plot(hist["ds"], hist["yhat"] / 1e6, color="#94A3B8", linewidth=1, linestyle="--", alpha=0.6, label="Ajuste in-sample")
ax.plot(fut["ds"],  fut["yhat"]  / 1e6, color="#F59E0B", linewidth=2.5, marker="o", markersize=5, label="Forecast")
ax.fill_between(fut["ds"], fut["yhat_lower"] / 1e6, fut["yhat_upper"] / 1e6,
                alpha=0.2, color="#F59E0B", label="IC 90%")

ax.axvline(ts_train_full.index.max(), color="#EF4444", linestyle=":", linewidth=1.5, label="Início do forecast")
ax.set_ylabel("R$ Milhões")
ax.legend(fontsize=9)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%Y"))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

plt.tight_layout()
plt.savefig("06_forecast_final.png", dpi=150, bbox_inches="tight")
plt.show()
print("→ 06_forecast_final.png salvo")

print(f"""
{'='*65}
SUMÁRIO FINAL
{'='*65}
Série bruta        : {len(ts)} observações
Série para treino  : {len(ts_train_full)} observações (sem outlier jul/2019, sem 2024)
Fs limpo           : {Fs_c:.3f}  |  Ft limpo: {Ft_c:.3f}
Modelo             : Prophet (sazonalidade multiplicativa, IC 90%)
MAPE validação     : {mape:.1f}%  |  MAE: R$ {mae/1e6:.1f}M  |  RMSE: R$ {rmse/1e6:.1f}M

Previsão para os próximos 12 meses gerada em 06_forecast_final.png
{'='*65}
""")
