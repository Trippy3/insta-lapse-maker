"""OS ネイティブのファイル/ディレクトリ選択ダイアログを表示する worker。

tkinter は FastAPI サーバ本体 (event loop / 別スレッド) から直接呼ぶと
"RuntimeError: main thread is not in main loop" 等の問題が起きるため、
必ず独立した Python プロセスとして起動される前提。結果は stdout に JSON で出す。

stdin / stdout ベースなので呼び出し側は subprocess.run で扱えば良い。
"""

from __future__ import annotations

import argparse
import json
import sys


def _dialog(args: argparse.Namespace) -> str | None:
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    # 最前面に出す (他のウィンドウに隠れないように)
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    filetypes: list[tuple[str, str]] = []
    if args.filetype_name and args.filetype_pattern:
        filetypes.append((args.filetype_name, args.filetype_pattern))
    filetypes.append(("All files", "*.*"))

    kwargs: dict[str, object] = {}
    if args.title:
        kwargs["title"] = args.title
    if args.initial_dir:
        kwargs["initialdir"] = args.initial_dir

    try:
        if args.mode == "directory":
            picked = filedialog.askdirectory(**kwargs)
        elif args.mode == "save-file":
            picked = filedialog.asksaveasfilename(
                defaultextension=args.default_ext or "",
                filetypes=filetypes,
                initialfile=args.initial_file or "",
                confirmoverwrite=True,
                **kwargs,
            )
        elif args.mode == "open-file":
            picked = filedialog.askopenfilename(
                filetypes=filetypes,
                **kwargs,
            )
        else:
            raise ValueError(f"unknown mode: {args.mode}")
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    # tkinter はキャンセル時に空文字を返す
    return picked or None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["directory", "save-file", "open-file"],
        required=True,
    )
    parser.add_argument("--initial-dir", default=None)
    parser.add_argument("--initial-file", default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--default-ext", default=None)
    parser.add_argument("--filetype-name", default=None)
    parser.add_argument("--filetype-pattern", default=None)
    args = parser.parse_args()

    try:
        picked = _dialog(args)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 2

    print(json.dumps({"path": picked}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
