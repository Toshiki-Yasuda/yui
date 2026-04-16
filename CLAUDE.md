# マリンバコンサート「結」公式サイト

## プロジェクト概要
マリンバコンサート「結」の公式ホームページ。静的HTML/CSSサイトで、GitHub Pagesでホスティング。
- 公開URL: https://toshiki-yasuda.github.io/yui/
- 公演日: 2026年10月25日（日）13:30開演
- 会場: HITARU クリエイティブスタジオ（札幌市）

## ファイル構成
- `index.html` — メインページ（公演情報・チケット・出演者紹介・FAQ等）
- `marimba.html` — マリンバ紹介ページ
- `pamphlet.html` — 印刷入稿用パンフレット（塗り足し対応）
- `flyer.html` — A4フライヤー（印刷用）
- `css/style.css` — 共通スタイルシート
- `favicon.svg` — ファビコン（「結」の文字）
- `images/` — 画像フォルダ

## 技術スタック
- HTML5 + CSS3（ビルドツール・JSフレームワークなし）
- Google Fonts: Noto Sans JP / Noto Serif JP
- レスポンシブデザイン（モバイルファースト）
- CSS変数によるデザイントークン管理
- 構造化データ（JSON-LD: MusicEvent）

## デザイン方針
- カラーパレット: ベビーピンク(`#F4C2C2`) / ソフトブルー(`#7A9BB5`) / ラベンダー(`#D8BFD8`)
- グラスモーフィズム効果を使用
- 和の要素と柔らかい雰囲気を両立

## 確認方法
- `index.html` をブラウザで直接開く、またはLive Serverで起動
- Playwright MCPでブラウザ確認可能

## デプロイ
- `main` ブランチへpushすると GitHub Pages に自動デプロイ

## 注意事項
- 印刷用ページ（pamphlet.html, flyer.html）は塗り足し・トンボなどの印刷仕様あり。編集時は印刷要件を崩さないこと
- コンテンツは日本語。コミットメッセージも日本語プレフィックス（feat/fix/update/add/style/remove）で統一
