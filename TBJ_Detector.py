# coding: utf-8

# Version 1.0.0.1	Details in TBJ_Update.log
# support python2 & python3

"""
JP智能AI特征检测算法流程:

  0.  NORMAL - 只有“出局”图片
  0.  连线奖 - “出局”图片  + “获得”图片 + 2项数字 （必须同时具备）
  0.  小玛丽 - “OUT”图片1个以上 + “获得”图片 + 2项数字
  0.  叠叠乐 - “枚数”图片 + “获得”图片 + 2项数字
  0.  JP1, JP2, JP3, ALL - “JP”图片 + 2项数字
  0.  ERROR - “小丑”图片

其中只有特征图片存在的情况下, 进行数字检测; 2行数字 0-9999最大, 数字小偏移要忽略, 返回GAIN数字, LEFT数字
"""

import cv2 as cv2
import numpy as np
import os
import logging
from interval import Interval

logger = logging.getLogger("TBJ_Main")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%d %b %Y %H:%M:%S",
)

withError = True
withDebug = True


def loge(msg):
    if withError:
        logger.error(msg)


def logd(msg):
    if withDebug:
        logger.debug(msg)


DETECT_THRESHOLD = [0.7, 0.7, 0.8]

DETECT_RECTS = {
    0: {
        "ERROR_RECT": [175, 310, 515, 640],
        "ERROR_NUMBER_RECT": [225, 255, 35, 70],
        "CHUJU_RECT": [235, 260, 545, 595],
        "HUODE_RECT": [145, 203, 75, 195],
        "BONUS_RECT": [70, 145, 340, 525],
        "MEISHU_RECT": [315, 337, 545, 598],
        "NUM1_RECT": [135, 205, 210, 470],
        "NUM2_RECT": [218, 284, 210, 470],
        "BONUS_NUM1_RECT": [155, 223, 265, 540],
        "BONUS_NUM2_RECT": [235, 300, 265, 540],
        "OUT1_RECT": [75, 110, 30, 95],
        "OUT2_RECT": [75, 110, 435, 500],
        "OUT3_RECT": [325, 360, 30, 95],
        "OUT4_RECT": [325, 360, 435, 500],
        "SPLASH_RECT": [0, 480, 35, 130],
        "TOTAL_SCORE_RECT": [112, 133, 524, 618],
    },
    1: {
        "ERROR_RECT": [205, 265, 0, 65],
        "ERROR_NUMBER_RECT": [220, 252, 110, 160],
        "CHUJU_RECT": [215, 235, 560, 605],
        "HUODE_RECT": [150, 205, 85, 185],
        "BONUS_RECT": [70, 145, 330, 525],
        "MEISHU_RECT": [320, 340, 555, 595],
        "NUM1_RECT": [145, 200, 205, 460],
        "NUM2_RECT": [220, 280, 205, 460],
        "BONUS_NUM1_RECT": [160, 220, 260, 530],
        "BONUS_NUM2_RECT": [235, 295, 260, 530],
        "OUT1_RECT": [75, 110, 33, 95],
        "OUT2_RECT": [75, 110, 440, 500],
        "OUT3_RECT": [328, 360, 33, 95],
        "OUT4_RECT": [328, 360, 440, 500],
        "SPLASH_RECT": [0, 480, 0, 210],
        "CONGRATS_RECT": [0, 45, 240, 400],
        "TOTAL_SCORE_RECT": [88, 110, 533, 628],
    },
    2: {"ERROR_RECT": [135, 235, 250, 315], "ERROR_NUMBER_RECT": [297, 314, 160, 184]},
}

TBJ_TYPE = {
    1: "JP1",
    2: "JP2",
    3: "JP3",
    4: "ALL",  # 全盘奖
    5: "Error",
    6: "Normal",
    7: "DDL",  # 叠叠乐
    8: "XML",  # 小玛莉
    9: "LXJ",  # 连线奖
    11: "Splash",
    70: "DDL",  # 叠叠乐（操作中）
    80: "XML",  # 小玛莉（操作中）
    90: "Congrats",
}

MATERIAL_FOLDER = {
    0: "TBJ_Material",  # 超级马戏团的素材目录
    1: "MSS_Material",  # 超级魔术师的素材目录
    2: "HLMXT_Material",  # 欢乐马戏团的素材目录
}

NUM_WIDTH = {0: [49, 22, 38, 34, 38, 30, 42, 36, 35, 40], 1: [30, 22, 30, 28, 36, 24, 28, 24, 28, 30]}

path = os.path.dirname(os.path.realpath(__file__))
logging.debug("OCR path: " + path)
print("OCR path: " + path)


class TBJDetector:
    def __init__(self, machine_type=0, debug=False):
        # Initial the default game, because of reference is different
        try:
            # Setup debug mode
            self.debug_mode = debug
            self.machine_type = machine_type

            if machine_type == 2:
                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Error1.png")
                self.error_image1 = cv2.imread(image_path)
                cv2.imwrite("error_image1.png", self.error_image1)
                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Error2.png")
                self.error_image2 = cv2.imread(image_path)
                cv2.imwrite("error_image2.png", self.error_image2)
                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "ErrorNumbers.png")
                self.error_numbers_image = cv2.imread(image_path)
            else:
                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "chuju.png")
                self.chuju_image = cv2.imread(image_path)
                # print image_path
                # cv2.imwrite("chuju_image.png", self.chuju_image)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "huode.png")
                self.huode_image = cv2.imread(image_path)
                # cv2.imwrite("huode_image.png", self.huode_image)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Numbers.png")
                self.numbers_image = cv2.imread(image_path)
                # cv2.imwrite("number.png", self.numbers_image)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "meishu.png")
                self.meishu_image = cv2.imread(image_path)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Error.png")
                self.error_image = cv2.imread(image_path)
                # cv2.imwrite("error_image.png", self.error_image)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "ErrorNumbers.png")
                self.error_numbers_image = cv2.imread(image_path)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Bonus.png")
                self.bonus_image = cv2.imread(image_path)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Out.png")
                self.out_image = cv2.imread(image_path)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Splash.png")
                self.splash_image = cv2.imread(image_path)

                image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "TotalScore.png")
                self.total_score_image = cv2.imread(image_path)

                if self.machine_type == 1:
                    image_path = os.path.join(path, MATERIAL_FOLDER[self.machine_type], "Congrats.png")
                    self.bonus_congrats_image = cv2.imread(image_path)

        except ():
            print("--- Error to initial ---")
            raise

    def check_congrats_status(self, detect_image_file):
        try:
            if self.machine_type != 1:
                return -3

            source_image = cv2.imread(detect_image_file, 1)
            height, width = source_image.shape[:2]
            if width != 640 or height != 480:
                logd("check_congrats_status -2")
                return -2

            crop_rect = DETECT_RECTS[self.machine_type]["CONGRATS_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.ocr_template(crop_image, self.bonus_congrats_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("bonus_congrats_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("error_image.png", crop_image)

                return 90
            return -1
        except ():
            print(" --- Error ---")
            logd("check_congrats_status Error")
            return -1

    def get_total_score(self, detect_image_file):
        try:
            source_image = cv2.imread(detect_image_file, 1)
            height, width = source_image.shape[:2]
            if width != 640 or height != 480:
                return -2

            if self.machine_type == 2:
                return -3
            else:
                crop_rect = DETECT_RECTS[self.machine_type]["TOTAL_SCORE_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.debug_mode:
                    cv2.imshow("total_score_image", crop_image)
                    cv2.waitKey(2000)
                    cv2.imwrite("total_score_image.png", crop_image)

                total_score = self.ocr_template(crop_image, self.total_score_image, 10, 0, 2)

                return total_score
        except ():
            print(" --- Error ---")
            return -1

    def get_gain_coins(self, detect_image_file, is_bonus):
        try:
            source_image = cv2.imread(detect_image_file, 1)
            height, width = source_image.shape[:2]
            if width != 640 or height != 480:
                return -2

            if is_bonus is True:
                crop_rect = DETECT_RECTS[self.machine_type]["BONUS_NUM1_RECT"]
            else:
                crop_rect = DETECT_RECTS[self.machine_type]["NUM1_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]

            # Testing only...
            if self.debug_mode:
                cv2.imshow("gain_image", crop_image)
                cv2.waitKey(2000)
                # cv2.imwrite("gain_coins.png", crop_image)

            gain_coins = self.ocr_template(crop_image, self.numbers_image, 10, 0, 1)

            if is_bonus is True:
                crop_rect = DETECT_RECTS[self.machine_type]["BONUS_NUM2_RECT"]
            else:
                crop_rect = DETECT_RECTS[self.machine_type]["NUM2_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]

            # Testing only...
            if self.debug_mode:
                cv2.imshow("left_image", crop_image)
                cv2.waitKey(2000)
                cv2.imwrite("left_coins.png", crop_image)

            left_coins = self.ocr_template(crop_image, self.numbers_image, 10, 0, 1)

            return {"gain_coins": gain_coins, "left_coins": left_coins}

        except ():
            print(" --- Error ---")
            return -1

    def get_error_code(self, detect_image_file):
        try:
            source_image = cv2.imread(detect_image_file, 1)
            height, width = source_image.shape[:2]
            if width != 640 or height != 480:
                return -2

            crop_rect = DETECT_RECTS[self.machine_type]["ERROR_NUMBER_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.machine_type == 2:
                error_code = self.ocr_template(crop_image, self.error_numbers_image, 11, 0)
            else:
                error_code = self.ocr_template(crop_image, self.error_numbers_image, 10, 0)
            if error_code >= 0:
                if self.debug_mode:
                    cv2.imshow("error_number_image", crop_image)
                    cv2.waitKey(2000)
                    cv2.imwrite("error_image.png", crop_image)

                return error_code
            return -1
        except ():
            print(" --- Error ---")
            return -1

    def detect_type(self, detect_image_file):
        try:
            source_image = cv2.imread(detect_image_file, 1)
            height, width = source_image.shape[:2]
            if width != 640 or height != 480:
                return -2

            if self.machine_type == 2:
                crop_rect = DETECT_RECTS[self.machine_type]["ERROR_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.ocr_template(crop_image, self.error_image1, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("error_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("error_image.png", crop_image)
                    return 5
                elif self.ocr_template(crop_image, self.error_image2, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("error_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("error_image.png", crop_image)
                    return 5
                else:
                    return 6

            crop_rect = DETECT_RECTS[self.machine_type]["SPLASH_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.debug_mode:
                cv2.imshow("splash_image", crop_image)
                cv2.waitKey(2000)
                cv2.imwrite("splash_image.png", crop_image)

            if self.ocr_template(crop_image, self.splash_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("splash_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("splash_image.png", crop_image)
                return 11

            crop_rect = DETECT_RECTS[self.machine_type]["CHUJU_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.debug_mode:
                cv2.imshow("chuju_image", crop_image)
                cv2.waitKey(2000)
                # cv2.imwrite("chuju.png", crop_image)
            if self.ocr_template(crop_image, self.chuju_image, 1) == 0:
                # Testing only...
                if self.debug_mode:
                    cv2.imshow("chuju_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("chuju.png", crop_image)

                crop_rect = DETECT_RECTS[self.machine_type]["HUODE_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.ocr_template(crop_image, self.huode_image, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("huode_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("huode_normal.png", crop_image)
                    return 9
                else:
                    return 6

            crop_rect = DETECT_RECTS[self.machine_type]["ERROR_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.ocr_template(crop_image, self.error_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("error_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("error_image.png", crop_image)
                return 5

            crop_rect = DETECT_RECTS[self.machine_type]["MEISHU_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.ocr_template(crop_image, self.meishu_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("meishu_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("meishu_image.png", crop_image)
                crop_rect = DETECT_RECTS[self.machine_type]["HUODE_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.ocr_template(crop_image, self.huode_image, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("huode_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("huode_normal.png", crop_image)
                    return 70
                else:
                    return 7

            crop_rect = DETECT_RECTS[self.machine_type]["BONUS_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            value = self.ocr_template(crop_image, self.bonus_image, 4)
            if value in Interval(0, 3):
                if self.debug_mode:
                    cv2.imshow("bonus_image", crop_image)
                    cv2.waitKey(2000)
                    cv2.imwrite("bonus_image.png", crop_image)
                return value + 1

            crop_rect = DETECT_RECTS[self.machine_type]["OUT1_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.ocr_template(crop_image, self.out_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("out_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("out_image1.png", crop_image)
                crop_rect = DETECT_RECTS[self.machine_type]["HUODE_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.ocr_template(crop_image, self.huode_image, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("huode_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("huode_normal.png", crop_image)
                    return 80
                else:
                    return 8

            crop_rect = DETECT_RECTS[self.machine_type]["OUT2_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.ocr_template(crop_image, self.out_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("out_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("out_image2.png", crop_image)
                crop_rect = DETECT_RECTS[self.machine_type]["HUODE_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.ocr_template(crop_image, self.huode_image, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("huode_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("huode_normal.png", crop_image)
                    return 80
                else:
                    return 8

            crop_rect = DETECT_RECTS[self.machine_type]["OUT3_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.ocr_template(crop_image, self.out_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("out_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("out_image3.png", crop_image)
                crop_rect = DETECT_RECTS[self.machine_type]["HUODE_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.ocr_template(crop_image, self.huode_image, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("huode_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("huode_normal.png", crop_image)
                    return 80
                else:
                    return 8

            crop_rect = DETECT_RECTS[self.machine_type]["OUT4_RECT"]
            crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
            if self.ocr_template(crop_image, self.out_image, 1) == 0:
                if self.debug_mode:
                    cv2.imshow("out_image", crop_image)
                    cv2.waitKey(2000)
                    # cv2.imwrite("out_image4.png", crop_image)
                crop_rect = DETECT_RECTS[self.machine_type]["HUODE_RECT"]
                crop_image = source_image[crop_rect[0] : crop_rect[1], crop_rect[2] : crop_rect[3]]
                if self.ocr_template(crop_image, self.huode_image, 1) == 0:
                    if self.debug_mode:
                        cv2.imshow("huode_image", crop_image)
                        cv2.waitKey(2000)
                        # cv2.imwrite("huode_normal.png", crop_image)
                    return 80
                else:
                    return 8

            return -1

        except (ValueError, TypeError):
            print(" --- Error ---")
            return -1

    # OCR with template matching technology ...Internal USE
    def ocr_template(self, source_image, template_image, divide_num, is_type=1, is_score=0):
        try:
            # 需要选出4个模版中的一部分，座位模式匹配的图片
            template_height, template_width = template_image.shape[:2]
            cell_height = template_height
            cell_width = template_width / divide_num
            cell_x = 0

            # Get the ref big photo
            crop_reference = template_image

            # 开始搜索
            location_data = []
            for i in range(0, divide_num):
                # 进行模式匹配
                if divide_num == 10 and is_score == 1:
                    cell_width = NUM_WIDTH[self.machine_type][i]
                cell_reference = crop_reference[0 : int(cell_height), int(cell_x) : int(cell_x + cell_width)]
                cell_x = cell_x + cell_width
                # if self.debug_mode:
                #     cv2.imshow('cell_reference', cell_reference)
                #     cv2.waitKey(2000)
                res = cv2.matchTemplate(source_image, cell_reference, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= DETECT_THRESHOLD[self.machine_type])

                # 可能会有多个数字检测出来
                for pt in zip(*loc[::-1]):
                    if divide_num == 11:
                        if i == 0 or i == 1:
                            location_data.append((pt[0], str(i), res[pt[1], pt[0]]))
                        else:
                            location_data.append((pt[0], str(i - 1), res[pt[1], pt[0]]))
                    else:
                        location_data.append((pt[0], str(i), res[pt[1], pt[0]]))

            # 我们得到的信息中，有重复的，也有假的；判别的方法是：相邻的数字里面，取匹配度最好
            group_data = []

            # 假如无法找到任何一个，说明图像没有任何数字
            if len(location_data) == 0:
                return -1

            # List需要排序
            location_data = sorted(location_data, key=lambda x: x[0])
            pre_data = location_data[0]

            # Testing ...
            if self.debug_mode:
                print(location_data)
            # 循环比对，找出最正确的一个数字
            offset = 5
            if is_type == 0:
                if is_score == 1:
                    if self.machine_type == 0:
                        offset = 30
                    elif self.machine_type == 1:
                        offset = 25
                    elif self.machine_type == 2:
                        offset = 10
                elif is_score == 2:
                    if self.machine_type == 0:
                        offset = 14
                    elif self.machine_type == 1:
                        offset = 13
                else:
                    if self.machine_type == 0:
                        offset = 10
                    elif self.machine_type == 1:
                        offset = 15

            for i in range(1, len(location_data)):
                if (location_data[i][0] - pre_data[0]) < offset:
                    if location_data[i][2] > pre_data[2]:
                        pre_data = location_data[i]
                else:
                    group_data.append(pre_data)
                    pre_data = location_data[i]

            # 添加最后一个数字
            group_data.append(pre_data)

            # Testing only ...
            if self.debug_mode:
                print("Before sorted", group_data)
            # List需要排序
            group_data = sorted(group_data, key=lambda x: x[0])

            # Testing only ...
            if self.debug_mode:
                print("After sorted:", group_data)

            # List 转换成 Array，以便于输出
            num_data = np.array(group_data)

            if is_type == 1:
                result = int(num_data[0][1])
                return result

            # 合并文本
            text = "{}".format("".join(num_data[:, 1]))
            result = int(float(text))
            # It's for the result value
            return result

        except (ValueError, TypeError):
            print(" --- Error use Template Matching OCR Engine ---")
            return -1
