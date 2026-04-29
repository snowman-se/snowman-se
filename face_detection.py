"""
Human Face Detection Prototype
-------------------------------
Supports three input modes:
  1. Static image file
  2. Live webcam feed
  3. Video file

Usage examples:
  python face_detection.py --image path/to/image.jpg
  python face_detection.py --video path/to/video.mp4
  python face_detection.py --webcam
  python face_detection.py --image path/to/image.jpg --method dnn

Press 'q' to quit webcam / video playback.
"""

import argparse
import os
import sys
import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Haar Cascade detector (no external weight files required)
# ---------------------------------------------------------------------------

def load_haar_detector():
    """Load the built-in OpenCV frontal-face Haar Cascade."""
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        raise RuntimeError(f"Failed to load Haar Cascade from {cascade_path}")
    return detector


def detect_faces_haar(frame, detector, scale_factor=1.1, min_neighbors=5, min_size=(30, 30)):
    """
    Detect faces in *frame* using a Haar Cascade classifier.

    Returns a list of (x, y, w, h) bounding boxes.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=scale_factor,
        minNeighbors=min_neighbors,
        minSize=min_size,
        flags=cv2.CASCADE_SCALE_IMAGE,
    )
    return faces if len(faces) > 0 else []


# ---------------------------------------------------------------------------
# DNN-based detector (uses OpenCV's built-in Caffe face detector)
# ---------------------------------------------------------------------------

DNN_PROTOTXT_URL = (
    "https://raw.githubusercontent.com/opencv/opencv/master/"
    "samples/dnn/face_detector/deploy.prototxt"
)
DNN_WEIGHTS_URL = (
    "https://raw.githubusercontent.com/opencv/opencv_3rdparty/"
    "dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
)
DNN_PROTOTXT_PATH = "deploy.prototxt"
DNN_WEIGHTS_PATH = "res10_300x300_ssd_iter_140000.caffemodel"
DNN_CONFIDENCE_THRESHOLD = 0.5


def load_dnn_detector():
    """Load the OpenCV DNN face detector, downloading weights if needed."""
    import urllib.request
    import os

    for url, path in [(DNN_PROTOTXT_URL, DNN_PROTOTXT_PATH), (DNN_WEIGHTS_URL, DNN_WEIGHTS_PATH)]:
        if not os.path.exists(path):
            print(f"Downloading {path} …")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as exc:
                raise RuntimeError(
                    f"Could not download {path}. "
                    "Please download it manually and place it in the current directory.\n"
                    f"URL: {url}\nError: {exc}"
                ) from exc

    net = cv2.dnn.readNetFromCaffe(DNN_PROTOTXT_PATH, DNN_WEIGHTS_PATH)
    return net


def detect_faces_dnn(frame, net):
    """
    Detect faces in *frame* using the DNN-based face detector.

    Returns a list of (x, y, w, h) bounding boxes.
    """
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)),
        scalefactor=1.0,
        size=(300, 300),
        mean=(104.0, 177.0, 123.0),
    )
    net.setInput(blob)
    detections = net.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence < DNN_CONFIDENCE_THRESHOLD:
            continue
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        x1, y1, x2, y2 = box.astype(int)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)
        boxes.append((x1, y1, x2 - x1, y2 - y1))
    return boxes


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_detections(frame, faces):
    """Draw bounding boxes and face count on *frame* (in-place)."""
    for i, (x, y, w, h) in enumerate(faces):
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        label = f"Face {i + 1}"
        label_y = y - 10 if y - 10 > 10 else y + h + 20
        cv2.putText(
            frame, label, (x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
        )

    count_text = f"Detected: {len(faces)} face(s)"
    cv2.putText(
        frame, count_text, (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2,
    )
    return frame


# ---------------------------------------------------------------------------
# Processing modes
# ---------------------------------------------------------------------------

def process_image(path, detect_fn):
    """Run face detection on a single image and display / save the result."""
    frame = cv2.imread(path)
    if frame is None:
        print(f"Error: could not read image '{path}'", file=sys.stderr)
        sys.exit(1)

    faces = detect_fn(frame)
    result = draw_detections(frame.copy(), faces)

    print(f"Detected {len(faces)} face(s) in '{path}'")

    output_path = "output_" + os.path.basename(path)
    cv2.imwrite(output_path, result)
    print(f"Result saved to '{output_path}'")

    cv2.imshow("Face Detection", result)
    print("Press any key to close the window.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def process_stream(source, detect_fn, window_title="Face Detection"):
    """Run face detection on a video stream (webcam or video file)."""
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: could not open source '{source}'", file=sys.stderr)
        sys.exit(1)

    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        faces = detect_fn(frame)
        result = draw_detections(frame, faces)

        cv2.imshow(window_title, result)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="Human face detection prototype (Haar Cascade or DNN).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", metavar="PATH", help="Path to an image file.")
    source.add_argument("--video", metavar="PATH", help="Path to a video file.")
    source.add_argument("--webcam", action="store_true", help="Use the default webcam (index 0).")
    source.add_argument(
        "--webcam-index", metavar="N", type=int,
        help="Use a specific webcam by index.",
    )

    parser.add_argument(
        "--method",
        choices=["haar", "dnn"],
        default="haar",
        help="Detection method: 'haar' (default, no download) or 'dnn' (more accurate).",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Load the chosen detector
    if args.method == "haar":
        detector = load_haar_detector()
        detect_fn = lambda frame: detect_faces_haar(frame, detector)
        print("Using Haar Cascade detector.")
    else:
        net = load_dnn_detector()
        detect_fn = lambda frame: detect_faces_dnn(frame, net)
        print("Using DNN detector.")

    # Run the chosen input mode
    if args.image:
        process_image(args.image, detect_fn)
    elif args.video:
        process_stream(args.video, detect_fn, window_title="Face Detection – Video")
    elif args.webcam:
        process_stream(0, detect_fn, window_title="Face Detection – Webcam")
    elif args.webcam_index is not None:
        process_stream(args.webcam_index, detect_fn, window_title="Face Detection – Webcam")


if __name__ == "__main__":
    main()
