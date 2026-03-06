import asyncio
import queue
import sys
import threading

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print(
            "Error: Python < 3.11 requires 'tomli'.\n"
            "Run: pip install tomli",
            file=sys.stderr,
        )
        sys.exit(1)

import dearpygui.dearpygui as dpg
import intdash

_MAX_MESSAGES = 100
_data_queue: queue.Queue[str] = queue.Queue()
_messages: list[str] = []


def load_config(path: str = "config.toml") -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        print(
            f"Error: '{path}' not found.\n"
            "Run: cp config.toml.example config.toml  and fill in your values.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to parse config: {e}", file=sys.stderr)
        sys.exit(1)


async def on_data(datapoint) -> None:
    """受信データをキューに積む。GUIスレッドが読み出して表示する。"""
    try:
        string_data = intdash.data.String.from_payload(datapoint.data_payload)
        _data_queue.put(string_data.value)
    except Exception as e:
        print(f"[warn] Failed to decode datapoint: {e}", file=sys.stderr)


async def on_close() -> None:
    print("Connection closed.", file=sys.stderr)


async def run_downstream(config: dict) -> None:
    cfg = config["intdash"]

    client = intdash.Client(
        url=cfg["url"],
        edge_token=cfg["api_token"],
    )

    spec = intdash.DownstreamSpec(
        src_edge_uuid=cfg["edge_uuid"],
        filters=[
            intdash.DataFilter(
                data_type=intdash.DataType.string,
                data_id=cfg.get("data_id", ""),  # 空文字 = 全データID
                channel=int(cfg.get("channel", 1)),
            )
        ],
    )

    conn = await client.connect_iscp(on_close=on_close)

    downstream = None
    try:
        downstream = await conn.open_downstream(spec=spec, on_msg=on_data)
        await asyncio.Event().wait()  # ウィンドウが閉じられるまで待機
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        if downstream:
            await downstream.close()
        await conn.close()
        print("Disconnected.", file=sys.stderr)


def _asyncio_thread(config: dict) -> None:
    asyncio.run(run_downstream(config))


def _clear_messages() -> None:
    _messages.clear()
    dpg.set_value("log_text", "")


def main() -> None:
    config = load_config()
    cfg = config["intdash"]

    thread = threading.Thread(target=_asyncio_thread, args=(config,), daemon=True)
    thread.start()

    dpg.create_context()
    dpg.create_viewport(title="intdash Viewer", width=900, height=600)
    dpg.setup_dearpygui()

    with dpg.window(tag="main_window"):
        dpg.add_text(f"Edge: {cfg['edge_uuid']}")
        dpg.add_text("Connecting...", tag="status_text", color=(255, 200, 0))
        dpg.add_separator()
        dpg.add_button(label="Clear", callback=_clear_messages)
        dpg.add_input_text(
            tag="log_text",
            multiline=True,
            readonly=True,
            width=-1,
            height=-1,
        )

    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)

    connected = False
    while dpg.is_dearpygui_running():
        # キューからデータを取り出して表示を更新
        updated = False
        while not _data_queue.empty():
            try:
                item = _data_queue.get_nowait()
                _messages.insert(0, item)
                if len(_messages) > _MAX_MESSAGES:
                    _messages.pop()
                updated = True
            except queue.Empty:
                break

        if updated:
            dpg.set_value("log_text", "\n".join(_messages))

        # 接続ステータスを更新
        if not connected and updated:
            connected = True
            dpg.set_value("status_text", "Connected")
            dpg.configure_item("status_text", color=(0, 255, 0))
        elif connected and not thread.is_alive():
            dpg.set_value("status_text", "Disconnected")
            dpg.configure_item("status_text", color=(255, 0, 0))
            connected = False

        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
