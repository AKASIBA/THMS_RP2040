import machine
from machine import UART, ADC
from machine import Pin, I2C
import time
import binascii
import os
import uio
import math

ser1 = Pin(0, Pin.OUT, value=0)  # serial pin initials
ser2 = Pin(1, Pin.OUT, value=0)  # serial pin initials
adr = '0000000000000000'
rtc = I2C(1, scl=Pin(3), sda=Pin(2), freq=400_000)
relay1 = Pin(5, Pin.OUT, value=0)
relay2 = Pin(4, Pin.OUT, value=0)
densyou = Pin(6, Pin.OUT, value=0)
kaonki = Pin(7, Pin.OUT, value=0)
sidewall_R = Pin(8, Pin.OUT, value=0)
sidewall_L = Pin(9, Pin.OUT, value=0)
sidewall_ex = Pin(10, Pin.OUT, value=0)
sw_close = Pin(16, Pin.IN, Pin.PULL_DOWN)
sw_open = Pin(17, Pin.IN, Pin.PULL_DOWN)
sw_remote = Pin(18, Pin.IN, Pin.PULL_DOWN)
led_time = Pin(19, Pin.OUT, value=0)
led_temp = Pin(20, Pin.OUT, value=0)
led_sw_manu = Pin(21, Pin.OUT, value=0)
led_sidewall = Pin(22, Pin.OUT, value=0)
led_densyou = Pin(23, Pin.OUT, value=0)  # Pin23
led_kaonki = Pin(24, Pin.OUT, value=0)  # Pin24
led_test = Pin(25, Pin.OUT, value=0)
adc_temp = ADC(Pin(26))
adc_ex = ADC(Pin(28))
buf_t = bytearray(7)
ser = UART(0, tx=Pin(0), rx=Pin(1))
temp_offset = 53.3
trig_r = rel_on = r = l = False
status_k = '>加温機:停止'
status_r = '>リレー2:停止'
time.sleep(3)


def db(d): return (d // 10) << 4 | (d % 10)


def bx(b): return '{:x}'.format(b)


def days(m, d):
    day = 0
    m_day = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for i in range(m - 1):
        day = day + m_day[i]
    day = day + d
    return day


def pr(x):
    p = 3.14159265359
    if x > p:
        if (x // p) % 2 == 1:
            x = x % p - p
        else:
            x = x % p
    return x


def time_calibration():
    w = 0
    uart_write('T', adr)
    time.sleep(0.02)
    while True:
        uart_data = uart_read()
        if uart_data:
            # print(uart_data[:2])
            if uart_data[:2] == '48':
                try:
                    buf = bytearray(7)
                    now_y = int(uart_data[2:4])
                    now_m = int(uart_data[4:6])
                    now_d = int(uart_data[6:8])
                    now_h = int(uart_data[8:10])
                    now_mi = int(uart_data[10:12])
                    now_s = int(uart_data[12:14])
                    buf[6] = db(int(now_y))
                    buf[5] = db(int(now_m))
                    buf[4] = db(int(now_d))
                    buf[3] = 0
                    buf[2] = db(int(now_h))
                    buf[1] = db(int(now_mi))
                    buf[0] = db(int(now_s))
                    rtc.writeto_mem(0x68, 0, buf)
                    print('Time Calibration success')
                    break
                except SyntaxError as te:
                    print('time calibration error', te)
                    pass
        w = w + 1
        time.sleep(0.05)
        if w > 100:
            set_time()
            break


def set_time():
    reg = rtc.readfrom_mem(0X68, 0, 1)[0]
    reg &= ~128
    rtc.writeto_mem(0x68, 0, bytearray([reg]))
    print('時刻設定は5秒以内にCtrl+C')
    try:
        for i in range(0, 5):
            time.sleep(1)
    except KeyboardInterrupt:
        it = ['minutes', 'hour', 'w', 'day', 'month', 'year']
        for i in range(6, 0, -1):
            if i == 6:
                buf_t[i] = db(int(input(it[i - 1] + ':  ')) - 2000)
                continue
            if i == 3:
                buf_t[i] = 0
                continue
            buf_t[i] = db(int(input(it[i - 1] + ':  ')))
        buf_t[0] = 0
        rtc.writeto_mem(0x68, 0, buf_t)


def check_sum(hex_data):
    hex_sum = 0
    data_len = len(hex_data)
    for i in range(6, data_len, 2):
        hex_sum = hex_sum + int(hex_data[i:i + 2], 16)
    che_sum = '{:0>2x}'.format(255 - hex_sum % 256, 16)
    return che_sum


def uart_read():
    data_law = ser.readline()
    try:
        if data_law:
            uart_data = str(binascii.hexlify(data_law).decode('utf-8'))
            if uart_data[6:8] == '8b':  # acknowledge
                print('DATA SEND SUCCESS !')
            else:
                print('reciev data')
                str_data = str(binascii.unhexlify(uart_data[30:-2]).decode('utf-8'))
                return str_data
    except SyntaxError as e:
        print(e)
        pass


def uart_write(send_data, xbee_adr):
    send_data = str(binascii.hexlify(send_data.encode()).decode('utf-8'))
    send_data = '1001' + xbee_adr + 'fffe0000' + send_data
    data_len = '{:0>4x}'.format(len(send_data) // 2)
    send_data = '7e' + data_len + send_data
    send_data = send_data + check_sum(send_data)
    write_data = binascii.unhexlify(send_data)
    ser.write(write_data)
    print('send data')


def thermo(com, st_dt):
    global status_k
    it_dt = int(st_dt[4:6]) * 60 + int(st_dt[6:])
    led_kaonki(1)
    try:
        t1 = min([t1 for t1 in com if t1 > it_dt])
    except:
        t1 = min([t1 for t1 in com])
    try:
        t2 = max([t2 for t2 in com if t2 <= it_dt])
    except:
        t2 = max([t2 for t2 in com])
    temp_d = int(com[t2])
    mes_t = str(t2 // 60) + ':' + '{:0>2}'.format(t2 % 60) + '-' + str(t1 // 60) + ':' + \
            '{:0>2}'.format(t1 % 60) + ' ' + str(temp_d) + '℃'
    t = adc_temp.read_u16() * 0.0050355 - temp_offset
    # status_k = '>加温機:' + mes_t
    if temp_d >= t:
        kaonki(1)
        status_k = '>加温機:ON ' + mes_t
    if temp_d + 3 <= t:  # ヒステリシス暫定
        kaonki(0)
        status_k = '>加温機:OFF ' + mes_t
    return status_k


def light(com, st_dt):
    status_d = '>電照稼働中'
    it_dt = int(st_dt[4:6]) * 60 + int(st_dt[6:])
    led_densyou(1)
    start_day = days(int(com[2:4]), int(com[4:6]))
    end_day = days(int(com[6:8]), int(com[8:10]))
    longitude = float(com[16:24])
    latitude = float(com[24:32])
    offset = int(com[14:16])
    day_times = int(com[10:12]) * 60 + int(com[12:14])  # 日長
    td = days(int(st_dt[:2]), int(st_dt[2:4]))  # 通算日
    pi = 3.1415926536
    ido = longitude * pi / 180  # degree>radian
    k = (td - 1) * 2 * pi / 365
    dl = 0.007 - 0.4 * math.cos(pr(k)) + 0.070257 * math.sin(pr(k)) - \
         0.00676 * math.cos(pr(2 * k)) + 0.001 * math.sin(pr(2 * k)) - 0.0027 * math.cos(pr(3 * k)) + 0.0015 * math.sin(
        pr(3 * k))
    et = (0.0172 + 0.43 * math.cos(pr(k)) - 7.35 * math.sin(pr(k)) - 3.35 * math.cos(pr(2 * k)) - 9.362 * math.sin(
        pr(2 * k))) / 60
    cn = (21 - et - latitude / 15) * 60
    om = math.acos((-0.0157 - math.sin(ido) * math.sin(pr(dl))) / (math.cos(ido) * math.cos(pr(dl))))
    ss = round(1260 - et * 60 + om * 720 / pi - latitude * 4) + offset  # 開始時間
    br = round(day_times - ss + cn * 2)  # 終了時間
    d = (ss - cn) * 2

    if day_times > d:
        if start_day < td < end_day or start_day > end_day and (td > start_day or td < end_day):
            dk = str(ss // 60) + ':' + str(ss % 60) + '-' + str(br // 60) + ':' + str(br % 60)
            if ss < br:
                if ss <= it_dt < br:
                    densyou(1)
                    status_d = '>電照:ON' + dk
                else:
                    densyou(0)
                    status_d = '>電照:OFF' + dk
            elif ss > br:
                if ss >= it_dt > br:
                    densyou(0)
                    status_d = '>電照:OFF' + dk
                else:
                    densyou(1)
                    status_d = '>電照:ON' + dk
        else:
            status_d = '>電照:稼働中'
    return status_d


def side_manu(com):
    global r, l
    if com[:2] == '04':  # open
        sidewall_R(r)
        sidewall_L(l)
        sidewall_ex(0)
    if com[:2] == '05':  # off
        sidewall_L(0)
        sidewall_R(0)
        sidewall_ex(0)
    if com[:2] == '06':  # close
        sidewall_R(r)
        sidewall_L(l)
        sidewall_ex(1)


def sidewall(com, st_dt):
    status_s = '>巻上:OFF'
    return status_s


def relay_1(com):
    if com == '07': relay1(1)
    if com == '08': relay1(0)


def relay_2(com, st_dt):
    global trig_r, rel_on, status_r
    it_nt = int(st_dt[4:6]) * 60 + int(st_dt[6:])
    evry_r = com[17]
    rel_sel = com[2:4]
    rel_temp = int(com[4:6])
    rel_time = com[6:11] + '-' + com[11:16]
    re_on_time = int(com[6:8]) * 60 + int(com[9:11])
    re_off_time = int(com[11:13]) * 60 + int(com[14:16])
    t = adc_temp.read_u16() * 0.0050355 - temp_offset
    if rel_sel == '21':
        if t >= rel_temp:
            relay2(1)
            status_r = '>リレー2:' + 'ON' + com[4:6] + '℃'
        elif t < rel_temp - 3:
            relay2(0)
            status_r = '>リレー2:' + 'OFF' + com[4:6] + '℃'
    else:
        if evry_r == '1' or trig_r:
            status_r = '>リレー2:' + rel_time
            if re_on_time < re_off_time:
                if re_on_time <= it_nt < re_off_time:
                    relay2(1)
                    rel_on = True
                    status_r = '>リレー2:' + 'ON' + rel_time
                else:
                    if rel_on:
                        relay2(0)
                        trig_r = False
                        status_r = '>リレー2:' + 'OFF' + rel_time
            else:
                if re_on_time >= it_nt > re_off_time:
                    if rel_on:
                        relay2(0)
                        trig_r = False
                        status_r = '>リレー2:' + 'OFF' + rel_time
                else:
                    relay2(1)
                    rel_on = True
                    status_r = '>リレー2:' + 'ON' + rel_time
        else:
            status_r = '>リレー2:' + '作動中'
    return status_r


def main():
    global r, l, trig_r, status_k, status_r
    ini_data = '0110050505050500:0000:0000:0000:0000:0000:000601001011231000000\
41.90176140.680006021101010202500:0000:001010212500:0000:0010060'
    ct_sw = on_test = o = p = sp = s_evry = sw_remo = trig_r = False
    sw_on = r_remo = sb_manu = True
    c_rem = 0
    mes_s = ''
    test_dic = command_k = {}
    now_time = ds_time = c_time = test_time = sw_on_t = off_time = sw_remo_t = time.ticks_ms()
    dt = rtc.readfrom_mem(0X68, 0, 7)
    st_dt = '{:0>2}'.format(bx(dt[5])) + '{:0>2}'.format(bx(dt[4])) + '{:0>2}'.format(bx(dt[2])) + '{:0>2}'.format(
        bx(dt[1]))
    try:
        f = uio.open('conf.txt', mode='r')
        ini_data = f.read()
        f.close()
        s_evry = r_evry = True
    except Exception as e:
        print(e)
        print('設定ファイルがありません')
    button = ini_data[:2]
    sw_k = ini_data[2:4]
    for i in range(6):
        it_dt = int(ini_data[16 + (5 * i):18 + (5 * i)]) * 60 + int(ini_data[19 + (5 * i):21 + (5 * i)])
        command_k[it_dt] = int(ini_data[4 + (2 * i):6 + (2 * i)])
    sw_d = ini_data[49:51]
    command_d = ini_data[49:84]
    sw_s = ini_data[90:92]
    command_s = ini_data[84:108]
    sw_r = ini_data[108:110]
    r = not not int(command_s[3])
    l = not not int(command_s[5])
    command_r = ini_data[108:129]
    status_k = thermo(command_k, st_dt)
    status_d = light(command_d, st_dt)
    status_s = sidewall(command_s, st_dt)
    status_r = relay_2(command_r, st_dt)
    time_calibration()
    while True:
        if time.ticks_diff(time.ticks_ms(), now_time) >= 86400000:
            now_time = time.ticks_ms()
            time_calibration()
        uart_data = uart_read()
        if uart_data and len(uart_data) == 135:
            command_k = {}
            button = uart_data[:2]
            sw_k = uart_data[2:4]
            sw_d = uart_data[49:51]
            sw_s = uart_data[90:92]
            sw_r = uart_data[108:110]
            for i in range(6):
                it_dt = int(uart_data[16 + (5 * i):18 + (5 * i)]) * 60 + int(uart_data[19 + (5 * i):21 + (5 * i)])
                command_k[it_dt] = int(uart_data[4 + (2 * i):6 + (2 * i)])
            command_d = uart_data[49:84]
            command_s = uart_data[84:108]
            r = not not int(command_s[3])
            l = not not int(command_s[5])
            command_r = uart_data[108:129]
            i_time = uart_data[129:]  #
            ct_sw = True
            test_dic['02'] = int(uart_data[46:49]) * 1000
            test_dic['03'] = int(command_d[-3:]) * 1000
            test_dic['09'] = int(command_r[-3:]) * 1000
            if button == '01':
                s_evry = trig_r = True
                sp = o = False
                mes_s = ''
                try:
                    os.remove('conf.txt')
                except OSError:
                    pass
                conf = uart_data[:129]
                f = uio.open('conf.txt', mode='w')
                f.write(conf)
                f.close()
            print('button', button)
            print('kaonki', command_k)
            print('densyou', command_d)
            print('sidewall', command_s)
            print('relay', command_r)
            print('i_time', i_time)
        if button in ['02', '03', '09'] and ct_sw:  # test button
            led_test(1)
            if not on_test:
                test_time = time.ticks_ms()
            on_test = True
            if button == '02':
                kaonki(1)
                status_k = '>加温機:TEST'
            if button == '03':
                densyou(1)
                status_d = '>電照:TEST'
            if button == '09':
                relay2(1)
                status_r = '>リレー2:TEST'
            if time.ticks_diff(time.ticks_ms(), test_time) >= test_dic[button]:
                led_test(0)
                kaonki(0)
                densyou(0)
                relay2(0)
                ct_sw = False
                on_test = False
        if button in ['04', '05', '06'] and sw_s == '11' and command_s[:2] == '21':
            s_manu = False
            led_time(0)
            led_temp(0)
            side_manu(button)  # リモート　マニュアル
        else:
            s_manu = True
        if sw_remote.value():  # マニュアルスイッチ
            c_rem = c_rem + 1
            if c_rem >= 5 and r_remo:
                sw_remo_t = time.ticks_ms()
                sb_manu = not sb_manu
                sw_remo = not sw_remo
                r_remo = False
                led_sw_manu(sw_remo)
        else:
            c_rem = 0
            r_remo = True
        if time.ticks_diff(time.ticks_ms(), sw_remo_t) >= 1800000:  # 1800000
            sb_manu = True
            sw_remo = False
            led_sw_manu(0)
        if sw_remo:
            if sw_open.value():
                sidewall_R(r)
                sidewall_L(l)
                sidewall_ex(0)
            elif sw_close.value():
                sidewall_R(r)
                sidewall_L(l)
                sidewall_ex(1)
            else:
                sidewall_R(0)
                sidewall_L(0)
                sidewall_ex(0)
        if button in ['07', '08']: relay_1(button)
        if time.ticks_diff(time.ticks_ms(), c_time) >= 1000:
            c_time = time.ticks_ms()
            if not on_test:
                dt = rtc.readfrom_mem(0X68, 0, 7)
                st_dt = '{:0>2}'.format(bx(dt[5])) + '{:0>2}'.format(bx(dt[4])) + '{:0>2}'.format(
                    bx(dt[2])) + '{:0>2}'.format(bx(dt[1]))
                it_nt = int(bx(dt[2])) * 60 + int(bx(dt[1]))
                if sw_k == '11':
                    thermo(command_k, st_dt)
                else:
                    status_k = '>加温機:停止'
                    led_kaonki(0)
                    kaonki(0)
                if sw_d == '11':
                    status_d = light(command_d, st_dt)
                else:
                    status_d = '>電照:停止'
                    led_densyou(0)
                    densyou(0)
                if not sw_remo:
                    if sw_s == '11' and command_s[:2] == '22':  # 巻上
                        led_sidewall(1)
                        # if not mes_s:
                        #    mes_s = '作動中'
                        if command_s[9] == '1':  # 温度
                            mes_s = command_s[10:12] + '℃'
                            c_temp = int(command_s[10:12])
                            a_temp = adc_temp.read_u16() * 0.0050355 - temp_offset
                            led_time(0)
                            led_temp(1)
                            if sw_on:
                                if a_temp >= c_temp + 3:  # open
                                    sw_on_t = time.ticks_ms()
                                    sw_on = False
                                    sidewall_R(r)
                                    sidewall_L(l)
                                    sidewall_ex(0)
                                elif a_temp < c_temp:  # close
                                    sw_on_t = time.ticks_ms()
                                    sw_on = False
                                    sidewall_R(r)
                                    sidewall_L(l)
                                    sidewall_ex(1)
                            if time.ticks_diff(time.ticks_ms(), sw_on_t) >= 3000:
                                if not sw_on:
                                    sidewall_R(0)
                                    sidewall_L(0)
                                    sidewall_ex(0)
                            if time.ticks_diff(time.ticks_ms(), sw_on_t) >= 300000:  # 300000
                                sw_on = True
                        if command_s[9] == '2' and s_evry:  # 時間
                            sw_time = command_s[12:17] + '-' + command_s[17:22]
                            open_time = int(command_s[12:14]) * 60 + int(command_s[15:17])
                            close_time = int(command_s[17:19]) * 60 + int(command_s[20:22])
                            led_time(1)
                            led_temp(0)
                            if not mes_s:
                                mes_s = sw_time
                            if open_time < close_time:
                                if open_time <= it_nt < close_time and p:
                                    sidewall_R(r)
                                    sidewall_L(l)
                                    sidewall_ex(0)
                                    off_time = time.ticks_ms()
                                    print('time_open')
                                    p = False
                                    o = True
                                    mes_s = '開' + sw_time
                                elif it_nt >= close_time and not p:
                                    sidewall_R(r)
                                    sidewall_L(l)
                                    sidewall_ex(1)
                                    off_time = time.ticks_ms()
                                    print('time_close')
                                    p = True
                                    o = True
                                    sp = True
                                    mes_s = '閉' + sw_time
                            else:
                                if open_time >= it_nt > close_time and p:
                                    sidewall_R(r)
                                    sidewall_L(l)
                                    sidewall_ex(1)
                                    off_time = time.ticks_ms()
                                    print('time_close')
                                    p = False
                                    o = True
                                    mes_s = '閉' + sw_time
                                elif it_nt >= open_time and not p:
                                    sidewall_R(r)
                                    sidewall_L(l)
                                    sidewall_ex(0)
                                    off_time = time.ticks_ms()
                                    print('time_open')
                                    p = True
                                    o = True
                                    sp = True
                                    mes_s = '開' + sw_time
                            if time.ticks_diff(time.ticks_ms(), off_time) >= 300000 and o:
                                sidewall_R(0)
                                sidewall_L(0)
                                sidewall_ex(0)
                                o = False
                            if command_s[22:] == '11':
                                s_evry = True
                            elif command_s[22:] == '10' and sp and not o:
                                s_evry = False
                                mes_s = '作動中'
                        status_s = '>巻上:' + mes_s
                    elif (sw_s == '10' or command_s[:2] == '22') and s_manu and sb_manu:
                        status_s = '>巻上:停止'
                        led_sidewall(0)
                        sidewall_R(0)
                        sidewall_L(0)
                        sidewall_ex(0)
                        led_time(0)
                        led_temp(0)
                if sw_r == '11':
                    relay_2(command_r, st_dt)
                else:
                    status_r = '>リレー2:停止'
                    relay2(0)
                led_test(1)
                time.sleep(0.1)
                led_test(0)
        if time.ticks_diff(time.ticks_ms(), ds_time) >= 30000:
            ds_time = time.ticks_ms()
            dt = rtc.readfrom_mem(0X68, 0, 7)
            st_dt = '{:0>2}'.format(bx(dt[5])) + '-' + '{:0>2}'.format(bx(dt[4])) + '-' + '{:0>2}'.format(
                bx(dt[2])) + ':' + '{:0>2}'.format(bx(dt[1])) + ':' + '{:0>2}'.format(bx(dt[0]))
            t = adc_temp.read_u16() * 0.0050355 - temp_offset
            temp = '>温度:' + '{:0.1f}'.format(t) + '℃'
            mes_k = 's0100001' + temp + status_k + status_d + status_s + status_r
            uart_write(mes_k, adr)
            print(mes_k, st_dt)
            # webserver 温度表示
            mes_temp = 'A01' + "{:05.1f}".format(t) + '温度:' + '{:0.1f}'.format(t) + '℃'
            uart_write(mes_temp, adr)
            print(mes_temp)
            """
            adc= adc_ex.read_u16()
            mes_adc = 'a01' + "{:05.1f}".format(t)+adc ###
            uart_write(mes_sdc, adr)
            print('adc ex', adc)
            """
        time.sleep(0.2)


try:
    main()
except Exception as e:
    print(e)
    machine.reset()
