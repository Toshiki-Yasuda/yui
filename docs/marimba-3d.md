# マリンバ3D表示の実装・公開・引き継ぎ

2026年9月14日。ユーザー指定の `adams_classic_55_v5.blend` をWeb向けGLBへ変換し、「マリンバとは」ページへ追加した。発音・演奏・AR機能は対象外。

## 確定した配置と見出し

- `marimba.html` の末尾、コンサート案内の後・「トップページに戻る」の前。
- 見出しは **立体で見るマリンバ（画像から生成した３Dモデル）**。括弧内は小さく表示する。
- 既存本文・水彩ヒーロー・比較表・導線は保持。
- ユーザーは実装後の公開を明示的に依頼済み。

## ファイル

- `models/marimba.glb`：公開用、テクスチャ内包。約1.02 MB（1,020,992 bytes）。
- `models/marimba-report.json`：容量・SHA256・三角形数・テクスチャ寸法・検証結果。
- `models/marimba-source.json`：元ファイルのハッシュとBlender書き出し時の計測値。
- `images/marimba-3d-poster.webp`：指定の確認PNGから作成した約60 KBの画像。元PNGは変更しない。
- `js/marimba-3d.js`：クリック後の読み込み、操作ボタン、エラー・タイムアウト・bfcache対応。
- `css/marimba.css`：専用スタイルは既存トークンを使用。
- `js/vendor/model-viewer/`：固定バージョン4.3.1とDracoデコーダーをローカル配信。LICENSEを同梱。
- `scripts/export-marimba.py`：Blender内での変換。元blendを保存しない。
- `scripts/check-marimba-model.mjs`：Dracoを展開してGLB検証、容量・描画予算をチェック。

Webサイト本体にはnpmビルドを導入していない。生成済みファイルをGitHub Pagesで配信する。

## 元モデルの扱いと軽量化

元ファイルはユーザー指定の `/Users/yasudaai/projects/ブレンダー/output/adams_classic_55_v5.blend`。元のSHA256は `28efca0b1b90b108ddd69cbf9ef4cc549da66aaad73bba3e4f9b7d62aacaa2d9`。書き出し前後で一致を検査している。

- 音板は68枚をassertで検査。低音側の折れ曲がった共鳴管、脚の調整機構、キャスターを含む全表示部品を元モデルから使用。
- カーブと文字を含む表示用形状は1,691個・1,019,528三角形。最初のメッシュのみの集計（約96万）とは対象が異なる。
- 木部80個は、統合前にオブジェクトごとの木目と粗さを焼き込んだ。Generated座標とObject Infoの変化を統合後に再評価しない。
- 木目4096px／粗さ1024pxでベイク後、配信用は2048px／1024pxのWebP。木部の微細なバンプと金属表面の微細なノイズは省略。ブラウザの環境光は元のBlender撮影照明とは異なる。
- 面取りの分割数を減らし、小部品をDecimate、同材質の固定部品を統合。glTF Transformで追加簡略化・材質パレット化。
- 最終 **177,300三角形・3プリミティブ**。Draco位置量子化を16bitにし、近接する細部の位置精度を確保。
- 親オブジェクトを除く前にワールド座標を保持すること。これを省くと銘板が原点へ移動する。ブラウザ確認で発見して修正済み。

## 表示と操作

[model-viewerの公式資料](https://modelviewer.dev/docs/)と[読み込みの例](https://modelviewer.dev/examples/loading/)に沿ったカスタム要素を使用。

- 「3Dで見る」を押すまでビューアー・GLB・Dracoを読み込まない。自動回転なし、影の追加描画なし。
- マウスドラッグ・ホイール、回転／拡大縮小／リセットのボタン。ボタンはキーボードでも操作できる。
- `touch-action="pan-y"` で縦方向のページスクロールを許容し、横から始めるタッチ回転とピンチに対応する設定。パンとタップによる注視点移動は無効。
- 読み込み中も指定画像を表示。失敗・60秒タイムアウト時は画像と再読み込みボタンを残す。JSなしでも画像を表示。
- `prefers-reduced-motion` ではカメラ補間を0にする。
- ページ離脱時にタイマー・モデルイベントを解除し、要素を取り外す。bfcacheから戻ると画像へ戻し、再度開始できる。
- 要素の表示領域を固定して画像から3Dへの切り替えによる高さ変化を防ぐ。操作バーは開始後に表示。

## 再生成

Blender 5.2.1 LTS、Node 24で作成。以下のnpm依存は作業用フォルダにだけ入れる。

```bash
npm install --prefix /tmp/yui-3d/tools --no-audit --no-fund @google/model-viewer@4.3.1 @gltf-transform/cli@4.5.0 gltf-validator@2.0.0-dev.3.10

/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --disable-autoexec '/Users/yasudaai/projects/ブレンダー/output/adams_classic_55_v5.blend' --python scripts/export-marimba.py

/tmp/yui-3d/tools/node_modules/.bin/gltf-transform optimize /tmp/yui-3d/marimba-raw.glb /tmp/yui-3d/marimba-optimized.glb --compress false --texture-compress webp --texture-size 2048 --simplify-ratio 0.4 --simplify-error 0.0002
/tmp/yui-3d/tools/node_modules/.bin/gltf-transform draco /tmp/yui-3d/marimba-optimized.glb models/marimba.glb --quantize-position 16 --quantize-normal 10
cp /tmp/yui-3d/export-report.json models/marimba-source.json
node scripts/check-marimba-model.mjs /tmp/yui-3d/tools
node --check js/marimba-3d.js
python3 scripts/check-site.py --baseline cd9b215
git diff --check
```

Blenderがサンドボックス内で起動直後に終了する環境では、許可されたローカル実行を使用した。元blendの自動実行は無効にする。

## 検証結果と限界

- ローカルのChromium系ブラウザで実際の描画・マウス回転・ホイールズーム・操作ボタン・Enterキーによる操作を確認。
- 1440×1000、1920×1080、768×1024、390×844、320×740のレイアウトを確認。確認した幅で横はみ出しなし。
- モデル取得を意図的に遮断してエラーを発生させ、確認画像・メッセージ・再読み込みボタンが表示され、モデル要素が残らないことを確認。
- JavaScript無効時も確認画像と案内が表示され、使用できない開始ボタンが隠れることを確認。
- モーション低減をブラウザでエミュレートし、補間0・自動回転なしを確認。
- 遅延読み込みは開始前のリソース一覧にビューアー・GLB・デコーダーがないことを検査。
- ローカルMac、1440幅、DPR 1、描画スケール1のドラッグ試験（約2秒）で、実描画3 calls／177,300三角形。描画フレーム更新間隔は中央値8.3ms、95パーセンタイル8.7ms（106サンプル）。これはこのMacの短時間測定で、GPU完了時間やモバイル性能の保証ではない。
- Draco展開後のglTF Validatorもエラー0・警告0。
- **iPhone／Android実機、Safari、実際のピンチと縦スワイプの競合、低性能GPU、長時間操作による発熱は未検証**。この検証ブラウザではネイティブtouchイベントの注入が未対応。画面幅のエミュレーションと実機試験を混同しない。
- WebGL2・WebAssembly・WebPに対応するブラウザが必要。非対応／読み込み失敗時は画像を表示する。

公開時は上記のHTML・CSS・JS・vendor・GLB・確認画像をまとめて反映し、公開ページでモデルを開くこと。今回以前から未コミットの冊子改訂は、この3D機能の公開に混ぜない。
