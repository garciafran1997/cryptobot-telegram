# CryptoBot — Alertas Telegram para BTC/USDT (100% gratis, sin servidor)

Bot que **no ejecuta órdenes** — solo te avisa por Telegram cuándo comprar
y cuándo vender, según una estrategia de cruce de medias móviles (SMA 20/50)
+ RSI, con stop-loss y take-profit.

Corre completamente gratis usando **GitHub Actions**: no necesitas pagar
servidor, ni dejar tu computadora prendida, ni instalar nada en tu celular.
GitHub revisa el mercado automáticamente cada 15 minutos y te avisa por
Telegram si hay señal.

## Archivos

- `backtest.py` — corre la estrategia contra ~1 año de datos históricos y
  muestra retorno total, drawdown máximo, % de operaciones ganadoras, etc.
  (úsalo localmente para validar la estrategia antes de activar las alertas).
- `alert_bot.py` — revisa el mercado una vez y te manda un mensaje de
  Telegram si detecta señal de COMPRA o VENTA. Guarda su estado en
  `alert_state.json` para recordar si ya tiene una posición "abierta".
- `.github/workflows/crypto-alert.yml` — el "reloj" gratuito que ejecuta
  `alert_bot.py` cada 15 minutos automáticamente.
- `requirements.txt` — dependencias Python.

## Paso 1: Configurar Telegram (ya lo hiciste)

Ya tienes tu `TELEGRAM_BOT_TOKEN` (de @BotFather) y tu `TELEGRAM_CHAT_ID`
(`542120952`).

## Paso 2: Subir el proyecto a GitHub

1. Crea un repositorio **público** (importante: así los minutos de GitHub
   Actions son ilimitados y gratis. Si lo haces privado también es gratis
   pero con un límite mensual de minutos).
2. Sube todos los archivos de esta carpeta, incluyendo la carpeta oculta
   `.github/workflows/crypto-alert.yml` (asegúrate de que se suba esa
   subcarpeta también, no solo los .py).

## Paso 3: Guardar tus credenciales como "Secrets" (privado y seguro)

Nunca pongas el token directamente en el código. En tu repositorio de
GitHub:

1. Ve a **Settings** (del repositorio) → **Secrets and variables** →
   **Actions**.
2. Click en **New repository secret**.
3. Crea uno llamado `TELEGRAM_BOT_TOKEN` con tu token como valor.
4. Crea otro llamado `TELEGRAM_CHAT_ID` con el valor `542120952`.

## Paso 4: Activarlo

El workflow ya está programado para correr cada 15 minutos automáticamente
en cuanto subas los archivos. Para probarlo ya mismo sin esperar:

1. Ve a la pestaña **Actions** de tu repositorio.
2. Selecciona el workflow "Crypto Alert Bot" en la lista de la izquierda.
3. Click en **Run workflow** (botón a la derecha) → **Run workflow**.
4. Espera unos segundos y revisa tu Telegram — si hay señal te llegará el
   mensaje; si no hay señal en este momento, no llega nada (es normal,
   las señales de compra/venta no ocurren a cada rato).

A partir de ahí, GitHub lo seguirá corriendo solo cada 15 minutos, 24/7,
sin que hagas nada ni gastes dinero.

## Uso local (opcional, para validar antes)

```bash
pip install -r requirements.txt

# Validar la estrategia con datos históricos
python backtest.py
```

## Personalizar parámetros

Los parámetros (par de trading, medias móviles, RSI, stop-loss, take-profit,
frecuencia) están definidos directamente en
`.github/workflows/crypto-alert.yml` bajo la sección `env:` — puedes
editarlos ahí mismo en GitHub sin tocar el código Python. La frecuencia de
revisión está en la línea `cron: "*/15 * * * *"` (cada 15 minutos; el
mínimo permitido por GitHub es cada 5 minutos).

## Limitaciones a tener en cuenta

- Los horarios de GitHub Actions son en UTC y pueden tener retrasos de
  varios minutos en horas de mucha demanda — no es instantáneo al segundo,
  pero es más que suficiente para esta estrategia.
- Si el repositorio queda 60 días sin ninguna actividad (sin commits),
  GitHub puede pausar el workflow automático; en ese caso solo necesitas
  entrar a Actions y darle "Run workflow" una vez para reactivarlo.

## Importante

Esto es una herramienta de apoyo, no una garantía de ganancias. Las señales
se basan en una estrategia técnica simple; siempre verifica el contexto del
mercado antes de operar y nunca arriesgues más de lo que estás dispuesto a
perder.
