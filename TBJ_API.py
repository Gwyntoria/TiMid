# -*- coding: utf-8 -*-

# Version 1.0.0.1	Details in TBJ_Update.log
# use python3

"""
API
"""

import sys
import os
import threading
import json
import websocket
import socket
import ssl
import http.client
import configparser
import time
import hashlib
import glob as gb
import logging

import requests
from interval import Interval
import smbus

import TBJ_WaInit

sys.setrecursionlimit(2000)
sys.path.append("../")
logger = logging.getLogger("WaController")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%d %b %Y %H:%M:%S",
)

MCP23017_IODIRA = 0x00
MCP23017_IPOLA = 0x02
MCP23017_GPINTENA = 0x04
MCP23017_DEFVALA = 0x06
MCP23017_INTCONA = 0x08
MCP23017_IOCONA = 0x0A
MCP23017_GPPUA = 0x0C
MCP23017_INTFA = 0x0E
MCP23017_INTCAPA = 0x10
MCP23017_GPIOA = 0x12
MCP23017_OLATA = 0x14

MCP23017_IODIRB = 0x01
MCP23017_IPOLB = 0x03
MCP23017_GPINTENB = 0x05
MCP23017_DEFVALB = 0x07
MCP23017_INTCONB = 0x09
MCP23017_IOCONB = 0x0B
MCP23017_GPPUB = 0x0D
MCP23017_INTFB = 0x0F
MCP23017_INTCAPB = 0x11
MCP23017_GPIOB = 0x13
MCP23017_OLATB = 0x15

MCP23017_ADDRESS = 0x20

bus = None

admin_id = ""
admin_token = ""
game_time = 30

user_info = {}
room_info = {}
is_new_user = False

playing = False
countdown_time = 30
end_play = False
responses = []
position = 0
compensation_ratio = 0.35

chubi_error = 0
ll_error_time = 0

restart = True

thread_count = 0

user_in_room = False

is_room_in = False
in_schedule_thread = False
in_detect_thread = False
is_detect_support = True
web_socket = None
web_socket_thread = None
detect_thread = None
check_coins_count_thread = None
coins2user_thread = None
check_socket_thread = None
remove_thread = None

coins_count = 0
can_check_score = 0
check_score_coins_count = 0

is_waiting = False
is_restart_camera = False

action_from = 0
drop_count = 1

in_drop_thread = False
user_drop_thread = None
count_down_thread = None

# process_dict = None
jp_register = ""
with_hisi = 0

ping_time = 0

stream_off_time = 0
is_stream_on = 0
is_add_cover = False

last_tbj_type = 0
last_event_type = 0
last_special_time = 0

video_client = None

sp_record_id = None
sp_expire_ts = 0

STATUS_DISCONNECTED = 0
STATUS_CONNECTED = 1
STATUS_CONNECTING = 2
STATUS_DISCONNECTING = 3

ERROR_TYPE = {
    0: "异常出币",
    1: "入币器故障",
    2: "回币器故障",
    3: "退币器故障",
    4: "推盘马达故障",
    5: "雨刷马达故障",
    6: "摇摆通道异常",
    7: "入币器空",
    8: "退币器空",
    9: "退币槽满",
    10: "推币率错误",
    11: "机台摇摆",
    12: "通道1卡币",
    13: "通道2卡币",
    14: "通道3卡币",
    15: "通道4卡币",
    16: "通道5卡币",
    17: "通道6卡币",
    18: "通道7卡币",
    19: "通道8卡币",
    20: "通道9卡币",
}

# 欢乐马戏团 --Error Code
ERROR_CODE = {
    0: "右边马达故障",
    1: "PLAY推币器错误",
    2: "RETURN推币器错误",
    3: "雨刷故障",
    4: "SPIN故障",
    5: "雨刷错误",
    6: "摇摆通道错误",
    7: "彩票机故障",
    8: "退币器空",
    9: "中间马达故障",
    10: "推盘出币率异常",
    11: "机台摇摆",
    12: "通道1卡币",
    13: "通道2卡币",
    14: "通道3卡币",
    15: "通道4卡币",
    16: "通道5卡币",
    17: "通道6卡币",
    18: "通道7卡币",
    19: "通道8卡币",
    20: "通道9卡币",
    21: "通道10卡币",
    22: "出币口故障",
    23: "通道11卡币",
    24: "通道12卡币",
    25: "通道13卡币",
    26: "网络联机错误",
    27: "台号设定错误",
    28: "打印机故障",
}

crc8Table = [
    0x00, 0x07, 0x0E, 0x09, 0x1C, 0x1B, 0x12, 0x15, 0x38, 0x3F, 0x36, 0x31, 0x24, 0x23, 0x2A, 0x2D,
    0x70, 0x77, 0x7E, 0x79, 0x6C, 0x6B, 0x62, 0x65, 0x48, 0x4F, 0x46, 0x41, 0x54, 0x53, 0x5A, 0x5D,
    0xE0, 0xE7, 0xEE, 0xE9, 0xFC, 0xFB, 0xF2, 0xF5, 0xD8, 0xDF, 0xD6, 0xD1, 0xC4, 0xC3, 0xCA, 0xCD,
    0x90, 0x97, 0x9E, 0x99, 0x8C, 0x8B, 0x82, 0x85, 0xA8, 0xAF, 0xA6, 0xA1, 0xB4, 0xB3, 0xBA, 0xBD,
    0xC7, 0xC0, 0xC9, 0xCE, 0xDB, 0xDC, 0xD5, 0xD2, 0xFF, 0xF8, 0xF1, 0xF6, 0xE3, 0xE4, 0xED, 0xEA,
    0xB7, 0xB0, 0xB9, 0xBE, 0xAB, 0xAC, 0xA5, 0xA2, 0x8F, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9D, 0x9A,
    0x27, 0x20, 0x29, 0x2E, 0x3B, 0x3C, 0x35, 0x32, 0x1F, 0x18, 0x11, 0x16, 0x03, 0x04, 0x0D, 0x0A,
    0x57, 0x50, 0x59, 0x5E, 0x4B, 0x4C, 0x45, 0x42, 0x6F, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7D, 0x7A,
    0x89, 0x8E, 0x87, 0x80, 0x95, 0x92, 0x9B, 0x9C, 0xB1, 0xB6, 0xBF, 0xB8, 0xAD, 0xAA, 0xA3, 0xA4,
    0xF9, 0xFE, 0xF7, 0xF0, 0xE5, 0xE2, 0xEB, 0xEC, 0xC1, 0xC6, 0xCF, 0xC8, 0xDD, 0xDA, 0xD3, 0xD4,
    0x69, 0x6E, 0x67, 0x60, 0x75, 0x72, 0x7B, 0x7C, 0x51, 0x56, 0x5F, 0x58, 0x4D, 0x4A, 0x43, 0x44,
    0x19, 0x1E, 0x17, 0x10, 0x05, 0x02, 0x0B, 0x0C, 0x21, 0x26, 0x2F, 0x28, 0x3D, 0x3A, 0x33, 0x34,
    0x4E, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5C, 0x5B, 0x76, 0x71, 0x78, 0x7F, 0x6A, 0x6D, 0x64, 0x63,
    0x3E, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2C, 0x2B, 0x06, 0x01, 0x08, 0x0F, 0x1A, 0x1D, 0x14, 0x13,
    0xAE, 0xA9, 0xA0, 0xA7, 0xB2, 0xB5, 0xBC, 0xBB, 0x96, 0x91, 0x98, 0x9F, 0x8A, 0x8D, 0x84, 0x83,
    0xDE, 0xD9, 0xD0, 0xD7, 0xC2, 0xC5, 0xCC, 0xCB, 0xE6, 0xE1, 0xE8, 0xEF, 0xFA, 0xFD, 0xF4, 0xF3,
]

STREAM_ADD_COVER = [0x01, 0x01, 0x00, 0x07, 0x01, 0xA1, 0x00]
STREAM_RMV_COVER = [0x01, 0x01, 0x00, 0x07, 0x01, 0xA2, 0x00]
ON_PONG_DATA = [0x01, 0x02, 0x00, 0x06, 0x00, 0x00]


def get_check_sum(data, len):
    sum = 0

    for x in range(0, len):
        sum = crc8Table[sum ^ data[x]]

    return sum


class Client:
    def __init__(self):
        # ipv4  TCP
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.status = 0
        self.ping_time = 0

    def connect(self, server_ip, server_port):
        logger.debug("Client- server_ip: " + server_ip)
        try:
            self.client.connect((server_ip, server_port))
            self.status = 1
        except Exception as e:
            logger.error("Client connect - Exception: " + str(e))
        except OSError as e:
            logger.error("Client connect OSError: " + str(e))
        except:
            logger.error("client connect - Error")

    def close(self):
        logger.debug("Client- close")
        try:
            self.client.close()
            self.status = 0
        except Exception as e:
            logger.error("Client close - Exception: " + str(e))
        except OSError as e:
            logger.error("Client close OSError: " + str(e))
        except:
            logger.error("client close - Error")

    def senddata(self, data):
        logger.debug("Client- senddata: " + str(data))
        try:
            self.client.sendall(data)
        except Exception as e:
            self.client.close()
            self.status = 0
            logger.error("Client connect - Exception: " + str(e))
        except OSError as e:
            self.client.close()
            self.status = 0
            logger.error("Client connect OSError: " + str(e))
        except:
            self.client.close()
            self.status = 0
            logger.error("lient connect - Error")

    def run(self):
        while self.status == 1:
            response = self.client.recv(1024)
            if response is not None:
                logger.debug("response: " + str(response))
                if len(response) == 2 and response[0] == 0x01 and response[1] == 0x02:
                    self.ping_time = int(time.time())
                    data = ON_PONG_DATA
                    if is_add_cover is True:
                        data[4] = 0x01
                    else:
                        data[4] = 0x00
                    check_sum = get_check_sum(data, 5)
                    logger.debug("on pong check_sum: " + str(check_sum))
                    data[5] = check_sum & 0xFF
                    command_data = data[:]
                    raw_packet = bytearray(command_data)
                    video_client.senddata(raw_packet)
                elif len(response) == 0:
                    logger.debug("Client run break")
                    break
            else:
                break
        logger.debug("Client end run")
        self.status = 0

    def get_ping_time(self):
        return self.ping_time

    def set_status(self, status):
        self.status = status


class RunVideoClient(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        global video_client
        logger.debug("RunVideoClient start: " + str(int(time.time())))
        while True:
            video_client = Client()
            video_client.connect(room_info["rtmp_ip"], 8998)
            video_client.run()
            time.sleep(5)


class CheckVideoClient(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        logger.debug("CheckVideoClient start: " + str(int(time.time())))
        while True:
            if video_client is not None:
                cur_time = int(time.time())
                push_ping_time = video_client.get_ping_time()
                if push_ping_time > 0 and (cur_time - push_ping_time) > 15:
                    video_client.set_status(0)
                    video_client.close()
                    break
            time.sleep(5)


def add_coin():
    try:
        gpio_a = bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)
        gpio_a = gpio_a | 0x02
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA, gpio_a)
        time.sleep(0.025)
        gpio_a = bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)
        gpio_a = gpio_a & 0xFD
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA, gpio_a)
    except Exception as e:
        logger.error("add_coin - Exception: " + str(e))
    except OSError as e:
        logger.error("add_coin OSError: " + str(e))
    except:
        logger.error("add_coin - Error")


def drop_coin():
    try:
        gpio_a = bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)
        gpio_a = gpio_a | 0x08
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA, gpio_a)
        time.sleep(0.025)
        gpio_a = bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)
        gpio_a = gpio_a & 0xF7
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA, gpio_a)
    except Exception as e:
        logger.error("drop_coin - Exception: " + str(e))
    except OSError as e:
        logger.error("drop_coin OSError: " + str(e))
    except:
        logger.error("drop_coin - Error")


def hash_code_24(combined_string):
    hash_code = 0
    if combined_string is None or len(combined_string) <= 0:
        return 0

    for x in combined_string:
        hash_code = ((hash_code << 5) - hash_code) + ord(x)
        hash_code = hash_code & 0x00FFFFFF

    return hash_code


class RemoveScreenshotFiles(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        while self._running:
            try:
                glob_param = "/home/pi/wawaji/ScreenShot_Image/" + room_info["name"] + "-AI-*.jpg"
                img_paths = gb.glob(glob_param)
                img_paths.sort()
                while len(img_paths) > 50:
                    img_path = img_paths[0]
                    if user_in_room is False:
                        command = "sudo rm " + img_path
                        os.system(command)
                        del img_paths[0]
                        time.sleep(0.01)
                    else:
                        break

                time.sleep(60)

            except OSError as err:
                logger.error("RemoveScreenshotFiles--failed: " + str(err))
            except:
                logger.error("RemoveScreenshotFiles--failed")


def handle_jp_detect():
    global process_dict

    process_dict["jp_detected"] = False

    if user_in_room is True:
        t = int(time.time())
        post = {
            "token": room_info["token"],
            "ts": str(t),
            "jp": {
                "type": process_dict["class_type"],
                "time": t,
                "user": user_info["user_id"],
                "room": room_info["roomid"],
                "grab": user_info["grab_id"],
                "status": 1,
            },
            "code": hash_code_24(
                room_info["token"]
                + room_info["roomid"]
                + user_info["user_id"]
                + user_info["grab_id"]
                + str(t)
            ),
        }

        logger.debug("Register JP POST: " + str(post))
        requests.urllib3.disable_warnings()
        r = requests.post(jp_register, json=post, verify=False)

        try:
            r_json = r.json()
        except:
            r_json = 0
            logger.error("jp_register requests.post Error")

        if user_in_room is True and r_json != 0 and web_socket_thread is not None:
            json_info = r_json
            logger.debug("jsonInfo: " + str(json_info))
            msg = {}
            if (
                "status" in json_info
                and "ok" in json_info["status"]
                and "code" in json_info
                and json_info["code"] == 0
                and "jp" in json_info
            ):
                msg["action"] = "room_opt"
                msg["event"] = "jp"
                msg["jp_type"] = process_dict["class_type"]
                msg["user_id"] = user_info["user_id"]
                msg["room_id"] = room_info["roomid"]
                if "doll_name" in user_info:
                    msg["doll_name"] = user_info["doll_name"]
                if "user_name" in user_info:
                    msg["user_name"] = user_info["user_name"]
                if "user_avatar" in user_info:
                    msg["user_avatar"] = user_info["user_avatar"]
                msg["jp_id"] = json_info["jp"]["_id"]
                msg["result"] = "ok"
                if "plus" in json_info["jp"]:
                    msg["plus"] = json_info["jp"]["plus"]

                web_socket_thread.send_message(json.dumps(msg), "handle_jp_detect")


def handle_detect_error(error_type):
    global playing
    global countdown_time
    global user_info
    global user_in_room
    global is_restart_camera
    global is_waiting
    global chubi_error
    global ll_error_time

    global process_dict

    # 房间断开连接
    temp_user_info = dict()
    if user_in_room is True:
        msg = {}
        for key in user_info:
            msg[key] = user_info[key]
        msg["win_coins"] = 0
        msg["grab_finished"] = 2
        msg["action"] = "room_ret"
        msg["result"] = "ok"

        for key in user_info:
            temp_user_info[key] = user_info[key]
        user_info = {}
        user_in_room = False
        countdown_time = 0
        playing = False
        if is_waiting is True:
            is_restart_camera = True
            is_waiting = False
            restart_camera_job()

        if is_detect_support is True:
            process_dict["interval"] = 5

        web_socket_thread.send_message(json.dumps(msg), "handle_detect_error0")

    # 处理错误
    reason = "NULL"
    need_return_coins = 0

    if error_type == 0:
        reason = "AI检测持续掉币"

    elif error_type == 1:
        reason = "AI检测故障"

        if process_dict["is_compensation"] is True:
            process_dict["is_compensation"] = False
            need_return_coins = 1

        if room_info["machine_type"] == 2:  # 欢乐马戏团
            if process_dict["error_code"] in Interval(0, 28):
                reason = (
                    "AI检测故障-" + str(process_dict["error_code"]) + "." + ERROR_CODE[process_dict["error_code"]]
                )
                process_dict["error_code"] = -1
        else:
            if process_dict["error_code"] in Interval(0, 20):
                reason = (
                    "AI检测故障-" + str(process_dict["error_code"]) + "." + ERROR_TYPE[process_dict["error_code"]]
                )
                process_dict["error_code"] = -1

    elif error_type == 2:
        reason = "AI检测-重启编码器"

    elif error_type == 3:
        reason = "AI检测-编码器HDMI视频线出错"

    elif error_type == 4:
        reason = "出币检测异常"
        if chubi_error == 0:
            chubi_error = 1
            cur_time = int(time.time())
            if (cur_time - ll_error_time) >= 30 * 60:
                ll_error_time = cur_time
            else:
                return -1
        else:
            chubi_error = 0
            return -1

    elif error_type == 5:
        reason = "机器死机"
        if chubi_error == 0:
            chubi_error = 1
            cur_time = int(time.time())
            if (cur_time - ll_error_time) >= 30 * 60:
                ll_error_time = cur_time
            else:
                return -1
        else:
            chubi_error = 0
            return -1

    # 构建错误信息
    msg = {
        "action": "room_out",
        "event": "machine_error",
        "reason": reason,
        "room_id": room_info["roomid"],
    }

    if len(temp_user_info) > 0:
        logger.debug(
            "handle_detect_error: temp_user_info = "
            + str(temp_user_info)
            + " vip = "
            + str(room_info["vip"])
            + " compensation_coins = "
            + str(process_dict["compensation_coins"])
        )

    if (
        len(temp_user_info) > 0
        and "user_id" in temp_user_info
        and "grab_id" in temp_user_info
        and need_return_coins == 1
        and (room_info["vip"] >= 0 or room_info["name"][0] == "Y")
    ):
        msg["user_id"] = temp_user_info["user_id"]
        msg["grab_id"] = temp_user_info["grab_id"]
        msg["need_return_coins"] = 1

        if process_dict["compensation_coins"] > 0:
            if "price" in temp_user_info:
                msg["price"] = temp_user_info["price"]

            if "room_type" in temp_user_info:
                msg["room_type"] = temp_user_info["room_type"]

            if "room_subtype" in temp_user_info:
                msg["room_subtype"] = temp_user_info["room_subtype"]

            if "doll_id" in temp_user_info:
                msg["doll_id"] = temp_user_info["doll_id"]

            if "doll_name" in temp_user_info:
                msg["doll_name"] = temp_user_info["doll_name"]

            if "user_name" in temp_user_info:
                msg["user_name"] = temp_user_info["user_name"]

            if "user_avatar" in temp_user_info:
                msg["user_avatar"] = temp_user_info["user_avatar"]

            msg["win_coins"] = int(process_dict["compensation_coins"] * compensation_ratio)
            process_dict["compensation_coins"] = 0

    logger.debug("handle_detect_error msg: " + str(msg))
    web_socket_thread.send_message(json.dumps(msg), "handle_detect_error")


def handle_tbj_type(tbj_type):
    global last_tbj_type
    global last_event_type
    global last_special_time

    if tbj_type == 5 or tbj_type == 11 or tbj_type == 90:
        return

    if tbj_type == 7 or tbj_type == 70:
        event_type = 1

    elif tbj_type == 8 or tbj_type == 80:
        event_type = 2

    elif tbj_type == 9:
        event_type = 3

    elif tbj_type in Interval(1, 4):
        event_type = 4

    else:
        event_type = 0

    last_tbj_type = tbj_type

    if user_in_room is True:
        msg = {
            "action": "room_opt",
            "event": "special_event",
            "room_id": room_info["roomid"],
            "user_id": user_info["user_id"],
            "event_type": event_type,
        }

        # 事件发生改变
        if event_type != last_event_type:
            logger.debug("handle_tbj_type msg: " + str(msg))
            web_socket_thread.send_message(json.dumps(msg), "handle_tbj_type")
            last_special_time = time.time()

        else:
            now_time = time.time()
            if now_time - last_special_time >= 5:
                logger.debug("handle_tbj_type msg: " + str(msg))
                web_socket_thread.send_message(json.dumps(msg), "handle_tbj_type")
                last_special_time = now_time

    if event_type != last_event_type:
        last_event_type = event_type


class TBJDetectionThread(threading.Thread):
    global process_dict

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        global in_detect_thread
        logger.debug("detectionThread")
        in_detect_thread = True
        # process_dict['interval'] = 5

        sleep_time = 0
        while is_detect_support is True:
            if is_room_in is True:
                logger.debug("TBJ detect: jp " + str(process_dict["jp_detected"]))
                if process_dict["jp_detected"] is True:
                    handle_jp_detect()

                if process_dict["drop_error"] is True:
                    process_dict["drop_error"] = False
                    handle_detect_error(0)

                if process_dict["machine_error"] is True:
                    process_dict["machine_error"] = False
                    handle_detect_error(1)

                if process_dict["encode_machine_error"] == 1:
                    handle_detect_error(2)
                    process_dict["encode_machine_error"] = 0

                if process_dict["encode_machine_error"] == 2:
                    handle_detect_error(3)
                    process_dict["encode_machine_error"] = 0

                handle_tbj_type(process_dict["tbj_type"])

            time.sleep(1)
            sleep_time = sleep_time + 1

        logger.debug("detectionThread End")
        in_detect_thread = False
        # TBJ_detection.stopDetectThread()


def restart_camera_job():
    global is_waiting
    global is_restart_camera

    logger.debug("restart_camera_job: playing = " + str(playing) + ", is_stream_on: " + str(is_stream_on))

    if is_stream_on == 0:
        is_restart_camera = False
        is_waiting = False
        return

    if is_restart_camera is True:
        os.system(
            'sudo python /home/pi/wawaji/WaController/GenPushURL.py && echo "$(date) - Restart one time..." >> /home/pi/wawaji/camRestart.log'
        )
        logger.debug("restart end: bRestartCamera = " + str(is_restart_camera))
        is_restart_camera = False
        is_waiting = False
    elif is_waiting is False:
        ini_cfg = configparser.RawConfigParser()
        ini_cfg.read("/home/pi/wawaji/WaController/genPushUrl.ini")
        section = "room"

        expired_time = 0
        if ini_cfg.has_option(section, "expiredTime"):
            expired_time = ini_cfg.getint(section, "expiredTime")

        now_time = int(time.time())
        if (expired_time > now_time and (expired_time - now_time) <= 12 * 3600) or now_time >= expired_time:
            # if (expiredTime > nowTime and (expiredTime-nowTime) <= 60) or nowTime >= expiredTime:
            if playing is False:
                os.system(
                    'sudo python /home/pi/wawaji/WaController/GenPushURL.py && echo "$(date) - Restart one time..." >> /home/pi/wawaji/camRestart.log'
                )
                logger.debug("restart end when no user")
            else:
                is_waiting = True


class CheckWebSocket(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        logger.debug("CheckWebSocket start: " + str(int(time.time())))
        while self._running:
            if ping_time > 0:
                current_time = int(time.time())
                if (current_time - ping_time) >= 30 and web_socket_thread.get_ws_status() == STATUS_CONNECTED:
                    logger.debug("CheckWebSocket: ping timeout")
                    if web_socket_thread is not None and web_socket_thread.is_alive() is True:
                        web_socket_thread.set_ws_status(STATUS_DISCONNECTING)
                        web_socket_thread.close_web_socket()
            time.sleep(1)


class WebSocketThread(threading.Thread):
    def __init__(self, ws):
        global check_socket_thread
        threading.Thread.__init__(self)
        self._running = True
        self._web_socket = ws
        self._ws_status = STATUS_DISCONNECTED
        self._reconnect_count = 0
        check_socket_thread = CheckWebSocket()
        check_socket_thread.start()

    def run(self):
        logger.debug("WebSocketThread start: " + str(int(time.time())))
        while self._running:
            try:
                if self._ws_status == STATUS_CONNECTING or self._ws_status == STATUS_DISCONNECTING:
                    continue

                current_time = int(time.time())
                if ping_time > 0 and (current_time - ping_time) >= 30 and self._ws_status == STATUS_CONNECTED:
                    logger.debug("WebSocketThread: ping timeout")
                    self.set_ws_status(STATUS_DISCONNECTING)
                    self.close_web_socket()
                    continue

                if self._reconnect_count > 0:
                    t = 5
                    if self._reconnect_count > 10:
                        t = 30
                    if self._reconnect_count > 20:
                        t = 60
                    if self._reconnect_count > 30:
                        t = 120
                    if self._reconnect_count > 40:
                        t = 240
                    time.sleep(t)
                logger.debug("WebSocketThread reconnect_count: " + str(self._reconnect_count))

                if self._ws_status == STATUS_DISCONNECTED:
                    self._ws_status = STATUS_CONNECTING
                    self._web_socket.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

            except Exception as e:
                logger.error("WebSocketThread - Exception: " + str(e))
            except:
                logger.error("WebSocketThread - except Error")

    def set_ws_status(self, ws_status):
        self._ws_status = ws_status

    def set_reconnect(self, count):
        if count == 0:
            self._reconnect_count = 0
        else:
            self._reconnect_count = self._reconnect_count + 1

    def send_message(self, message, title):
        is_sent = False
        try:
            self._web_socket.send(message)
            is_sent = True
        except Exception as e:
            logger.error("WebSocketThread--" + title + "--send_message: " + str(e))
        except:
            logger.error("WebSocketThread--" + title + "--send_message error")
        return is_sent

    def close_web_socket(self):
        self._web_socket.close()
        if self._ws_status == STATUS_DISCONNECTING:
            self._ws_status = STATUS_DISCONNECTED
            self.set_reconnect(1)

    def get_ws_status(self):
        return self._ws_status

    def get_reconnect(self):
        return self._reconnect_count


def event(a):
    logger.debug("event: " + a)
    eventDict[a]()


def machine_settings():
    logger.debug("machine_settings")

    msg = {
        "ret": "failed",
        "action": "admin_settings",
        "event": "machine_settings",
        "user_id": admin_id,
        "room_id": room_info["roomid"],
        "adToken": admin_token,
    }

    web_socket_thread.send_message(json.dumps(msg), "machine_settings")


def move_brush():
    logger.debug("Open Wiper")
    try:
        gpio_a = bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)
        gpio_a = gpio_a | 0x04
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA, gpio_a)
        time.sleep(0.025)
        # time.sleep(0.06)                                              # 埃及宝藏间隔0.06秒
        gpio_a = bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)
        gpio_a = gpio_a & 0xFB
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA, gpio_a)
    except Exception as e:
        logger.error("move_brush - Exception: " + str(e))
    except OSError as e:
        logger.error("move_brush OSError: " + str(e))
    except:
        logger.error("move_brush - Error")


def user_out_manually():
    global countdown_time
    global action_from
    global process_dict

    if (
        process_dict["left_coins"] >= 50
        or process_dict["tbj_type"] == 7
        or process_dict["tbj_type"] == 8
        or process_dict["tbj_type"] == 70
        or process_dict["tbj_type"] == 80
    ):
        logger.debug("user_out_manually- left_coins: " + str(process_dict["left_coins"]))
        return

    logger.debug("user_out_manually")
    if countdown_time > 0:
        action_from = 1
        countdown_time = 0


# def user_drop(drop_count):
#     global playing
#     global countdown_time
#     global end_play
#     global user_in_room
#     global action_from
#
#     user_in_room = True
#     action_from = 0
#
#     if is_detect_support is True:
#         process_dict['interval'] = 1
#
#     countdown_time = game_time
#
#     if drop_count <= 1:
#         drop_coin()
#         time.sleep(0.15)
#         add_coin()
#     else:
#         for i in range(0, drop_count):
#             if i > 0:
#                 time.sleep(0.15)
#             drop_coin()
#         time.sleep(0.15)
#         for i in range(0, drop_count):
#             if i > 0:
#                 time.sleep(0.15)
#             add_coin()
#
#     if is_new_user is True or end_play is True:
#         end_play = False
#         playing = True
#         count_down_thread = PlayCountDown()
#         count_down_thread.start()


class UserDropThread(threading.Thread):
    global process_dict

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        global in_drop_thread
        global count_down_thread
        global drop_count
        logger.debug("UserDropThread")
        in_drop_thread = True
        process_dict["coins_count"] = 0

        while playing is True:
            if count_down_thread is None or count_down_thread.is_alive() is False:
                count_down_thread = PlayCountDown()
                count_down_thread.start()

            while drop_count > 0:
                global countdown_time
                global user_in_room
                global action_from

                user_in_room = True
                action_from = 0

                if is_detect_support is True:
                    process_dict["interval"] = 1

                countdown_time = game_time

                drop_count -= 1
                drop_coin()
                # time.sleep(0.15)
                add_coin()
                time.sleep(0.16)

        logger.debug("UserDropThread End")
        in_drop_thread = False


class PlayCountDown(threading.Thread):
    def __init__(self):
        global thread_count
        threading.Thread.__init__(self)
        self._running = True
        self.name = "playCountDown" + str(thread_count)
        thread_count = thread_count + 1

    def terminate(self):
        logger.debug("playCountDown: terminate")
        self._running = False

    def run(self):
        global countdown_time

        countdown_time = game_time
        while end_play is False:
            if countdown_time <= 0:
                end_game()
                break

            current_time = int(time.time())
            if sp_record_id is not None and sp_expire_ts <= current_time:
                end_game()
                break

            time.sleep(1)
            countdown_time = countdown_time - 1
            logger.debug("countdownTime = " + str(countdown_time))


def end_game():
    global end_play
    global playing

    end_play = True

    logger.debug("end_play() end_play = " + str(end_play))
    time.sleep(3)

    if playing is True and end_play is True:
        playing = False
        return_room_info(0, 1)


class Coins2User(threading.Thread):
    global process_dict

    def __init__(self):
        global thread_count
        threading.Thread.__init__(self)
        self._running = True

    def terminate(self):
        logger.debug("Coins2User: terminate")
        self._running = False

    def run(self):
        global playing
        global end_play
        global countdown_time
        global can_check_score
        global check_score_coins_count  # 用户已获得币数量

        last_time = 0
        grab_finished = 0
        last_total_score = process_dict["total_score"]

        left_coins = 0
        fall_coins = 0
        fall_time = 0

        logger.debug("Coins2User")
        while True:
            coins = process_dict["coins_count"]
            can_check_score = process_dict["can_check_score"]
            check_score_coins_count = process_dict["check_score_coins_count"]
            
            cur_time = time.time()
            if left_coins == 0:
                left_coins = coins
                fall_coins += coins

            if room_info['roomid'] is not None and fall_coins > 0 and fall_time + 1 < cur_time:
                logger.debug('return_room_opt--fallcoins: ' + str(fall_coins))
                msg = {}
                msg['action'] = 'room_opt'
                msg['event'] = 'fallcoins_event'
                msg['room_id'] = room_info['roomid']
                msg['coins'] = fall_coins
                msg['ts'] = str(int(cur_time * 1000))
                web_socket_thread.send_message(json.dumps(msg), "return_room_opt")
                logger.debug("handle_tbj_type msg: " + str(msg))
                fall_coins = 0
                fall_time = cur_time

            if playing is False:
                process_dict["coins_count"] = process_dict["coins_count"] - coins
                process_dict["can_check_score"] = 0
                process_dict["check_score_coins_count"] = (
                    process_dict["check_score_coins_count"] - check_score_coins_count
                )
                left_coins = process_dict['coins_count']
                continue

            if playing is True and coins > 0 and last_time == 0:
                last_time = int(cur_time * 1000)
            now_time = int(cur_time * 1000)

            if playing is True and end_play is True:
                playing = False
                grab_finished = 1

            win_coin = {"coins": str(coins), "time": int(cur_time * 1000)}
            if grab_finished == 1:
                logger.debug("Coins2User--grab_finished--win coins: " + str(win_coin))
                if countdown_time > 0 and coins > 0:
                    end_play = False
                    countdown_time = game_time
                    grab_finished = 0
                    playing = True
                return_room_info(coins, grab_finished)
                process_dict["coins_count"] = process_dict["coins_count"] - coins
                last_time = now_time
                grab_finished = 0
                left_coins = process_dict['coins_count']
            elif playing is True and now_time - last_time > 1000:
                if coins > 0 and grab_finished == 0:
                    logger.debug("Coins2User--win coins: " + str(win_coin))
                    if countdown_time > 0:
                        end_play = False
                        countdown_time = game_time
                        playing = True
                    return_room_info(coins, grab_finished)
                process_dict["coins_count"] = process_dict["coins_count"] - coins
                last_time = now_time
                left_coins = process_dict['coins_count']

            gpio_low_start_time = process_dict["gpio_low_start_time"]
            if gpio_low_start_time > 0:
                check_now_time = int(time.time() * 1000)
                if (check_now_time - gpio_low_start_time) >= 3000:
                    handle_detect_error(4)
                    break

            # total_score = process_dict["total_score"]
            # if can_check_score == 1 and check_score_coins_count >= 50:
            #     if 0 < last_total_score == total_score:
            #         logger.debug("Coins2User--total_score: " + str(total_score))
            #         process_dict["can_check_score"] = 0
            #         process_dict["check_score_coins_count"] = 0
            #         handle_detect_error(5)
            #         break
            #     else:
            #         process_dict["can_check_score"] = 0
            #         process_dict["check_score_coins_count"] = (
            #             process_dict["check_score_coins_count"] - check_score_coins_count
            #         )
            #         last_total_score = total_score
            #         logger.debug("Coins2User--machine is working")

            machine_status = process_dict["machine_stuck"]
            if machine_status:
                handle_detect_error(5)
                break


def return_room_info(coins, grab_finished):
    global is_waiting
    global user_in_room
    global user_info
    global is_restart_camera

    global sp_record_id
    global sp_expire_ts
    global process_dict

    logger.debug("return_room_info--wincoins: " + str(coins))

    t = str(int(time.time() * 1000))
    msg = {"ts": t}
    for key in user_info:
        if key != "countdown":
            msg[key] = user_info[key]
        elif grab_finished == 0:
            msg[key] = countdown_time

    msg["win_coins"] = coins
    msg["grab_finished"] = grab_finished
    msg["action"] = "room_ret"
    msg["result"] = "ok"
    if grab_finished == 1:
        msg["action_from"] = action_from
        if is_detect_support is True:
            process_dict["interval"] = 5

    if grab_finished == 1:
        user_info = {}
        user_in_room = False
        sp_record_id = None
        sp_expire_ts = 0
        if is_waiting is True:
            is_restart_camera = True
            is_waiting = False
            restart_camera_job()

    if web_socket_thread.send_message(json.dumps(msg), "return_room_info") is True:
        if process_dict["need_count_coins"] is True:
            process_dict["total_coins"] += coins


# actionDict = {'user_drop': user_drop}
eventDict = {"machine_settings": machine_settings}


def get_mac(interface="eth0"):
    # Return the MAC address of the specified interface
    try:
        mac_address = open("/sys/class/net/%s/address" % interface).read().strip().replace(":", "")
    except:
        mac_address = "00:00:00:00:00:00"
    return mac_address[0:17]


def restart_camera():
    # r = os.system('sudo python /home/pi/wawaji/WaController/GenPushURL.py')

    try_count = 0
    while True:
        conn = http.client.HTTPConnection(room_info["rtmp_ip"])
        conn.request("GET", "/reboot")
        r = conn.getresponse()
        if r.status == 200:
            msg = {
                "ret": "ok",
                "action": "admin_settings",
                "event": "restart_camera",
                "user_id": admin_id,
                "room_id": room_info["roomid"],
                "adToken": admin_token,
            }
            web_socket_thread.send_message(json.dumps(msg), "restart_camera success")
            break
        try_count = try_count + 1
        if try_count >= 5:
            break
        time.sleep(1)

    msg = {
        "ret": "failed",
        "action": "admin_settings",
        "event": "restart_camera",
        "user_id": admin_id,
        "room_id": room_info["roomid"],
        "adToken": admin_token,
    }
    web_socket_thread.send_message(json.dumps(msg), "restart_camera failed")


def reboot():
    os.system("sudo reboot")


def on_open(ws):
    global playing
    global countdown_time

    reconnect = web_socket_thread.get_reconnect()
    if playing is True and reconnect > 20:
        countdown_time = 0
        playing = False

    web_socket_thread.set_reconnect(0)
    logger.debug("websocket on_open")

    logger.debug(room_info)
    if len(room_info) > 0:
        t = str(int(time.time() * 1000))
        logger.debug(room_info["roomid"] + get_mac() + t)
        md5 = hashlib.md5()
        data = room_info["roomid"] + get_mac() + t
        md5.update(data.encode("gb2312"))
        msg = {"action": "room_in", "room_id": room_info["roomid"], "sign": md5.hexdigest(), "ts": t}
        web_socket_thread.send_message(json.dumps(msg), "on_open")
        logger.debug("ws thread start")
    else:
        logger.debug("not roomInfo")


def on_close(ws):
    logger.debug("websocket on_close: ")
    web_socket_thread.set_ws_status(STATUS_DISCONNECTED)
    web_socket_thread.set_reconnect(1)


def on_error(ws, error):
    logger.debug("websocket on_error: " + str(error))
    web_socket_thread.set_ws_status(STATUS_DISCONNECTING)
    web_socket_thread.set_reconnect(1)


def on_ping(ws, ping):
    global ping_time

    logger.debug("websocket on_ping: " + str(ping))
    ping_time = int(time.time())


def stream_off():
    global is_add_cover
    global stream_off_time

    logger.debug("stream_off thread begin")
    while is_stream_on == 0:
        if stream_off_time > 0 and (int(time.time()) - stream_off_time) >= 10:
            # data = STREAM_ADD_COVER
            # check_sum = get_check_sum(data, 6)
            # logger.debug("add cover check_sum: " + str(check_sum))
            # data[6] = check_sum & 0xFF
            # command_data = data[:]
            # raw_packet = bytearray(command_data)
            # video_client.senddata(raw_packet)
            try_count = 0
            while True:
                conn = http.client.HTTPConnection(room_info["rtmp_ip"])
                conn.request("GET", "/set_params?cover=1")
                r = conn.getresponse()
                if r.status == 200:
                    logger.debug("add cover")
                    break
                try_count = try_count + 1
                if try_count >= 5:
                    break
                time.sleep(1)

            is_add_cover = True
            break
        time.sleep(10)

    stream_off_time = 0
    logger.debug("stream_off thread end")


def stream_switch(is_on):
    global stream_off_time
    global is_stream_on
    global is_add_cover

    is_stream_on = is_on

    logger.debug(
        "stream_switch, is_stream_on: "
        + str(is_stream_on)
        + ", is_add_cover: "
        + str(is_add_cover)
        + ", stream_off_time: "
        + str(stream_off_time)
    )
    if is_on == 1 and is_add_cover is True:
        # data = STREAM_RMV_COVER
        # check_sum = get_check_sum(data, 6)
        # logger.debug("remove cover check_sum: " + str(check_sum))
        # data[6] = check_sum & 0xFF
        # command_data = data[:]
        # raw_packet = bytearray(command_data)
        # video_client.senddata(raw_packet)

        try_count = 0
        while True:
            conn = http.client.HTTPConnection(room_info["rtmp_ip"])
            conn.request("GET", "/set_params?cover=0")
            r = conn.getresponse()
            if r.status == 200:
                logger.debug("remove cover")
                break
            try_count = try_count + 1
            if try_count >= 5:
                break
            time.sleep(1)

        stream_off_time = 0
        is_add_cover = False
    elif is_on == 0:
        if stream_off_time == 0:
            stream_off_time = int(time.time())
            threading.Thread(target=stream_off).start()


def restart_frp():
    cf_server = configparser.RawConfigParser()
    cf_server.read("/home/pi/wawaji/WaController/server.ini")

    frp_url = cf_server.get("server", "frp")
    server_token = "w129edsudgqKHSsjbw98eiGDsnj1qj0ad2u1hsjxzcnjfsGj"
    if cf_server.has_option("server", "token"):
        server_token = cf_server.get("server", "token")
    logger.debug("frp_url: " + frp_url + "\nserver_token: " + server_token)

    mac = TBJ_WaInit.get_mac()
    token = server_token
    t = int(time.time())
    md5 = hashlib.md5()
    data = mac + token + str(t)
    md5.update(data.encode("gb2312"))
    logger.debug(str(t))
    post = {
        "mac": mac,
        "token": token,
        "ts": str(t),
        "sign": md5.hexdigest(),
        "code": TBJ_WaInit.hash_code_24(token + mac + str(t)),
    }
    logger.debug(post)
    requests.urllib3.disable_warnings()
    r = requests.post(frp_url, json=post, verify=False)

    try:
        r_json = r.json()
    except Exception as e:
        r_json = 0
        logger.error("requests.post Error: " + str(e))
    except:
        r_json = 0
        logger.error("requests.post Error")

    if r_json != 0:
        json_info = r_json
        logger.debug("jsonInfo: " + str(json_info))

        if "status" in json_info and "ok" in json_info["status"]:
            room_info = json_info["room"]
            if room_info is not None:
                frp_addr = ""
                frp_port = ""
                if "frps" in room_info:
                    frps = room_info["frps"]
                    frp_addr = frps.split(":")[0]
                    frp_port = frps.split(":")[1]

                frpc_file = "/home/pi/wawaji/frp_0.13.0_linux_arm/frpc.ini"
                fd = open(frpc_file).readlines()
                lines = []
                for line in fd:
                    if len(frp_addr) > 0 and "server_addr" in line:
                        lines.append("server_addr=" + frp_addr + "\n")
                    elif len(frp_port) > 0 and "server_port" in line:
                        lines.append("server_port=" + frp_port + "\n")
                    else:
                        lines.append(line)
                    if "log_max_days" in line:
                        lines.append("\n")
                        break
                lines.append("[" + room_info["frpport"] + "]" + "\n")
                lines.append("type = tcp" + "\n")
                lines.append("local_ip = 127.0.0.1" + "\n")
                lines.append("local_port = 22" + "\n")
                lines.append("remote_port = " + room_info["frpport"] + "\n")

                logger.debug("frp lines: " + str(lines))

                fc = open(frpc_file, "w")
                fc.writelines(lines)
                fc.flush()
                fc.close()

                time.sleep(1)
                os.system("sudo supervisorctl restart frp")
                logger.debug("restart_frp")


def on_message(ws, message):
    global user_info
    global admin_id
    global admin_token
    global game_time
    global sp_expire_ts
    global sp_record_id
    global is_new_user
    global is_room_in
    global ping_time
    global drop_count
    global detect_thread
    global user_drop_thread
    global check_coins_count_thread
    global coins2user_thread
    global remove_thread
    global compensation_ratio
    global playing
    global end_play

    global process_dict

    logger.debug("msg: " + message)

    msg = json.loads(message)
    if "action" in msg:
        # 管理员设置
        if "admin_settings" in msg["action"]:
            admin_token = msg["adToken"]
            admin_id = msg["user_id"]

            # Event-driven
            if "machine_settings" in msg["event"]:  #
                machine_settings()

            elif "restart_camera" in msg["event"]:  # IPC 重启
                restart_camera()

            elif "reboot" in msg["event"]:  # 树莓派重启
                reboot()

            elif "get_systeminfo" in msg["event"]:  # 树莓派系统信息
                get_system_info()

            elif "change_server" in msg["event"]:  # 切换正式/测试服
                change_server(msg)

            elif "add_coins" in msg["event"]:
                threading.Thread(target=add_coins, args=(msg,)).start()

            elif "restart_frp" in msg["event"]:  # 重启frp
                restart_frp()

            elif "room_error" in msg["event"]:
                process_dict["error_code"] = 5
                process_dict["machine_error"] = True

        # 用户选项
        elif "user_opt" in msg["action"]:
            if "move_brush" in msg["event"]:  # 雨刷
                threading.Thread(target=move_brush).start()

            elif "user_out_manually" in msg["event"]:  # 用户手动退出
                user_out_manually()

        # 管理员选项
        elif "admin_opt" in msg["action"]:
            if "stream_switch" in msg["event"]:
                logger.debug("stream_switch")
                if with_hisi == 1:
                    stream_switch(msg["on"])

        # 进入房间
        elif "room_in" in msg["action"]:
            is_room_in = True
            web_socket_thread.set_ws_status(STATUS_CONNECTED)
            ping_time = int(time.time())

            if is_detect_support is True:
                process_dict["interval"] = 5

        elif "room_in" not in msg["action"] and "room_out" not in msg["action"]:
            if "user_create_push_sp" in msg["action"]:
                if len(user_info) <= 0 or msg["user_id"] != user_info["user_id"]:
                    is_new_user = True
                    drop_count = 0
                    # sp_record_id = msg['sp_id']
                    # sp_expire_ts = int(time.time()) + msg['sp_duration']
                else:
                    is_new_user = False

                sp_record_id = msg["sp_id"]
                sp_expire_ts = int(time.time()) + msg["sp_duration"]

                playing = True
                end_play = False

                game_time = msg["countdown"]
                if "return_rate" in msg:
                    compensation_ratio = msg["return_rate"]
                    if isinstance(compensation_ratio, float) is False:
                        compensation_ratio = 0.35
                else:
                    compensation_ratio = 0.35

                if compensation_ratio <= 0 or compensation_ratio >= 1:
                    compensation_ratio = 0.35

                user_info = msg

            elif "user_drop" in msg["action"]:
                if len(user_info) <= 0 or msg["user_id"] != user_info["user_id"]:
                    is_new_user = True
                    drop_count = 0
                    sp_record_id = None
                    sp_expire_ts = 0
                else:
                    is_new_user = False

                playing = True
                end_play = False

                game_time = msg["countdown"]
                if "count" in msg:
                    drop_count += msg["count"]
                else:
                    drop_count += 1

                if "return_rate" in msg:
                    # 补偿倍率
                    compensation_ratio = msg["return_rate"]
                    if isinstance(compensation_ratio, float) is False:
                        compensation_ratio = 0.35
                else:
                    compensation_ratio = 0.35

                if compensation_ratio <= 0 or compensation_ratio >= 1:
                    compensation_ratio = 0.35

                user_info = msg

            # if len(user_info) > 2 and msg['user_id'] == user_info['user_id']:
            if len(user_info) > 2 and msg["user_id"] == user_info["user_id"]:
                if user_drop_thread is None or user_drop_thread.is_alive() is False:
                    user_drop_thread = UserDropThread()
                    user_drop_thread.start()

                # threading.Thread(target=action, args=[msg['action'], drop_count]).start()
            # action(msg['action'])

            if is_detect_support is True:
                if detect_thread is None or detect_thread.is_alive() is False:
                    detect_thread = TBJDetectionThread()
                    detect_thread.start()

            if remove_thread is None or remove_thread.is_alive() is False:
                remove_thread = RemoveScreenshotFiles()
                remove_thread.start()

            if coins2user_thread is None or coins2user_thread.is_alive() is False:
                coins2user_thread = Coins2User()
                coins2user_thread.start()


def add_coins(msg):
    multiple = msg["multiple"]
    if multiple <= 0:
        multiple = 0

    for x in range(0, multiple * 255):
        add_coin()
        time.sleep(0.15)


def change_server(msg):
    logger.debug("change_server: " + str(msg))

    is_changed = False
    server_file = "/home/pi/wawaji/WaController/server.ini"
    fr = open(server_file).readlines()
    lines = []
    server_url = ""
    for line in fr:
        logger.debug("from file: " + line)
        if "https://r.zhuagewawa.com" in line:
            line = line.replace("https://r.zhuagewawa.com", "https://t.zhuagewawa.com")
            logger.debug("after replace: " + line)
            lines.append(line)
            is_changed = True
        elif "https://t.zhuagewawa.com" in line:
            line = line.replace("https://t.zhuagewawa.com", "https://r.zhuagewawa.com")
            logger.debug("after replace: " + line)
            lines.append(line)
            is_changed = True
        else:
            if "url" in line:
                server_url = line
            lines.append(line)

    if is_changed is True:
        fc = open(server_file, "w")
        fc.writelines(lines)
        fc.flush()
        fc.close()

        logger.debug("is_changed: " + str(lines))
        time.sleep(5)

        os.system("sudo reboot")
    else:
        msg = {
            "ret": "ok",
            "action": "admin_settings",
            "event": "change_server",
            "user_id": admin_id,
            "room_id": room_info["roomid"],
            "adToken": admin_token,
            "server_url": server_url,
        }

        logger.debug("change_server: " + str(msg))
        web_socket_thread.send_message(json.dumps(msg), "change_server")


def get_system_info():
    temp_file = open("/sys/class/thermal/thermal_zone0/temp")
    temp = float(temp_file.read()) / 1000
    temp_file.close()
    temperature = "%.1f °C" % temp

    mem_cmd = "free -m | grep Mem | awk '{print ($4+$6)/$2}'"
    mem_sur = round(float(os.popen(mem_cmd).read()), 2) * 100
    free_memory = "%d%%" % mem_sur

    cpu_cmd = "uptime | awk '{print $8,$9,$10,$11,$12}'"
    cpu_used = os.popen(cpu_cmd).read()
    cpu_used = cpu_used.replace("load average:", "")
    cpu = "%s" % cpu_used.replace("\n", "")

    msg = {
        "ret": "ok",
        "action": "admin_settings",
        "event": "get_system_info",
        "user_id": admin_id,
        "room_id": room_info["roomid"],
        "adToken": admin_token,
        "temperature": temperature,
        "free memory": free_memory,
        "cpu": cpu,
    }

    logger.debug("get_system_info: " + str(msg))
    web_socket_thread.send_message(json.dumps(msg), "get_system_info")


def init_controller():
    global bus
    try:
        bus = smbus.SMBus(1)
        # Configue the register to default value
        for addr in range(22):
            if (addr == 0) or (addr == 1):
                bus.write_byte_data(MCP23017_ADDRESS, addr, 0xFF)
            else:
                bus.write_byte_data(MCP23017_ADDRESS, addr, 0x00)

        # configue all PinA output
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_IODIRA, 0x01)
        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPPUA, 0x01)

        bus.write_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA, 0x00)
        print("GPIOA: ", bin(bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)))
    except Exception as e:
        logger.error("init_controller Exception: " + str(e))
    except OSError as e:
        logger.error("init_controller OSError: " + str(e))
    except:
        logger.error("init_controller Error")


def init(my_dict=None):
    global with_debug
    global room_info
    global admin_token
    global web_socket_thread
    global web_socket
    global process_dict
    global jp_register
    global with_hisi

    time.sleep(1)

    if my_dict is None:
        process_dict = dict()
    else:
        process_dict = my_dict

    logger.debug("TBJ_API")

    process_dict["is_init_end"] = False

    init_controller()  # 初始化控制板
    TBJ_WaInit.init()  # 初始化房间信息

    # threading.Thread(target=TBJ_PushURL.init).start()
    with_debug = True
    process_dict["is_init_end"] = True

    cfg = configparser.RawConfigParser()
    cfg.read("/home/pi/wawaji/WaController/config.ini")

    sub = "room"
    room_info = {
        "token": cfg.get(sub, "token"),
        "domain": cfg.get(sub, "domain"),
        "name": cfg.get(sub, "name"),
        "roomid": cfg.get(sub, "roomid"),
        "websocket": cfg.get(sub, "websocket"),
        "vip": cfg.getint(sub, "vip"),
        "rtmp": {
            "pushurl": cfg.get(sub, "f_push"),
            "pullurl": cfg.get(sub, "f_pull"),
        },
        "encode_type": cfg.getint(sub, "encode_type"),
        "machine_type": cfg.getint(sub, "machine_type"),
    }

    if cfg.has_option("room", "rtmp_ip"):
        room_info["rtmp_ip"] = cfg.get(sub, "rtmp_ip")

    cf_server = configparser.RawConfigParser()
    cf_server.read("/home/pi/wawaji/WaController/server.ini")

    if cf_server.has_option("server", "jp_register"):
        jp_register = cf_server.get("server", "jp_register")

    if cf_server.has_option("server", "with_hisi"):
        with_hisi = cf_server.getint("server", "with_hisi")

    logger.debug("jp_register: " + jp_register + " with_hisi: " + str(with_hisi))

    url = cf_server.get("server", "url")
    is_release_server = url.find("https://t.zhuagewawa.com") == -1
    try_count = 0

    while True:
        try:
            conn = http.client.HTTPConnection(room_info["rtmp_ip"])

            if is_release_server:
                conn.request("GET", "/set_params?server_url=1")
            else:
                conn.request("GET", "/set_params?server_url=0")

            r = conn.getresponse()
            if r.status == 200:
                logger.debug("set server_url")
                break

            try_count = try_count + 1
            if try_count >= 5:
                break
            time.sleep(1)

        except Exception as e:
            logger.error("ipc_socket_connection Exception: " + str(e))
        except OSError as e:
            logger.error("ipc_socket_connection OSError: " + str(e))
        except:
            logger.error("ipc_socket_connection Error")

    admin_token = room_info["token"]

    # if with_hisi == 1:
    #     run_video_client_thread = RunVideoClient()
    #     run_video_client_thread.start()
    #
    # check_video_client_thread = CheckVideoClient()
    # check_video_client_thread.start()

    websocket.enableTrace(with_debug)
    web_socket = websocket.WebSocketApp(
        room_info["websocket"],
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
        on_ping=on_ping,
    )

    web_socket_thread = WebSocketThread(web_socket)
    web_socket_thread.start()
    web_socket_thread.join()


if __name__ == "__main__":
    init()
