# マリンバコンサート「結」公式サイト

マリンバコンサート「結」の公式ホームページです。

## 公演情報

- **日時**: 2026年10月25日（日）13:00開場 / 13:30開演
- **会場**: HITARU クリエイティブスタジオ（札幌市）
- **出演**: 安田 愛（マリンバ）、田中 K助（ピアノ）、土田 祐生（パーカッション）
- **主催**: マリンバ北星会
- **後援**: 札幌市／札幌市教育委員会／日本マリンバ協会／北海道打楽器協会

## 公開URL

https://toshiki-yasuda.github.io/yui/

## 技術仕様

- HTML5 + CSS3 + 依存ライブラリを使わない JavaScript
- レスポンシブデザイン（モバイルファースト）
- GitHub Pages でホスティング

## ファイル構成

```
yui/
├── index.html          # メインページ
├── marimba.html        # マリンバ紹介ページ
├── pamphlet.html       # 印刷入稿用パンフレット（塗り足し対応）
├── flyer.html          # A4フライヤー（印刷用）
├── css/
│   ├── style.css       # 共通・メインページのスタイル
│   └── marimba.css     # 楽器紹介のスタイル
├── js/site.js          # ナビゲーション・スクロール・動画・画像拡大
├── scripts/check-site.py # 内容とリンクの整合性検証
├── docs/redesign-review.md # デザイン方針・検証記録
├── images/             # 画像フォルダ
├── favicon.svg         # ファビコン（「結」の文字）
└── README.md           # このファイル
```

## ローカルでの確認方法

```bash
# リポジトリをクローン
git clone https://github.com/Toshiki-Yasuda/yui.git

# リポジトリ内でローカルサーバーを起動
python3 -m http.server 8001 --bind 127.0.0.1
```

[http://127.0.0.1:8001/index.html](http://127.0.0.1:8001/index.html) を開きます。ビルドは不要です。

変更後は次の検証を実行します。`--baseline` は比較する変更前のコミットです。

```bash
python3 scripts/check-site.py --baseline cd9b215
node --check js/site.js
git diff --check
```

## 更新履歴

- 2026-01-26: 初版公開
