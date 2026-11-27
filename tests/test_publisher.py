"""Publicación MQTT: formato, solo cambios, reconexión, TLS y opciones."""

import asyncio
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
import ipaddress
import ssl
from unittest.mock import patch
import zlib

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from PIL import Image
import pytest

from custom_components.pvpc_planner import config_flow, publisher as pub
from custom_components.pvpc_planner.const import (
    CONF_ACTIVE_FROM,
    CONF_ACTIVE_TO,
    CONF_CA_CERT,
    CONF_HEIGHT,
    CONF_INTERVAL,
    CONF_TLS,
    CONF_TOPIC_TODAY,
    CONF_TOPIC_TOMORROW,
    CONF_WIDTH,
    DOMAIN,
)
from custom_components.pvpc_planner.render import Cell, Table, render

from .common import TERMO, async_setup_integration
from .mqtt_broker import Broker

TODAY, TOMORROW = "pvpc_planner/image/today", "pvpc_planner/image/tomorrow"


def _prices(base: float = 0.1, tomorrow: bool = True) -> dict:
    attrs = {f"price_{h:02d}h": base + h / 100 for h in range(24)}
    if tomorrow:
        attrs |= {f"price_next_day_{h:02d}h": 0.3 - h / 100 for h in range(24)}
    return attrs


def _options(broker: Broker, **extra) -> dict:
    return {
        CONF_HOST: "127.0.0.1",
        CONF_PORT: broker.port,
        CONF_TLS: False,
        CONF_TOPIC_TODAY: TODAY,
        CONF_TOPIC_TOMORROW: TOMORROW,
        CONF_INTERVAL: 60,
    } | extra


async def _until(cond: Callable[[], bool]) -> None:
    """Espera a lo que hacen los hilos de paho, que no avisan al loop."""
    async with asyncio.timeout(5):
        while not cond():  # noqa: ASYNC110
            await asyncio.sleep(0.01)


def _publisher(hass) -> pub.Publisher:
    return hass.data[f"{DOMAIN}_publisher"]


@pytest.fixture(autouse=True)
def fast_reconnect(socket_enabled):
    with patch.object(pub, "RECONNECT_MIN", 0.05):
        yield


@pytest.fixture
async def broker():
    broker = Broker()
    await broker.start()
    yield broker
    await broker.stop()


async def _setup(hass, broker: Broker, hass_storage=None, **extra):
    hass.states.async_set("sensor.pvpc", "0.2", _prices())
    entry = await async_setup_integration(
        hass, hass_storage, options=_options(broker, **extra)
    )
    await _until(lambda: len(broker.messages) == 2)
    return entry


# Copia del script legacy (pvpc_epaper.py): contrato del firmware.
def _legacy_1bit(img: Image.Image) -> Image.Image:
    return img.point(lambda p: 255 if p >= 128 else 0).convert("1", dither=Image.NONE)


def _legacy_payload(img: Image.Image) -> bytes:
    crudo = img.convert("1").tobytes()
    assert len(crudo) == 800 * 480 // 8, len(crudo)
    return zlib.compress(crudo, 9)


@pytest.mark.parametrize("cells", [0, 24])
def test_payload_matches_legacy(cells: int) -> None:
    table = Table(
        day=date(2026, 11, 25),
        today=True,
        lang="es",
        cells=tuple(
            Cell(h, 0.1 + h / 100, None, h < 10, h == 10, False, ())
            for h in range(cells)
        ),
        width=800,
        height=480,
    )
    img = render(table)
    data = pub.payload(img)
    assert data == _legacy_payload(_legacy_1bit(img.convert("L")))
    assert len(zlib.decompress(data)) == 48000


@pytest.mark.parametrize(
    ("now", "start", "end", "inside"),
    [
        (time(3), None, None, True),
        (time(3), time(7), time(7), True),
        (time(7), time(7), time(23), True),
        (time(23), time(7), time(23), False),
        (time(3), time(22), time(6), True),
        (time(12), time(22), time(6), False),
    ],
)
def test_in_window(now, start, end, inside) -> None:
    assert pub.in_window(now, start, end) is inside


async def test_disabled_by_default(hass) -> None:
    await async_setup_integration(hass)
    publisher = _publisher(hass)
    assert not publisher.enabled
    assert not publisher.connected


async def test_publishes_only_changes(hass, hass_storage, broker) -> None:
    entry = await _setup(hass, broker, hass_storage)
    assert broker.sessions == [(pub.CLIENT_ID, True)]
    assert {m.topic for m in broker.messages} == {TODAY, TOMORROW}
    assert all(m.qos == 1 and m.retain for m in broker.messages)

    publisher = _publisher(hass)
    await publisher.async_check()
    assert len(broker.messages) == 2

    # Cambia la programación de hoy: solo se publica hoy.
    await hass.data[DOMAIN].async_set_slot(
        datetime.now().date(), (datetime.now().hour + 1) % 24, [TERMO]
    )
    await publisher.async_check()
    assert [m.topic for m in broker.messages[2:]] == [TODAY]

    # Tras reiniciar no se repinta lo que ya estaba publicado.
    await hass.config_entries.async_reload(entry.entry_id)
    await _until(lambda: _publisher(hass).connected)
    await _publisher(hass).async_check()
    assert len(broker.messages) == 3
    assert hass_storage[f"{DOMAIN}.mqtt"]["data"]
    await hass.config_entries.async_unload(entry.entry_id)


async def test_reconnect_sends_only_current_state(hass, broker) -> None:
    entry = await _setup(hass, broker)
    publisher = _publisher(hass)

    await broker.stop()
    await _until(lambda: not publisher.connected)
    await asyncio.sleep(0.3)  # reintentos fallidos con el broker caído
    # Varios cambios sin conexión: no se acumulan.
    for base in (0.2, 0.3):
        hass.states.async_set("sensor.pvpc", str(base), _prices(base))
        await publisher.async_check()

    await broker.start()
    await _until(lambda: len(broker.messages) == 3)
    await asyncio.sleep(0.2)
    assert len(broker.messages) == 3
    current = await hass.async_add_executor_job(
        pub.render_payload, pub.build_table(hass, hass.data[DOMAIN], False)
    )
    assert broker.messages[-1].topic == TODAY
    assert broker.retained[TODAY] == current
    assert broker.sessions[-1] == (pub.CLIENT_ID, True)

    # Un corte con la conexión ya hecha también reconecta.
    broker.drop()
    await _until(lambda: len(broker.sessions) == 3)
    await hass.config_entries.async_unload(entry.entry_id)


async def test_unacked_publish_reconnects(hass, broker) -> None:
    broker.ack = False
    with patch.object(pub, "ACK_TIMEOUT", 0.2):
        hass.states.async_set("sensor.pvpc", "0.2", _prices())
        entry = await async_setup_integration(hass, options=_options(broker))
        await _until(lambda: len(broker.sessions) >= 2)
        broker.ack = True
        await _until(lambda: TOMORROW in broker.retained)
    await hass.config_entries.async_unload(entry.entry_id)


async def test_skips_when_sensor_down_or_out_of_window(hass, broker) -> None:
    entry = await _setup(
        hass, broker, **{CONF_ACTIVE_FROM: "00:00:00", CONF_ACTIVE_TO: "23:59:59"}
    )
    publisher = _publisher(hass)
    assert publisher._window == (time(0), time(23, 59, 59))

    hass.states.async_set("sensor.pvpc", "unavailable", {})
    await publisher.async_check()
    hass.states.async_set("sensor.pvpc", "0.5", _prices(0.5))
    with patch.object(pub, "in_window", return_value=False):
        await publisher.async_check()
    assert len(broker.messages) == 2
    await hass.config_entries.async_unload(entry.entry_id)


async def test_publish_refused_by_client(hass, broker) -> None:
    entry = await _setup(hass, broker)
    publisher = _publisher(hass)
    with patch.object(publisher._client, "publish") as publish:
        publish.return_value.rc = pub.mqtt.MQTT_ERR_NO_CONN
        assert not await publisher._async_publish(TODAY, b"x")
    publisher._client = None
    assert not await publisher._async_publish(TODAY, b"x")
    await hass.config_entries.async_unload(entry.entry_id)


async def test_interval_ticks(hass, broker) -> None:
    entry = await _setup(hass, broker, **{CONF_INTERVAL: 15})
    publisher = _publisher(hass)
    with patch.object(publisher, "async_check") as check:
        base = datetime(2026, 11, 25, 10, tzinfo=UTC)
        for minute in (0, 7, 15, 30):
            publisher._on_time(base + timedelta(minutes=minute))
        await hass.async_block_till_done()
    assert check.call_count == 3
    await hass.config_entries.async_unload(entry.entry_id)


def _cert(subject: str, issuer=None, key=None, ca: bool = False):
    own = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)])
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(issuer.subject if issuer else name)
        .public_key(own.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    builder = builder.add_extension(
        x509.SubjectKeyIdentifier.from_public_key(own.public_key()), critical=False
    )
    if issuer:
        builder = builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()),
            critical=False,
        )
    if ca:
        builder = builder.add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
    else:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
    cert = builder.sign(key or own, hashes.SHA256())
    return cert, own


def _pem(cert) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture
async def tls_broker(tmp_path):
    ca, ca_key = _cert("ca", ca=True)
    server, server_key = _cert("broker", issuer=ca, key=ca_key)
    (tmp_path / "cert.pem").write_text(_pem(server))
    (tmp_path / "key.pem").write_bytes(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(tmp_path / "cert.pem", tmp_path / "key.pem")
    broker = Broker(context=context, users={"pvpc": "secreto"})
    await broker.start()
    yield broker, _pem(ca)
    await broker.stop()


async def test_check_connection_tls(hass, tls_broker) -> None:
    broker, ca = tls_broker
    base = {
        CONF_HOST: "127.0.0.1",
        CONF_PORT: broker.port,
        CONF_TLS: True,
        CONF_CA_CERT: ca,
        CONF_USERNAME: "pvpc",
        CONF_PASSWORD: "secreto",
    }
    other_ca = _pem(_cert("otra", ca=True)[0])

    def check(**changes) -> str | None:
        return pub.check_connection(base | changes)

    assert await hass.async_add_executor_job(check) is None
    assert (
        await hass.async_add_executor_job(lambda: check(password="mal"))
        == "invalid_auth"
    )
    assert (
        await hass.async_add_executor_job(lambda: check(ca_cert="basura"))
        == "invalid_ca"
    )
    assert (
        await hass.async_add_executor_job(lambda: check(ca_cert=other_ca))
        == "cannot_connect"
    )
    # Sin CA propia se usan las del sistema, que no conocen la de prueba.
    assert (
        await hass.async_add_executor_job(lambda: check(ca_cert=None))
        == "cannot_connect"
    )


async def test_connack_timeout(hass) -> None:
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    with patch.object(pub, "CONNECT_TIMEOUT", 0.3):
        error = await hass.async_add_executor_job(
            pub.check_connection,
            {CONF_HOST: "127.0.0.1", CONF_PORT: port, CONF_TLS: False},
        )
    server.close()
    assert error == "cannot_connect"


async def test_options_flow(hass, broker) -> None:
    hass.states.async_set("sensor.pvpc", "0.2", _prices())
    entry = await async_setup_integration(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    form = {
        CONF_HOST: " 127.0.0.1 ",
        CONF_PORT: float(broker.port),
        CONF_TLS: False,
        CONF_USERNAME: "pvpc",
        CONF_PASSWORD: "secreto",
        CONF_TOPIC_TODAY: TODAY,
        CONF_INTERVAL: 30.0,
        CONF_WIDTH: 480.0,
        CONF_HEIGHT: 800.0,
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], form | {CONF_TOPIC_TOMORROW: "a/#"}
    )
    assert result["errors"] == {"base": "invalid_topic"}

    with patch.object(config_flow, "check_connection", return_value="invalid_auth"):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], form
        )
    assert result["errors"] == {"base": "invalid_auth"}
    # La contraseña no vuelve al navegador.
    keys = {str(k): k for k in result["data_schema"].schema}
    assert "suggested_value" not in (keys[CONF_PASSWORD].description or {})

    result = await hass.config_entries.options.async_configure(result["flow_id"], form)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        CONF_HOST: "127.0.0.1",
        CONF_PORT: broker.port,
        CONF_TLS: False,
        CONF_USERNAME: "pvpc",
        CONF_PASSWORD: "secreto",
        CONF_TOPIC_TODAY: TODAY,
        CONF_TOPIC_TOMORROW: "",
        CONF_INTERVAL: 30,
        CONF_WIDTH: 480,
        CONF_HEIGHT: 800,
    }
    # Cambiar opciones reinicia solo la publicación.
    await _until(lambda: [m.topic for m in broker.messages] == [TODAY])
    assert len(zlib.decompress(broker.messages[0].payload)) == 480 * 800 // 8

    # Contraseña vacía: se mantiene la guardada. Sin usuario: se borra.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    form.pop(CONF_PASSWORD)
    result = await hass.config_entries.options.async_configure(result["flow_id"], form)
    await hass.async_block_till_done()
    assert entry.options[CONF_PASSWORD] == "secreto"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    form.pop(CONF_USERNAME)
    del form[CONF_HOST]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], form | {CONF_PASSWORD: "x"}
    )
    await hass.async_block_till_done()
    assert CONF_PASSWORD not in entry.options
    assert CONF_HOST not in entry.options
    assert not _publisher(hass).enabled
    await hass.config_entries.async_unload(entry.entry_id)
