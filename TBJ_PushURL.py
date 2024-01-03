# coding=utf-8

# Version 1.0.0.1	Details in TBJ_Update.log
# use python3


import os
import configparser
import time
import hashlib
import http.client
import logging

logger = logging.getLogger('WaController')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [line:%(lineno)d] %(levelname)s %(message)s', datefmt='%d %b %Y %H:%M:%S')


def create_ws_md5(key, uri, ws_abs_time):
	logger.debug("key+uri+ws_abs_time: " + key + uri + ws_abs_time)
	m = hashlib.md5()
	data = key + uri + ws_abs_time
	m.update(data.encode("gb2312"))
	return m.hexdigest().lower()


def create_ws_url(key, url, ws_abs_time):
	if len(url) <= 0:
		return ''

	index = url.find('com/')
	if index <= -1:
		return ''
	else:
		uri = url[index+3:len(url)]
		ws_secret = create_ws_md5(key, uri, ws_abs_time)
		return url+'?wsSecret='+ws_secret+'&wsABSTime='+ws_abs_time


def get_web_server_time(host):
	conn = http.client.HTTPConnection(host)
	conn.request("GET", "/")
	r = conn.getresponse()
	ts = r.getheader('date')
	local_time = time.mktime(time.strptime(ts[5:], "%d %b %Y %H:%M:%S GMT")) + (8 * 60 * 60)
	l_time = time.gmtime(local_time)
	dat = 'date -u -s "%d-%d-%d %d:%d:%d" ' % (l_time.tm_year,l_time.tm_mon,l_time.tm_mday,l_time.tm_hour,l_time.tm_min,l_time.tm_sec)
	logger.debug("web server time: "+dat)
	os.system(dat)


def init():
	get_web_server_time('i.zhuagewawa.com')

	cfg = configparser.RawConfigParser()
	cfg.read('/home/pi/wawaji/WaController/config.ini')
	sub = 'room'

	room_type = 0
	if cfg.has_option(sub, 'roomtype'):
		room_type = int(cfg.get(sub, 'roomtype'))
	if room_type == 2:
		return

	subtype = 0
	if cfg.has_option(sub, 'subtype'):
		subtype = int(cfg.get(sub, 'subtype'))
	vip = 0
	if cfg.has_option(sub, 'vip'):
		vip = int(cfg.get(sub, 'vip'))
	jp = 0
	if cfg.has_option(sub, 'JP'):
		jp = int(cfg.get(sub,'JP'))

	room_name_upper = cfg.get(sub, 'name').upper()
	logger.debug("room_name: "+room_name_upper+' room_type: '+str(room_type)+' subtype: '+str(subtype)+' vip: '+str(vip)+' JP: '+str(jp))

	push_url = cfg.get(sub, 'f_push')

	cf_server = configparser.RawConfigParser()
	cf_server.read('/home/pi/wawaji/WaController/server.ini')
	md5key = "qwe12ASQI1209LPL!~#OKDOlp.[p[l-12oqdkdlm/'sc,f]120"
	if cf_server.has_option('server', 'md5key'):
		md5key = cf_server.get('server', 'md5key')

	server_type = 0
	if cf_server.has_option('server', 'servertype'):
		server_type = int(cf_server.get('server','servertype'))

	if server_type == 0 or server_type == 1:
		if room_type == 1 or room_type == 0:
			expired_time = int(time.time() + 24 * 3600 * 365)
			push_url = create_ws_url(md5key, push_url, str(expired_time))

			if room_type == 1:
				config_file = "/home/pi/wawaji/WaController/genPushUrl.ini"
				if os.path.exists(config_file):
					os.remove(config_file)
				lines = list()
				lines.append('[room]'+'\n')
				lines.append('expiredTime='+str(expired_time)+'\n')
				lines.append('pushUrl='+push_url+'\n')
				fc = open(config_file, 'w')
				fc.writelines(lines)
				fc.flush()
				fc.close()

	logger.debug("pushurl: "+push_url)

	had = False
	update_supervisorctl = False

	camera_config_file = "/etc/supervisor/conf.d/WaCamera.conf"
	if len(push_url) > 0:
		lines = list()
		if os.path.exists(camera_config_file) is True:
			fr = open(camera_config_file).readlines()
			for line in fr:
				logger.debug("from file: "+line)

				if room_type == 1:
					if room_name_upper[0] == 'Y':
						if 'annotation-text=' in line and '#' not in line:
							if subtype == 1:
								line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\'' + room_name_upper + ' \' annotation-text-size=32 annotation-text-bg-colour=0xEE35FF annotation-text-colour=0x000000\n'
							else:
								if vip == 0:
									line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\'' + room_name_upper + ' \' annotation-text-size=32 annotation-text-bg-colour=0x3300F0 annotation-text-colour=0x000000\n'
								else:
									if jp == 1:
										line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\'' + room_name_upper + ' \' annotation-text-size=32 annotation-text-bg-colour=0xE0E000\n'
									else:
										line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\'' + room_name_upper + ' \' annotation-text-size=32 annotation-text-bg-colour=0xFF4700\n'

							update_supervisorctl = True

						if 'rtmpsink location=' in line and '#' not in line:  # this line is not comment
							had = True
							if push_url not in line:
								line = '        ! rtmpsink location=' + '\'' + push_url + '\'' + '\n'
								update_supervisorctl = True
								logger.debug("rtmpsink: " + line)

						if 'sharpness' in line and '#' not in line:
							line = '        keyframe-interval=30 sharpness=100 sensor-mode=4 bitrate=0 awb-mode=6 saturation=3 quantisation-parameter=35 metering-mode=0 exposure-compensation=0 do-timestamp=true rotation=90\n'
							update_supervisorctl = True
					else:
						if 'annotation-text=' in line and '#' not in line:
							if subtype == 1:
								line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\''+room_name_upper+' \' annotation-text-size=32 annotation-text-bg-colour=0xEE35FF annotation-text-colour=0x000000\n'
							else:
								if vip == 0:
									line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\''+room_name_upper+' \' annotation-text-size=32 annotation-text-bg-colour=0x3300F0 annotation-text-colour=0x000000\n'
								else:
									if jp == 1:
										line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\''+room_name_upper+' \' annotation-text-size=32 annotation-text-bg-colour=0xE0E000\n'
									else:
										line = '        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\''+room_name_upper+' \' annotation-text-size=32 annotation-text-bg-colour=0xFF4700\n'

							update_supervisorctl = True

						if 'rtmpsink location=' in line and '#' not in line:		#this line is not comment
							had = True
							if push_url not in line:
								line = '        -e flvmux name=mux ! rtmpsink location=' + '\'' + push_url + '\'' + '\n'
								update_supervisorctl = True
								logger.debug("rtmpsink: "+line)

						if 'sharpness' in line and '#' not in line:
							line = '        keyframe-interval=25 sharpness=80 bitrate=2000000 saturation=5 exposure-compensation=0 do-timestamp=true rotation=90\n'
							update_supervisorctl = True

				lines.append(line)
		if not had:
			logger.debug("WaCamera.conf is opened or not exist")
			update_supervisorctl = False
			line = ""
			if room_type == 1:
				if room_name_upper[0] == 'Y':
					update_supervisorctl = True

					if subtype == 1:
						timestamp_color = ' annotation-text-bg-colour=0xEE35FF annotation-text-colour=0x000000\n'
					else:
						if vip == 0:
							timestamp_color = ' annotation-text-bg-colour=0x3300F0 annotation-text-colour=0x000000\n'
						else:
							if jp == 1:
								timestamp_color = ' annotation-text-bg-colour=0xE0E000\n'
							else:
								timestamp_color = ' annotation-text-bg-colour=0xFF4700\n'

					line = '[program:WaCamera]\ncommand=/usr/bin/gst-launch-1.0\n        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\'' + room_name_upper + ' \' annotation-text-size=32' + timestamp_color + '        keyframe-interval=30 sharpness=100 sensor-mode=4 bitrate=0 awb-mode=6 saturation=3 quantisation-parameter=35 metering-mode=0 exposure-compensation=0 do-timestamp=true rotation=90\n        ! \'video/x-h264,width=720,height=1280,framerate=30/1,profile=high\' ! h264parse ! flvmux name=mux\n        ! rtmpsink location=\'' + push_url + '&record=mp4&record_interval=7200\'\n        alsasrc device="hw:0,0" ! queue ! voaacenc bitrate=48000 ! aacparse ! queue ! mux.\n' + 'stdout_logfile=/home/pi/wawaji/WaCamera.log\nredirect_stderr=true\nautostart=true\nautorestart=true\nstopasgroup=true\nkillasgroup=true\n'
				else:
					update_supervisorctl = True
					if subtype == 1:
						timestamp_color = ' annotation-text-bg-colour=0xEE35FF annotation-text-colour=0x000000\n'
					else:
						if vip == 0:
							timestamp_color = ' annotation-text-bg-colour=0x3300F0 annotation-text-colour=0x000000\n'
						else:
							if jp == 1:
								timestamp_color = ' annotation-text-bg-colour=0xE0E000\n'
							else:
								timestamp_color = ' annotation-text-bg-colour=0xFF4700\n'

					line = '[program:WaCamera]\ncommand=/usr/bin/gst-launch-1.0\n        -e flvmux name=mux ! rtmpsink location=\''+push_url+'\'\n        -v rpicamsrc preview=0 annotation-mode=custom-text+date+time+black-background annotation-text=\''+room_name_upper+' \' annotation-text-size=32'+timestamp_color+'        keyframe-interval=25 sharpness=80 bitrate=2000000 saturation=5 exposure-compensation=0 do-timestamp=true rotation=90\n        ! \'video/x-h264,width=720,height=1280,framerate=30/1,profile=high\' ! h264parse ! queue ! mux.\n        alsasrc device="hw:0,0" ! queue ! voaacenc bitrate=48000 ! aacparse ! queue ! mux.\n'+'stdout_logfile=/home/pi/wawaji/WaCamera.log\nredirect_stderr=true\nautostart=true\nautorestart=true\nstopasgroup=true\nkillasgroup=true\n'

			logger.debug("WaCamera.conf new Contents: "+line)

			if len(line) > 0:
				lines.append(line)

		if len(lines) > 0:
			fw = open(camera_config_file, 'w')
			fw.writelines(lines)
			fw.flush()
			fw.close()

	if update_supervisorctl is True:
		# time.sleep(1)
		os.system('sudo supervisorctl update')
		logger.debug("updateSupervisorctl")
		time.sleep(5)
		os.system('sudo supervisorctl restart WaCamera')


if __name__ == '__main__':
	init()



