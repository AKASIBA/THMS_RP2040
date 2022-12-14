from machine import Pin, UART
import time

led = Pin(25, Pin.OUT)
serial0 = UART(0)
while True:
    led(1)
    time.sleep(1)
    led(0)
    time.sleep(1)
    serial0.write('sibainu')
    print('こんにちは　柴犬!!')