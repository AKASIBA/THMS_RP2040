from machine import UART
from machine import Pin, I2C
import time
import binascii

led = Pin(25, Pin.OUT)
ser = UART(0)
adr = '0000000000000000'
rtc = I2C(1, scl=Pin(3), sda=Pin(2), freq=400_000)


def db(d): return (d // 10) << 4 | (d % 10)


def bx(b): return '{:x}'.format(b)


def set_time():
    it = ['mi', 'h', 'w', 'd', 'mo', 'y']
    buf = bytearray(7)
    for i in range(6, 0, -1):
        if i == 6:
            buf[i] = db(int(input(it[i - 1] + ':  ')) - 2000)
            continue
        if i == 3:
            buf[i] = 0
            continue
        buf[i] = db(int(input(it[i - 1] + ':  ')))
    buf[0] = 0
    rtc.writeto_mem(0x68, 0, buf)


def check_sum(hex_data):
    hex_sum = 0
    data_len = len(hex_data)
    for i in range(6, data_len, 2):
        hex_sum = hex_sum + int(hex_data[i:i + 2], 16)
    che_sum = '{:0>2x}'.format(255 - hex_sum % 256, 16)
    return che_sum


def uart_write(send_data, xbee_adr):
    send_data = str(binascii.hexlify(send_data.encode()).decode('utf-8'))
    send_data = '1001' + xbee_adr + 'fffe0000' + send_data
    data_len = '{:0>4x}'.format(len(send_data) // 2)
    send_data = '7e' + data_len + send_data
    send_data = send_data + check_sum(send_data)
    write_data = binascii.unhexlify(send_data)
    ser.write(write_data)
    print(write_data)


def kaonki():
    status_k = 1
    return status_k


def densyou():
    status_d = 1
    return status_d


def sidewall():
    status_s = 1
    return status_s


def main():
    reg = rtc.readfrom_mem(0X68, 0, 1)[0]
    reg &= ~128
    rtc.writeto_mem(0x68, 0, bytearray([reg]))
    print('時刻設定は5秒以内にCtrl+C')
    try:
        for i in range(0, 5): time.sleep(1)
    except KeyboardInterrupt:
        set_time()
    while True:
        # status_k = kaonki()
        # status_d = densyou()
        # status_s = sidewall()
        dt = rtc.readfrom_mem(0X68, 0, 7)
        st_dt = '{:0>2}'.format(bx(dt[5])) + '{:0>2}'.format(bx(dt[4]))+'{:0>2}'.format(bx(dt[2])) + '{:0>2}'.format(bx(dt[1]))
        led(1)
        time.sleep(1)
        led(0)
        time.sleep(1)
        # status_k = '停止'
        # mes_k = '>加温機: ' + status_k
        mes = 'S0100001' + '>SIBAINU'
        uart_write(mes, adr)
        print(st_dt)
        print('こんにちは　柴犬!!!!')


main()
