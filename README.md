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
uv run --with vllm vllm serve Qwen/Qwen3-1.7B \
  --host 127.0.0.1 --port 8000 --dtype auto \
  --max-model-len 4096 --gpu-memory-utilization 0.80

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
