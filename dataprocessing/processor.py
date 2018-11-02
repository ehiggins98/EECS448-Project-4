import line_processor as lp
import cv2 as cv
import math
import numpy as np
from os import listdir
from os.path import isfile, join
import re

page1 = [
 '!', ')', '"', '*', '#', '+', '$', '-', '%', '.', '&', '/', '\'', ':', '(', ';'
]

page2 = [
    '<', '^', '=', '_', '>', '`', '?', '{', '@', '}', '[', '|', '\\', '~', ']', ','
]

classes = {
    ':': 62,
    ';': 63,
    '<': 64,
    '=': 65,
    '>': 66,
    '?': 67,
    '!': 68,
    '"': 69,
    '%': 70,
    '&': 71,
    '\'': 72,
    '(': 73,
    ')': 74,
    '*': 75,
    '+': 76,
    ',': 77,
    '-': 78,
    '.': 79,
    '/': 80,
    '[': 81,
    ']': 82,
    '^': 83,
    '{': 84,
    '|': 85,
    '}': 86,
    '#': 87,
    '$': 88,
    '_': 89,
    '`': 90,
    '@': 91,
    '\\': 92,
    '~': 93
}

def angle(line):
    return math.atan((line[1][1] - line[0][1]) / (line[1][0] - line[0][0]))

def add_to_sorted_list(list, line, direction):
    dimension = 1 if direction == 'horizontal' else 0
    i = 0
    while i < len(list) and list[i][0][dimension] < line[0][dimension]:
        i += 1

    list.insert(i, line)

def process_image_step_1(img):
    orig = np.copy(img)
    img = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    img = cv.inRange(img, (0.0, 0.0, 0.0),  (180.0, 255.0, 117.2))
    img = cv.GaussianBlur(img, (0, 0), 1)
    im2, contours, hierarchy = cv.findContours(img, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    bound_x, bound_y, bound_w, bound_h = cv.boundingRect(contours[0])

    for c in contours:
        x, y, w, h = cv.boundingRect(c)
        if bound_x > x:
            w = bound_w + bound_x - x
            bound_x = x
        if bound_x + bound_w < x + w:
             bound_w = x + w - bound_x
        if bound_y > y:
             h = bound_h + bound_y - y
             bound_y = y
        if bound_y + bound_h < y + h:
             bound_h = y + h - bound_y

    return img, (bound_x-2, bound_y-2, bound_w+2, bound_h+2)

def process_image_step_2(img, size, original_bounds):
    x, y, w, h = original_bounds;
    img = img[y:y+h, x:x+w]
    dim = max(int(size), 32)
    if dim % 2 == 1:
        dim += 1
    center = (int(np.size(img, axis=0)/2), int(np.size(img, axis=1)/2))
    square = np.zeros((size, size))

    for i in range(0, np.size(img, axis=0)):
        for j in range(0, np.size(img, axis=1)):
            square[math.floor(dim / 2 - center[0]) + i - 1, math.floor(dim / 2 - center[1]) + j - 1] = img[i, j]
    square = cv.resize(square, (32, 32), interpolation=cv.INTER_CUBIC)

    return square

def get_label(row, col, configuration):
    if configuration == 1:
        label = classes[page1[2*(row-1) + (col > 3)]]
    elif configuration == 2:
        label = classes[page2[2*(row-1) + (col > 3)]]
    return label

def crop_data(file, configuration):
    images = np.zeros((0, 32, 32))
    labels = np.zeros((0))
    lines = lp.process_lines(file)
    angle_threshold = 0.1
    img = cv.imread(file)
    vertical = []
    horizontal = []
    min_y = 1000
    argmin_y = 0
    max_dim = 0
    bounding_boxes = []
    for l in lines:
        if lp.lineMagnitude(l[0][0], l[0][1], l[1][0], l[1][1]) > 400:
            if l[0][1] < min_y and l[1][1] < min_y:
                min_y = min(l[0][1], l[1][1])
                argmin_y = l
            add_to_sorted_list(horizontal, l, 'horizontal') if abs(angle(l) - 0) < angle_threshold else add_to_sorted_list(vertical, l, 'vertical')
    count = 0

    if len(horizontal) != 10 or len(vertical) != 6:
        print("Incorrect number of lines detected in", file)
        print("Skipping; data would likely be incorrect")
        return

    for i in range(1, len(vertical)-1):
        if i != 3:
            left_line = vertical[i]
            right_line = vertical[i+1]
            for j in range(0, len(horizontal) - 1):
                if horizontal[j][0][1] != argmin_y[0][1] or horizontal[j][1][1] != argmin_y[1][1]:
                    count += 1
                    top_line = horizontal[j]
                    bottom_line = horizontal[j+1]
                    cropped = img[top_line[0][1]+25:bottom_line[0][1]-25, left_line[0][0]+25:right_line[0][0]-25]
                    cropped, box = process_image_step_1(cropped)
                    bounding_boxes.append((cropped, box, get_label(j, i, configuration)))
                    if max(box[2], box[3]) > max_dim:
                        max_dim = max(box[2], box[3])

    for i in range(0, len(bounding_boxes)):
        img = process_image_step_2(bounding_boxes[i][0], max_dim, bounding_boxes[i][1])
        img = np.reshape(img, (1, 32, 32))
        images = np.append(images, img, axis=0)
        labels = np.append(labels, bounding_boxes[i][2])

    return images, labels

image_files = [f for f in listdir('.') if isfile(join('.', f)) and re.compile('.+\.(JPG|jpg)$').match(f)]
all_images = np.zeros((0, 32, 32))
all_labels = np.zeros((0))
for file in image_files:
    images, labels = crop_data(file, 1)
    all_images = np.append(all_images, images, axis=0)
    all_labels = np.append(all_labels, labels, axis=0)

np.save('images.npy', all_images)
np.save('labels.npy', all_labels)
