import os
import cv2


INPUT_DIR = os.path.expanduser('~/jazzy_ws/face_input')
OUTPUT_DIR = os.path.expanduser('~/jazzy_ws/face_database')

HAAR_PATH = '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml'


def preprocess_face(face_img):
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (100, 100))
    gray = cv2.equalizeHist(gray)
    return gray


def main():
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    detector = cv2.CascadeClassifier(HAAR_PATH)

    if detector.empty():
        print(f'ERROR: No se pudo cargar Haar Cascade: {HAAR_PATH}')
        return

    files = os.listdir(INPUT_DIR)

    if not files:
        print(f'No hay imágenes en: {INPUT_DIR}')
        return

    for filename in files:
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        input_path = os.path.join(INPUT_DIR, filename)

        image = cv2.imread(input_path)

        if image is None:
            print(f'No se pudo leer: {input_path}')
            continue

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        faces = detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        if len(faces) == 0:
            print(f'No se detectó rostro en: {filename}')
            continue

        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face

        face_img = image[y:y + h, x:x + w]
        face_processed = preprocess_face(face_img)

        user_name = os.path.splitext(filename)[0]
        output_path = os.path.join(OUTPUT_DIR, f'{user_name}.png')

        cv2.imwrite(output_path, face_processed)

        print(f'Usuario registrado: {user_name}')
        print(f'Guardado en: {output_path}')


if __name__ == '__main__':
    main()
