"""Playwright でデモ操作を自動録画し、スクリーンショットも保存する。

前提: Streamlit（既定 http://localhost:8501）と vLLM が起動していること。
uv run python -m scripts.record_demo --url http://localhost:8599 --out docs/demo
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright

VIEWPORT = {"width": 1280, "height": 800}
HEADER_PX, ROW_PX = 36, 35  # data_editor（glide-data-grid）のヘッダー・行の高さ

CAPTION_JS = """(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = 'position:fixed;left:50%;bottom:24px;transform:translateX(-50%);' +
      'z-index:99999;background:rgba(17,24,39,.88);color:#fff;padding:10px 22px;' +
      'border-radius:10px;font:600 20px sans-serif;max-width:90%;text-align:center;';
    document.body.appendChild(el);
  }
  el.textContent = text;
}"""


class DemoRecorder:
    def __init__(self, page: Page, shots: Path) -> None:
        self.page = page
        self.shots = shots

    # ---- 共通操作 ----
    def caption(self, text: str, wait_ms: int = 1800) -> None:
        self.page.evaluate(CAPTION_JS, text)
        self.page.wait_for_timeout(wait_ms)

    def shot(self, name: str) -> None:
        self.page.screenshot(path=str(self.shots / f"{name}.png"))

    def open_tab(self, name: str) -> None:
        self.page.get_by_role("tab", name=name).click()
        self.page.wait_for_timeout(800)

    def click_button(self, name: str) -> None:
        self.page.get_by_role("button", name=name).click()

    def wait_text(self, text: str, timeout: int = 60_000) -> Locator:
        loc = self.page.get_by_text(text).filter(visible=True).first
        loc.wait_for(timeout=timeout)
        return loc

    def scroll_to(self, loc: Locator, settle_ms: int = 600) -> None:
        loc.scroll_into_view_if_needed()
        self.page.wait_for_timeout(settle_ms)

    def visible_grids(self) -> list[Locator]:
        grids = self.page.locator('[data-testid="stDataFrame"]')
        return [grids.nth(i) for i in range(grids.count()) if grids.nth(i).is_visible()]

    def grid_cell(self, grid: Locator, x_frac: float, row: int) -> tuple[float, float]:
        box = grid.bounding_box()
        assert box is not None
        return box["x"] + box["width"] * x_frac, box["y"] + HEADER_PX + ROW_PX * row + ROW_PX / 2

    # ---- シナリオ ----
    def intro(self) -> None:
        self.wait_text("Lean Agent Verification Lab")
        self.caption("Lean Agent Verification Lab — Lean 4 × OR-Tools × vLLM(Qwen3-1.7B)", 2500)
        self.shot("00_top")

    def demo_coding(self) -> None:
        self.open_tab("1. Verified Coding")
        self.caption("Demo 1: 送金ルール 0 ≤ 送金額 ≤ 残高 を Lean で検証")
        self.verify_transfer(80, "PASS", "01_coding_pass", "残高100・送金80 → Lean が安全性を証明（PASS）")
        self.verify_transfer(120, "VIOLATION", "02_coding_violation",
                             "送金120 → Lean が『許可されない』ことを証明（VIOLATION）")
        self.scroll_to(self.wait_text("生成された Lean 検証ソース"))
        self.wait_text("生成された Lean 検証ソース").click()
        self.caption("入力値から生成された Lean ソース（承認済みテンプレート + 型付きデータ）", 2500)
        self.shot("03_coding_source")

    def verify_transfer(self, amount: int, status: str, shot: str, caption: str) -> None:
        box = self.page.get_by_label("送金額 amount")
        box.fill(str(amount))
        box.press("Enter")
        self.page.wait_for_timeout(500)
        self.click_button("Lean で検証")
        self.scroll_to(self.wait_text(f"Lean 検証: {status}"))
        self.caption(caption, 2200)
        self.shot(shot)

    def demo_rbac(self) -> None:
        self.open_tab("2. RBAC Security")
        self.page.mouse.wheel(0, -2000)
        self.caption("Demo 2: RBAC 権限表を編集し、禁止ルールを Lean で検証")
        grid = self.visible_grids()[0]
        self.toggle_checkbox(grid, x_frac=0.61, row=2)  # viewer × write
        self.caption("Viewer に Write 権限を付与してみる")
        self.shot("04a_rbac_edit")
        self.page.get_by_role("button", name="Lean で検証").first.click()
        self.scroll_to(self.wait_text("Lean 検証: VIOLATION"))
        self.caption("Lean が違反一覧 [(viewer, write)] の完全一致と ¬Secure を証明（VIOLATION）", 2800)
        self.shot("04_rbac_violation")

    def toggle_checkbox(self, grid: Locator, x_frac: float, row: int) -> None:
        self.scroll_to(grid)
        x, y = self.grid_cell(grid, x_frac, row)
        self.page.mouse.click(x, y)
        self.page.wait_for_timeout(300)
        self.page.keyboard.press("Space")
        self.page.wait_for_timeout(700)

    def demo_optimization(self) -> None:
        self.open_tab("3. Verified Optimization")
        self.page.mouse.wheel(0, -3000)
        self.caption("Demo 3: 社員5名×案件3件を OR-Tools CP-SAT でコスト最小に割当")
        self.shot("05_opt_inputs")
        self.click_button("最適化して Lean で検証")
        self.scroll_to(self.wait_text("配置行列"))
        self.caption("OPTIMAL な具体解を Lean に渡し、全制約の充足と総コストを証明（PASS）", 2800)
        self.shot("06_opt_pass")
        self.edit_hours(x_frac=0.84, row=0, value="5")  # 佐藤 × 案件C（スキル不適合）
        self.caption("配置を手で編集: スキル不適合の 佐藤×案件C に 5h を割当")
        self.click_button("編集した配置を Lean で検証")
        self.scroll_to(self.wait_text("Lean 検証: VIOLATION"))
        self.caption("検出した制約違反を Lean が 1 件ずつ証明（VIOLATION）", 2800)
        self.shot("07_opt_violation")

    def edit_hours(self, x_frac: float, row: int, value: str) -> None:
        grid = self.visible_grids()[-1]
        self.scroll_to(grid)
        x, y = self.grid_cell(grid, x_frac, row)
        self.page.mouse.dblclick(x, y)
        self.page.wait_for_timeout(300)
        self.page.keyboard.press("Control+A")
        self.page.keyboard.type(value)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(1000)

    def demo_agent(self) -> None:
        self.open_tab("4. AI Agent")
        self.page.mouse.wheel(0, -3000)
        self.caption("Demo 4: 自然言語の要求 → Qwen がツールと引数を提案 → Lean が判定")
        self.ask_agent("残高100円から120円送金しても大丈夫？", "VIOLATION", "08_agent_transfer")
        self.ask_agent("案件Cの必要時間を90時間にして人員配置を最適化して", "PASS", "09_agent_optimize")

    def ask_agent(self, text: str, status: str, shot: str) -> None:
        self.page.mouse.wheel(0, -3000)
        area = self.page.get_by_label("要求文")
        area.fill(text)
        area.press("Control+Enter")
        self.page.wait_for_timeout(500)
        self.caption(f"要求: {text}", 1500)
        self.click_button("Agent に依頼")
        self.scroll_to(self.wait_text(f"Lean 検証: {status}"), 300)
        self.scroll_to(self.wait_text("提案されたツール"))
        self.caption(f"Qwen の提案をスキーマ検証 → 実行 → Lean 判定 {status}", 2800)
        self.shot(shot)

    def outro(self) -> None:
        self.caption("LLM は提案のみ。判定は常にレビュー済みの Lean 4 証明が行う", 3000)


def record(url: str, out: Path) -> Path:
    shots, raw = out / "screenshots", out / "_raw"
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, record_video_dir=str(raw),
                                  record_video_size=VIEWPORT, locale="ja-JP")
        page = ctx.new_page()
        page.goto(url)
        _run_scenario(DemoRecorder(page, shots))
        video = page.video
        ctx.close()
        browser.close()
        return _move_video(video.path(), out / "demo.webm", raw)


def _run_scenario(rec: DemoRecorder) -> None:
    rec.intro()
    rec.demo_coding()
    rec.demo_rbac()
    rec.demo_optimization()
    rec.demo_agent()
    rec.outro()


def _move_video(src: str, dst: Path, raw: Path) -> Path:
    shutil.move(src, dst)
    shutil.rmtree(raw, ignore_errors=True)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    ap.add_argument("--out", type=Path, default=Path("docs/demo"))
    args = ap.parse_args()
    print(record(args.url, args.out))


if __name__ == "__main__":
    main()
