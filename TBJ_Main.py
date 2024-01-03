# coding: utf-8

# Version 1.0.0.1	Details in TBJ_Update.log


from re import S
import time
import threading
import configparser
from multiprocessing import Manager, process
import random
import glob as gb
import logging
import os

from interval import Interval
import cv2 as cv2

# from TBJ_Detector import *
import TBJ_API
import TBJ_Coins
from TBJ_Communication import TbjSerialCommunication
from TBJ_Communication import TBJ_TYPE

logger = logging.getLogger("TBJ_Main")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%d %b %Y %H:%M:%S",
)

room_info = {}

in_detection_thread = False
detect_thread = 0

# process_dict = None

my_tbj_detector = None
# tbj_communication = None
last_check_image = ""
last_tbj_type = 0
last_tbj_coins_dict = {}
last_total_score = 0
drop_error_begin_time = 0
no_signal_count = 0
is_jp_type = False
is_bonus_type = False

# cap = None
# is_congrats = False

# rtscap = None

is_test = 0
test_begin_time = 0
is_save_jp = 0


"""实例化&初始化
rtscap = RTSCapture.create("rtsp://example.com/live/1")
or
rtscap = RTSCapture.create("http://example.com/live/1.m3u8", "http://")
"""


class RTSCapture(cv2.VideoCapture):
    """
    获取视频帧
    """

    _instance = None
    _lock = threading.Lock()

    # _cur_frame = None
    # _reading = False
    # frame_receiver = None

    def __new__(cls):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._cur_frame = None
                cls._instance._reading = False
                cls._instance.frame_receiver = None
            return cls._instance

    # @staticmethod
    # def create(url):
    #     global rtscap

    #     rtscap = RTSCapture(url)
    #     rtscap.frame_receiver = threading.Thread(target=rtscap.recv_frame, daemon=True)
    #     rtscap._reading = True
    #     return rtscap

    def is_started(self):
        """替代 VideoCapture.isOpened()"""
        ok = self.isOpened()
        if ok and self._reading:
            ok = self.frame_receiver.is_alive()
        return ok

    def recv_frame(self):
        """子线程读取最新视频帧方法"""
        while self._reading and self.isOpened():
            ok, frame = self.read()
            if not ok:
                break
            self._cur_frame = frame
        self._reading = False

    def read2(self):
        """读取最新视频帧 返回结果格式与 VideoCapture.read() 一样"""
        frame = self._cur_frame
        self._cur_frame = None
        return frame is not None, frame

    def start_read(self):
        """启动子线程读取视频帧"""
        if not self._reading:
            self._reading = True
            self.frame_receiver = threading.Thread(target=rtscap.recv_frame, daemon=True)
            self.frame_receiver.start()

    def stop_read(self):
        """退出子线程方法"""
        if self._reading:
            self._reading = False
            if self.frame_receiver.is_alive():
                self.frame_receiver.join()


def get_video_frame():
    global rtscap

    save_frame_path = "/home/pi/wawaji/ScreenShot_Image/"
    if os.path.exists(save_frame_path) is False:
        os.makedirs(save_frame_path)

    try:
        t = time.time()
        time_array = time.localtime(t)
        other_style_time = time.strftime("%Y-%m-%d-%H-%M-%S", time_array)
        image_path = (
            "/home/pi/wawaji/ScreenShot_Image/" + room_info["name"] + "-AI-" + other_style_time + ".jpg"
        )

        if rtscap.is_started():
            ok, frame = rtscap.read2()
            if ok is True:
                cv2.imwrite(image_path, frame)
                logger.debug(
                    "TBJ_Main--get_video_frame--image_path: "
                    + image_path
                    + "---download and save image Time: "
                    + str(time.time() - t)
                )
                return image_path
            else:
                ok, frame = rtscap.read()
                if ok is True:
                    cv2.imwrite(image_path, frame)
                    logger.debug(
                        "TBJ_Main--get_video_frame--image_path: "
                        + image_path
                        + "---download and save image Time: "
                        + str(time.time() - t)
                    )
                    return image_path
                else:
                    return None

        # ret, frame = cap.read()
        # if ret is True:
        # 	cv2.imwrite(image_path, frame)
        # 	logger.debug('TBJ_Main--get_video_frame--image_path: ' + image_path + '---download and save image Time: ' + str(time.time() - t))
        # 	return image_path
        # else:
        # 	return None
    except:
        logger.debug("TBJ_Main--An Unknown Error")


def check_coins_dict(coins_dict=None):
    if len(coins_dict) > 0:
        if coins_dict["gain_coins"] < coins_dict["left_coins"]:
            process_dict["machine_error"] = True
            process_dict["error_code"] = 0

            # 补偿判断
            if (
                last_tbj_type == 6
                or last_tbj_type in Interval(1, 4)
                or last_tbj_type == 70
                or last_tbj_type == 80
                or last_tbj_type == 9
            ):
                # 在进入错误状态之前为奖励状态，则进入补偿
                process_dict["is_compensation"] = True
                if len(last_tbj_coins_dict) > 0:
                    process_dict["compensation_coins"] = last_tbj_coins_dict["gain_coins"]
                else:
                    process_dict["compensation_coins"] = 0

                logger.debug(
                    "TBJ_Main--tbj_ai_check_job---last_tbj_coins_dict: "
                    + str(last_tbj_coins_dict)
                    + " compensation_coins = "
                    + str(process_dict["compensation_coins"])
                )

            else:
                process_dict["is_compensation"] = False

    else:
        logger.debug("coins_dict content is wrong")


def tbj_ai_check_job():
    global last_check_image
    global last_tbj_type
    global test_begin_time
    global last_tbj_coins_dict
    global last_total_score
    global drop_error_begin_time
    global no_signal_count
    global is_jp_type
    global is_bonus_type
    # global is_congrats

    global tbj_serial_communication

    start_time = int(time.time() * 1000)
    coins_dict = {}
    try:
        # if room_info["encode_type"] == 1:
        #     image_path = get_video_frame()
        # else:
        #     save_frame_path = "/home/pi/wawaji/ScreenShot_Image/"
        #     glob_param = save_frame_path + room_info["name"] + "-AI-*.jpg"
        #     img_paths = gb.glob(glob_param)
        #     img_paths.sort(reverse=True)

        #     if len(img_paths) <= 0:
        #         return
        #     image_path = img_paths[0]

        # if image_path is None or len(image_path) <= 0:
        #     logger.debug("TBJ_Main--No Image File")
        #     process_dict["total_score"] = 0
        #     return

        # c_time = int(os.path.getctime(image_path))
        # now_time = int(time.time())
        # logger.debug("TBJ_Main--tbj_ai_check_job--create time: " + str(c_time) + " now_time: " + str(now_time))

        # if my_tbj_detector is not None and last_check_image != image_path and c_time > (now_time - 5):
        if tbj_serial_communication is not None:
            # if is_test == 1 and test_begin_time == 0:
            #     test_begin_time = time.time()
            #     logger.debug("TBJ_Main--tbj_ai_check_job---Test begin time: " + str(int(test_begin_time)))

            # last_check_image = image_path
            # logger.debug("TBJ_Main--last_check_image: " + last_check_image)

            # if my_tbj_detector.check_congrats_status(last_check_image) == 90:
            # 	if is_congrats is False:
            # 		is_congrats = True
            # 		logger.debug("TBJ_Main--tbj_ai_check_job--is_congrats = True")
            # 		congrats_file_path = '/home/pi/wawaji/Congrats_Image/'
            # 		if os.path.exists(congrats_file_path) is False:
            # 			os.makedirs(congrats_file_path)
            # 		time_array = time.localtime(time.time())
            # 		other_style_time = time.strftime("%Y-%m-%d-%H-%M-%S", time_array)
            # 		image_name = room_info['name'] + "-" + other_style_time + ".jpg"
            # 		image_path = os.path.join(congrats_file_path, image_name)
            # 		command = "sudo cp " + last_check_image + " " + image_path
            # 		os.system(command)
            # 		logger.debug("TBJ_Main--tbj_ai_check_job--Congrats File: " + command)
            # else:
            # 	if is_congrats is True:
            # 		is_congrats = False
            # 		logger.debug("TBJ_Main--tbj_ai_check_job--is_congrats = False")

            t1 = time.time() * 1000
            # tbj_type = my_tbj_detector.detect_type(last_check_image)
            tbj_type = tbj_serial_communication.get_tbj_type()
            t2 = time.time() * 1000

            logger.debug(
                "TBJ_Main--tbj_ai_check_job---The TBJ type is:"
                + str(tbj_type)
                + " Detection duration: "
                + str(t2 - t1)
                + " ms"
            )

            # 获取屏幕右上角的总分
            # total_score = my_tbj_detector.get_total_score(last_check_image)
            # total_score = tbj_serial_communication.get_total_score()
            # process_dict["total_score"] = total_score
            # logger.debug("TBJ_Main--tbj_ai_check_job--get_total_score: " + str(total_score))

            # 图片尺寸错误（reserved）
            if tbj_type == -2:
                process_dict["encode_machine_error"] = 1

            # 串口数据解析错误
            elif tbj_type == -1:
                # error_type_file_path = "/home/pi/wawaji/AI_ERROR_Image/"
                # if os.path.exists(error_type_file_path) is False:
                #     os.makedirs(error_type_file_path)
                # time_array = time.localtime(time.time())
                # other_style_time = time.strftime("%Y-%m-%d-%H-%M-%S", time_array)
                # image_name = room_info["name"] + "-AI-Check-1-" + other_style_time + ".jpg"
                # image_path = os.path.join(error_type_file_path, image_name)
                # command = "sudo cp " + last_check_image + " " + image_path
                # os.system(command)
                # logger.debug("TBJ_Main--tbj_ai_check_job--Detect -1: " + command)

                logger.debug("TBJ_Main--tbj_ai_check_job--Detect -1: tbj_serial_communication error")

            # deal with the tbj_type
            if tbj_type in Interval(1, 11) or tbj_type == 70 or tbj_type == 80:
                logger.debug("TBJ_Main--tbj_ai_check_job---type name: " + TBJ_TYPE[tbj_type])

                # 进入到 JP1, JP2, JP3, ALL, 叠叠乐（状态中）, 小玛莉（状态中）
                if (
                    tbj_type in Interval(1, 4) or tbj_type == 70 or tbj_type == 80
                ) and tbj_type != last_tbj_type:
                    process_dict["need_count_coins"] = True
                    process_dict["total_coins"] = 0

                # error
                if tbj_type == 5 and last_tbj_type != 5 and last_tbj_type != 0:
                    # error_type_file_path = "/home/pi/wawaji/AI_ERROR_Image/"
                    # if os.path.exists(error_type_file_path) is False:
                    #     os.makedirs(error_type_file_path)
                    # time_array = time.localtime(time.time())
                    # other_style_time = time.strftime("%Y-%m-%d-%H-%M-%S", time_array)
                    # image_name = room_info["name"] + "-AI-Error-" + other_style_time + ".jpg"
                    # image_path = os.path.join(error_type_file_path, image_name)
                    # command = "sudo cp " + last_check_image + " " + image_path
                    # os.system(command)

                    error_code = 21
                    if (
                        room_info["machine_type"] == 0
                        or room_info["machine_type"] == 1
                        or room_info["machine_type"] == 2
                    ):
                        # error_code = my_tbj_detector.get_error_code(last_check_image)
                        error_code = tbj_serial_communication.get_error_code()
                        logger.debug("TBJ_Main--tbj_ai_check_job---Error Code: " + str(error_code))
                        # 死机
                        if error_code == 0xFF:
                            process_dict["machine_stuck"] = True

                    process_dict["machine_error"] = True
                    process_dict["error_code"] = error_code

                    # 补偿判断
                    if (
                        last_tbj_type == 6
                        or last_tbj_type in Interval(1, 4)
                        or last_tbj_type == 70
                        or last_tbj_type == 80
                        or last_tbj_type == 9
                    ):
                        # 在进入错误状态之前为奖励状态，则进入补偿
                        process_dict["is_compensation"] = True
                        if len(last_tbj_coins_dict) > 0:
                            # 补偿币数量为先前得奖后剩余的币数量
                            process_dict["compensation_coins"] = last_tbj_coins_dict["left_coins"]
                        else:
                            process_dict["compensation_coins"] = 0

                        logger.debug(
                            "TBJ_Main--tbj_ai_check_job---last_tbj_coins_dict: "
                            + str(last_tbj_coins_dict)
                            + " compensation_coins = "
                            + str(process_dict["compensation_coins"])
                        )

                    else:
                        process_dict["is_compensation"] = False

                # unknown type
                elif tbj_type == 10 and (last_tbj_type != 10 or no_signal_count < 10):
                    if last_tbj_type != 10:
                        no_signal_count = 1
                    else:
                        no_signal_count += 1

                    if no_signal_count >= 10:
                        process_dict["encode_machine_error"] = 2

                    error_type_file_path = "/home/pi/wawaji/AI_ERROR_Image/"
                    if os.path.exists(error_type_file_path) is False:
                        os.makedirs(error_type_file_path)
                    time_array = time.localtime(time.time())
                    other_style_time = time.strftime("%Y-%m-%d-%H-%M-%S", time_array)
                    image_name = room_info["name"] + "-AI-Check-2-" + other_style_time + ".jpg"
                    image_path = os.path.join(error_type_file_path, image_name)
                    command = "sudo cp " + last_check_image + " " + image_path
                    os.system(command)
                    logger.debug(
                        "TBJ_Main--tbj_ai_check_job--Detect -2: "
                        + command
                        + " no_signal_count: "
                        + str(no_signal_count)
                    )

                # 判断 JP 状态
                if is_jp_type is True and tbj_type != 10 and tbj_type not in Interval(1, 4) and tbj_type != 5:
                    is_jp_type = False

                # 判断奖励状态
                if (
                    is_bonus_type is True
                    and tbj_type != 10
                    and tbj_type != 7
                    and tbj_type != 8
                    and tbj_type != 70
                    and tbj_type != 80
                    and tbj_type != 5
                ):
                    is_bonus_type = False

            t1 = time.time() * 1000

            # JP 奖，全盘奖
            if tbj_type in Interval(1, 4) or (is_test == 1 and time.time() - test_begin_time >= 180):
                current_tbj_type = tbj_type

                if tbj_type in Interval(1, 4):
                    # coins_dict = my_tbj_detector.get_gain_coins(last_check_image, True)
                    coins_dict = tbj_serial_communication.get_gain_coins()
                    t2 = time.time() * 1000
                    logger.debug(
                        "TBJ_Main--tbj_ai_check_job---Bonus coins_dict: "
                        + str(coins_dict)
                        + " Detection duration: "
                        + str(t2 - t1)
                        + " ms"
                    )

                    check_coins_dict(coins_dict)

                if (tbj_type in Interval(1, 4) and is_jp_type is False) or (
                    is_test == 1 and time.time() - test_begin_time >= 180
                ):
                    if is_test == 1:
                        test_begin_time = time.time()
                        logger.debug(
                            "TBJ_Main--tbj_ai_check_job---Test JP time: " + str(int(test_begin_time))
                        )
                        tbj_type = random.randint(1, 6)

                    is_jp_type = True
                    process_dict["jp_detected"] = True
                    process_dict["class_type"] = tbj_type
                    # if is_save_jp == 1:
                    #     jp_file_path = "/home/pi/wawaji/JP_Image/"
                    #     if os.path.exists(jp_file_path) is False:
                    #         os.makedirs(jp_file_path)
                    #     time_array = time.localtime(time.time())
                    #     other_style_time = time.strftime("%Y-%m-%d-%H-%M-%S", time_array)
                    #     image_name = room_info["name"] + "-" + other_style_time + ".jpg"
                    #     image_path = os.path.join(jp_file_path, image_name)
                    #     command = "sudo cp " + last_check_image + " " + image_path
                    #     os.system(command)
                    #     logger.debug("TBJ_Main--tbj_ai_check_job--JP File: " + command)

                if is_test == 1:
                    tbj_type = current_tbj_type

            # 叠叠乐，小玛莉
            elif (tbj_type == 7 or tbj_type == 8) and is_bonus_type is False:
                is_bonus_type = True
                process_dict["jp_detected"] = True

                coins_dict = tbj_serial_communication.get_gain_coins()
                t2 = time.time() * 1000
                logger.debug(
                    "TBJ_Main--tbj_ai_check_job---coins_dict: "
                    + str(coins_dict)
                    + " Detection duration: "
                    + str(t2 - t1)
                    + " ms"
                )

                check_coins_dict(coins_dict)

                if tbj_type == 7:
                    process_dict["class_type"] = 5
                elif tbj_type == 8:
                    process_dict["class_type"] = 6

            # 叠叠乐（状态中），小玛莉（状态中），连线奖
            elif tbj_type == 70 or tbj_type == 80 or tbj_type == 9:
                # coins_dict = my_tbj_detector.get_gain_coins(last_check_image, False)
                coins_dict = tbj_serial_communication.get_gain_coins()
                t2 = time.time() * 1000
                logger.debug(
                    "TBJ_Main--tbj_ai_check_job---coins_dict: "
                    + str(coins_dict)
                    + " Detection duration: "
                    + str(t2 - t1)
                    + " ms"
                )

                check_coins_dict(coins_dict)

            # 判断是否异常出币
            if len(coins_dict) > 0:
                if len(last_tbj_coins_dict) > 0 and last_tbj_type == tbj_type:
                    if (
                        last_tbj_coins_dict["gain_coins"] == coins_dict["gain_coins"]
                        and coins_dict["left_coins"] > last_tbj_coins_dict["left_coins"]
                    ):
                        if drop_error_begin_time == 0:
                            drop_error_begin_time = int(time.time())
                        elif (int(time.time()) - drop_error_begin_time) >= 10:
                            process_dict["drop_error"] = True
                            drop_error_begin_time = 0
                    else:
                        drop_error_begin_time = 0
                else:
                    drop_error_begin_time = 0

                logger.debug(
                    "TBJ_Main--tbj_ai_check_job---coins_dict: "
                    + str(coins_dict)
                    + " last_tbj_coins_dict: "
                    + str(last_tbj_coins_dict)
                    + " tbj_type: "
                    + str(tbj_type)
                    + " last_tbj_type: "
                    + str(last_tbj_type)
                    + " drop_error_begin_time: "
                    + str(drop_error_begin_time)
                )
                if coins_dict["left_coins"] >= 0 and coins_dict["gain_coins"] >= 0:
                    last_tbj_coins_dict = coins_dict

            else:
                if is_jp_type is False:
                    last_tbj_coins_dict = {}
                drop_error_begin_time = 0

            if len(last_tbj_coins_dict) > 0:
                process_dict["left_coins"] = last_tbj_coins_dict["left_coins"]
            else:
                process_dict["left_coins"] = 0

            if process_dict["need_count_coins"] is True and len(coins_dict) <= 0:
                logger.debug(
                    "TBJ_Main--tbj_ai_check_job---user own total coins: " + str(process_dict["total_coins"])
                )
                process_dict["need_count_coins"] = False
                process_dict["total_coins"] = 0

            last_tbj_type = tbj_type
            process_dict["tbj_type"] = tbj_type

            logger.debug(
                "TBJ_Main--tbj_ai_check_job time: " + str(int(time.time() * 1000 - start_time)) + " ms"
            )

    except Exception as e:
        logger.error(f"TBJ_Main--tbj_ai_check_job--failed with exception {type(e).__name__}")


class DetectionThread(threading.Thread):
    def __init__(self):
        # threading.Thread.__init__(self)
        super(DetectionThread, self).__init__()
        self._running = True

    def terminate(self):
        self._running = False

    def run(self):
        global in_detection_thread
        global room_info
        global my_tbj_detector
        global is_jp_type
        global is_test
        global is_save_jp

        global tbj_serial_communication
        global process_dict

        in_detection_thread = True

        if len(process_dict) <= 0:
            print(f"process_dict is empty")
            exit(1)

        while process_dict["is_init_end"] is False:
            continue

        cfg = configparser.RawConfigParser()
        cfg.read("/home/pi/wawaji/WaController/config.ini")

        sub = "room"
        room_info = {
            "token": cfg.get(sub, "token"),
            "name": cfg.get(sub, "name"),
            "roomid": cfg.get(sub, "roomid"),
            "machine_type": cfg.getint(sub, "machine_type"),
            "encode_type": cfg.getint(sub, "encode_type"),
        }

        cf_server = configparser.RawConfigParser()
        cf_server.read("/home/pi/wawaji/WaController/server.ini")
        is_test = cf_server.getint("server", "test_jp")
        is_save_jp = cf_server.getint("server", "save_jp")

        logger.debug("TBJ_Main---room_info: " + str(room_info))

        # my_tbj_detector = TBJDetector(room_info["machine_type"])
        tbj_serial_communication = TbjSerialCommunication()
        tbj_serial_communication.start_accept_serial_data()

        is_jp_type = False

        while self._running:
            try:
                ret = tbj_serial_communication.deal_serial_data()
                if ret < 0:
                    time.sleep(50 / 1000)
                    continue

                tbj_ai_check_job()

                tbj_serial_communication.clear_serial_data()
                time.sleep(process_dict["interval"])

            except KeyboardInterrupt:
                tbj_serial_communication.stop_accept_serial_data()
                tbj_serial_communication.close_serail_dev()
                logger.debug("TBJ_Main---TBJDetector Error")


def init(init_dict=None):
    global detect_thread
    global process_dict
    # global cap
    global rtscap

    if init_dict is None:
        process_dict = dict()
    else:
        process_dict = init_dict

    process_dict["drop_error"] = False
    process_dict["machine_error"] = False
    process_dict["is_compensation"] = False
    process_dict["jp_detected"] = False
    process_dict["interval"] = 10
    process_dict["class_type"] = 0
    process_dict["encode_machine_error"] = 0
    process_dict["error_code"] = -1
    process_dict["is_init_end"] = False
    process_dict["compensation_coins"] = 0
    process_dict["need_count_coins"] = False
    process_dict["coins_count"] = 0
    process_dict["left_coins"] = 0
    process_dict["tbj_type"] = 0
    process_dict["total_coins"] = 0
    process_dict["gpio_low_start_time"] = 0
    process_dict["can_check_score"] = 0
    process_dict["check_score_coins_count"] = 0
    process_dict["machine_stuck"] = False

    logger.debug("TBJ_Main")
    # cap = cv2.VideoCapture(0)

    # rtscap = RTSCapture.create(0)
    # rtscap = RTSCapture()
    # rtscap.start_read()  # 启动子线程并改变 read_latest_frame 的指向

    time.sleep(1)

    while True:
        detect_thread = DetectionThread()
        detect_thread.start()
        detect_thread.join()
        logger.debug("TBJ_Main---thread exit")

    rtscap.stop_read()
    rtscap.release()


if __name__ == "__main__":
    my_dict = Manager().dict()
    my_dict["drop_error"] = False
    my_dict["machine_error"] = False
    my_dict["encode_machine_error"] = 0
    my_dict["is_compensation"] = False
    my_dict["jp_detected"] = False
    my_dict["interval"] = 10
    my_dict["class_type"] = 0
    my_dict["error_code"] = -1
    my_dict["is_init_end"] = False
    my_dict["compensation_coins"] = 0
    my_dict["need_count_coins"] = False
    my_dict["coins_count"] = 0
    my_dict["left_coins"] = 0
    my_dict["tbj_type"] = 0
    my_dict["total_score"] = 0
    my_dict["total_coins"] = 0
    my_dict["gpio_low_start_time"] = 0
    my_dict["can_check_score"] = 0
    my_dict["check_score_coins_count"] = 0
    my_dict["machine_stuck"] = False

    pid = os.fork()
    if pid < 0:
        logger.debug("TBJ_Main--fork failed")
    elif pid == 0:
        # child process
        logger.debug("TBJ_Main--TBJ_API in main process")
        TBJ_API.init(my_dict)
        logger.debug("TBJ_Main--sub process0 end")
        exit(0)

    pid1 = os.fork()
    if pid1 < 0:
        logger.debug("TBJ_Main--fork1 failed")
    elif pid1 == 0:
        # child process
        # 光眼检测
        logger.debug("TBJ_Main--TBJ_Coins in main process")
        TBJ_Coins.init(my_dict)
        logger.debug("TBJ_Main--sub process1 end")
        exit(0)
    else:
        # parrent process
        logger.debug("TBJ_Main--main process")
        init(my_dict)
        logger.debug("TBJ_Main--main process end")

    # logger.debug("TBJ_Main--main process")
    # init(my_dict)
    # logger.debug("TBJ_Main--main process end")
