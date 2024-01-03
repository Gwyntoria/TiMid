# -*- coding: utf-8 -*-

# Version 1.0.0.1	Details in TBJ_Update.log
# use python3

import threading
import time
import smbus
import logging

logger = logging.getLogger('TBJ_Coins')

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s', datefmt='%d %b %Y %H:%M:%S')


with_error = True
with_debug = True

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


def loge(msg):
    if with_error is True:
        logger.error(msg)


def logd(msg):
    if with_debug is True:
        logger.debug(msg)


# check_coins_count_thread = None
# process_dict = None


class CheckCoinsCountThread(threading.Thread):    
    global process_dict
    
    def __init__(self):
        threading.Thread.__init__(self)
        self._running = True

    def run(self):
        process_dict['coins_count'] = 0
        process_dict['gpio_low_start_time'] = 0

        process_dict['can_check_score'] = 0
        process_dict['check_score_coins_count'] = 0

        logd('CheckCoinsCountThread')
        bus = smbus.SMBus(1)

        while True:
            try:
                # logd("CheckCoinsCountThread-- read_byte_data_start_time: " + str(int(time.time() * 1000)))
                input_a = bus.read_byte_data(MCP23017_ADDRESS, MCP23017_GPIOA)
                result = input_a & 0x01
                if result == 0:
                    if process_dict['gpio_low_start_time'] == 0:
                        process_dict['gpio_low_start_time'] = int(time.time() * 1000)
                else:
                    if process_dict['gpio_low_start_time'] != 0:
                        process_dict['gpio_low_start_time'] = 0
                        process_dict['coins_count'] += 1

                        if process_dict['can_check_score'] == 0:
                            process_dict['can_check_score'] = 1
                            
                        if process_dict['can_check_score'] == 1:
                            process_dict['check_score_coins_count'] += 1

                time.sleep(0.001)

            except Exception as e:
                logger.error("CheckCoinsCountThread Exception: " + str(e))
            except OSError as e:
                logger.error("CheckCoinsCountThread OSError: " + str(e))
            except:
                logger.error("CheckCoinsCountThread Error")


def init(my_dict=None):
    global check_coins_count_thread
    global process_dict

    time.sleep(2)

    if my_dict is None:
        process_dict = dict()
    else:
        process_dict = my_dict

    logger.debug("TBJ_Coins")

    while True:
        check_coins_count_thread = CheckCoinsCountThread()
        check_coins_count_thread.start()
        check_coins_count_thread.join()
        logd("TBJ_Coins---thread exit")


if __name__ == '__main__':
    init()
