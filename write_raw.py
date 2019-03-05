from serial import Serial
from queue import Empty
import numpy as np
import mat_c
import time

def write(name_file, start_nm, end_nm, speed_nm, com, q_bar, q_str):
    q_str.put('Scan starting')
    s = Serial(com, baudrate = 500000, timeout = 1)     ### Настрйока сериал порта
    time.sleep(4)
    ###############################################
    T = int((end_nm - start_nm) / speed_nm) * 60  ### Расчетное время сканирования 
    F = 7000    ### Частота дискритизации 
    N = int((F*T) / 10 )
    st = int(N / 100)
    ###############################################
    t = time.time()
    s.read_all() ### Считываем все из порта
    q_str.put('Get ready')
    time.sleep(3)
    s.write(b"s") ### Отправка команды микрокотроллеру для старта
    started = s.readline().strip() 
    ############################################### Проверка ответной команды от микроконтроллера о страте
    if not started.endswith(b"started"):
        print(started)
        s.close()
        raise RuntimeError("Couldn't start reading!")
    else:
        print("Started")
    cur = b""
    a = bytearray()
    q_str.put('Scaning')
    for i in range(N):
        if i % st == 0:
            print((i / st) + 1, end="\n")
            q_bar.put(int(i / st) + 1)
        cur = s.read(70)
        a.extend(cur)
    s.write(b"e")   ### Отправка команды микрокотроллеру для завершения
    stopped = s.readline().strip()
    s.close()
    ############################################### Проверка ответной команды от микроконтроллера о заерщении
    if not stopped.endswith(b"stopped"): 
        print("Uncorrect stop!")
    else:
        print("Succesfully stopped.")
    e = time.time()
    print("Elapsed", e - t)
    q_str.put('Scan end, start correct')
    print('Scan end, start correct')
    ############################################### Проверка на плохие(поломанные) данные, если нашли то "выбрасываем" 
    bytes_ = [0b00100010, 0b00100000, 0b00100100]
    d = bytearray()
    i = 0
    while i < len(a):
        pack = a[i:i+7]
        if len(pack) == 7:
            c = pack[0] in bytes_
            if c == True:
                d.extend(pack)    
            else:
                while not a[i] in bytes_:
                    i+= 1            
        i+= 7  
                     
    dtype = np.dtype([('signals','uint8'),('value', 'uint16'),('time','uint32')])
    data = np.frombuffer(d, dtype) 
    diff = np.diff(data['time'])
    ind = np.where(diff < np.median(diff)*2)
    data = data[ind]
    np.save(name_file, data)

    time.sleep(2)
    q_str.put('Mathematical processing')
    mat_c.mat_calculations(start_nm, speed_nm, name_file, q_str)