from machine import UART, ADC
from machine import Pin, I2C
import time
import binascii

ini_data = '01100500:000500:000500:000500:000500:000500:000601001011231143000\
41.90176140.680006021101010202500:0000:001010212500:0000:0010060'
ser = UART(0)
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
led_kaonki = Pin(24, Pin.OUT, value=0)
led_test = Pin(25, Pin.OUT, value=0)
adc_temp = ADC(Pin(26))
adc_ex = ADC(Pin(28))
buf_t = bytearray(7)


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


def thermo(com):

    status_k = '>加温機:OFF'
    return status_k


def light(com):
    status_d = '>電照:OFF'
    return status_d


def sidewall(com):
    status_s = '>巻上:OFF'
    return status_s


def relay_1(com):
    if com == '07': relay1.on()
    if com == '08': relay1.off()


def relay_2(com):
    relay = '>リレー:OFF'
    return relay


def main():
    now_time = time.ticks_ms()
    ds_time = time.ticks_ms()
    time_calibration()
    button = ini_data[:2]
    command_k = ini_data[:49]
    command_d = button + ini_data[49:84]
    command_s = button + ini_data[84:108]
    command_r = button + ini_data[108:129]
    status_k = thermo(command_k)
    status_d = light(command_d)
    status_s = sidewall(command_s)
    status_r = relay_2(command_r)

    while True:
        if time.ticks_diff(time.ticks_ms(), now_time) >= 864000000:
            now_time = time.ticks_ms()
            time_calibration()
        uart_data = uart_read()
        if uart_data:
            print(uart_data, len(uart_data))
            button = uart_data[:2]
            command_k = uart_data[:49]
            command_d = button + uart_data[49:84]
            command_s = button + uart_data[84:108]
            command_r = button + uart_data[108:129]
            i_time = uart_data[129:]
            print('button', button)
            print('kaonki', command_k)
            print('densyou', command_d)
            print('sidewall', command_s)
            print('relay', command_r)
            print('i_time', i_time)
            if button in ['07', '08']: relay_1(button)
            if button in ['01', '02']: status_k = thermo(command_k)
            if button in ['01', '03']: status_d = light(command_d)
            if button in ['04', '05', '06']: status_s = light(command_s)
            if button in ['01', '09']: status_d = light(command_d)
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
