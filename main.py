import asyncio
import sys

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

import intdash


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
    """受信データを表示する。GUI化時にここを差し替える。"""
    try:
        string_data = intdash.String.from_payload(datapoint.data_payload)
        print(string_data.value)
    except Exception as e:
        print(f"[warn] Failed to decode datapoint: {e}", file=sys.stderr)


async def on_close() -> None:
    print("Connection closed.", file=sys.stderr)


async def run(config: dict) -> None:
    cfg = config["intdash"]

    client = intdash.Client(url=cfg["url"])

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

    print(f"Connecting to {cfg['url']} ...", file=sys.stderr)

    conn = await client.connect_iscp(
        on_close=on_close,
        token_source=intdash.StaticTokenSource(cfg["api_token"]),
    )

    print(
        f"Connected. Streaming from edge {cfg['edge_uuid']} (Ctrl+C to stop)",
        file=sys.stderr,
    )

    downstream = None
    try:
        downstream = await conn.open_downstream(spec=spec, on_msg=on_data)
        await asyncio.Event().wait()  # Ctrl+C まで待機
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        if downstream:
            await downstream.close()
        await conn.close()
        print("Disconnected.", file=sys.stderr)


def main() -> None:
    config = load_config()
    try:
        asyncio.run(run(config))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
