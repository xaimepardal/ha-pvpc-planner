# PVPC Planner

Panel para Home Assistant que muestra los precios PVPC por horas (hoy y, cuando se publican, mañana) y permite marcar en qué horas encender cada dispositivo.

- Verde: las 6 horas más baratas del día. Rojo: las 6 más caras.
- Pulsa una hora y elige los dispositivos (`switch`, `light`, `fan`, `input_boolean`, `humidifier`) que deben estar encendidos.
- La programación es por fecha y no se repite.
- Al empezar una hora marcada se encienden. Al empezar una hora en la que ya no están marcados, se apagan. No se tocan dispositivos que el panel no haya encendido.

## Requisitos

- Home Assistant 2024.7 o superior.
- Integración oficial **Spain electricity hourly pricing (PVPC)** (`pvpc_hourly_pricing`) configurada.

## Instalación

1. HACS → Repositorios personalizados → URL de este repo, tipo *Integración*.
2. Instala **PVPC Planner** y reinicia Home Assistant.
3. Ajustes → Dispositivos y servicios → Añadir integración → *PVPC Planner* y elige el sensor PVPC.
4. Aparecerá **PVPC** en la barra lateral.

## Desarrollo

```bash
pip install pytest-homeassistant-custom-component
pytest
```
