# 管理画面からのウォッチ対象の変更

読者ひとりが、ローカルの管理画面からウォッチ対象を追加・編集・削除する。正本は設定ファイルのまま。用語はリポジトリ直下の [CONTEXT.md](../../../CONTEXT.md) に従う。設定の形・取り込み・マージ・ビルド成果物のタイムラインは [2026-08-30-libwatch-design.md](./2026-08-30-libwatch-design.md) のまま。タイムラインのマークアップと見た目は [2026-08-31-timeline-ui-design.md](./2026-08-31-timeline-ui-design.md) のまま。待ち受けを localhost のプロセスに限る判断は [0001-localhost-watchlist-management.md](../../adr/0001-localhost-watchlist-management.md)。

## Classification

architectural

## Approach

設定ファイルを正本のまま残す。localhost の管理プロセスが管理画面を出し、YAML を正規化して書く。タイムラインの更新は今までのビルド。コピーした `site/` と GitHub Actions の成果物は読むだけ。

画面や DB・ブラウザ保存を正本にする常駐アプリ化、保存のたびに取り込みまで走らせること、管理 UI を静的 `site/` に含めて公開面からも触れるようにすることは採らない。

この spec が親仕様から置き換えるのは次だけである。

- non-goal「画面からウォッチ対象を登録する UI」→ 任意の管理画面を足す（必須にはしない）
- 「実行時サーバは無い」→ 読む成果物にサーバは不要。管理とローカルプレビューだけ `serve` を使う

## Goals

- 読者が管理画面からウォッチ対象を追加・編集・削除できる。正本は設定ファイル。YAML 直接編集も残る。
- 画面登録は必須にしない。最後の1件は削除できない。
- 管理プロセスは `127.0.0.1` だけで、タイムライン（`site/`）と管理画面を出す。保存は YAML のみ。
- ビルド済みの読む画面は今のタイムライン仕様のまま。管理画面は `site/` に書かない。
- 引数なしのビルドコマンドと、既定テストがネットワークに出ないことは変えない。

## Non-goals

- 公開サイトからの保存、ログイン、共有ウォッチリスト、DB。
- 管理画面を静的成果物に含める、タイムライン上の登録 UI、読む画面から管理へのリンク。
- 保存時の自動ビルド、更新源の自動推定、カタログ、プリセット必須。
- 管理画面の script、並び替え UI、成功フラッシュ。
- `localhost` ホスト名での案内・書き込み許可、`0.0.0.0` 待ち受け。
- 壊れた YAML の画面からの修復、コメント保持。
- GitHub Actions での serve、Pages 公開。

## Architecture

実行時サーバは読む成果物には無い。コピーした `site/` は今どおり静的ファイルだけで読める。ウォッチ対象を画面から変えるときと、ローカルでプレビューするときだけ、同じプロセスが待ち受ける。

```text
watchlist.yml（正本）
  → python -m libwatch          既存の取り込み・マージ・site/ 書き出し
  → site/index.html + style.css  タイムライン（親仕様のまま）

watchlist.yml
  ⇄ python -m libwatch serve     127.0.0.1 のみ
       GET  /              site/index.html。無ければ未ビルド説明ページ
       GET  /style.css     site/style.css（無ければ 404）
       GET  /manage        管理画面（YAML を読む。site/ は見ない）
       GET  /manage.css    管理用 CSS（site/ は見ない）
       POST /manage        検証して YAML を正規化書き込み。ビルドしない
```

`/manage` と `/manage.css` は予約パスで、`site/` より優先する。`/manage` と `/manage/` は同じである。

待ち受けは `127.0.0.1`。既定ポートは 8000。`--port` で変更できる。使用中なら起動失敗。起動時に標準出力へ `http://127.0.0.1:{port}/` と `http://127.0.0.1:{port}/manage` を出す。`localhost` は案内しない。

第一引数が無ければビルド。第一引数が `serve` なら管理プロセス。それ以外の第一引数は起動失敗。`--port` は serve 専用である。ビルドに付けると起動失敗。serve の未知引数も起動失敗。GitHub Actions はビルドだけ。

## Components

- **設定ファイル**: リポジトリ直下の `watchlist.yml`。正本。形と検証は親仕様の Config のまま（1件以上、`name` 一意、`blog` と/または `releases`、未知キー禁止）。
- **ビルド**: 既存の `python -m libwatch`。この spec では変えない。
- **管理プロセス**: `python -m libwatch serve`。カレントディレクトリの `watchlist.yml` と `site/` を使う（ビルドと同じ）。
- **静的出し**: `site/` 配下を GET で出す。予約パス以外。正規化後のパスが `site/` の外なら出さない。ディレクトリ一覧は出さない。
- **管理画面**: プロセスだけが HTML を出す。script なし。追加フォームは常時。一覧は読むだけ。編集は `?edit={name}` でその1件のフォーム。削除確認は `?confirm_delete={name}` で確認専用表示。タイムライン `/` へのリンクはある。読む画面からこちらへのリンクは無い。
- **管理 CSS**: プロセスが `/manage.css` で出す。トークンと制約はタイムライン仕様と同じ（システム色、単一カラム、カードなし、Web フォントなし、`color-scheme: light dark`、本文幅 `68ch`）。フォーム用の規則を足してよい。未ビルドの `/` もこれを参照する。
- **YAML 書き込み**: 画面保存が成功したとき、ファイル全体を正規化して置き換える。コメント・元のキー順・引用符は残さない。無い任意キー（`blog` / `releases`）は出力しない。一時ファイル経由で置き換え、壊れた中間ファイルを残さない。
- **衝突検知**: フォームに、読み込み時のファイル生バイトの SHA-256（小文字 hex）を `hash` として hidden で載せる。書き込み直前のディスク上の生バイトと違えば保存しない。
- **Origin 検査**: 書き込み POST だけ。後述の規則。GET は検査しない。

アプリ用の DB・外部 JS・追加の成果物ファイルは足さない。ビルドは管理 HTML を `site/` に書かない。

## Config

親仕様の Config / GitHub Releases URL を変えない。画面からの追加・編集の検証も、書き込み後の YAML が同じ規則を満たすことである。

画面が書き出す YAML の値は、親仕様が読み込み後に持つ値と同じである。`name` は前後空白を除いた値。`blog` があるときはフラグメントを除いた絶対 `http` / `https` URL。`releases` があるときは常に `https://github.com/{owner}/{repo}/releases.atom`。手で書いた `/releases` ページ URL は、画面保存後はこの atom URL になる。

キー順は各件で `name`、あれば `blog`、あれば `releases`。トップレベルは `targets` のみ。UTF-8。追加はリスト末尾。改名は位置を変えない。

## Data flow

カレントディレクトリはビルドと同じ。設定ファイルは `watchlist.yml`、成果物は `site/`。

### 起動

1. `127.0.0.1:{port}` で待つ。既定 8000。`--port` は 1〜65535 の整数。取れなければ起動失敗（終了コード非ゼロ）。
2. 標準出力に次の2行を出す（このホスト名以外は出さない）。
   - `http://127.0.0.1:{port}/`
   - `http://127.0.0.1:{port}/manage`
3. 起動時にビルドしない。YAML の可否もここでは見ない。

### 読み（GET）

許可メソッドは GET と POST。それ以外は 405。YAML は触らない。

予約パス（`site/` より先）:

- `/manage.css` → プロセスの CSS。常に 200。
- `/manage`（末尾スラッシュは同一）。クエリだけ見る。

クエリ値は URL デコードしたあと、YAML 上の `name`（trim 済み）と照合する。href に載せるときは URL エンコードする。

`/manage` のクエリ:

- `edit` と `confirm_delete` が両方ある、どちらかの値が空、該当する `name` が YAML に無い、`confirm_delete` が最後の1件 → **一覧**（追加フォームあり）とエラー。確認専用にも編集フォームにもしない。
- `confirm_delete` だけが、2件以上ある既存の `name` → **確認専用**（一覧・追加・編集は出さない）。
- `edit` だけが既存の `name` → 一覧 + 常時の追加フォーム + その1件の編集フォーム。
- クエリなし → 一覧 + 常時の追加フォーム。

YAML が無い・UTF-8 でない・親仕様の Config に反する（0件を含む）ときは、上記にせず **エラー表示だけ**。フォームは出さない。

`/`:

- `site/index.html` があれば、そのバイトを返す（親仕様の HTML。相対 `style.css` のまま）。管理へのリンクは足さない。
- 無ければ 200 で未ビルド説明ページ。`/manage.css` を参照する。管理へのリンクは置かない。

`/style.css`: `site/style.css` があればそのバイト。無ければ 404。

予約パス以外の GET は `site/` 配下のファイル。リクエストパスを正規化した結果が `site/` ディレクトリの外なら 404。ディレクトリ一覧は出さない。ファイルが無ければ 404。

### 書き（POST `/manage`）

POST の対象は `/manage` だけである。それ以外のパスへの POST は 405。YAML を触らない。

1. Origin 検査。`Origin` ヘッダがある場合はその値だけを見る。値が `http://127.0.0.1:{port}` と一致するときだけ続ける（`{port}` は実際に待っているポート。スキーム・ホスト・ポート以外を含む値は不一致）。`Origin` が無ければ `Referer` からスキーム・ホスト・ポートだけを取り、同じ文字列と比較する。両方無い、一致しない、`localhost` や別ポート → YAML を触らず 403。本文の詳細は出さなくてよい。
2. 本文が 64 KiB を超える → YAML を触らず 400。
3. `Content-Type` のメディアタイプ（`;` より前、前後空白を除き小文字）が `application/x-www-form-urlencoded` でない → YAML を触らず 400。charset パラメータはあってよい。
4. YAML が読めない（GET のエラー表示と同じ条件）→ YAML を触らず 200 でエラー表示だけ。フォームなし。
5. 読み込んだファイルの生バイトの SHA-256（小文字 hex）が、フォームの `hash` と一致しなければ、YAML を触らず 200 で管理画面（一覧+追加）と衝突エラー。`hash` が無いときも同じ。POST された name / blog / releases はフォームに戻さない。
6. `action` は `add` / `edit` / `delete` のどれか。それ以外・欠落は YAML を触らず 200 で一覧+追加とエラー。

フィールドの空文字は、`blog` と `releases` では「その更新源は無し」である。`name` の空は検証失敗である。

**add:** `name`, `blog`, `releases`。末尾に1件足したリストを、親仕様の Config と同じ規則で検証する。失敗なら YAML を触らず 200。エラーと入力値を追加フォームに残す。一覧の他件は読むだけ。

**edit:** `original_name` が既存の `name`。同じ位置で `name` / `blog` / `releases` を置き換える（改名可）。検証は Config と同じ。失敗なら YAML を触らず 200。エラーと入力値を、その `original_name` の編集フォームに残す。`original_name` が YAML に無い → YAML を触らず 200、一覧+追加とエラー。編集フォームにはしない。入力値は戻さない。

**delete:** `name` が既存。残りが 0 件になるなら拒否（YAML を触らず 200、一覧+追加、エラー。確認専用にはしない）。`name` が無いときも同じ。それ以外はその件を除く。確認用 GET を経ていなくても、POST がこの規則を満たせば削除してよい。

検証成功:

7. ファイル全体を正規化して書き、一時ファイル経由で置き換える。書き出し失敗なら既存ファイルを残し、200 でエラー。壊れた中間ファイルを残さない。
8. 成功なら **303 See Other**、`Location: /manage`（クエリなし、本文なし）。成功メッセージ用のクエリは付けない。

失敗した書き込みのあと、次の GET はディスク上の現在のバイトを正とする。

## Page

未ビルドの `/`:

```text
html lang="ja"
  head: charset, viewport, title「ライブラリ更新ウォッチ」, link href="/manage.css"
  header > h1「ライブラリ更新ウォッチ」
  main > p「タイムラインはまだビルドされていない」
```

`script` なし。管理へのリンクなし。このページはエラーではなく、200 である。「更新はまだない」は使わない。

管理画面（YAML が読めたとき）:

```text
html lang="ja"
  head: charset, viewport, title「ウォッチ対象」, link href="/manage.css"
  header
    h1「ウォッチ対象」
    a href="/"「タイムライン」
  main
    エラーがあれば p
    確認専用でなければ 追加フォーム POST /manage
      hidden action=add, hash
      name, blog, releases
    確認専用でなければ 各ウォッチ対象（YAML 順）
      編集中の1件: 編集フォーム POST /manage
        hidden action=edit, hash, original_name
        name, blog, releases
        a「キャンセル」href="/manage"
      それ以外: 表示 + a「編集」href="/manage?edit={urlencoded name}"
        2件以上なら a「削除」href="/manage?confirm_delete={urlencoded name}"
    確認専用:
      p「{name} を削除しますか」
      form POST /manage: hidden action=delete, hash, name
      a「キャンセル」href="/manage"
```

ラベルは用語どおり（公式ブログ、リリースノート）。タイトル・名前・URL・エラーは HTML として解釈せずエスケープする。`hash` は当該 GET で読んだファイル生バイトの SHA-256 hex。1件のときは削除リンクを出さない。キャンセルは `GET /manage`（クエリなし）。確認専用のあいだは一覧・追加・編集フォームを出さない。

YAML が読めないときの `/manage` は同じヘッダ（タイムラインへのリンクあり）と、エラーの `p` だけ。フォームなし。`script` なし。

ビルド済みタイムラインの HTML は親仕様・タイムライン仕様のままである。`nav` / 管理へのリンク / `script` を足さない。

## Error handling

**起動失敗**（プロセスは待たない。終了コード非ゼロ）:

- 第一引数が `serve` でも空でもない。
- ビルドに `--port` など未知の引数がある。
- `--port` が整数でない、範囲外（1〜65535 以外）、serve の未知引数。
- `127.0.0.1:{port}` を取れない（使用中を含む）。

**GET / POST 以外**: 405。YAML も `site/` も触らない。

**Origin 不一致・Origin も Referer も無い POST**: 403。YAML を触らない。

**POST の本文が 64 KiB 超、または Content-Type が上記でない**: 400。YAML を触らない。

**POST 先が `/manage` 以外**: 405。YAML を触らない。

**設定が読めない**（ファイル無し、UTF-8 でない、親仕様の Config 違反、0 件）:

- GET `/manage`: 200。ヘッダとエラーのみ。フォームなし。
- POST `/manage`: Origin とサイズと Content-Type を見たあと、YAML を触らず 200。同じエラー表示。フォームなし。
- GET `/` と `site/` の静的出しは、YAML に依存しない。

**クエリ不正**（`edit` と `confirm_delete` の同時、空値、無い `name`、最後の1件の `confirm_delete`）: 200 で一覧+追加とエラー。確認専用にも編集フォームにもしない。YAML を触らない。

**衝突**（`hash` 不一致または欠落）: YAML を触らず 200。一覧+追加と衝突エラー。入力値は戻さない。

**`action` 不正・欠落**: YAML を触らず 200。一覧+追加とエラー。

**add / edit の検証失敗**（親仕様の Config と同じ: 空名、重複名、更新源ゼロ、不正 URL）: YAML を触らず 200。エラーと入力値を残す。add なら追加フォームに残す。edit ならその件の編集フォームのまま（`original_name` 基準）。一覧の他件は読むだけ。

**edit で `original_name` が YAML に無い**: YAML を触らず 200。一覧+追加とエラー。編集フォームにはしない。入力値は戻さない。

**delete で `name` が無い、または削除すると 0 件になる**: YAML を触らず 200。一覧+追加とエラー。確認専用にはしない。

**書き出し失敗**（権限、ディスク、置換失敗）: 既存の `watchlist.yml` を残す。200 でエラー。成功時と同じく壊れた中間ファイルを残さない。

**静的ファイル**: 予約パス以外でファイルが無い、または `site/` の外になるパス → 404。`/` で `index.html` が無いこと自体はエラーではなく、未ビルド説明ページ（200）。

取り込み失敗の扱い（源のスキップ等）はこの spec の対象外（親仕様のまま）。serve は保存時も起動時もフィードを取りに行かない。

## Numeric defaults

- 待ち受け: `127.0.0.1`。既定ポート 8000。`--port` は 1〜65535。
- 許可 Origin: `http://127.0.0.1:{port}` のみ（実際に待っているポート）。
- POST 本文上限: 64 KiB。
- 衝突ハッシュ: SHA-256、小文字 hex、ファイルの生バイト。
- 成功: 303、`Location: /manage`。
- 管理 CSS パス: `/manage.css`。管理パス: `/manage`（末尾スラッシュ同一）。
- クエリ: `edit`, `confirm_delete`。
- フォーム `action`: `add` | `edit` | `delete`。
- Python: 3.11 以上（親仕様）。HTTP 取り込みの 15 秒・2 MiB はこの spec では触らない。

## 否定と順序

- GET は YAML を変えない。削除の確定は POST。確認用 GET はまだ消さない。
- 最後の1件に削除リンクを出さない。出なくても POST なら拒否する。
- 追加はリスト末尾。改名は位置を維持。並び替え UI なし。
- 画面保存はファイル全体の正規化置き換え。部分置換しない。
- 成功メッセージ用のクエリもフラッシュも無い。
- `localhost` を案内しない。その Origin の書き込みは 403。
- 管理画面を `site/` に書かない。ビルドは管理 HTML を出さない。
- serve は保存時も起動時もビルドしない。

## Consuming paths

- ウォッチ対象の正本は今までどおり `watchlist.yml`。手編集してよい。
- タイムラインを出す: リポジトリ直下で `python -m libwatch`（引数なし、親仕様のまま）。
- ローカルで読む・管理する: 同じディレクトリで `python -m libwatch serve`。ブラウザは起動時に出た `http://127.0.0.1:8000/` と `http://127.0.0.1:8000/manage` を開く（ポートを変えたらその URL）。
- ポート変更: `python -m libwatch serve --port 8001`。
- 停止は `Ctrl+C`。
- README の `python -m http.server --directory site --bind 127.0.0.1 8000` はこの serve に置き換える。コピーした `site/` をサーバ無しで開く手順は残してよい。
- GitHub Actions は今どおりビルドだけ。serve は載せない。
- 画面で保存したあとにタイムラインへ新しい更新を載せるには、今までどおりビルドする。serve は再起動しなくてよい（`/` はディスク上の `site/` を読む）。

## Testing

既定テストはネットワークに出ない。フィード取得の差し込みは親仕様のまま。serve のテストは `127.0.0.1` に対するプロセス内（または同等）の HTTP でよい。外部ホストへは出ない。スクリーンショットは取らない。

残す（親仕様・タイムライン仕様）:

- 設定検証、取り込みスキップ、マージ、`site/` のタイムライン HTML/CSS、空メッセージ「更新はまだない」。
- ビルド成果物に `script` が無い。管理用 HTML を `site/` に書かない。

足す:

- 引数なしはビルド。第一引数 `serve` と `--port` は serve だけ。不正な `--port`、未知引数、`serve` 以外の第一引数は起動失敗。
- `site/index.html` が無い GET `/` は 200 で「タイムラインはまだビルドされていない」。`/manage.css` を参照する。管理へのリンクも `script` も無い。
- `site/index.html` がある GET `/` はそのファイル。管理リンクを足さない。
- GET `/manage` は YAML 順の一覧と追加フォーム。1件のときは削除リンクが無い。2件以上なら各件に削除リンクがある。
- GET `?edit=` はその1件だけ編集フォーム。YAML を変えない。
- GET `?confirm_delete=` は確認専用。YAML を変えない。最後の1件や無い名前は一覧+エラー。
- POST add は末尾に足し、303 で `/manage`。再 GET で新しい件がある。
- POST edit は改名でき、位置は変わらない。衝突する `name` は保存しない。
- POST delete は消え、タイムライン成果物は変えない。最後の1件の POST は保存しない。
- 手で YAML を変えたあと古い `hash` の POST は保存しない。
- 不正 URL・更新源ゼロ・重複名の POST は 200 で入力を残し、ファイルは変わらない。
- Origin 無し / `http://localhost:{port}` / 別ポート の POST は 403、ファイルは変わらない。`Origin: http://127.0.0.1:{port}` は通る。
- `site/manage.html` があっても GET `/manage` はプロセスの管理画面。
- 画面保存後の YAML は `targets` のみ。`releases` は解決済み atom URL。コメントは残らない。
- GET だけでは `watchlist.yml` のバイトが変わらない。
- 既定テストランナーはネットワークに接続しない。

## 親仕様との衝突

衝突したら、管理プロセス・管理画面・`watchlist.yml` の画面からの書き込み・README のローカルプレビューはこのファイル。設定の形、取り込み、マージ、ビルド成果物のタイムライン HTML/CSS は親仕様（タイムライン見た目は 2026-08-31）。親の non-goal「画面からウォッチ対象を登録する UI」と「実行時サーバは無い」は、このファイルの Goals のとおり狭める。
