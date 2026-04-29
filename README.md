# Human Face Detection Prototype

Pythonと OpenCV を使ったヒトの顔検出プロトタイプです。  
静止画・動画ファイル・Webカメラの3つの入力モードに対応しており、
**Haar Cascade（追加ダウンロード不要）** または **DNN ベース（高精度）** の2種類の検出方法を選べます。

---

## 必要環境

| ソフトウェア | バージョン |
|---|---|
| Python | 3.8 以上 |
| opencv-python | 4.5 以上 |
| numpy | 1.21 以上 |

---

## セットアップ

```bash
# 仮想環境を作成（任意）
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

---

## 使い方

### 1. 静止画ファイル

```bash
python face_detection.py --image path/to/photo.jpg
```

検出結果の画像が `output_photo.jpg` として保存されます。

### 2. 動画ファイル

```bash
python face_detection.py --video path/to/video.mp4
```

### 3. Webカメラ（デフォルト）

```bash
python face_detection.py --webcam
```

### 4. Webカメラ（インデックス指定）

```bash
python face_detection.py --webcam-index 1
```

---

## 検出方法の切り替え

| オプション | 説明 |
|---|---|
| `--method haar` | Haar Cascade（デフォルト・追加ダウンロード不要） |
| `--method dnn` | DNN（より高精度・初回のみモデルを自動ダウンロード） |

```bash
# DNN モードで静止画を処理する例
python face_detection.py --image photo.jpg --method dnn
```

---

## 実行中の操作

- `q` キー：動画・Webカメラの映像を終了
- 任意のキー：静止画ウィンドウを閉じる

---

## 検出アルゴリズムの概要

### Haar Cascade（デフォルト）

OpenCV に同梱されている `haarcascade_frontalface_default.xml` を使用します。  
追加ファイルのダウンロードは不要で、正面を向いた顔の検出に適しています。

### DNN（ディープニューラルネットワーク）

OpenCV の `dnn` モジュールで SSD + ResNet-10 モデルを使用します。  
初回実行時にモデルファイル（約 10 MB）を自動でダウンロードします。  
複数の顔・斜め方向・遠距離など難易度の高い検出により強い精度を発揮します。

---

## ディレクトリ構成

```
.
├── face_detection.py   # メインスクリプト
├── requirements.txt    # 依存パッケージ
└── README.md
```
