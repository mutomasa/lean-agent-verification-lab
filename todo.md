# TODO — Lean Agent Verification Lab

仕様書: `lean_agent_verification_design.md`
運用: 機能ごとにブランチ → PR → マージ。問題点は GitHub Issues に記録する。

## Phase 0: 開発基盤
- [x] git 初期化・GitHub リポジトリ作成
- [x] todo.md / CLAUDE.md / .gitignore

## Phase 1: リポジトリと環境 (`feature/phase1-setup`)
- [x] uv プロジェクト作成（streamlit, openai, ortools, pytest）
- [x] Lean 4 プロジェクト作成（lean-toolchain, lakefile.toml）
- [x] `lake env lean` の動作確認
- [x] README（インストール、GPU要件、2プロセス起動）
- [x] `.env.example` / `config/settings.py`

## Phase 2: Lean 4 単体の検証 (`feature/phase2-lean`)
- [x] `Status` / `VerificationResult`（results.py）
- [x] 安全な Lean ランナー（shell=False, timeout, 作業ディレクトリ限定）
- [x] 出力分類（PASS / VIOLATION / PROOF_FAILED / ERROR / TIMEOUT）
- [x] `sorry` / `admit` / `axiom` 検出
- [x] `Demo/Coding.lean`（送金）
- [x] `Demo/Security.lean`（RBAC）
- [x] `Demo/Optimization.lean`（配賦制約）
- [x] source_builder（型付きデータ → Lean ソース）
- [x] 正常・違反・異常の固定ケーステスト

## Phase 3: ドメインサービス + Streamlit 3タブ (`feature/phase3-ui`)
- [ ] demos/coding.py
- [ ] demos/security.py（9組列挙＋Lean検証）
- [ ] optimization/staffing.py（CP-SAT, INFEASIBLE）
- [ ] demos/optimization.py
- [ ] app.py 3タブ UI
- [ ] 入力変更で検証対象が変わる結合テスト

## Phase 4: vLLM + Qwen Agent (`feature/phase4-agent`)
- [ ] 接続設定の環境変数化
- [ ] schemas.py（ツール引数の JSON スキーマ検証）
- [ ] tools.py（allowlist ツール）
- [ ] client.py（OpenAI 互換クライアント）
- [ ] orchestrator.py（再試行・エラー表示）
- [ ] vLLM 停止時でも Lean 単体デモが動く
- [ ] UI に Agent モード追加

## Phase 5: 評価と仕上げ (`feature/phase5-eval`)
- [ ] 正常・違反・タイムアウト・vLLM 停止の pytest
- [ ] 評価スクリプト（証明成功、応答時間、ツール選択成功率、VRAM）
- [ ] vLLM + Qwen3-1.7B を A1000 で実機確認
- [ ] `uv run pytest` 全成功 / Lean 全サンプル検証成功

## 受け入れ条件
- [ ] Streamlit の3デモが動作する
- [ ] vLLM + 小型 Qwen が RTX A1000 8GB で実行できる
- [ ] 3デモすべてに自作 Lean 4 の検証がある
- [ ] Qwen 停止時も UI から Lean 単体検証を実行できる
- [ ] RBAC 編集結果と最適化の具体解が Lean 検証入力に反映される
- [ ] 違反・証明失敗・実行エラー・タイムアウトを区別する
- [ ] LLM の生成テキストを無制限に実行しない
- [ ] 正常・違反・異常のテストがある
- [ ] README に環境構築・起動・使用方法を記載
