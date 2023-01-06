import sys
import os
import IO
import matplotlib
import numpy as np
import cv2 as cv

from math import tan
from enum import Enum
from matplotlib import pyplot as plt
from tqdm import tqdm
from plyfile import PlyData, PlyElement
import open3d as o3d


class DispDirection(Enum):
    left_to_right = 0
    right_to_left = 1

class DispCriterium(Enum):
    argmax = 0
    argmin = 1

# >>> Disparity variables <<<
DISP_FILE = r"./disp_output_file_Car.json"
use_saved_disp = True

max_disp = 64
window_size = (11, 11)
disp_direction = DispDirection.left_to_right
disp_criterium = DispCriterium.argmin

IMG_LEFT = r"./Car/left.png"
IMG_RIGHT = r"./Car/right.png"
# IMG_LEFT = r"./Cones/im2.png"
# IMG_RIGHT = r"./Cones/im6.png"
# IMG_LEFT = r"./Motocycle/im0.png"
# IMG_RIGHT = r"./Motocycle/im1.png"
#https://vision.middlebury.edu/stereo/data/scenes2014/datasets/Motorcycle-perfect/
#https://vision.middlebury.edu/stereo/data/scenes2003/newdata/cones/

# Dane w calib.txt datasetu - w tym przypadku dla bike1 i bike2
DOFFS = None
BASELINE = 0.6
F = None
FOV = 120




def calculate_focal_with_FOV(image_width, fov):
    return (image_width / (2 * tan(fov / 2)))

def calculate_disparity(img_left, img_right, max_disparity, window_size, direction, criterium):
    if use_saved_disp and os.path.isfile(DISP_FILE):
        disp = IO.read_disp_data(DISP_FILE)
        return disp

    else:
        if direction == DispDirection.right_to_left:
            disp = calculate_disparity_bm_from_right_to_left(img_left, img_right, max_disparity, window_size, criterium)
        elif direction == DispDirection.left_to_right:
            disp = calculate_disparity_bm_from_left_to_right(img_left, img_right, max_disparity, window_size, criterium)

        IO.save_disp_to_json(disp, DISP_FILE)
        return disp

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
                score[offset - 1] = ssd(template, roi)

            if criterium == DispCriterium.argmax:
                disparity[y, x] = score.argmax()
            elif criterium == DispCriterium.argmin:
                disparity[y, x] = score.argmin()
    return disparity

# Sum of square difference
def ssd(img_left, img_right):
    return np.sum((img_left - img_right) ** 2) #/ np.sqrt(np.sum(img_left * img_left) * np.sum(img_right * img_right))






def calculate_depth_from_disp(disp, f, baseline, doffs):
    depth = np.zeros(shape=disp.shape)
    for i in range(len(disp)):
        for j in range(len(disp[i])):
            if (disp[i][j] == 0):
                depth[i][j] = (f * baseline) / 1
            else:
                depth[i][j] = (f * baseline) / (disp[i][j] + doffs)
    return depth

def calculate_disp_from_depth(depth, f, baseline, doffs):
    disp = np.zeros(shape=depth.shape)
    for i in range(len(depth)):
        for j in range(len(depth[i])):
            if (depth[i][j] == 0):
                disp[i][j] = (baseline * f) / 1
            else:
                disp[i][j] = (baseline * f) / (depth[i][j] - doffs)
    return disp

def compute_cx_cy(width,height):
    cx = width/2
    cy = height/2
    return (cx,cy)

def save_depth_to_ply(depth,fov):
    pcd = []
    height, width = depth.shape
    cx,cy = compute_cx_cy(width,height)
    for i in range(height):
        for j in range(width):
            z = depth[i][j]
            x = (j - cx) * z / fov #fx
            y = (i - cy) * z / fov #fy
            pcd.append([x, y, z])
    pcd_o3d = o3d.geometry.PointCloud()  # create point cloud object
    pcd_o3d.points = o3d.utility.Vector3dVector(pcd)  # set pcd_np as the point cloud points
    o3d.io.write_point_cloud("depth.ply", pcd_o3d)
    # Visualize:
    o3d.visualization.draw_geometries([pcd_o3d])




def array_to_bgra(image):
    """Convert a CARLA raw image to a BGRA numpy array."""
    array = np.frombuffer(image, dtype=np.dtype("uint8"))
    array = np.reshape(array, (image.shape[0], image.shape[1], 4))
    return array

def array_to_rgb(image):
    """Convert a CARLA raw image to a RGB numpy array."""
    array = array_to_bgra(image)
    # Convert BGRA to RGB.
    array = array[:, :, :3]
    array = array[:, :, ::-1]
    return array

def calculate_depth_from_rgb24(image):
    """
    Convert an image containing CARLA encoded depth-map to a 2D array containing
    the depth value of each pixel normalized between [0.0, 1.0].
    """
    array = array_to_bgra(image)
    array = array.astype(np.float32)
    # # Apply (R + G * 256 + B * 256 * 256) / (256 * 256 * 256 - 1).
    normalized_depth = np.dot(array[:, :, :3], [65536.0, 256.0, 1.0])

    # # TO DO - transform algorithm form np.dot to normal loops
    normalized_depth2 = np.zeros(shape=array.shape[:2])
    # for i in range(len(array)):
    #     for j in range(len(array[i])):
    #         value = array[i][j][2] + array[i][j][1] * 256 + array[i][j][0] * 256 * 256
    #         normalized_depth2[i][j] = value

    normalized_depth /= 16777215.0  # (256.0 * 256.0 * 256.0 - 1.0)
    normalized_depth2 /= 16777215.0
    return (normalized_depth * 1000, normalized_depth2 * 1000)

def calculate_rgb24_from_depth(image):
    array = image.astype(np.float32)
    array /= 1000
    array *= 16777215.0

    rgb24 = np.zeros(shape=[array.shape[0], array.shape[1], 3])
    for i in range(len(array)):
        for j in range(len(array[i])):
            data = array[i][j]
            r = data % 256
            data = (data - r) / 256
            g = data % 256
            b = (data - g) / 256

            rgb24[i][j][0] = b % 256
            rgb24[i][j][1] = g % 256
            rgb24[i][j][2] = r % 256
    
    return rgb24


if __name__ == '__main__':
    img_left = cv.imread(IMG_LEFT)
    img_right = cv.imread(IMG_RIGHT)

    read_depth = IO.read_image_to_np_array("results/depth_raw.png")
    read_depth2 = cv.imread("results/depth_raw.png")

    # Calculate disparity
    disp = calculate_disparity(img_left, img_right, max_disp, window_size, disp_direction, disp_criterium)

    # Plot and save disparity
    matplotlib.pyplot.imshow(disp)
    plt.show()
    plt.imsave("results/disparity.png", disp)
    cv.imwrite("results/disparity_raw.png", disp)

    # Calculate focal and depth
    F = calculate_focal_with_FOV(np.shape(img_left)[1], FOV)
    depth = calculate_depth_from_disp(disp, F, BASELINE, 0)
    
    # Save depth as ply
    Fy = calculate_focal_with_FOV(np.shape(img_left)[0], FOV)
    save_depth_to_ply(depth,F) #fx fy???

    # Plot and save depth
    matplotlib.pyplot.imshow(depth)
    plt.show()
    plt.imsave("results/depth.png", depth)
    cv.imwrite("results/depth_raw.png", depth)

    # Calculate rgb24 depth
    rgb24 = calculate_rgb24_from_depth(depth)
    rgb24 = rgb24.astype(np.uint8)

    # Plot and save rgb24
    matplotlib.pyplot.imshow(rgb24)
    plt.show()
    plt.imsave("results/rgb24.png", rgb24)
    cv.imwrite("results/rgb24_raw.png", rgb24)
    sys.exit()

    # Read 24bit map form file and calculate depth from it
    read_24bit = IO.read_image_to_np_array("Car/depth.png")
    (new_depth, new_depth2) = calculate_depth_from_rgb24(read_24bit)
    matplotlib.pyplot.imshow(new_depth)
    plt.show()
    cv.imwrite("read_depth.png", new_depth)

    matplotlib.pyplot.imshow(new_depth2)
    plt.show()
    cv.imwrite("read_depth.png", new_depth2)

    new_rgb24 = calculate_rgb24_from_depth(new_depth)
    matplotlib.pyplot.imshow(new_rgb24)
    plt.show()
    cv.imwrite("read_rgb24.png", new_rgb24)

    # # Save depth from file
    # read_depth = IO.read_image_to_np_array("results/depth_raw.png")

    # # Calculate disparity from read depth
    # read_disp = calculate_disp_from_depth(read_depth, F, BASELINE, 0)

    # # Plot read disparity
    # matplotlib.pyplot.imshow(read_disp)
    # plt.show()

    # Plot read disparity
    # matplotlib.pyplot.imshow(read_disp)
    # plt.show()