import base64
import cv2
import datetime
import logging
import numpy as np
import subprocess
import time
from datetime import datetime
from fischertechnik.camera.VideoStream import VideoStream
from fischertechnik.controller.Motor import Motor
from fischertechnik.machine_learning.ObjectDetector import ObjectDetector
from lib.camera import *
from lib.controller import *
from lib.display import *
from lib.node_red import *
from lib.node_red import *

tag = None
value = None
num = None
color = None
ts = None
filename = None
sat = None
hue = None
duration = None
prob = None
keytext = None
pos = None
frame = None
ts_process0 = None
detector = None
ts_process1 = None
result = None
ts_process = None
key = None
log = None


def MakePictureRunKiReturnFoundPart():
    global tag, value, num, color, ts, filename, sat, hue, duration, prob, keytext, pos, frame, ts_process0, detector, ts_process1, result, ts_process, key, log
    reset_inteface()
    TXT_SLD_M_O4_led.set_brightness(int(512))
    time.sleep(0.2)
    TXT_SLD_M_O4_led.set_brightness(int(30))
    time.sleep(0.8)
    duration = (time.time() * 1000)
    num = 4
    prob = 0
    keytext = 'No feature found'
    pos = ''
    display.set_attr("part_pass_fail.text", str(containInHTML('i', 'processing')))
    frame = TXT_SLD_M_USB1_1_camera.read_frame()
    #get color from frame
    color = (np.mean(frame[ 80:120,  100:240], axis=(0, 1)))
    color = cv2.cvtColor(np.uint8([[[color[0],color[1],color[2]]]]),cv2.COLOR_BGR2HLS)[0][0]
    hue = color[0] # range 0-180
    sat = color[2] # range 0-255
    TXT_SLD_M_C1_motor_step_counter.reset()
    TXT_SLD_M_M1_encodermotor.set_speed(int(160), Motor.CCW)
    TXT_SLD_M_M1_encodermotor.set_distance(int(200))
    ts_process0 = (time.time() * 1000)
    detector = ObjectDetector('/opt/ft/workspaces/machine-learning/object-detection/sorting_line/model.tflite', '/opt/ft/workspaces/machine-learning/object-detection/sorting_line/labels.txt')
    ts_process1 = (time.time() * 1000)
    result = detector.process_image(frame)
    ts_process = (time.time() * 1000)
    print('processing time: {:.0f} ms {:.0f} ms'.format(ts_process1 - ts_process0, ts_process - ts_process1))
    color = get_color()
    TXT_SLD_M_O4_led.set_brightness(int(0))
    print(result)
    if len(result) > 0:
        prob = result[0]['probability']
        pos = result[0]['position']
        key = result[0]['label']
        if True:
            log = open('/opt/ft/workspaces/log.txt', 'a', encoding='utf8')
            log.write('{} ms: {:.0f} {:.0f} key: {} prob: {:.2f} color: {}'.format(timestamp(), ts_process1 - ts_process0, ts_process - ts_process1, key, prob, color) + '\n')
            log.close()
        keytext = ''
        if key == 'CRACK':
            keytext = 'Cracks in Workpiece'
        elif key == 'MIPO1':
            keytext = '1x milled pocket'
        elif key == 'MIPO2':
            keytext = '2x milled pocket'
        elif key == 'BOHO':
            keytext = 'Round hole'
        elif key == 'BOHOEL':
            keytext = 'Hole elyptical'
        elif key == 'BOHOMIPO1':
            keytext = 'Hole and 1x milled pocket'
        elif key == 'BOHOMIPO2':
            keytext = 'Hole and 2x milled pocket'
        elif key == 'BLANK':
            keytext = 'Workpiece without features'
        else:
            keytext = key
        print('{} {} {} {} {} {}'.format(key, keytext, num, prob, pos, color))
        if key == 'BOHO' and color == 1:
            num = 1
            display.set_attr("white.active", str(True).lower())
            display.set_attr("part_pass_fail.text", str(containInHTML('b', "Workpiece <font color='#88ff88'> PASSED</font>")))
        elif key == 'MIPO2' and color == 2:
            num = 2
            display.set_attr("red.active", str(True).lower())
            display.set_attr("part_pass_fail.text", str(containInHTML('b', "Workpiece <font color='#88ff88'> PASSED</font>")))
        elif key == 'BOHOMIPO2' and color == 3:
            num = 3
            display.set_attr("blue.active", str(True).lower())
            display.set_attr("part_pass_fail.text", str(containInHTML('b', "Workpiece <font color='#88ff88'> PASSED</font>")))
        else:
            num = 4
            display.set_attr("fail.active", str(True).lower())
            display.set_attr("part_pass_fail.text", str(containInHTML('b', "Workpiece <font color='#ff8888'>FAILED</font>")))
    else:
        display.set_attr("part_pass_fail.text", str(containInHTML('b', "Workpiece <font color='#ff8888'>FAILED</font>")))
    duration = (time.time() * 1000) - duration
    saveFileandPublish()
    return num


def reset_inteface():
    global tag, value, num, color, ts, filename, sat, hue, duration, prob, keytext, pos, frame, ts_process0, detector, ts_process1, result, ts_process, key, log
    display.set_attr("part_pass_fail.text", str(containInHTML('i', 'Not analysed yet')))
    display.set_attr("red.active", str(False).lower())
    display.set_attr("white.active", str(False).lower())
    display.set_attr("blue.active", str(False).lower())
    display.set_attr("fail.active", str(False).lower())


def containInHTML(tag, value):
    global num, color, ts, filename, sat, hue, duration, prob, keytext, pos, frame, ts_process0, detector, ts_process1, result, ts_process, key, log
    return ''.join([str(x) for x in ['<', tag, '>', value, '</', tag, '>']])


def get_color():
    global tag, value, num, color, ts, filename, sat, hue, duration, prob, keytext, pos, frame, ts_process0, detector, ts_process1, result, ts_process, key, log
    if hue >= 85 and hue < 130 and sat >= 40:
        color = 3
    elif (hue >= 130 and hue <= 180 or hue >= 0 and hue < 15) and sat >= 40:
        color = 2
    else:
        color = 1
    return color


def timestamp():
    global tag, value, num, color, ts, filename, sat, hue, duration, prob, keytext, pos, frame, ts_process0, detector, ts_process1, result, ts_process, key, log
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return ts


def saveFileandPublish():
    global tag, value, num, color, ts, filename, sat, hue, duration, prob, keytext, pos, frame, ts_process0, detector, ts_process1, result, ts_process, key, log
    filename = '/opt/ft/workspaces/last-image.png'
    if(pos != ""):
        image = cv2.rectangle(frame, (pos[0], pos[1]), (pos[2], pos[3]), (180,105,0), 2)
    logging.debug("write png file: ", filename)
    cv2.imwrite(filename, frame)
    subprocess.Popen(['chmod', '777', filename])

    with open(filename, "rb") as img_file:
        my_string = base64.b64encode(img_file.read())
    imgb64 = "data:image/jpeg;base64," + (my_string.decode('utf-8'))
    time.sleep(0.2)
    publish(imgb64,keytext,color,num,prob,duration)
    displaystr= "<img width='200' height='150' src='" +  imgb64  + "'>"
    display.set_attr("img_label.text", str(displaystr))


