"""Publicación de las imágenes por MQTT para pantallas e-paper.

Bitmap del tamaño de las opciones a 1 bpp por umbral (128, sin tramado), por filas,
MSB = píxel izquierdo y 1 = blanco, comprimido con zlib 9.
Retenido y QoS 1: en el broker queda solo la última imagen de cada topic.

Cada publicación repinta la pantalla, así que solo se envía lo que cambia. Cada
conexión usa un cliente nuevo con sesión limpia: tras un corte no se reenvía
nada pendiente, solo el estado actual.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from contextlib import suppress
from datetime import datetime, time
import hashlib
import logging
import ssl
import threading
from typing import Any
import zlib

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.ssl import client_context
import paho.mqtt.client as mqtt
from PIL import Image

from .const import (
    CONF_ACTIVE_FROM,
    CONF_ACTIVE_TO,
    CONF_CA_CERT,
    CONF_INTERVAL,
    CONF_TLS,
    CONF_TOPIC_TODAY,
    CONF_TOPIC_TOMORROW,
    DEFAULT_INTERVAL,
    DEFAULT_MQTT_PORT,
    DOMAIN,
)
from .image import build_table, image_size
from .planner import Planner
from .render import Table, render

_LOGGER = logging.getLogger(__name__)

CLIENT_ID = "pvpc-planner"
KEEPALIVE = 60
CONNECT_TIMEOUT = 10
ACK_TIMEOUT = 30
RECONNECT_MIN, RECONNECT_MAX = 1.0, 300.0
# Una conexión que dura menos que esto no reinicia la espera entre intentos.
STABLE_CONNECTION = 60
# CONNACK "usuario o contraseña incorrectos" y "no autorizado".
_AUTH_FAILURES = (134, 135)


class ConnectError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def payload(img: Image.Image) -> bytes:
    bits = img.convert("L").convert("1", dither=Image.Dither.NONE).tobytes()
    return zlib.compress(bits, 9)


def render_payload(table: Table) -> bytes:
    return payload(render(table))


def in_window(now: time, start: time | None, end: time | None) -> bool:
    """Franja [start, end), que puede cruzar la medianoche; sin franja, siempre."""
    if start is None or end is None or start == end:
        return True
    if start < end:
        return start <= now < end
    return now >= start or now < end


def ssl_context(options: Mapping[str, Any]) -> ssl.SSLContext | None:
    """Bloqueante. Con CA propia solo se confía en ella."""
    if not options.get(CONF_TLS, True):
        return None
    if ca := options.get(CONF_CA_CERT):
        return ssl.create_default_context(cadata=ca)
    return client_context()


def open_client(
    options: Mapping[str, Any],
    context: ssl.SSLContext | None,
    on_publish: Callable[[int], None] | None = None,
    on_disconnect: Callable[[], None] | None = None,
) -> mqtt.Client:
    """Bloqueante: conecta, espera al CONNACK y deja la red en un hilo de paho."""
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=CLIENT_ID,
        clean_session=True,
        protocol=mqtt.MQTTv311,
        reconnect_on_failure=False,
    )
    if user := options.get(CONF_USERNAME):
        client.username_pw_set(user, options.get(CONF_PASSWORD))
    if context:
        client.tls_set_context(context)
    client.connect_timeout = CONNECT_TIMEOUT

    connack: list[mqtt.ReasonCode] = []
    done = threading.Event()

    def _on_connect(*args: Any) -> None:
        connack.append(args[3])
        done.set()

    client.on_connect = _on_connect
    if on_publish:
        client.on_publish = lambda _c, _u, mid, _rc, _p: on_publish(mid)
    if on_disconnect:
        client.on_disconnect = lambda *_: on_disconnect()
    host, port = options[CONF_HOST], options.get(CONF_PORT, DEFAULT_MQTT_PORT)
    try:
        client.connect(host, port, KEEPALIVE)
    except (OSError, ValueError) as err:
        _LOGGER.debug("No se pudo conectar a %s:%s: %s", host, port, err)
        raise ConnectError("cannot_connect") from err
    client.loop_start()
    if done.wait(CONNECT_TIMEOUT) and not connack[0].is_failure:
        return client
    close_client(client)
    if connack and connack[0].value in _AUTH_FAILURES:
        raise ConnectError("invalid_auth")
    _LOGGER.debug("%s:%s rechazó la conexión: %s", host, port, connack or "timeout")
    raise ConnectError("cannot_connect")


def close_client(client: mqtt.Client) -> None:
    """Bloqueante: espera a que termine el hilo de paho."""
    client.disconnect()
    client.loop_stop()


def check_connection(options: Mapping[str, Any]) -> str | None:
    """Bloqueante. Clave del error o None si el broker acepta la conexión."""
    try:
        context = ssl_context(options)
    except (ssl.SSLError, ValueError):
        return "invalid_ca"
    try:
        close_client(open_client(options, context))
    except ConnectError as err:
        return err.reason
    return None


class Publisher:
    """Mantiene la conexión y publica hoy y mañana cuando cambian."""

    def __init__(
        self, hass: HomeAssistant, planner: Planner, options: Mapping[str, Any]
    ) -> None:
        self.hass = hass
        self._planner = planner
        self._options = options
        self._topics = {
            tomorrow: topic
            for tomorrow, key in (
                (False, CONF_TOPIC_TODAY),
                (True, CONF_TOPIC_TOMORROW),
            )
            if (topic := options.get(key))
        }
        self._size = image_size(options)
        self._interval = int(options.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        self._window = tuple(
            time.fromisoformat(v) if (v := options.get(k)) else None
            for k in (CONF_ACTIVE_FROM, CONF_ACTIVE_TO)
        )
        self._store: Store[dict[str, str]] = Store(hass, 1, f"{DOMAIN}.mqtt")
        # Topic -> sha256 de lo último publicado con éxito (sobrevive a reinicios).
        self._sent: dict[str, str] = {}
        self._tables: dict[bool, Table] = {}
        self._client: mqtt.Client | None = None
        self._acks: dict[int, asyncio.Future[bool]] = {}
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._runner: asyncio.Task | None = None
        self._checks: set[asyncio.Task] = set()
        self._unsubs: list[Callable[[], None]] = []

    @property
    def enabled(self) -> bool:
        return bool(self._options.get(CONF_HOST) and self._topics)

    @property
    def connected(self) -> bool:
        return self._client is not None

    async def async_start(self) -> None:
        if not self.enabled:
            return
        stored = await self._store.async_load() or {}
        if self._stop.is_set():
            return
        self._sent = {k: v for k, v in stored.items() if k in self._keys()}
        self._runner = self.hass.async_create_background_task(
            self._async_run(), f"{DOMAIN} mqtt"
        )
        self._unsubs += [
            async_track_time_change(self.hass, self._on_time, second=2),
            async_at_started(self.hass, self._on_started),
        ]

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._stop.set()
        for task in self._checks:
            task.cancel()
        await asyncio.gather(*self._checks, return_exceptions=True)
        if self._runner:
            await self._runner

    def _keys(self) -> set[str]:
        return {self._key(t) for t in self._topics.values()}

    def _key(self, topic: str) -> str:
        host, port = self._options[CONF_HOST], self._options.get(CONF_PORT)
        return f"{host}:{port}/{topic}"

    @callback
    def _schedule_check(self) -> None:
        task = self.hass.async_create_background_task(
            self.async_check(), f"{DOMAIN} mqtt check"
        )
        self._checks.add(task)
        task.add_done_callback(self._checks.discard)

    @callback
    def _on_started(self, _hass: HomeAssistant) -> None:
        self._schedule_check()

    @callback
    def _on_time(self, now: datetime) -> None:
        if (now.hour * 60 + now.minute) % self._interval == 0:
            self._schedule_check()

    async def _async_run(self) -> None:
        """Conecta y reconecta con espera exponencial hasta async_stop."""
        loop = self.hass.loop
        context = await self.hass.async_add_executor_job(ssl_context, self._options)
        host, port = self._options[CONF_HOST], self._options.get(CONF_PORT)
        delay, error = RECONNECT_MIN, None
        while not self._stop.is_set():
            lost = asyncio.Event()
            try:
                client = await self.hass.async_add_executor_job(
                    open_client,
                    self._options,
                    context,
                    lambda mid: loop.call_soon_threadsafe(self._acked, mid),
                    lambda lost=lost: loop.call_soon_threadsafe(lost.set),
                )
            except ConnectError as err:
                if err.reason != error:
                    _LOGGER.warning("MQTT %s:%s: %s; se reintenta", host, port, err)
                    error = err.reason
                await self._sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX)
                continue
            _LOGGER.info("Conectado a MQTT %s:%s", host, port)
            error, since = None, loop.time()
            self._client = client
            if self.hass.is_running:
                self._schedule_check()
            stop = asyncio.ensure_future(self._stop.wait())
            dropped = asyncio.ensure_future(lost.wait())
            await asyncio.wait((stop, dropped), return_when=asyncio.FIRST_COMPLETED)
            stop.cancel()
            dropped.cancel()
            self._client = None
            for fut in self._acks.values():
                if not fut.done():
                    fut.set_result(False)
            await self.hass.async_add_executor_job(close_client, client)
            if self._stop.is_set():
                break
            _LOGGER.warning("Conexión MQTT con %s:%s perdida; se reintenta", host, port)
            delay = (
                RECONNECT_MIN
                if loop.time() - since >= STABLE_CONNECTION
                else min(delay * 2, RECONNECT_MAX)
            )
            await self._sleep(delay)

    async def _sleep(self, seconds: float) -> None:
        with suppress(TimeoutError):
            await asyncio.wait_for(self._stop.wait(), seconds)

    @callback
    def _acked(self, mid: int) -> None:
        if (fut := self._acks.get(mid)) and not fut.done():
            fut.set_result(True)

    async def async_check(self) -> None:
        """Publica el estado actual de cada topic que haya cambiado."""
        async with self._lock:
            if not self.connected or not in_window(dt_util.now().time(), *self._window):
                return
            # Con el sensor caído se mantiene lo publicado en vez de "sin precios".
            state = self.hass.states.get(self._planner.price_entity)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return
            changed = False
            for tomorrow, topic in self._topics.items():
                table = build_table(self.hass, self._planner, tomorrow, self._size)
                if self._tables.get(tomorrow) == table:
                    continue
                data = await self.hass.async_add_executor_job(render_payload, table)
                digest = hashlib.sha256(data).hexdigest()
                key = self._key(topic)
                if self._sent.get(key) != digest:
                    if not await self._async_publish(topic, data):
                        break
                    self._sent[key] = digest
                    changed = True
                self._tables[tomorrow] = table
            if changed:
                await self._store.async_save(self._sent)

    async def _async_publish(self, topic: str, data: bytes) -> bool:
        if (client := self._client) is None:
            return False
        info = client.publish(topic, data, qos=1, retain=True)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            _LOGGER.warning("No se pudo publicar en %s: %s", topic, info.rc)
            return False
        fut = self._acks[info.mid] = self.hass.loop.create_future()
        try:
            async with asyncio.timeout(ACK_TIMEOUT):
                ok = await fut
        except TimeoutError:
            # Se fuerza una conexión nueva para que paho no lo reenvíe más tarde.
            _LOGGER.warning("Sin confirmación del broker para %s", topic)
            client.disconnect()
            ok = False
        finally:
            del self._acks[info.mid]
        if ok:
            _LOGGER.debug("Publicada %s (%d bytes)", topic, len(data))
        return ok
