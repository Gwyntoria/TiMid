# coding: utf-8

#######################################
# OCR game UI numbers DEMO - By Shawn Lin
# TODO: the return value should be float or Int
#
# import the necessary packages
from TBJ_Detector import *
import argparse
import glob as gb
import time
import logging

logger = logging.getLogger("TBJ_Detection_Demo")
logger.setLevel(level=logging.DEBUG)
handler = logging.FileHandler("TBJ_Detection_Demo.log")
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# Get the Arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", type=str,
                help="path to input image to be OCR'd")
ap.add_argument("-f", "--folder", type=str,
                help="Demo loop all through the folder")
ap.add_argument("-d", "--debug", type=bool, default=False,
                help="Demo loop all through the folder")
ap.add_argument("-t", "--machine_type", type=int, default=0,
                help="Demo loop all through the folder")


args = vars(ap.parse_args())

# Read the Argument
myTBJDetector = TBJDetector(args["machine_type"], args["debug"])

if args["folder"] is not None and args["folder"].strip() != '':
    # 获取numbers文件夹下所有文件路径
    folderName = args["folder"] + "/*"
    print(folderName)
    img_path = gb.glob(args["folder"]+"/*")

    # 文件名排序，方便查看
    img_path.sort()

    for path in img_path:
        print("Processing", path)
        logger.debug("Processing: " + path)
        TBJ_type = myTBJDetector.detect_type(path)
        print("The TBJ type is:" + str(TBJ_type))
        logger.debug("The TBJ type is:" + str(TBJ_type))
        if TBJ_type in Interval(1, 11) or TBJ_type == 70 or TBJ_type == 80:
            print('type name: ' + TBJ_TYPE[TBJ_type])
            logger.debug('type name: ' + TBJ_TYPE[TBJ_type])
        key = cv2.waitKey(1000)
        if TBJ_type in Interval(1, 4):
            coins_dict = myTBJDetector.get_gain_coins(path, True)
            print('Bonus coins_dict: ' + str(coins_dict))
            logger.debug('Bonus coins_dict: ' + str(coins_dict))
        elif TBJ_type == 70 or TBJ_type == 80 or TBJ_type == 9:
            coins_dict = myTBJDetector.get_gain_coins(path, False)
            print('coins_dict: ' + str(coins_dict))
            logger.debug('coins_dict: ' + str(coins_dict))
        elif TBJ_type == 5:
            error_code = myTBJDetector.get_error_code(path)
            t2 = time.time() * 1000
            print('error_code: ' + str(error_code))
            logger.debug('error_code: ' + str(error_code))
        print('----------------')
        logger.debug('----------------')
        key = cv2.waitKey(2000)
else:
    print("image Processing", args["image"])
    logger.debug("image Processing: " + args["image"])

    if myTBJDetector.check_congrats_status(args["image"]) == 90:
        print("The TBJ is Congrats")

    t1 = time.time()*1000
    TBJ_type = myTBJDetector.detect_type(args["image"])
    t2 = time.time()*1000
    print("The TBJ type is:" + str(TBJ_type) + ' Detection duration: ' + str(t2-t1) + ' ms')
    logger.debug("The TBJ type is:" + str(TBJ_type) + ' Detection duration: ' + str(t2-t1) + ' ms')
    if TBJ_type in Interval(1, 11) or TBJ_type == 70 or TBJ_type == 80:
        print('type name: ' + TBJ_TYPE[TBJ_type])
        logger.debug('type name: ' + TBJ_TYPE[TBJ_type])

    key = cv2.waitKey(2000)

    total_score = myTBJDetector.get_total_score(args["image"])
    print('total_score: ' + str(total_score))

    t1 = time.time() * 1000

    if TBJ_type in Interval(1, 4):
        coins_dict = myTBJDetector.get_gain_coins(args["image"], True)
        t2 = time.time() * 1000
        print('Bonus coins_dict: ' + str(coins_dict) + ' Detection duration: ' + str(t2-t1) + ' ms')
        logger.debug('Bonus coins_dict: ' + str(coins_dict) + ' Detection duration: ' + str(t2-t1) + ' ms')
    elif TBJ_type == 70 or TBJ_type == 80 or TBJ_type == 9:
        coins_dict = myTBJDetector.get_gain_coins(args["image"], False)
        t2 = time.time() * 1000
        print('coins_dict: ' + str(coins_dict) + ' Detection duration: ' + str(t2-t1) + ' ms')
        logger.debug('coins_dict: ' + str(coins_dict) + ' Detection duration: ' + str(t2-t1) + ' ms')
    elif TBJ_type == 5:
        error_code = 21
        if args["machine_type"] == 0 or args["machine_type"] == 1 or args["machine_type"] == 2:
            error_code = myTBJDetector.get_error_code(args["image"])
        t2 = time.time() * 1000
        print('error_code: ' + str(error_code) + ' Detection duration: ' + str(t2 - t1) + ' ms')
        logger.debug('error_code: ' + str(error_code) + ' Detection duration: ' + str(t2 - t1) + ' ms')
