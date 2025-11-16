import cv2, os, shutil

RAW = "raw_images"
PROC = "processed"
os.makedirs(PROC, exist_ok=True)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def process_images():
    for person in os.listdir(RAW):
        input_folder  = os.path.join(RAW, person)
        output_folder = os.path.join(PROC, person)
        os.makedirs(output_folder, exist_ok=True)

        count = 0

        for img_name in os.listdir(input_folder):
            img_path = os.path.join(input_folder, img_name)
            img = cv2.imread(img_path)

            if img is None: continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x,y,w,h) in faces:
                face = gray[y:y+h, x:x+w]
                face = cv2.resize(face, (200,200))

                count += 1
                cv2.imwrite(os.path.join(output_folder, f"{count}.jpg"), face)

        print(f"✔ {person} → {count} valid face images")

print("\n⚙ Processing images...\n")
process_images()
print("\n🎯 Processing done! Check /processed folder\n")
