"""Lean を安全に呼び出すランナー。

* `subprocess.run` を shell=False で使う
* 必ずタイムアウトを設定する
* 生成ファイルは専用作業ディレクトリ内に限定する
"""

from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LeanRun:
    stdout: str
    stderr: str
    exit_code: int | None
    elapsed_ms: int
    timed_out: bool


class LeanRunner:
    def __init__(self, project_dir: Path, work_dir: Path, timeout_sec: int = 60,
                 lake_cmd: str = "lake") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.work_dir = Path(work_dir).resolve()
        self.timeout_sec = timeout_sec
        self.lake_cmd = lake_cmd

    def run(self, source: str) -> LeanRun:
        path = self._write_source(source)
        try:
            return self._execute([self.lake_cmd, "env", "lean", str(path)])
        finally:
            path.unlink(missing_ok=True)

    def build(self) -> LeanRun:
        """レビュー済み Lean ライブラリ（Demo）をビルドする。"""
        return self._execute([self.lake_cmd, "build"])

    def _write_source(self, source: str) -> Path:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        path = (self.work_dir / f"check_{uuid.uuid4().hex}.lean").resolve()
        if path.parent != self.work_dir:
            raise ValueError("作業ディレクトリ外への書き込みは禁止されています")
        path.write_text(source, encoding="utf-8")
        return path

    def _execute(self, args: list[str]) -> LeanRun:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                args, cwd=self.project_dir, capture_output=True, text=True,
                timeout=self.timeout_sec, shell=False, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return LeanRun(_decode(exc.stdout), _decode(exc.stderr), None,
                           _elapsed_ms(start), timed_out=True)
        except FileNotFoundError as exc:
            return LeanRun("", str(exc), None, _elapsed_ms(start), timed_out=False)
        return LeanRun(proc.stdout, proc.stderr, proc.returncode,
                       _elapsed_ms(start), timed_out=False)


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _decode(data: bytes | str | None) -> str:
    if data is None:
        return ""
    return data.decode(errors="replace") if isinstance(data, bytes) else data
