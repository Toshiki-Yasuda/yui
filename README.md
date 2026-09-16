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

## マリンバ3D表示

「マリンバとは」ページ末尾に「立体で見るマリンバ（画像から生成した３Dモデル）」を配置。約1.02MBのGLBと、開始時のみ読み込むローカル配信のmodel-viewer 4.3.1を使用。元のBlenderファイルは変更していない。再生成方法・構成・検証結果と実機未検証の制約は [docs/marimba-3d.md](docs/marimba-3d.md) を参照。

## 当日配布プログラム

A3二つ折り・A4仕上がりの4ページ版です。曲目紹介は全11曲の全文を掲載しています。

- [印刷用A3 PDF](output/pdf/yui-program-a3.pdf)（両面短辺綴じ・原寸100%）
- [閲覧用A4 PDF](output/pdf/yui-program-a4.pdf)／[塗り足し付きPDF](output/pdf/yui-program-a3-bleed.pdf)
- [制作・印刷メモ](docs/program-production.md)／[編集原稿](プログラム/source/program.json)

本文はJSONから生成します。変更後は `scripts/build-program.py` と `scripts/check-program.py` で再生成・検証してください。

### 文字を大きくした三つ折りプログラム

A3・外三つ折り（Z折り）、本文12.5pt。二つ折り版とは別に保存。曲目紹介は全文掲載、安田愛のプロフィールは元PDFの短い略歴を使用。

- [印刷用A3](output/pdf/yui-program-trifold-a3.pdf)
- [読む順6面](output/pdf/yui-program-trifold-a3-reading.pdf)
- [制作・印刷手順](docs/program-trifold-production.md)

### A4配布用の三つ折りプログラム

A4用紙1枚・外三つ折り（Z折り）。全文保持、曲目紹介9pt、プロフィール10.5pt。出演者面は文章のみ、表紙は99×210mm専用の水彩画。

- [印刷用A4](output/pdf/yui-program-trifold-a4.pdf)
- [読む順6面](output/pdf/yui-program-trifold-a4-reading.pdf)
- [A4版の制作・印刷手順](docs/program-trifold-a4-production.md)
