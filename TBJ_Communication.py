"""
接收游戏主机直传的关于错误和奖励的心跳包信息，并作出相应解析

TBJ_Communication 的对象可以通过相应接口访问错误类型，奖励类型，获币数目等信息
"""

from collections import deque
from errno import errorcode
import logging
import threading
from numpy import true_divide
import serial
import sys
import time

logger = logging.getLogger("TBJ_Communication")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%d %b %Y %H:%M:%S",
)


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
    11: "Splash", # 0x 0B
    70: "DDL",  # 0x46 叠叠乐（状态中）
    80: "XML",  # 0x50 小玛莉（状态中）
    90: "Congrats", # 0x5A
}

TBJ_ERROR_TYPE = {
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
    255: "死机", # 0x00FF
}

MESSAGE_TYPE = {
    "error": 0xFF,
    "ping": 0x01,
    "bonus": 0x10,
}

BONUS_TYPE = (
    1,
    2,
    3,
    4,
    7,
    8,
    9,
    11,
    70,
    80,
)


class TbjSerialCommunication:
    def __init__(
        self,
        tbj_serial=serial.Serial("/dev/ttyUSB0", 9600, timeout=5 / 1000, stopbits=1, rtscts=True),
        pack_header=0xAA,
    ) -> None:
        self._tbj_type = -1
        self._error_code = -1
        self._total_score = 0
        self._gain_coins = 0
        self._left_coins = 0
        self._serial_data = []
        self.tbj_serial = tbj_serial
        self._pack_header = pack_header
        self._accept_data_thread = threading.Thread(target=self._accept_data)
        self._accept_working = False
        self._lock = threading.Lock()

    def get_tbj_type(self) -> int:
        return self._tbj_type

    def get_error_code(self):
        return self._error_code

    def get_total_score(self):
        return self._total_score

    def get_gain_coins(self):
        gain_coins = self._gain_coins
        left_coins = self._left_coins
        return {"gain_coins": gain_coins, "left_coins": left_coins}

    def close_serail_dev(self):
        self.tbj_serial.close()

    def reconnect_serial(self):
        count = 0
        while True:
            try:
                # 重新打开串口
                self.tbj_serial.open()
                logger.debug("Serial port reopened successfully.")
                break
            except serial.SerialException as e:
                count += 1
                logger.error(f"Reconnection failed: {e}, count: {count}")
                if count > 5:
                    return -1
                time.sleep(500 / 1000)

        return 0

    def _accept_data(self):
        while self._accept_working:
            try:
                serial_data = self.tbj_serial.read(8)
            except serial.SerialException as e:
                logger.error(f"SerialException: {e}")
                self.close_serail_dev()
                self.reconnect_serial()
                continue
            
            if not serial_data:
                # with self._lock:
                #     if (len(self._serial_data) > 0):
                #         self._serial_data.clear()
                # logger.error("serial_data is empty")
                time.sleep(100 / 1000)
                continue

            with self._lock:
                serial_data = [int(byte) for byte in serial_data]
                self._serial_data = serial_data
                # logger.debug(self._serial_data)

                # serial_data_hex = [hex(num) for num in self._serial_data]
                # logger.debug(f"serial_data_hex:\n{serial_data_hex}\n")

            time.sleep(50 / 1000)

    def start_accept_serial_data(self):
        self._accept_working = True
        self._accept_data_thread.start()

    def stop_accept_serial_data(self):
        self._accept_working = False
        if self._accept_data_thread.is_alive():
            self._accept_data_thread.join()

    def clear_serial_data(self):
        with self._lock:
            self._serial_data.clear()

    def _read_one_pack(self) -> list:
        with self._lock:
            pack_data = self._serial_data.copy()
        return pack_data

    def _crc8(self, data):
        """generate 1 octet checksum

        Args:
            data (bytes): data stream

        Returns:
            int: generated checksum
        """

        crc8_polynomial = 0x07
        crc = 0

        for byte in data:
            crc ^= byte

            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ crc8_polynomial
                else:
                    crc <<= 1

        return crc & 0xFF

    def _check_serial_data(self) -> int:
        pack_data = self._read_one_pack()

        pack_data_len = len(pack_data)
        if pack_data_len != 8:
            logger.debug(f"serial_data_len({pack_data_len})")
            return -1

        pack_data_hex = [hex(num) for num in pack_data]
        logger.debug(f"pack_data_hex: {pack_data_hex}")

        # Check the package head byte
        pack_header = pack_data[0] & 0xFF
        if pack_header != 0xAA:
            logger.error(f"pack_header({pack_header}) is wrong")
            return -1

        # Check the message type
        msg_type = pack_data[1] & 0xFF
        if msg_type not in MESSAGE_TYPE.values():
            logger.error(f"msg_type({msg_type}) is wrong")
            return -1

        # Check the checksum
        checksum_recv = pack_data.pop()
        checksum_calc = self._crc8(pack_data)
        logger.debug(f"checksum_recv: {hex(checksum_recv)}")
        logger.debug(f"checksum_calc: {hex(checksum_calc)}")

        if checksum_recv != checksum_calc:
            logger.debug(f"checksum({hex(checksum_recv)}) is wrong")
            return -1

        return 0

    def deal_serial_data(self) -> int:
        # Check whether there are any errors in the data
        ret = self._check_serial_data()
        if ret < 0:
            return -1

        pack_data = self._read_one_pack()

        # Deal different message type
        msg_type = int(pack_data[1]) & 0xFF
        tbj_type = int(pack_data[2]) & 0xFF

        if msg_type == MESSAGE_TYPE["error"]:
            if tbj_type != 0x05:
                logger.error(f"tbj_type({tbj_type}) is wrong")
                return -1

            error_code = (pack_data[3] << 8 | pack_data[4]) & 0xFFFF

            if error_code not in TBJ_ERROR_TYPE.keys():
                logger.error(f"error_type({error_code}) was not defined!")
                return -1

            self._error_code = error_code
            # logger.debug("error_type: ", self._error_type)

        elif msg_type == MESSAGE_TYPE["ping"]:
            if tbj_type != 0x06:
                logger.error(f"tbj_type({tbj_type}) is wrong")
                return -1

        elif msg_type == MESSAGE_TYPE["bonus"]:
            if tbj_type not in BONUS_TYPE:
                logger.error(f"tbj_type:{tbj_type} is wrong")
                return -1

            self._gain_coins = (pack_data[3] << 8 | pack_data[4]) & 0xFFFF
            self._left_coins = (pack_data[5] << 8 | pack_data[6]) & 0xFFFF

        else:
            logger.error("message type is wrong")
            return -1

        self._tbj_type = tbj_type

        return tbj_type


if __name__ == "__main__":
    ret = 0
    # tbj_serial = serial.Serial("/dev/ttyUSB0", 115200, timeout=20 / 1000, stopbits=1)
    tbj_serial_communication = TbjSerialCommunication()
    tbj_serial_communication.start_accept_serial_data()
    try:
        while True:
            tbj_type = tbj_serial_communication.deal_serial_data()

            if tbj_type > 0:
                print("tbj_type:        ", tbj_serial_communication._tbj_type)
                print("error_type:      ", tbj_serial_communication._error_code)
                print("total_score:     ", tbj_serial_communication._total_score)
                print("obtained_score:  ", tbj_serial_communication._gain_coins)
                print()

            tbj_serial_communication.clear_serial_data()
            time.sleep(50 / 1000)

    except KeyboardInterrupt:
        tbj_serial_communication.close_serail_dev()
