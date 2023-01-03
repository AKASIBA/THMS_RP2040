from machine import UART, ADC
from machine import Pin, I2C
import time
import binascii
import os
import uio

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
sw_light = Pin(16, Pin.IN, Pin.PULL_UP)
sw_left = Pin(17, Pin.IN, Pin.PULL_UP)
sw_remote = Pin(18, Pin.IN, Pin.PULL_UP)
led_time = Pin(19, Pin.OUT, value=0)
led_temp = Pin(20, Pin.OUT, value=0)
led_remote = Pin(21, Pin.OUT, value=0)
led_sidewall = Pin(22, Pin.OUT, value=0)
led_densyou = Pin(23, Pin.OUT, value=0)
led_kaonki = Pin(14, Pin.OUT, value=0)
led_test = Pin(25, Pin.OUT, value=0)
adc_temp = ADC(Pin(26))
adc_ex = ADC(Pin(28))
buf_t = bytearray(7)
ser = UART(0, tx=Pin(0), rx=Pin(1))
time.sleep(20)


def db(d): return (d // 10) << 4 | (d % 10)


def bx(b): return '{:x}'.format(b)


def time_calibration():
    w = 0
    uart_write('T', adr)
    while True:
        uart_data = uart_read()
        if uart_data:
            print(uart_data[:2])
            if uart_data[:2] == '48':
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
                print('time calibration')
                break
        w = w + 1
        time.sleep(0.01)
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
        it = ['mi', 'h', 'w', 'd', 'mo', 'y']
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
    if data_law:
        uart_data = str(binascii.hexlify(data_law).decode('utf-8'))
        print(uart_data)
        print('reciev data')
        try:
            str_data = str(binascii.unhexlify(uart_data[30:-2]).decode('utf-8'))
            return str_data
        except:
            pass


def uart_write(send_data, xbee_adr):
    send_data = str(binascii.hexlify(send_data.encode()).decode('utf-8'))
    send_data = '1001' + xbee_adr + 'fffe0000' + send_data
    data_len = '{:0>4x}'.format(len(send_data) // 2)
    send_data = '7e' + data_len + send_data
    send_data = send_data + check_sum(send_data)
    write_data = binascii.unhexlify(send_data)
    ser.write(write_data)
    print('send data', send_data)


def thermo(com, st_dt):
    st_dt = st_dt[4:6] + ':' + st_dt[6:]
    it_dt = int(st_dt[:2]) * 60 + int(st_dt[3:5])
    led_kaonki(1)
    try:
        t1 = min([t1 for t1 in com if t1 > it_dt])
    except:
        t1 = min([t1 for t1 in com])
    try:
        t2 = max([t2 for t2 in com if t2 <= it_dt])
    except:
        t2 = max([t2 for t2 in com])
    print(it_dt, t2, t1)
    temp_d = int(com[t2])
    mes_t = str(t2 // 60) + ':' + '{:0>2}'.format(t2 % 60) + '-' + str(t1 // 60) + ':' + \
            '{:0>2}'.format(t1 % 60) + ' ' + str(temp_d) + '℃'
    t = adc_temp.read_u16() * 0.0050355 - 55.3
    print('t', t)
    status_k = '>加温機:OFF' + mes_t
    # if ks == 0: status_k = '>加温機:OFF'+mes_t
    if temp_d >= t:
        # ks = 1
        kaonki(1)
        status_k = '>加温機:ON ' + mes_t
    if temp_d + 3 <= t:  # ヒステリシス暫定
        kaonki(0)
        status_k = '>加温機:OFF ' + mes_t
        # ks = 0

    return status_k


def light(com, st_dt):
    status_d = '>電照:OFF'
    return status_d


def sidewall(com, st_dt):
    status_s = '>巻上:OFF'
    return status_s


def relay_1(com):
    if com == '07': relay1.on()
    if com == '08': relay1.off()


def relay_2(com, st_dt):
    relay = '>リレー:OFF'
    return relay


def main():
    ini_data = '0110050505050500:0000:0000:0000:0000:0000:000601001011231000000\
41.90176140.680006021101010202500:0000:001010212500:0000:0010060'
    global uart_data
    ct_sw = False
    on_test = False
    test_dic = {}
    command_k = {}
    now_time = ds_time = c_time = test_time = time.ticks_ms()
    dt = rtc.readfrom_mem(0X68, 0, 7)
    st_dt = '{:0>2}'.format(bx(dt[5])) + '{:0>2}'.format(bx(dt[4])) + '{:0>2}'.format(bx(dt[2])) + '{:0>2}'.format(
        bx(dt[1]))
    try:
        f = uio.open('conf.txt', mode='r')
        ini_data = f.read()
        f.close()
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
    sw_s = ini_data[88:90]
    command_s = ini_data[84:108]
    sw_r = ini_data[106:108]
    command_r = ini_data[108:129]
    status_k = thermo(command_k, st_dt)
    status_d = light(command_d, st_dt)
    status_s = sidewall(command_s, st_dt)
    status_r = relay_2(command_r, st_dt)
    time_calibration()
    while True:
        if time.ticks_diff(time.ticks_ms(), now_time) >= 864000000:
            now_time = time.ticks_ms()
            time_calibration()
        uart_data = uart_read()
        if uart_data:
            command_k = {}
            print(uart_data, len(uart_data))
            button = uart_data[:2]
            sw_k = uart_data[2:4]
            sw_d = uart_data[49:51]
            sw_s = uart_data[90:92]
            print(sw_s)
            sw_r = uart_data[106:108]
            for i in range(6):
                it_dt = int(uart_data[16 + (5 * i):18 + (5 * i)]) * 60 + int(uart_data[19 + (5 * i):21 + (5 * i)])
                command_k[it_dt] = int(uart_data[4 + (2 * i):6 + (2 * i)])
            # command_k = uart_data[2:49]
            command_d = uart_data[49:84]
            command_s = uart_data[84:108]
            command_r = uart_data[108:129]
            i_time = uart_data[129:]  #
            ct_sw = True
            test_dic['02'] = int(uart_data[46:49]) * 1000
            test_dic['03'] = int(command_d[-3:]) * 1000
            test_dic['09'] = int(command_r[-3:]) * 1000
            if button == '01':
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
            print('i_time', i_time)  #
        if button in ['02', '03', '09'] and ct_sw:  # test button
            led_test(1)
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
            if not on_test:
                test_time = time.ticks_ms()
            if time.ticks_diff(time.ticks_ms(), test_time) >= test_dic[button]:
                led_test(0)
                kaonki(0)
                densyou(0)
                relay2(0)
                ct_sw = False
                on_test = False
        if button in ['07', '08']: relay_1(button)
        if time.ticks_diff(time.ticks_ms(), c_time) >= 1000:
            c_time = time.ticks_ms()
            if not on_test:
                dt = rtc.readfrom_mem(0X68, 0, 7)
                st_dt = '{:0>2}'.format(bx(dt[5])) + '{:0>2}'.format(bx(dt[4])) + '{:0>2}'.format(
                    bx(dt[2])) + '{:0>2}'.format(bx(dt[1]))
                if sw_k == '11':
                    status_k = thermo(command_k, st_dt)
                else:
                    status_k = '>加温機:停止'
                    led_kaonki(0)
                    kaonki(1)
                if sw_d == '11':
                    status_d = light(command_d, st_dt)
                else:
                    status_d = '>電照:停止'
                if button in ['04', '05', '06'] or sw_s == '11':
                    status_s = sidewall(command_s, st_dt)
                else:
                    status_s = '>巻上:停止'
                if sw_r == '11':
                    status_r = relay_2(command_r, st_dt)
                else:
                    status_r = '>リレー2:停止'

        if time.ticks_diff(time.ticks_ms(), ds_time) >= 30000:
            ds_time = time.ticks_ms()
            dt = rtc.readfrom_mem(0X68, 0, 7)
            st_dt = '{:0>2}'.format(bx(dt[5])) + '-' + '{:0>2}'.format(bx(dt[4])) + '-' + '{:0>2}'.format(
                bx(dt[2])) + ':' + '{:0>2}'.format(bx(dt[1])) + ':' + '{:0>2}'.format(bx(dt[0]))
            led_test(1)
            time.sleep(0.1)
            led_test(0)
            t = adc_temp.read_u16() * 0.0050355 - 55.3
            temp = '>温度:' + '{:0.1f}'.format(t) + '℃'
            mes_k = 's0100001' + temp + status_k + status_d + status_s + status_r
            uart_write(mes_k, adr)
            print(mes_k, st_dt)
        time.sleep(0.1)


main()
