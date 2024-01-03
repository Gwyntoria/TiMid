# coding=utf-8

# Version 1.0.0.1	Details in TBJ_Update.log
# use python3

import os
import requests
import socket
import time
import hashlib
import configparser
import logging

logger = logging.getLogger('WaController')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s', datefmt='%d %b %Y %H:%M:%S')


def get_mac(interface='eth0'):
	# Return the MAC address of the specified interface
	try:
		mac_str = open('/sys/class/net/%s/address' % interface).read().strip().replace(':', '')
	except():
		mac_str = "00:00:00:00:00:00"
	return mac_str[0:17]


def hash_code_24(combined_string):
	hash_code = 0
	if combined_string is None or len(combined_string) <= 0:
		return 0
	for x in combined_string:
		hash_code = ((hash_code << 5) - hash_code) + ord(x)
		hash_code = hash_code & 0x00FFFFFF
	return hash_code


def init():
	cf_server = configparser.RawConfigParser()
	cf_server.read('/home/pi/wawaji/WaController/server.ini')

	server_url = cf_server.get('server','url')
	server_token = "w129edsudgqKHSsjbw98eiGDsnj1qj0ad2u1hsjxzcnjfsGj"
	if cf_server.has_option('server','token'):
		server_token = cf_server.get('server','token')
	logger.debug("server_url: "+server_url+"\nserver_token: "+server_token)

	while True:
		mac = get_mac()
		token = server_token
		t = int(time.time())
		md5 = hashlib.md5()
		data = mac+token+str(t)
		md5.update(data.encode("gb2312"))
		logger.debug(str(t))
		post = {
			"mac": mac,
			"token": token,
			"ts": str(t),
			"sign": md5.hexdigest(),
			"code": hash_code_24(token+mac+str(t))
		}
		logger.debug(post)
		requests.urllib3.disable_warnings()
		r = requests.post(server_url, json=post, verify=False)

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
			logger.debug("jsonInfo: "+str(json_info))

			if 'status' in json_info and 'ok' in json_info['status']:
				room_info = json_info['room']
				if room_info is not None:
					logger.debug("get room info success")
					break

		time.sleep(60)

	dhcpcd_file = "/etc/dhcpcd.conf"
	fd = open(dhcpcd_file).readlines()
	is_ho = False
	lines = []
	for line in fd:
		if 'hostname' in line and len(line) < 10:
			line = json_info['room']['hostname']
			lines.append(line)
		elif '127.0.0.1' in line:
			pass
		elif 'Inform the DHCP' in line:
			lines.append(line)
			is_ho = True
		elif 'ip_address=' in line:
			line = 'static ip_address='+json_info['room']['ip']+'/22\n'
			lines.append(line)
		elif 'routers=' in line:
			line = 'static routers='+json_info['room']['routerip']+'\n'
			lines.append(line)
		elif 'domain_name_servers=' in line:
			line = 'static domain_name_servers='+json_info['room']['routerdns']+'\n'
			lines.append(line)
		else:
			if is_ho is True:
				lines.append(json_info['room']['hostname']+'\n')
				is_ho = False
			else:
				lines.append(line)
	fc = open(dhcpcd_file, 'w')
	fc.writelines(lines)
	fc.flush()
	fc.close()

	hosts_file = "/etc/hosts"
	fd = open(hosts_file).readlines()
	lines = []
	for line in fd:
		if '127.0.0.1' in line and 'localhost' not in line:
			pass
		else:
			lines.append(line)
	lines.append('127.0.0.1       '+json_info['room']['hostname']+'\n')

	fc = open(hosts_file, 'w')
	fc.writelines(lines)
	fc.flush()
	fc.close()

	hostname_file = "/etc/hostname"
	lines = list()
	lines.append(json_info['room']['hostname']+'\n')

	fc = open(hostname_file,'w')
	fc.writelines(lines)
	fc.flush()
	fc.close()

	frp_addr = ''
	frp_port = ''
	if 'frps' in json_info['room']:
		frps = json_info['room']['frps']
		frp_addr = frps.split(':')[0]
		frp_port = frps.split(':')[1]

	frpc_file = "/home/pi/wawaji/frp_0.13.0_linux_arm/frpc.ini"
	fd = open(frpc_file).readlines()
	lines = []
	for line in fd:
		if len(frp_addr) > 0 and 'server_addr' in line:
			lines.append('server_addr='+frp_addr+'\n')
		elif len(frp_port) > 0 and 'server_port' in line:
			lines.append('server_port='+frp_port+'\n')
		else:
			lines.append(line)
		if 'log_max_days' in line:
			lines.append('\n')
			break
	lines.append('['+json_info['room']['frpport']+']'+'\n')
	lines.append('type = tcp'+'\n')
	lines.append('local_ip = 127.0.0.1'+'\n')
	lines.append('local_port = 22'+'\n')
	lines.append('remote_port = '+json_info['room']['frpport']+'\n')
	fc = open(frpc_file, 'w')
	fc.writelines(lines)
	fc.flush()
	fc.close()

	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(('8.8.8.8', 80))
		ip = s.getsockname()[0]
	finally:
		s.close()

	config_file = "/home/pi/wawaji/WaController/config.ini"
	if os.path.exists(config_file) is True:
		os.remove(config_file)
	lines = list()
	lines.append('[room]'+'\n')
	lines.append('roomid='+json_info['room']['_id']+'\n')
	lines.append('token='+server_token+'\n')
	lines.append('domain='+json_info['room']['domain']+'\n')
	lines.append('name='+json_info['room']['name']+'\n')
	lines.append('websocket='+json_info['room']['websocket']+'\n')
	lines.append('f_pull='+json_info['room']['rtmp']['pullurl']+'\n')
	lines.append('f_push='+json_info['room']['rtmp']['pushurl']+'\n')
	if 'grab' in json_info['room']:
		lines.append('win_vol='+str(json_info['room']['grab']['win_vol'])+'\n')
		lines.append('high_vol='+str(json_info['room']['grab']['high_vol'])+'\n')
		lines.append('win_rate='+str(json_info['room']['grab']['win_rate'])+'\n')
		lines.append('low_vol='+str(json_info['room']['grab']['low_vol'])+'\n')
	room_type = 0
	if 'type' in json_info['room']:
		room_type = json_info['room']['type']
	lines.append('roomtype='+str(room_type)+'\n')
	subtype = 0
	if 'subtype' in json_info['room']:
		subtype = json_info['room']['subtype']
	lines.append('subtype='+str(subtype)+'\n')
	vip = 0
	if room_type == 1 and 'vip' in json_info['room']:
		vip = json_info['room']['vip']
	lines.append('vip='+str(vip)+'\n')
	is_jp = 0
	if vip != 0 and 'jp' in json_info['room']:
		is_jp = json_info['room']['jp']
	lines.append('JP='+str(is_jp)+'\n')
	machine_type = 0
	if 'machtype' in json_info['room']:
		machine_type = json_info['room']['machtype']
	lines.append('machine_type='+str(machine_type)+'\n')
	encode_type = 0
	if 'encodetype' in json_info['room']:
		encode_type = json_info['room']['encodetype']
	lines.append('encode_type=' + str(encode_type) + '\n')

	if 'screenshot' in json_info['room']['rtmp']:
		lines.append('f_screenshot=' + json_info['room']['rtmp']['screenshot'] + '\n')

	if 'ip' in json_info['room']['rtmp']:
		lines.append('rtmp_ip=' + json_info['room']['rtmp']['ip'] + '\n')

	if 'game' in json_info['room'] and 'count' in json_info['room']['game']:
		lines.append('player_count=' + str(json_info['room']['game']['count']) + '\n')

	monster = 0
	if 'monster' in json_info['room']:
		monster = json_info['room']['monster']
	lines.append('monster=' + str(monster) + '\n')

	# Line.append('t_push='+jsonInfo['room']['rtmpTop']['pushurl']+'\n')
	# Line.append('t_pull='+jsonInfo['room']['rtmpTop']['pullurl']+'\n')
	logger.debug('config')
	fc = open(config_file, 'w')
	fc.writelines(lines)
	fc.flush()
	fc.close()


if __name__ == '__main__':
	init()
