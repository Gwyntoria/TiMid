# -*- coding: utf-8 -*-

# Version 1.0.0.1	Details in TBJ_Update.log
# use python3

import sys
import os
import threading
import json
import websocket
import ssl

import configparser
import time
import hashlib

import requests

import TBJ_WaInit
import glob as gb
from interval import Interval
import smbus
import RPi.GPIO as GPIO

import logging

sys.setrecursionlimit(2000)
sys.path.append('../')
logger = logging.getLogger('WaController')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s', datefmt='%d %b %Y %H:%M:%S')


with_error = True
with_debug = True


def loge(msg):
    if with_error is True:
        logger.error(msg)


def logd(msg):
    if with_debug is True:
        logger.debug(msg)


GUANGYAN_PIN = 3       # guangyan detector
SHOOT_COIN_PIN = 8     # shoot the coin to play
RAIN_BRUSH_PIN = 7     # turn on/off rain brush
ADD_COINS_PIN = 5      # add more coins for playing

# GUANGYAN_PIN = 24       # guangyan detector
# SHOOT_COIN_PIN = 22     # shoot the coin to play
# RAIN_BRUSH_PIN = 27     # turn on/off rain brush
# ADD_COINS_PIN = 17      # add more coins for playing


admin_id = ''
admin_token = ''
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
check_socket_thread = None
remove_thread = None

coins_count = 0

is_waiting = False
is_restart_camera = False

action_from = 0
drop_count = 1

in_drop_thread = False
user_drop_thread = None
count_down_thread = None

process_dict = None
jp_register = ''

ping_time = 0

stream_off_time = 0
is_stream_on = 0
is_stopped_camera = False

last_tbj_type = 0
last_event_type = 0
last_special_time = 0

bus = 0

STATUS_DISCONNECTED = 0
STATUS_CONNECTED = 1
STATUS_CONNECTING = 2
STATUS_DISCONNECTING = 3

ERROR_TYPE = {
    0: '异常出币',
    1: '入币器故障',
    2: '回币器故障',
    3: '退币器故障',
    4: '推盘马达故障',
    5: '雨刷马达故障',
    6: '摇摆通道异常',
    7: '入币器空',
    8: '退币器空',
    9: '退币槽满',
    10: '推币率错误',
    11: '机台摇摆',
    12: '通道1卡币',
    13: '通道2卡币',
    14: '通道3卡币',
    15: '通道4卡币',
    16: '通道5卡币',
    17: '通道6卡币',
    18: '通道7卡币',
    19: '通道8卡币',
    20: '通道9卡币'
}


def add_coin():
    try:
        # GPIO.output(ADD_COINS_PIN, GPIO.LOW)
        # time.sleep(0.03)
        # GPIO.output(ADD_COINS_PIN, GPIO.HIGH)
        GPIO.output(ADD_COINS_PIN, GPIO.HIGH)
        time.sleep(0.025)
        GPIO.output(ADD_COINS_PIN, GPIO.LOW)

    except:
        loge('GPIO error')
        GPIO.cleanup()
        set_gpio()


def drop_coin():
    try:
        # GPIO.output(SHOOT_COIN_PIN, GPIO.LOW)
        # time.sleep(0.03)
        # GPIO.output(SHOOT_COIN_PIN, GPIO.HIGH)
        GPIO.output(SHOOT_COIN_PIN, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(SHOOT_COIN_PIN, GPIO.LOW)
    except:
        loge('GPIO error')
        GPIO.cleanup()
        set_gpio()


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
                glob_param = '/home/pi/wawaji/ScreenShot_Image/' + room_info['name'] + "-AI-*.jpg"
                img_paths = gb.glob(glob_param)
                img_paths.sort()
                while len(img_paths) > 50:
                    img_path = img_paths[0]
                    if user_in_room is False:
                        command = 'sudo rm ' + img_path
                        os.system(command)
                        del img_paths[0]
                        time.sleep(0.01)
                    else:
                        break

                time.sleep(60)

            except OSError as err:
                loge('RemoveScreenshotFiles--failed: ' + str(err))
            except:
                loge('RemoveScreenshotFiles--failed')


def handle_jp_detect():
    process_dict['jp_detected'] = False

    if user_in_room is True:
        t = int(time.time())
        post = {
            "token": room_info['token'],
            "ts": str(t),
            "jp": {
                'type': process_dict['class_type'],
                'time': t,
                'user': user_info['user_id'],
                'room': room_info['roomid'],
                'grab': user_info['grab_id'],
                'status': 1
            },
            'code': hash_code_24(room_info['token'] + room_info['roomid'] + user_info['user_id'] + user_info['grab_id'] + str(t))
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
            if 'status' in json_info and 'ok' in json_info['status'] and 'code' in json_info and json_info['code'] == 0 and 'jp' in json_info:
                msg['action'] = 'room_opt'
                msg['event'] = 'jp'
                msg['jp_type'] = process_dict['class_type']
                msg['user_id'] = user_info['user_id']
                msg['room_id'] = room_info['roomid']
                if 'doll_name' in user_info:
                    msg['doll_name'] = user_info['doll_name']
                if 'user_name' in user_info:
                    msg['user_name'] = user_info['user_name']
                if 'user_avatar' in user_info:
                    msg['user_avatar'] = user_info['user_avatar']
                msg['jp_id'] = json_info['jp']['_id']
                msg['result'] = 'ok'
                if 'plus' in json_info['jp']:
                    msg['plus'] = json_info['jp']['plus']

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

    can_send = 1

    temp_user_info = dict()
    if user_in_room is True:
        msg = {}
        for key in user_info:
            msg[key] = user_info[key]
        msg['win_coins'] = 0
        msg['grab_finished'] = 2
        msg['action'] = 'room_ret'
        msg['result'] = 'ok'

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
            process_dict['interval'] = 5

        web_socket_thread.send_message(json.dumps(msg), "handle_detect_error0")

    reason = 'AI检测持续掉币'
    need_return_coins = 0
    if error_type == 0:
        reason = 'AI检测持续掉币'
    elif error_type == 1:
        reason = 'AI检测故障'
        if process_dict['is_compensation'] is True:
            process_dict['is_compensation'] = False
            need_return_coins = 1
        if process_dict['error_code'] in Interval(0, 20):
            reason = 'AI检测故障-' + str(process_dict['error_code']) + '.' + ERROR_TYPE[process_dict['error_code']]
            process_dict['error_code'] = -1
    elif error_type == 2:
        reason = 'AI检测-重启编码器'
    elif error_type == 3:
        reason = 'AI检测-编码器HDMI视频线出错'
    elif error_type == 4:
        reason = '出币检测异常'
        if chubi_error == 0:
            chubi_error = 1
            cur_time = int(time.time())
            if (cur_time - ll_error_time) >= 30*60:
                ll_error_time = cur_time
            else:
                can_send = 0
        else:
            chubi_error = 0
            can_send = 0

    if can_send == 0:
        return

    msg = {
        "action": 'room_out',
        "event": 'machine_error',
        "reason": reason,
        "room_id": room_info['roomid']
    }

    if len(temp_user_info) > 0:
        logd("handle_detect_error: temp_user_info = " + str(temp_user_info) + ' vip = ' + str(room_info['vip']) + ' compensation_coins = ' + str(process_dict['compensation_coins']))

    if len(temp_user_info) > 0 and 'user_id' in temp_user_info and 'grab_id' in temp_user_info and need_return_coins == 1 and (room_info['vip'] >= 1 or room_info["name"][0] == 'Y'):
        msg['user_id'] = temp_user_info['user_id']
        msg['grab_id'] = temp_user_info['grab_id']
        msg['need_return_coins'] = 1
        if process_dict['compensation_coins'] > 0:
            if 'price' in temp_user_info:
                msg['price'] = temp_user_info['price']
            if 'room_type' in temp_user_info:
                msg['room_type'] = temp_user_info['room_type']
            if 'room_subtype' in temp_user_info:
                msg['room_subtype'] = temp_user_info['room_subtype']
            if 'doll_id' in temp_user_info:
                msg['doll_id'] = temp_user_info['doll_id']
            if 'doll_name' in temp_user_info:
                msg['doll_name'] = temp_user_info['doll_name']
            if 'user_name' in temp_user_info:
                msg['user_name'] = temp_user_info['user_name']
            if 'user_avatar' in temp_user_info:
                msg['user_avatar'] = temp_user_info['user_avatar']

            msg['win_coins'] = int(process_dict['compensation_coins'] * compensation_ratio)
            process_dict['compensation_coins'] = 0

    logd("handle_detect_error msg: " + str(msg))
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
            "action": 'room_opt',
            "event": 'special_event',
            "room_id": room_info['roomid'],
            "user_id": user_info['user_id'],
            "event_type": event_type
        }
        if event_type != last_event_type:
            logd("handle_tbj_type msg: " + str(msg))
            web_socket_thread.send_message(json.dumps(msg), "handle_tbj_type")
            last_special_time = time.time()

        else:
            now_time = time.time()
            if now_time-last_special_time >= 5:
                logd("handle_tbj_type msg: " + str(msg))
                web_socket_thread.send_message(json.dumps(msg), "handle_tbj_type")
                last_special_time = now_time

    if event_type != last_event_type:
        last_event_type = event_type


class TBJDetectionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        global in_detect_thread
        logd('detectionThread')
        in_detect_thread = True
        # process_dict['interval'] = 5

        sleep_time = 0
        while is_detect_support is True:
            if is_room_in is True:
                logd("TBJ detect: jp" + str(process_dict['jp_detected']))
                if process_dict['jp_detected'] is True:
                    handle_jp_detect()
                if process_dict['drop_error'] is True:
                    process_dict['drop_error'] = False
                    handle_detect_error(0)
                if process_dict['machine_error'] is True:
                    process_dict['machine_error'] = False
                    handle_detect_error(1)
                if process_dict['encode_machine_error'] == 1:
                    handle_detect_error(2)
                    process_dict['encode_machine_error'] = 0
                if process_dict['encode_machine_error'] == 2:
                    handle_detect_error(3)
                    process_dict['encode_machine_error'] = 0

                handle_tbj_type(process_dict['tbj_type'])

            time.sleep(1)
            sleep_time = sleep_time + 1

        logd('detectionThread End')
        in_detect_thread = False
        # TBJ_detection.stopDetectThread()


def restart_camera_job():
    global is_waiting
    global is_restart_camera

    logd('restart_camera_job: playing = ' + str(playing) + ", is_stream_on: " + str(is_stream_on))

    if is_stream_on == 0:
        is_restart_camera = False
        is_waiting = False
        return

    if is_restart_camera is True:
        os.system('sudo python /home/pi/wawaji/WaController/GenPushURL.py && echo "$(date) - Restart one time..." >> /home/pi/wawaji/camRestart.log')
        logd('restart end: bRestartCamera = ' + str(is_restart_camera))
        is_restart_camera = False
        is_waiting = False
    elif is_waiting is False:

        ini_cfg = configparser.RawConfigParser()
        ini_cfg.read('/home/pi/wawaji/WaController/genPushUrl.ini')
        section = 'room'

        expired_time = 0
        if ini_cfg.has_option(section, 'expiredTime'):
            expired_time = ini_cfg.getint(section, 'expiredTime')

        now_time = int(time.time())
        if (expired_time > now_time and (expired_time - now_time) <= 12 * 3600) or now_time >= expired_time:
            # if (expiredTime > nowTime and (expiredTime-nowTime) <= 60) or nowTime >= expiredTime:
            if playing is False:
                os.system('sudo python /home/pi/wawaji/WaController/GenPushURL.py && echo "$(date) - Restart one time..." >> /home/pi/wawaji/camRestart.log')
                logd('restart end when no user')
            else:
                is_waiting = True


class CheckWebSocket(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        logd('CheckWebSocket start: ' + str(int(time.time())))
        while self._running:
            if ping_time > 0:
                current_time = int(time.time())
                if (current_time - ping_time) >= 30 and web_socket_thread.get_ws_status() == STATUS_CONNECTED:
                    logd('CheckWebSocket: ping timeout')
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
        logd('WebSocketThread start: ' + str(int(time.time())))
        while self._running:
            try:
                if self._ws_status == STATUS_CONNECTING or self._ws_status == STATUS_DISCONNECTING:
                    continue

                current_time = int(time.time())
                if ping_time > 0 and (current_time - ping_time) >= 30 and self._ws_status == STATUS_CONNECTED:
                    logd('WebSocketThread: ping timeout')
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
                logd("WebSocketThread reconnect_count: " + str(self._reconnect_count))

                if self._ws_status == STATUS_DISCONNECTED:
                    self._ws_status = STATUS_CONNECTING
                    self._web_socket.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

            except Exception as e:
                loge("WebSocketThread - Exception: " + str(e))
            except:
                loge("WebSocketThread - except Error")

    def set_ws_status(self, ws_status):
        self._ws_status = ws_status

    def set_reconnect(self, count):
        if count == 0:
            self._reconnect_count = 0
        else:
            self._reconnect_count = self._reconnect_count+1

    def send_message(self, message, title):
        is_sent = False
        try:
            self._web_socket.send(message)
            is_sent = True
        except Exception as e:
            loge("WebSocketThread--" + title + "--send_message: " + str(e))
        except:
            loge("WebSocketThread--" + title + "--send_message error")
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
    logd('event: ' + a)
    eventDict[a]()


def machine_settings():
    logd('machine_settings')

    msg = {
        "ret": 'failed',
        "action": 'admin_settings',
        "event": 'machine_settings',
        "user_id": admin_id,
        "room_id": room_info['roomid'],
        "adToken": admin_token
    }

    web_socket_thread.send_message(json.dumps(msg), "machine_settings")


def move_brush():
    logd('Open Wiper')
    try:
        # GPIO.output(RAIN_BRUSH_PIN, GPIO.LOW)
        # time.sleep(0.025)
        # GPIO.output(RAIN_BRUSH_PIN, GPIO.HIGH)
        GPIO.output(RAIN_BRUSH_PIN, GPIO.HIGH)
        time.sleep(0.025)
        GPIO.output(RAIN_BRUSH_PIN, GPIO.LOW)
    except:
        GPIO.cleanup()
        set_gpio()
        # GPIO.output(RAIN_BRUSH_PIN, GPIO.LOW)
        # time.sleep(0.025)
        # GPIO.output(RAIN_BRUSH_PIN, GPIO.HIGH)
        GPIO.output(RAIN_BRUSH_PIN, GPIO.HIGH)
        time.sleep(0.025)
        GPIO.output(RAIN_BRUSH_PIN, GPIO.LOW)


def user_out_manually():
    global countdown_time
    global action_from

    if process_dict['left_coins'] >= 50 or process_dict['tbj_type'] == 7 or process_dict['tbj_type'] == 8\
            or process_dict['tbj_type'] == 70 or process_dict['tbj_type'] == 80:
        logd("user_out_manually- left_coins: " + str(process_dict['left_coins']))
        return

    logd("user_out_manually")
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
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        global in_drop_thread
        global count_down_thread
        global drop_count
        logd('UserDropThread')
        in_drop_thread = True

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
                    process_dict['interval'] = 1

                countdown_time = game_time

                drop_count -= 1
                drop_coin()
                # time.sleep(0.15)
                # add_coin()
                time.sleep(0.1)

        logd('UserDropThread End')
        in_drop_thread = False


class PlayCountDown(threading.Thread):
    def __init__(self):
        global thread_count
        threading.Thread.__init__(self)
        self._running = True
        self.name = "playCountDown" + str(thread_count)
        thread_count = thread_count + 1

    def terminate(self):
        logd('playCountDown: terminate')
        self._running = False

    def run(self):
        global countdown_time

        countdown_time = game_time
        while end_play is False:
            if countdown_time <= 0:
                end_game()
                break

            time.sleep(1)
            countdown_time = countdown_time - 1
            logd("countdownTime = " + str(countdown_time))


def end_game():
    global end_play
    global playing

    end_play = True

    logd('end_play() end_play = ' + str(end_play))
    time.sleep(3)

    if playing is True and end_play is True:
        playing = False
        return_room_info(0, 1)


class CheckCoinsCountThread(threading.Thread):
    def __init__(self):
        global thread_count
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        global playing
        global end_play
        global countdown_time

        last_time = int(time.time() * 1000)
        grab_finished = 0
        coins_count = 0
        gpio_low_start_time = 0
        is_low = 0

        logd('CheckCoinsCountThread')
        while True:
            try:
                result = GPIO.input(GUANGYAN_PIN)
                # logd("CheckCoinsCountThread-- GPIO.input result: " + str(result))
                # result = value & 0x02
                now_time = int(time.time() * 1000)
                if result == 0:
                    if is_low == 0:
                        if gpio_low_start_time != 0:
                            is_low = 1
                            time.sleep(0.001)
                        if gpio_low_start_time == 0:
                            gpio_low_start_time = int(time.time() * 1000)
                            time.sleep(0.01)
                    else:
                        time.sleep(0.001)

                    continue
                else:
                    if is_low == 1:
                        is_low = 0
                        if playing is True:
                            coins_count += 1
                            logd("CheckCoinsCountThread-- coins_count: " + str(coins_count))
                        else:
                            coins_count = 1

                    if playing is True and end_play is True:
                        playing = False
                        grab_finished = 1

                    win_coin = {'coins': str(coins_count), 'time': int(time.time() * 1000)}
                    if grab_finished == 1:
                        logd('CheckCoinsCountThread--grab_finished--wincoins: ' + str(win_coin))
                        if countdown_time > 0 and coins_count > 0:
                            end_play = False
                            countdown_time = game_time
                            grab_finished = 0
                            playing = True
                        return_room_info(coins_count, grab_finished)
                        coins_count = 0
                        last_time = now_time
                        grab_finished = 0
                    elif playing is True and now_time - last_time > 1000:
                        if coins_count > 0 and grab_finished == 0:
                            logd('CheckCoinsCountThread--wincoins: ' + str(win_coin))
                            if countdown_time > 0:
                                end_play = False
                                countdown_time = game_time
                                playing = True
                            return_room_info(coins_count, grab_finished)
                        coins_count = 0
                        last_time = now_time

                    gpio_low_start_time = 0
                    time.sleep(0.001)

            except Exception as e:
                logger.error("CheckCoinsCountThread Exception: " + str(e))
            except OSError as e:
                logger.error("CheckCoinsCountThread OSError: " + str(e))
            except:
                logger.error("CheckCoinsCountThread Error")


def return_room_info(coins, grab_finished):
    global is_waiting
    global user_in_room
    global user_info
    global is_restart_camera

    t = str(int(time.time() * 1000))
    msg = {'ts': t}
    for key in user_info:
        if key != "countdown":
            msg[key] = user_info[key]
        elif grab_finished == 0:
            msg[key] = countdown_time

    msg['win_coins'] = coins
    msg['grab_finished'] = grab_finished
    msg['action'] = 'room_ret'
    msg['result'] = 'ok'
    if grab_finished == 1:
        msg['action_from'] = action_from
        if is_detect_support is True:
            process_dict['interval'] = 5

    if grab_finished == 1:
        user_info = {}
        user_in_room = False
        if is_waiting is True:
            is_restart_camera = True
            is_waiting = False
            restart_camera_job()

    if web_socket_thread.send_message(json.dumps(msg), "return_room_info") is True:
        if process_dict['need_count_coins'] is True:
            process_dict['coins_count'] += coins


# actionDict = {'user_drop': user_drop}
eventDict = {'machine_settings': machine_settings}


def get_mac(interface='eth0'):
    # Return the MAC address of the specified interface
    try:
        mac_address = open('/sys/class/net/%s/address' % interface).read().strip().replace(':', '')
    except:
        mac_address = "00:00:00:00:00:00"
    return mac_address[0:17]


def restart_camera():
    r = os.system('sudo python /home/pi/wawaji/WaController/GenPushURL.py')
    if r == 0:
        msg = {
            "ret": 'ok',
            "action": 'admin_settings',
            "event": 'restart_camera',
            "user_id": admin_id,
            "room_id": room_info['roomid'],
            "adToken": admin_token
        }
        web_socket_thread.send_message(json.dumps(msg), "restart_camera success")
    else:
        msg = {
            "ret": 'failed',
            "action": 'admin_settings',
            "event": 'restart_camera',
            "user_id": admin_id,
            "room_id": room_info['roomid'],
            "adToken": admin_token
        }
        web_socket_thread.send_message(json.dumps(msg), "restart_camera failed")


def reboot():
    os.system('sudo reboot')


def on_open(ws):
    global playing
    global countdown_time

    if playing is True:
        countdown_time = 0

    playing = False
    web_socket_thread.set_reconnect(0)
    logd('websocket on_open')

    logd(room_info)
    if len(room_info) > 0:
        t = str(int(time.time()*1000))
        logd(room_info['roomid'] + get_mac() + t)
        md5 = hashlib.md5()
        data = room_info['roomid'] + get_mac() + t
        md5.update(data.encode("gb2312"))
        msg = {'action': 'room_in', 'room_id': room_info['roomid'], 'sign': md5.hexdigest(), 'ts': t}
        web_socket_thread.send_message(json.dumps(msg), "on_open")
        logd("ws thread start")
    else:
        logd("not roomInfo")


def on_close(ws):
    logd("websocket on_close: ")
    web_socket_thread.set_ws_status(STATUS_DISCONNECTED)
    web_socket_thread.set_reconnect(1)


def on_error(ws, error):
    logd("websocket on_error: " + str(error))
    web_socket_thread.set_ws_status(STATUS_DISCONNECTING)
    web_socket_thread.set_reconnect(1)


def on_ping(ws, ping):
    global ping_time

    logd("websocket on_ping: " + str(ping))
    ping_time = int(time.time())


def stream_off():
    global is_stopped_camera
    global stream_off_time

    logd("stream_off thread begin")
    while is_stream_on == 0:
        if stream_off_time > 0 and (int(time.time())-stream_off_time) >= 300:
            os.system('sudo supervisorctl stop WaCamera')
            is_stopped_camera = True
            break
        time.sleep(10)

    stream_off_time = 0
    logd("stream_off thread end")


def stream_switch(is_on):
    global stream_off_time
    global is_stream_on
    global is_stopped_camera

    is_stream_on = is_on

    logd("stream_switch, is_stream_on: "+str(is_stream_on)+", is_stopped_camera: "+str(is_stopped_camera)+", stream_off_time: "+str(stream_off_time))
    if is_on == 1 and is_stopped_camera is True:
        os.system('sudo python /home/pi/wawaji/WaController/GenPushURL.py && echo "stream_switch restart - $(date) - Restart one time..." >> /home/pi/wawaji/camRestart.log')
        stream_off_time = 0
        is_stopped_camera = False
    elif is_on == 0:
        if stream_off_time == 0:
            stream_off_time = int(time.time())
            threading.Thread(target=stream_off).start()


def restart_frp():
    cf_server = configparser.RawConfigParser()
    cf_server.read('/home/pi/wawaji/WaController/server.ini')

    frp_url = cf_server.get('server', 'frp')
    server_token = "w129edsudgqKHSsjbw98eiGDsnj1qj0ad2u1hsjxzcnjfsGj"
    if cf_server.has_option('server', 'token'):
        server_token = cf_server.get('server', 'token')
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
        "code": TBJ_WaInit.hash_code_24(token + mac + str(t))
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

        if 'status' in json_info and 'ok' in json_info['status']:
            room_info = json_info['room']
            if room_info is not None:
                frp_addr = ''
                frp_port = ''
                if 'frps' in room_info:
                    frps = room_info['frps']
                    frp_addr = frps.split(':')[0]
                    frp_port = frps.split(':')[1]

                frpc_file = "/home/pi/wawaji/frp_0.13.0_linux_arm/frpc.ini"
                fd = open(frpc_file).readlines()
                lines = []
                for line in fd:
                    if len(frp_addr) > 0 and 'server_addr' in line:
                        lines.append('server_addr=' + frp_addr + '\n')
                    elif len(frp_port) > 0 and 'server_port' in line:
                        lines.append('server_port=' + frp_port + '\n')
                    else:
                        lines.append(line)
                    if 'log_max_days' in line:
                        lines.append('\n')
                        break
                lines.append('[' + room_info['frpport'] + ']' + '\n')
                lines.append('type = tcp' + '\n')
                lines.append('local_ip = 127.0.0.1' + '\n')
                lines.append('local_port = 22' + '\n')
                lines.append('remote_port = ' + room_info['frpport'] + '\n')

                logger.debug("frp lines: " + str(lines))

                fc = open(frpc_file, 'w')
                fc.writelines(lines)
                fc.flush()
                fc.close()

                time.sleep(1)
                os.system('sudo supervisorctl restart frp')
                logger.debug("restart_frp")


def on_message(ws, message):
    global user_info
    global admin_id
    global admin_token
    global game_time
    global is_new_user
    global is_room_in
    global ping_time
    global drop_count
    global detect_thread
    global user_drop_thread
    global check_coins_count_thread
    global remove_thread
    global compensation_ratio
    global playing
    global end_play

    logd("msg: " + message)

    msg = json.loads(message)
    if 'action' in msg:
        if msg['action'] in 'admin_settings':
            admin_token = msg['adToken']
            admin_id = msg['user_id']
            if msg['event'] in 'machine_settings':
                machine_settings()
            elif msg['event'] in 'restart_camera':
                restart_camera()
            elif msg['event'] in 'reboot':
                reboot()
            elif msg['event'] in 'get_systeminfo':
                get_system_info()
            elif msg['event'] in 'change_server':
                change_server(msg)
            elif msg['event'] in 'add_coins':
                threading.Thread(target=add_coins, args=(msg,)).start()
            elif msg['event'] in 'restart_frp':
                restart_frp()
        elif msg['action'] in 'user_opt':
            if msg['event'] in 'move_brush':
                # move_brush()
                threading.Thread(target=move_brush).start()
            elif msg['event'] in 'user_out_manually':
                user_out_manually()
        elif msg['action'] in 'admin_opt':
            if msg['event'] in 'stream_switch':
                print("stream_switch")
                # stream_switch(msg['on'])
        elif 'room_in' in msg['action']:
            is_room_in = True
            web_socket_thread.set_ws_status(STATUS_CONNECTED)
            ping_time = int(time.time())
            if is_detect_support is True:
                process_dict['interval'] = 5

        elif 'room_in' not in msg['action'] and 'room_out' not in msg['action']:
            if 'user_drop' in msg['action']:
                if len(user_info) <= 0 or msg['user_id'] != user_info['user_id']:
                    is_new_user = True
                    playing = True
                    end_play = False
                    drop_count = 0
                else:
                    is_new_user = False

                game_time = msg['countdown']
                if 'count' in msg:
                    drop_count += msg['count']
                else:
                    drop_count += 1

                if 'return_rate' in msg:
                    compensation_ratio = msg['return_rate']
                    if isinstance(compensation_ratio, float) is False:
                        compensation_ratio = 0.35
                else:
                    compensation_ratio = 0.35

                if compensation_ratio <= 0 or compensation_ratio >= 1:
                    compensation_ratio = 0.35

                user_info = msg

            if len(user_info) > 2 and msg['user_id'] == user_info['user_id']:
                if len(user_info) > 2 and msg['user_id'] == user_info['user_id']:
                    if user_drop_thread is None or user_drop_thread.is_alive() is False:
                        user_drop_thread = UserDropThread()
                        user_drop_thread.start()

                    # threading.Thread(target=action, args=[msg['action'], drop_count]).start()
                # action(msg['action'])

        if is_detect_support is True:
            if detect_thread is None or detect_thread.is_alive() is False:
                detect_thread = TBJDetectionThread()
                detect_thread.start()

            if room_info['encode_type'] == 1 and (remove_thread is None or remove_thread.is_alive() is False):
                remove_thread = RemoveScreenshotFiles()
                remove_thread.start()

        if check_coins_count_thread is None or check_coins_count_thread.is_alive() is False:
            check_coins_count_thread = CheckCoinsCountThread()
            check_coins_count_thread.start()


def add_coins(msg):
    multiple = msg['multiple']
    if multiple <= 0:
        multiple = 0

    for x in range(0, multiple * 255):
        # GPIO.output(ADD_COINS_PIN, GPIO.LOW)
        # time.sleep(0.025)
        # GPIO.output(ADD_COINS_PIN, GPIO.HIGH)
        GPIO.output(ADD_COINS_PIN, GPIO.HIGH)
        time.sleep(0.04)
        GPIO.output(ADD_COINS_PIN, GPIO.LOW)
        time.sleep(0.15)


def change_server(msg):
    logd('change_server: ' + str(msg))

    is_changed = False
    server_file = "/home/pi/wawaji/WaController/server.ini"
    fr = open(server_file).readlines()
    lines = []
    server_url = ''
    for line in fr:
        logger.debug("from file: " + line)
        if 'https://r.zhuagewawa.com' in line:
            line = line.replace('https://r.zhuagewawa.com', 'https://t.zhuagewawa.com')
            logger.debug("after replace: " + line)
            lines.append(line)
            is_changed = True
        elif 'https://t.zhuagewawa.com' in line:
            line = line.replace('https://t.zhuagewawa.com', 'https://r.zhuagewawa.com')
            logger.debug("after replace: " + line)
            lines.append(line)
            is_changed = True
        else:
            if 'url' in line:
                server_url = line
            lines.append(line)

    if is_changed is True:
        fc = open(server_file, 'w')
        fc.writelines(lines)
        fc.flush()
        fc.close()

        logd('is_changed: ' + str(lines))
        time.sleep(5)

        os.system('sudo reboot')
    else:
        msg = {
            "ret": 'ok',
            "action": 'admin_settings',
            "event": 'change_server',
            "user_id": admin_id,
            "room_id": room_info['roomid'],
            "adToken": admin_token,
            "server_url": server_url
        }

        logd('change_server: ' + str(msg))
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
    cpu_used = cpu_used.replace('load average:', '')
    cpu = "%s" % cpu_used.replace('\n', '')

    msg = {
        "ret": 'ok',
        "action": 'admin_settings',
        "event": 'get_system_info',
        "user_id": admin_id,
        "room_id": room_info['roomid'],
        "adToken": admin_token,
        "temperature": temperature,
        "free memory": free_memory,
        "cpu": cpu
    }

    logd('get_system_info: ' + str(msg))
    web_socket_thread.send_message(json.dumps(msg), "get_system_info")


def set_gpio():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(SHOOT_COIN_PIN, GPIO.OUT)
    GPIO.setup(ADD_COINS_PIN, GPIO.OUT)
    GPIO.setup(RAIN_BRUSH_PIN, GPIO.OUT)
    GPIO.setup(GUANGYAN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # GPIO.output(SHOOT_COIN_PIN, GPIO.HIGH)
    GPIO.output(SHOOT_COIN_PIN, GPIO.LOW)
    # GPIO.output(ADD_COINS_PIN, GPIO.HIGH)
    # GPIO.output(RAIN_BRUSH_PIN, GPIO.HIGH)
    GPIO.output(ADD_COINS_PIN, GPIO.LOW)
    GPIO.output(RAIN_BRUSH_PIN, GPIO.LOW)


def init(my_dict=None):
    global with_debug
    global room_info
    global admin_token
    global web_socket_thread
    global web_socket
    global process_dict
    global jp_register

    if my_dict is None:
        logd("")
        process_dict = dict()
    else:
        process_dict = my_dict

    logger.debug("TBJ_API")

    process_dict['is_init_end'] = False
    TBJ_WaInit.init()
    # threading.Thread(target=TBJ_PushURL.init).start()
    with_debug = True
    process_dict['is_init_end'] = True

    cfg = configparser.RawConfigParser()
    cfg.read('/home/pi/wawaji/WaController/config.ini')

    sub = 'room'
    room_info = {
        "token": cfg.get(sub, 'token'),
        "domain": cfg.get(sub, 'domain'),
        "name": cfg.get(sub, 'name'),
        "roomid": cfg.get(sub, 'roomid'),
        "websocket": cfg.get(sub, 'websocket'),
        "vip": cfg.getint(sub, 'vip'),
        "rtmp": {
            "pushurl": cfg.get(sub, 'f_push'),
            "pullurl": cfg.get(sub, 'f_pull'),
        },
        "encode_type": cfg.getint(sub, 'encode_type'),
        "machine_type": cfg.getint(sub, 'machine_type')
    }

    cf_server = configparser.RawConfigParser()
    cf_server.read('/home/pi/wawaji/WaController/server.ini')

    if cf_server.has_option('server', 'jp_register'):
        jp_register = cf_server.get('server', 'jp_register')
    logger.debug("jp_register: " + jp_register)

    admin_token = room_info['token']
    set_gpio()

    websocket.enableTrace(with_debug)
    web_socket = websocket.WebSocketApp(room_info['websocket'], on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open, on_ping=on_ping)
    web_socket_thread = WebSocketThread(web_socket)
    web_socket_thread.start()
    web_socket_thread.join()


if __name__ == '__main__':
    init()
