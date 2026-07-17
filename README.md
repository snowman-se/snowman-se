# YOLO + OCR 車両文字認識サンプル

YOLOでナンバープレート領域を検出し、OCRで文字認識する最小構成のサンプルです。

## できること
- 画像ファイルまたはURLを入力
- YOLOでプレート領域候補を検出
- OCRで文字を読み取り
- 傾き対策として複数角度（-20/-10/0/10/20度）で推論
- 夜間向けに明るさ補正＋ノイズ低減を実施

> 完全に「どの角度・夜間・季節でも100%」を保証することはできません。実運用では対象環境に合わせた追加学習（データ拡張込み）が必要です。

## セットアップ
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 実行方法
```bash
python anpr_yolo_ocr.py \
  --source "https://example.com/car.jpg" \
  --plate-model "weights/license_plate_yolo.pt" \
  --conf 0.25
```

### JSONファイルに出力
```bash
python anpr_yolo_ocr.py \
  --source "/path/to/car.jpg" \
  --plate-model "weights/license_plate_yolo.pt" \
  --output "/tmp/result.json"
```

## 精度改善のポイント
- プレート専用YOLOモデルを学習（回転、モーションブラー、低照度、雨/雪/逆光の拡張）
- 昼夜・季節・カメラ角度別に評価データセットを分けて閾値調整
- OCR辞書を日本のナンバー表記に合わせてポストプロセス
