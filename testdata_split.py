import os
import shutil
import random
from tqdm import tqdm

SOURCE_DIR = 'dataset'        
TEST_DIR = 'test_dataset'     
NUM_TO_MOVE = 20             

if not os.path.exists(TEST_DIR):
    os.makedirs(TEST_DIR)

classes = os.listdir(SOURCE_DIR)

print(f"Toplam {len(classes)} sınıf bulundu.")

total_moved = 0

for class_name in tqdm(classes):
    source_class_dir = os.path.join(SOURCE_DIR, class_name)
    test_class_dir = os.path.join(TEST_DIR, class_name)
    
    if not os.path.isdir(source_class_dir):
        continue
        
    images = os.listdir(source_class_dir)
    random_images = random.sample(images, NUM_TO_MOVE)
    
    if not os.path.exists(test_class_dir):
        os.makedirs(test_class_dir)
        
    for img_name in random_images:
        src = os.path.join(source_class_dir, img_name)
        dst = os.path.join(test_class_dir, img_name)
        
        shutil.move(src, dst)
        total_moved += 1

print(f"işlem tamamlandı. Toplam {total_moved} data, test olarak ayrıldı.")