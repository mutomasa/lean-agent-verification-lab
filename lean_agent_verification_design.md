# Lean Agent Verification Lab — Claude Code 開発設計書

## 1. 目的

ローカルGPU **NVIDIA RTX A1000 8GB** 上の **vLLM + 小型Qwen** を使うAI Agentと、手書きの **Lean 4** 形式検証を組み合わせ、3種類の検証デモを **Streamlit** で実装する。

1. **Verified Coding Agent**：送金処理の安全な仕様を検証する。
2. **Security Policy Verifier**：RBAC権限ルールを検証する。
3. **Verified Optimization**：OR-Toolsで得た人員配置が制約を満たすことを検証する。

**Leanstral、Hugging Face GPU、Ollamaは使わない。** Python環境管理には **uv**、LLM推論には **vLLM** を使う。Lean 4の定義・定理・証明は開発者が作成・レビューし、LLMには証明の正当性の判定を任せない。

## 2. 実装原則

- **形式仕様が主役**：自然言語をLLMが解釈しても、何を保証するかは人がレビューしたLean 4の仕様で定義する。
- **責務分離**：Qwenは要求解釈・ツール選択・説明、Lean 4は証明、OR-Toolsは最適化を担当。
- **安全な構造化入力**：LLMはあらかじめ定義したJSONスキーマに沿う操作を提案する。任意のシェルコマンドやLeanソースを無制限に実行させない。
- **三値以上の判定**：`PASS / VIOLATION / PROOF_FAILED / ERROR / TIMEOUT` を区別する。Leanの証明失敗だけを「反例が見つかった」と解釈しない。
- **証明の抜け道を許さない**：`sorry`、`admit`、未承認の `axiom`、検証を迂回する実装は禁止。Lean 4の実行結果と検証対象を保存する。
- **ローカル完結**：通常動作にクラウドAPIや外部GPUを必要としない。初期セットアップのパッケージ取得は許可。
- **段階的開発**：まずLLMなしで3デモを動かし、その後AI Agentを接続する。

## 3. 技術スタック

| 分類 | 採用技術 | 備考 |
|---|---|---|
| UI | Streamlit | 3タブ、ログ表示 |
| Python | Python 3.11+ / uv | 互換性が確認できるバージョンを固定 |
| Agent | Python、必要ならLangGraph | 初期版は薄い状態遷移でもよい |
| LLM | Qwen3 1.7B | RTX A1000 8GBでの起動を優先 |
| 推論 | vLLM | ローカルOpenAI互換API |
| 形式検証 | Lean 4 | `lake env lean`、必要な場合のみMathlib |
| 数理最適化 | OR-Tools CP-SAT | 整数ベースの割当モデル |
| APIクライアント | openai Python SDK | `base_url`をローカルvLLMに向ける |
| テスト | pytest | 単体・結合・異常系 |

### GPU運用

まず **Qwen/Qwen3-1.7B** をvLLMで起動し、GPUメモリを実測する。4B量子化モデルへの拡張は任意の後続タスクとする。使用するQwenのTool Calling形式・vLLMバージョンで互換性をテストし、動作しない場合は**JSON出力を検証する方式**へ切り替える。モデルコンテキスト長、KVキャッシュ、他プロセスによって8GB VRAMを超える可能性があるため、パラメータを調整できるようにする。

## 4. アーキテクチャ

```text
Streamlit UI
  ├── Demo 1: Verified Coding
  ├── Demo 2: RBAC Security
  └── Demo 3: Verified Optimization (元の案の Demo 4)
             │
             ▼
      Demo Service Layer
             │
             ├── AI Agent ── OpenAI-compatible client ── vLLM ── Qwen (A1000 8GB)
             │      └── JSON schema validation + allowlisted tools
             │
             ├── Lean Verification Service ── lake env lean ── Lean 4 Kernel
             │
             └── Optimization Service ── OR-Tools CP-SAT
             │
             ▼
  Structured Results / Evidence / Logs
```

重要：**Leanをモデル推論サーバー内で実行しない**。vLLMはGPU、LeanとOR-ToolsとStreamlitはCPU主体で独立稼働させる。

## 5. デモ仕様

### Demo 1 — Verified Coding Agent

**シナリオ**：口座残高 `balance` と送金額 `amount`。`amount ≤ balance` のときだけ送金を許可し、送金後の残高が非負であることを検証する。

- Leanで自然数の残高・金額・送金可否・送金後残高を定義。
- 検証する定理：`amount ≤ balance` なら `balance - amount ≤ balance`、残高は非負。
- **正常例**：残高100、送金80。
- **違反例**：残高100、送金120。業務上の検証結果は `VIOLATION`（許可しない）。
- Qwen Agentは要求文を構造化し、検証ツールを選び、結果を自然言語で説明。
- UI：要求文、金額入力、ルール、Leanコード（読み取り専用）、検証結果、実行ログ。

**注意**：このデモはLean上のモデルについての保証。別途記述した実際のPython送金プログラムまで検証済みと主張しない。

### Demo 2 — Security Policy Verifier

**シナリオ**：RBACの `Admin / Editor / Viewer` と `Read / Write / Delete`。

| Role | Read | Write | Delete |
|---|---|---|---|
| Admin | 可 | 可 | 可 |
| Editor | 可 | 可 | 不可 |
| Viewer | 可 | 不可 | 不可 |

- LeanでRole、Action、アクセス判定関数、禁止ルールを定義。
- 検証する性質：ViewerはWrite/Deleteできない、EditorはDeleteできない、Delete可能ならAdminである。
- UIから権限マトリクスを編集。Python側で有限な9組を列挙し、明示的な違反 `(role, action)` を抽出する。
- 同じ入力ポリシーをLean側のデータとして生成し、レビュー済みの検証定理・決定手続きを用いてチェック。固定デフォルト表に対する定理だけを実行して、ユーザー編集後のポリシーを検証したことにしない。
- UI：編集可能な権限表、検証開始ボタン、検出した違反、Lean結果、ログ。

### Demo 3 — Verified Optimization（旧 Demo 4）

**シナリオ**：社員5名を案件3件に割り当て、制約を満たしつつコストを最小化。

- 初期サンプルは整数時間の割当 `hours[employee, project]`。
- 制約：各社員の週稼働時間 ≤ 40、各案件の必要時間以上を配賦、非負整数、任意で社員別スキル適合。
- 目的：整数の時間単価 × 配賦時間の総和を最小化。
- OR-Tools CP-SATで解を求める。**解の最適性はOR-Toolsのステータスを表示するだけで、Leanによる数学的な最適性証明とは区別する。**
- 求めた具体的な割当行列と制約パラメータをLeanへ渡し、各制約が真であることを検証する。
- UI：社員・案件・需要工数・単価、配置行列、総コスト、OR-Toolsステータス、Leanによる制約検証結果。
- 異常系：需要工数が総稼働可能時間を超える場合は `INFEASIBLE` として明示する。

## 6. AI Agentの責務とツール

**LLMには決定権を持たせず、検証用のツール呼び出しを提案させる。** 実際のパラメータ検証・呼び出し・最終判定はPython側で実施する。

| Tool | 入力 | 出力 |
|---|---|---|
| `verify_transfer` | `balance: int`, `amount: int` | `VerificationResult` |
| `verify_rbac` | 権限マトリクス | `VerificationResult` + 違反箇所 |
| `optimize_staffing` | 社員/案件/需要/単価 | 配賦案 + 最適化ステータス |
| `verify_staffing` | 具体的な配賦案 + 制約 | `VerificationResult` |

```python
from dataclasses import dataclass
from enum import Enum

class Status(str, Enum):
    PASS = "PASS"
    VIOLATION = "VIOLATION"
    PROOF_FAILED = "PROOF_FAILED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    INFEASIBLE = "INFEASIBLE"

@dataclass
class VerificationResult:
    status: Status
    summary: str
    lean_stdout: str = ""
    lean_stderr: str = ""
    elapsed_ms: int = 0
```

## 7. 推奨ディレクトリ構成

```text
lean-agent-verification-lab/
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── app.py
├── config/
│   └── settings.py
├── src/
│   ├── agent/
│   │   ├── client.py
│   │   ├── orchestrator.py
│   │   ├── schemas.py
│   │   └── tools.py
│   ├── demos/
│   │   ├── coding.py
│   │   ├── security.py
│   │   └── optimization.py
│   ├── verification/
│   │   ├── lean_runner.py
│   │   ├── source_builder.py
│   │   └── results.py
│   └── optimization/
│       └── staffing.py
├── lean/
│   ├── lean-toolchain
│   ├── lakefile.toml
│   └── Demo/
│       ├── Coding.lean
│       ├── Security.lean
│       └── Optimization.lean
└── tests/
    ├── test_coding.py
    ├── test_security.py
    ├── test_optimization.py
    └── test_lean_runner.py
```

## 8. 起動方法（目標形）

依存関係とLeanをセットアップ後、別ターミナルで起動する。

```bash
# Terminal 1: vLLM（vLLM対応のLinux/CUDA環境）
uv run vllm serve Qwen/Qwen3-1.7B \
  --host 127.0.0.1 \
  --port 8000 \
  --dtype auto \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80

# Terminal 2: Streamlit
uv run streamlit run app.py
```

環境によってはvLLMを別のuv環境に分離してもよい。vLLM/CUDA/PyTorchの対応バージョンを確認して固定する。Tool Callingが必要なら対象モデル・vLLMバージョンで検証後、対応するparser設定を追加する。

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="local")
response = client.chat.completions.create(
    model="Qwen/Qwen3-1.7B",
    messages=[{"role": "user", "content": "送金額が残高を超えないことを検証したい"}],
    temperature=0.1,
)
```

`model` は実際にvLLMが提供するモデル名と一致させる。

## 9. Lean実行に関する安全要件

- `lake env lean <allowlisted-generated-file>` を `subprocess.run` で実行する。`shell=True` を使わない。
- 必ずタイムアウトを設定し、stdout/stderr/終了コードを保存する。
- 生成するLeanソースは承認済みテンプレートと型付きデータから組み立て、任意のLLM文字列をコードとして直結しない。
- ファイルパスは専用の作業ディレクトリ内に限定する。
- 予期しない構文エラー・未証明・Lean実行エラーを分離する。
- UIには具体的な違反内容と、Leanの検証結果を別々に表示する。

## 10. Claude Codeへの実装指示

この設計書に従い、以下の順序で実装すること。

### Phase 1: リポジトリと環境

- `uv` プロジェクトを作成し、Streamlit・OpenAI SDK・OR-Tools・pytestを追加。
- Lean 4プロジェクトを作成し、`lake env lean` の動作を確認。
- READMEにインストール手順、GPU要件、2プロセス起動手順を記載。

### Phase 2: Lean 4単体の検証

- `Coding.lean`、`Security.lean`、`Optimization.lean` を手書きで実装。
- 成功・違反・異常の固定ケースを準備。
- PythonからLeanを安全に呼び出す共通ランナーを作成。

### Phase 3: Streamlit 3タブ

- Demo 1、Demo 2、Demo 3をUIから実行可能にする。
- Lean検証と業務ルール違反を区別して表示。
- 入力を変えると検証対象も変わることを結合テストで確認。

### Phase 4: vLLM + Qwen Agent

- vLLMの接続設定を環境変数化。
- Qwenから定義済みツールの呼び出しパラメータを取得する機能を追加。
- 構造化出力のスキーマ検証に失敗した場合は再試行またはユーザーにエラーを表示。
- vLLMが停止していてもLean単体デモが動くようにする。

### Phase 5: 評価と仕上げ

- 正常系・違反系・タイムアウト・vLLM停止をpytestで確認。
- Proof success、応答時間、Agentツール選択成功率、VRAM使用量を記録。
- `uv run pytest` とLeanの全サンプル検証を成功させる。

## 11. 受け入れ条件

- [ ] Streamlitの3つのデモが動作する。
- [ ] vLLM + 小型QwenがRTX A1000 8GBで実行できる（実機で確認）。
- [ ] 3デモすべてに自作Lean 4の検証がある。
- [ ] Qwenが停止しても、UIからLean単体検証を実行できる。
- [ ] RBAC編集結果と最適化の具体的な解が、実際のLean検証入力に反映される。
- [ ] 違反・証明失敗・実行エラー・タイムアウトを区別する。
- [ ] LLMの生成テキストを無制限に実行しない。
- [ ] 正常・違反・異常のテストがある。
- [ ] READMEに環境構築・起動・使用方法を記載する。

## 12. スコープ外

- Leanstral、Hugging Face有料GPU、Ollama、外部LLM API。
- LLMによる自動定理生成を正当性保証の中心にすること。
- Pythonの実行コード全体についての形式的正当性の保証。
- 最適化アルゴリズムの**大域的最適性**のLean形式証明（今回証明するのは**制約充足**）。

---

**Claude Code開始用プロンプト**

> この `lean_agent_verification_design.md` を仕様書として読み、Phase 1から順番に実装してください。最初に `CLAUDE.md` と実装チェックリストを作成し、各Phaseの完了時にテスト結果を示してください。構成はStreamlit + uv + vLLM + Qwen3-1.7B + RTX A1000 8GB + 自作Lean 4 + OR-Toolsです。Leanstral、Ollama、クラウドLLMは使用しません。特に、UI入力に応じてLeanの検証対象が変わること、証明失敗を仕様違反と誤認しないこと、LLM生成コードの任意実行をしないことを守ってください。
