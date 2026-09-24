#!/usr/bin/env python3
"""iFlytek real-time speech-to-text (IST / Real-time ASR) in the terminal.

Streams microphone audio to iFlytek's international IST WebSocket API
(ist-api-sg.xf-yun.com, the Singapore endpoint) and prints the live
transcription: in-progress segments update in place, completed ones are
printed on their own line.

Setup
-----
1. Create an app on the international platform (console-global.xfyun.cn)
   and enable the "Real-time ASR (IST)" service. You need the APPID,
   APIKey and APISecret (all three are used by the WebAPI handshake).
2. Install dependencies (macOS: `brew install portaudio` first):
       pip install websocket-client pyaudio
3. Credentials: the app's keys are embedded in this file already; the
   IFLYTEK_APP_ID / IFLYTEK_API_KEY / IFLYTEK_API_SECRET environment
   variables override them, and the settings menu can change them per run.
4. Run with no arguments:
       python iflytek_realtime_asr.py
   An arrow-key settings menu opens first: move with ↑/↓, press Enter to
   change a setting or start listening, q or Esc to exit.

Protocol reference: https://global.xfyun.cn/doc (Voice Recognition →
Real-time ASR), endpoint ws[s]://ist-api-sg.xf-yun.com/v2/ist
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
import select
import shutil
import sys
import threading
import time
import wave
from types import SimpleNamespace
from urllib.parse import quote

try:
    import termios
    import tty
except ImportError:  # Windows has no POSIX terminal API
    termios = None
    tty = None

import websocket  # pip install websocket-client

try:
    import pyaudio  # pip install pyaudio
except ImportError:
    pyaudio = None  # file mode still works without it

IST_HOST = "ist-api-sg.xf-yun.com"
IST_PATH = "/v2/ist"

# Credentials from https://console-global.xfyun.cn (IST service page).
# Environment variables override these defaults.
DEFAULT_APP_ID = "gaabacfd"
DEFAULT_API_KEY = "c16bf34b9770270fc3f02a99fba090d6"
DEFAULT_API_SECRET = "2536ecf23492749c712d1c46c23d78e1"

# IST requires 16 kHz / 16-bit / mono PCM, sent as ~1280-byte JSON frames
# every 40 ms: 640 samples = 1280 bytes = 40 ms of audio.
SAMPLE_RATE = 16000
FRAME_SAMPLES = 640
FRAME_INTERVAL = 0.04

# language / accent / domain combos from the official Basic Engine table
ENGINE_PRESETS: list[tuple[str, str, str, str]] = [
    ("Chinese  zh_cn", "zh_cn", "mandarin", "ist_open"),
    ("English  en_us", "en_us", "mandarin", "ist_open"),
    ("Chinese + English  zh_en", "zh_en", "mandarin", "ist_hy"),
    ("Cantonese  zh_cn", "zh_cn", "cantonese", "ist"),
]


def build_url(app_id: str, api_key: str, api_secret: str) -> str:
    """IST handshake auth: sign host/date/request-line with hmac-sha256."""
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    signature_origin = f"host: {IST_HOST}\ndate: {date}\nGET {IST_PATH} HTTP/1.1"
    signature = base64.b64encode(
        hmac.new(api_secret.encode(), signature_origin.encode(),
                 hashlib.sha256).digest()
    ).decode()
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()
    return (f"wss://{IST_HOST}{IST_PATH}?authorization={quote(authorization)}"
            f"&date={quote(date)}&host={IST_HOST}")


def result_text(result: dict) -> str:
    """Concatenate the words of one IST result: result.ws[].cw[].w."""
    return "".join(
        cw.get("w", "")
        for ws_item in result.get("ws", [])
        for cw in ws_item.get("cw", [])
    )


class TranscriptPrinter:
    """IST tags every result with a serial number (sn). The same sn can be
    refined several times — shown as one in-place partial line — and the
    previous sn is committed to its own line as soon as a new sn appears."""

    def __init__(self) -> None:
        self._sn = None
        self._partial = ""
        self.sentences = 0

    def update(self, sn, text: str) -> None:
        if sn != self._sn:
            self.commit()
            self._sn = sn
        if text == self._partial:
            return
        self._partial = text
        sys.stdout.write(f"\r\x1b[2K\x1b[2m… {text}\x1b[0m")
        sys.stdout.flush()

    def commit(self) -> None:
        if self._partial:
            sys.stdout.write(f"\r\x1b[2K› {self._partial}\n")
            self.sentences += 1
        self._partial = ""
        sys.stdout.flush()


class ISTClient:
    def __init__(self, args: SimpleNamespace) -> None:
        self.args = args
        self.printer = TranscriptPrinter()
        self.stop_event = threading.Event()
        self.ws = None
        self.audio_thread = None

    # -- websocket callbacks -------------------------------------------------

    def on_open(self, ws) -> None:
        target = self._stream_file if self.args.file else self._stream_mic
        self.audio_thread = threading.Thread(target=target, args=(ws,), daemon=True)
        self.audio_thread.start()

    def on_message(self, _ws, message: str) -> None:
        try:
            msg = json.loads(message)
        except ValueError:
            return  # ignore non-JSON keep-alive frames
        code = msg.get("code", 0)
        if code:
            print(f"\n[server error {code}] {msg.get('message', '')}",
                  file=sys.stderr)
            return
        data = msg.get("data") or {}
        result = data.get("result")
        if result is not None:
            self.printer.update(result.get("sn"), result_text(result))
        if data.get("status") == 2:  # recognition completed for this session
            self.printer.commit()
            print("\n— recognition complete —")

    def on_error(self, _ws, error) -> None:
        if isinstance(error, KeyboardInterrupt):
            return
        text = str(error)
        print(f"\n[connection error] {text}", file=sys.stderr)
        if "Handshake status 401" in text:
            print(
                "    Handshake rejected: check App ID / API key / API secret",
                "    (settings menu, first three rows) — the signature is",
                "    computed from the API secret.",
                sep="\n", file=sys.stderr,
            )
        elif "Handshake status 403" in text:
            print(
                "    Clock skew over 5 min or IP whitelist: check system time,",
                "    and disable the IP whitelist for this app in the console.",
                sep="\n", file=sys.stderr,
            )

    def on_close(self, _ws, _code, _reason) -> None:
        self.stop_event.set()

    # -- audio sources -------------------------------------------------------

    def _frame(self, audio: bytes, status: int) -> str:
        """One IST request frame; common/business ride on the first frame."""
        frame = {"data": {
            "status": status,
            "format": "audio/L16;rate=16000",
            "encoding": "raw",
            "audio": base64.b64encode(audio).decode(),
        }}
        if status == 0:
            _, language, accent, domain = ENGINE_PRESETS[self.args.preset]
            frame["common"] = {"app_id": self.args.app_id}
            frame["business"] = {"language": language, "accent": accent,
                                 "domain": domain}
        return json.dumps(frame)

    def _stream_mic(self, ws) -> None:
        if pyaudio is None:
            print("[!] PyAudio not installed: pip install pyaudio", file=sys.stderr)
            ws.close()
            return
        pa = pyaudio.PyAudio()
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self.args.device,
                frames_per_buffer=FRAME_SAMPLES,
            )
        except OSError as exc:
            print(f"[!] could not open microphone: {exc}", file=sys.stderr)
            pa.terminate()
            ws.close()
            return

        print("— listening, speak now (Ctrl+C to stop) —")
        # Blocking reads pace the stream at real time: 640 samples ≈ 40 ms.
        first = True
        while not self.stop_event.is_set():
            data = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
            ws.send(self._frame(data, 0 if first else 1))
            first = False
        ws.send(self._frame(b"", 2))  # end-of-data marker
        stream.stop_stream()
        stream.close()
        pa.terminate()
        ws.close()

    def _stream_file(self, ws) -> None:
        with wave.open(self.args.file, "rb") as wav:
            if (
                wav.getframerate() != SAMPLE_RATE
                or wav.getnchannels() != 1
                or wav.getsampwidth() != 2
            ):
                print(
                    f"[!] {self.args.file} must be 16 kHz / 16-bit / mono WAV",
                    file=sys.stderr,
                )
                ws.close()
                return
            print("— streaming file —")
            first = True
            while not self.stop_event.is_set():
                frame = wav.readframes(FRAME_SAMPLES)
                if not frame:
                    break
                ws.send(self._frame(frame, 0 if first else 1))
                first = False
                time.sleep(FRAME_INTERVAL)
        ws.send(self._frame(b"", 2))  # end-of-data marker
        time.sleep(1.0)  # let the engine flush the audio tail
        ws.close()

    # -- lifecycle -----------------------------------------------------------

    def run(self) -> None:
        self.ws = websocket.WebSocketApp(
            build_url(self.args.app_id, self.args.api_key, self.args.api_secret),
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        try:
            self.ws.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_event.set()
            if self.audio_thread:
                self.audio_thread.join(timeout=2.0)
            self.printer.commit()
        print(f"\n— done: {self.printer.sentences} segment(s) —")


# -- arrow-key settings menu -------------------------------------------------


@contextlib.contextmanager
def cbreak_terminal():
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    tty.setcbreak(fd)  # keys arrive immediately; Ctrl+C still interrupts
    try:
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def _read_bytes(fd: int, count: int, timeout: float = 0.1) -> bytes:
    """Read up to `count` raw bytes, waiting briefly for stragglers."""
    data = b""
    while len(data) < count:
        if not select.select([sys.stdin], [], [], timeout)[0]:
            break
        chunk = os.read(fd, count - len(data))
        if not chunk:  # EOF
            break
        data += chunk
    return data


def read_key() -> str:
    """Read one keypress and map it to an action name.

    Reads raw bytes via os.read: buffered sys.stdin would swallow the rest
    of an escape sequence, which select() then can't see — arrow keys would
    look like a bare Esc.
    """
    fd = sys.stdin.fileno()
    data = os.read(fd, 1)
    if not data:
        return "quit"  # EOF (stdin closed)
    ch = data.decode(errors="replace")
    if ch == "\x03":
        raise KeyboardInterrupt
    if ch == "\x1b":
        arrows = {b"[A": "up", b"[B": "down", b"[C": "right", b"[D": "left",
                  b"OA": "up", b"OB": "down", b"OC": "right", b"OD": "left"}
        return arrows.get(_read_bytes(fd, 2), "esc")
    if ch in ("\r", "\n"):
        return "enter"
    return {"j": "down", "k": "up", "q": "quit"}.get(ch.lower(), ch)


def pick(title: str, options: list[str], selected: int = 0) -> int | None:
    """Arrow-key menu: returns the chosen index, or None when cancelled."""
    height = len(options) + 1  # lines to climb back up to the title

    def draw() -> None:
        sys.stdout.write(f"\r\x1b[2K{title}\n")
        for i, option in enumerate(options):
            cursor = "❯" if i == selected else " "
            sys.stdout.write(f"\r\x1b[2K {cursor} {option}\n")

    with cbreak_terminal():
        sys.stdout.write("\x1b[?25l")  # hide the cursor while the menu is up
        try:
            draw()
            sys.stdout.flush()
            while True:
                key = read_key()
                if key == "up":
                    selected = (selected - 1) % len(options)
                elif key == "down":
                    selected = (selected + 1) % len(options)
                elif key == "enter":
                    sys.stdout.write("\n")
                    return selected
                elif key in ("esc", "quit"):
                    sys.stdout.write("\n")
                    return None
                else:
                    continue
                sys.stdout.write(f"\x1b[{height}A")
                draw()
                sys.stdout.flush()
        finally:
            sys.stdout.write("\x1b[?25h")  # restore the cursor
            sys.stdout.flush()


def device_options() -> list[tuple[str, int | None]]:
    """(label, PyAudio index) pairs for the mic picker; None = system default."""
    options = [("System default", None)]
    if pyaudio is not None:
        width = shutil.get_terminal_size().columns - 8
        pa = pyaudio.PyAudio()
        try:
            for index in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(index)
                if info.get("maxInputChannels", 0) > 0:
                    options.append((f"[{index}] {info['name']}"[:width], index))
        finally:
            pa.terminate()
    return options


def settings_menu(settings: dict) -> bool:
    """Arrow-key settings screen; returns True when the user picks Start."""
    while True:
        devices = device_options()
        indexes = [index for _, index in devices]
        device_label = next(
            (label for label, index in devices if index == settings["device"]),
            "System default",
        )
        preset_label = ENGINE_PRESETS[settings["preset"]][0]
        source_label = (
            f"WAV file: {os.path.basename(settings['file'])}"
            if settings["file"]
            else "Microphone"
        )
        rows = [
            f"App ID        {settings['app_id'] or '(not set)'}",
            f"API key       {'••• set' if settings['api_key'] else '(not set)'}",
            f"API secret    {'••• set' if settings['api_secret'] else '(not set)'}",
            f"Language      {preset_label}",
            f"Microphone    {device_label}",
            f"Audio source  {source_label}",
            "─" * 36,
            "▶ Start listening",
            "Exit",
        ]
        choice = pick("iFlytek IST  ·  ↑/↓ move, Enter select, q quit", rows,
                      selected=7)
        if choice is None or choice == len(rows) - 1:
            return False
        if choice == 7:  # Start
            if not (settings["app_id"] and settings["api_key"]
                    and settings["api_secret"]):
                print("[!] set App ID, API key and API secret first "
                      "(https://console-global.xfyun.cn)")
                continue
            return True
        if choice == 0:
            settings["app_id"] = input("App ID: ").strip()
        elif choice == 1:
            settings["api_key"] = input("API key: ").strip()
        elif choice == 2:
            settings["api_secret"] = input("API secret: ").strip()
        elif choice == 3:
            i = pick("Language", [p[0] for p in ENGINE_PRESETS],
                     selected=settings["preset"])
            if i is not None:
                settings["preset"] = i
        elif choice == 4:
            i = pick("Microphone", [l for l, _ in devices],
                     selected=indexes.index(settings["device"])
                     if settings["device"] in indexes else 0)
            if i is not None:
                settings["device"] = devices[i][1]
        elif choice == 5:
            if settings["file"]:
                settings["file"] = None  # switch back to the microphone
            else:
                path = input("Path to a 16 kHz / 16-bit / mono WAV file: ").strip()
                if path and not os.path.isfile(path):
                    print(f"[!] no such file: {path}")
                else:
                    settings["file"] = path or None
        # choice 6 is the separator row — nothing to do


def main() -> None:
    if termios is None or not sys.stdin.isatty():
        sys.exit("the interactive menu needs to run in a POSIX terminal (macOS/Linux)")
    settings = {
        "app_id": os.environ.get("IFLYTEK_APP_ID") or DEFAULT_APP_ID,
        "api_key": os.environ.get("IFLYTEK_API_KEY") or DEFAULT_API_KEY,
        "api_secret": os.environ.get("IFLYTEK_API_SECRET") or DEFAULT_API_SECRET,
        "preset": 0,
        "device": None,
        "file": None,
    }
    try:
        while settings_menu(settings):
            ISTClient(SimpleNamespace(**settings)).run()
            # hold the session log (errors, transcript) on screen until it has
            # been read, then redraw the menu
            input("\nPress Enter to return to the menu… ")
    except KeyboardInterrupt:
        pass  # terminal state is restored by the context managers


if __name__ == "__main__":
    main()
