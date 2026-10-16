# Lean Agent Verification Lab

ローカル GPU 上の **vLLM + Qwen3-1.7B** を使う AI Agent と、手書きの **Lean 4** 形式検証を組み合わせた 3 つの検証デモ（Streamlit）。

| Demo | 内容 | Lean で検証すること |
|---|---|---|
| 1. Verified Coding | 送金可否 | `amount ≤ balance` のときのみ許可・送金後残高 ≤ 元残高 |
| 2. Security Policy | RBAC 権限表 | 編集後のポリシーが禁止ルールを満たすか |
| 3. Verified Optimization | OR-Tools による人員配置 | 求めた具体解が全制約を満たすか（最適性は証明しない） |

詳細仕様は [`lean_agent_verification_design.md`](lean_agent_verification_design.md)、進捗は [`todo.md`](todo.md)。

## 要件

- Linux / Python 3.12+ / [uv](https://docs.astral.sh/uv/)
- Lean 4（[elan](https://github.com/leanprover/elan) 経由。バージョンは `lean/lean-toolchain` で固定）
- （Agent 利用時）NVIDIA GPU 8GB 以上（RTX A1000 8GB で確認）、CUDA 対応ドライバ

## セットアップ

```bash
uv sync                      # Python 依存関係
cp .env.example .env         # 必要に応じて編集
(cd lean && lake build)      # Lean ライブラリのビルド（初回はツールチェーン取得）
uv run pytest                # テスト
```

## 起動（2 プロセス）

```bash
# Terminal 1: vLLM（任意。停止していても Lean 単体デモは動く）
#   vllm-server/ は CUDA/PyTorch 依存をアプリ本体から分離した独立 uv 環境
(cd vllm-server && uv sync)          # 初回のみ（vLLM 0.31.0 / torch 2.13 で確認）
./vllm-server/serve.sh               # Qwen/Qwen3-1.7B, max-model-len 4096, gpu-mem 0.80

# Terminal 2: Streamlit
uv run streamlit run app.py
```

## 判定ステータス

| Status | 意味 |
|---|---|
| `PASS` | 仕様を満たし、Lean の証明も成功 |
| `VIOLATION` | 入力が業務ルールに違反（Lean が違反を証明） |
| `PROOF_FAILED` | Lean の証明が通らなかった（違反の証明ではない） |
| `ERROR` | Lean 実行エラー・禁止構文の検出など |
| `TIMEOUT` | Lean 実行がタイムアウト |
| `INFEASIBLE` | 最適化問題に実行可能解がない |

## AI Agent（タブ 4）

Qwen は要求文から **許可済みツールと引数を提案するだけ** で、判定は Python + Lean が行う。

1. 提案: `AGENT_TOOL_MODE=json`（既定。vLLM の構造化出力で JSON スキーマに制約）または `tools`（Tool Calling, `tool_choice=required`）
2. スキーマ検証（`jsonschema`）。失敗時はエラーを返して最大 `AGENT_MAX_RETRIES` 回再試行、それでも駄目ならユーザーにエラー表示
3. 事後チェック: 引数の数値が要求文に現れない場合は警告（LLM の抽出誤り対策）
4. allowlist ツールを実行 → Lean 検証
5. Qwen が結果を説明。判定と矛盾する説明は定型文に置換

vLLM が停止していてもタブ 1〜3（Lean 単体デモ）は動作する。

### 実機確認（RTX A1000 8GB, Qwen3-1.7B, vLLM 0.31.0）

- GPU 使用量: 約 7.0 GB（他プロセス約 1.1 GB を含む）、KV キャッシュ 1.7 GiB
- CUDA Toolkit（nvcc）が無い環境では FlashInfer サンプラーの JIT が失敗するため、`serve.sh` で `VLLM_USE_FLASHINFER_SAMPLER=0` を設定している
- 実機テスト: `uv run pytest -m vllm`（vLLM 起動時のみ）

## テスト

```bash
uv run pytest            # 単体 + Lean 結合 + UI（vLLM 不要）
uv run pytest -m vllm    # 起動中の vLLM を使う実機テスト
uv run python -m scripts.evaluate   # 評価（Lean 全サンプル + Agent 成功率 + 応答時間 + VRAM）
```

評価結果は [`docs/evaluation.md`](docs/evaluation.md)。
