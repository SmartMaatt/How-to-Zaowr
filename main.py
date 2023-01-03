import json
import os

#import pyplot from matplotlib
from enum import Enum
from json import JSONEncoder
from matplotlib import pyplot as plt
import matplotlib
from tqdm import tqdm
import numpy as np
import cv2 as cv


class DispDirection(Enum):
    left_to_right = 0
    right_to_left = 1

class DispCriterium(Enum):
    argmax = 0
    argmin = 1

# >>> Disparity variables <<<
DISP_OUTPUT_FILE = r"./disp_output_file.json"
use_saved_disp = False

max_disp = 64
window_size = (11, 11)
disp_direction = DispDirection.left_to_right
disp_criterium = DispCriterium.argmin

IMG_LEFT = r"./Cones/im2.png"
IMG_RIGHT = r"./Cones/im6.png"
# IMG_LEFT = r"./Motocycle/im0.png"
# IMG_RIGHT = r"./Motocycle/im1.png"
#https://vision.middlebury.edu/stereo/data/scenes2014/datasets/Motorcycle-perfect/
#https://vision.middlebury.edu/stereo/data/scenes2003/newdata/cones/

# Dane w calib.txt datasetu - w tym przypadku dla bike1 i bike2
DOFFS = 124.343
BASELINE = 193.001
F = 3979.911



def calculate_disparity(img_left, img_right, max_disparity, window_size, direction, criterium):
    if use_saved_disp and os.path.isfile(DISP_OUTPUT_FILE):
        disp = read_disp_data()
        return disp

    else:
        if direction == DispDirection.right_to_left:
            return calculate_disparity_bm_from_right_to_left(img_left, img_right, max_disparity, window_size, criterium)
        elif direction == DispDirection.left_to_right:
            return calculate_disparity_bm_from_left_to_right(img_left, img_right, max_disparity, window_size, criterium)     

def calculate_disparity_bm_from_right_to_left(img_left, img_right, max_disparity, window_size, criterium):
    height = np.shape(img_left)[0]
    width = np.shape(img_left)[1]
    window_height = window_size[0]
    window_width = window_size[1]
    half_window_height = window_height // 2
    half_window_width = window_width // 2
    disparity = np.zeros((height, width))

    for y in tqdm(range(half_window_height, height - half_window_height)):
        for x in range(width - half_window_width, half_window_width, -1):
            template = img_left[y - half_window_height: y + half_window_height, x - half_window_width: x + half_window_width]
            n_disparity = min(max_disparity, x - half_window_width)
            score = np.zeros(n_disparity)

            for offset in range(n_disparity, 0, -1):
                roi = img_right[y - half_window_height: y + half_window_height, x - half_window_width - offset: x + half_window_width - offset]
                score[offset - 1] = ssd(roi, template)

            if criterium == DispCriterium.argmax:
                disparity[y, x] = score.argmax()
            elif criterium == DispCriterium.argmin:
                disparity[y, x] = score.argmin()
    return disparity

def calculate_disparity_bm_from_left_to_right(img_left, img_right, max_disparity, window_size, criterium):
    height = np.shape(img_left)[0]
    width = np.shape(img_left)[1]
    window_height = window_size[0]
    window_width = window_size[1]
    half_window_height = window_height // 2
    half_window_width = window_width // 2
    disparity = np.zeros((height, width))

    for y in tqdm(range(half_window_height, height - half_window_height)):
        for x in range(half_window_width, width - half_window_width):
            template = img_right[y - half_window_height: y + half_window_height, x - half_window_width: x + half_window_width]
            n_disparity = min(max_disparity, width - x - half_window_width)
            score = np.zeros(n_disparity)

            for offset in range(n_disparity):
                roi = img_left[y - half_window_height: y + half_window_height, x - half_window_width + offset: x + half_window_width + offset]
                score[offset + 1] = ssd(template, roi)

            if criterium == DispCriterium.argmax:
                disparity[y, x] = score.argmax()
            elif criterium == DispCriterium.argmin:
                disparity[y, x] = score.argmin()
    return disparity

# Sum of square difference
def ssd(img_left, img_right):
    return np.sum((img_left - img_right) ** 2)

def save_disp_to_json(disp):
    # >>> Saving result to json <<<
    class NumpyArrayEncoder(JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return JSONEncoder.default(self, obj)

    json_data = {
        'disp': disp
    }

    # Writing to json
    with open(DISP_OUTPUT_FILE, "w") as outfile:
        json.dump(json_data, outfile, indent=4, cls=NumpyArrayEncoder)

def read_disp_data():
    # Read JSON file
    print(f'Reading calibration file: {DISP_OUTPUT_FILE}')
    with open(fr'{DISP_OUTPUT_FILE}', 'r') as f:
      calibration_data = json.load(f)

    disp = np.array(calibration_data['disp'])
    return disp




def disp_to_depth(disp, baseline, f, doffs):
    return baseline * f / (disp + doffs)

def depth_to_disp(depth, baseline, f, doffs):
    return baseline * f / depth - doffs



if __name__ == '__main__':
    img_left = cv.imread(IMG_LEFT)
    img_right = cv.imread(IMG_RIGHT)

    disp = calculate_disparity(img_left, img_right, max_disp, window_size, disp_direction, disp_criterium)
    save_disp_to_json(disp)

    color_map = plt.cm.get_cmap('turbo', 8)
    plt.imshow(disp, cmap=color_map)
    plt.show()

    imgPlot = matplotlib.pyplot.imshow(disp)
    plt.show()

    # depth tylko jeżeli jest baseline, fokal i doffs - dla bike byly w pliku calib.txt https://vision.middlebury.edu/stereo/data/scenes2014/
    # depth = disparity.disp_to_depth(disp, BASELINE, F, DOFFS)

    #jak zapisac disparity i depth do pliku? - na zajeciach mowil o 3 mozliwosciach:
    # #bilbioteką (?)tif(?) zapisać tablicę
    #zapisać jako obrraz (.png)
    #znormalizować do 8 bitów i zapisać jako obraz