# CLAUDE.md

- 仕様書: `lean_agent_verification_design.md`、進捗: `todo.md`（チェックボックス管理）
- 会話は日本語
- 開発フロー: 機能ごとに `feature/*` ブランチ → PR → マージ。見つけた問題は GitHub Issues に記録
- Python は uv、テストは pytest（`uv run pytest`）
- 関数は小さく、SOLID 原則に従う
- Lean: `lean/` 配下。`sorry` / `admit` / 未承認 `axiom` は禁止
- Lean 実行は `subprocess.run`（shell=False）+ timeout。LLM 文字列を Lean コードに直結しない
