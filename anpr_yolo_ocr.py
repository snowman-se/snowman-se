#!/usr/bin/env python3
"""YOLO + OCR pipeline for Japanese vehicle plate text extraction."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import cv2
import easyocr
import numpy as np
import requests
from ultralytics import YOLO


@dataclass
class OcrResult:
    text: str
    confidence: float


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_image(source: str) -> np.ndarray:
    if _is_url(source):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        image_array = np.frombuffer(response.content, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    else:
        image = cv2.imread(source, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(f"Could not load image from '{source}'")
    return image


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def improve_for_night(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    l = clahe.apply(l)
    merged = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return cv2.fastNlMeansDenoisingColored(enhanced, None, 5, 5, 7, 21)


def text_variants(plate_crop: np.ndarray) -> Iterable[np.ndarray]:
    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    adaptive = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        7,
    )
    otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # OCR works on both binary and color variants depending on illumination.
    return [plate_crop, improve_for_night(plate_crop), cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), cv2.cvtColor(adaptive, cv2.COLOR_GRAY2BGR), cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)]


def detect_plate_regions(model: YOLO, image: np.ndarray, confidence_threshold: float) -> list[tuple[int, int, int, int]]:
    results = model.predict(source=image, conf=confidence_threshold, verbose=False)
    if not results:
        return []

    boxes = []
    h, w = image.shape[:2]
    for r in results:
        if r.boxes is None:
            continue
        for b in r.boxes.xyxy.cpu().numpy():
            x1, y1, x2, y2 = map(int, b)
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w - 1))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h - 1))
            if x2 > x1 and y2 > y1:
                boxes.append((x1, y1, x2, y2))

    boxes.sort(key=lambda item: (item[2] - item[0]) * (item[3] - item[1]), reverse=True)
    return boxes


def read_plate_text(reader: easyocr.Reader, plate_crop: np.ndarray) -> OcrResult:
    best = OcrResult(text="", confidence=0.0)

    for variant in text_variants(plate_crop):
        detections = reader.readtext(variant, detail=1, paragraph=False)
        for _, text, confidence in detections:
            normalized = "".join(ch for ch in text.strip() if ch.isalnum() or ch in "ー-・ ")
            if not normalized:
                continue
            if float(confidence) > best.confidence:
                best = OcrResult(normalized, float(confidence))

    return best


def run_pipeline(source: str, plate_model_path: str, conf: float) -> dict:
    image = load_image(source)
    detector = YOLO(plate_model_path)
    reader = easyocr.Reader(["ja", "en"], gpu=False)

    best_candidate = OcrResult(text="", confidence=0.0)
    best_bbox: tuple[int, int, int, int] | None = None

    for angle in (-20, -10, 0, 10, 20):
        rotated = rotate_image(image, angle) if angle else image
        boxes = detect_plate_regions(detector, rotated, conf)

        if not boxes:
            continue

        for box in boxes[:5]:
            x1, y1, x2, y2 = box
            crop = rotated[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            candidate = read_plate_text(reader, crop)
            if candidate.confidence > best_candidate.confidence:
                best_candidate = candidate
                best_bbox = box

    if not best_candidate.text:
        # Fallback OCR when detector misses a difficult case.
        fallback = read_plate_text(reader, image)
        best_candidate = fallback

    return {
        "source": source,
        "text": best_candidate.text,
        "confidence": round(best_candidate.confidence, 4),
        "bbox": best_bbox,
        "note": "For high accuracy under night/angle/weather changes, train the YOLO plate model with matching augmented data.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YOLO + OCR plate text extraction")
    parser.add_argument("--source", required=True, help="Image path or URL")
    parser.add_argument(
        "--plate-model",
        default="weights/license_plate_yolo.pt",
        help="Path to YOLO license-plate detection model",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Detection confidence threshold")
    parser.add_argument("--output", default="", help="Optional output JSON path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_pipeline(args.source, args.plate_model, args.conf)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
