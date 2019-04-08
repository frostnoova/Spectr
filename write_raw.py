from serial import Serial
from queue import Empty
import numpy as np
import s_mar_c
import mat_c
import time
 
def write(name_file, start_nm, end_nm, speed_nm, com, q_bar, q_str, q_stop, mode, direct):
    print(direct)
#     np.save(direct + '\\' + name_file, [1, 2, 3, 4, 5])
    old_l = 0
    stop = False
    q_str.put('Scan starting')
    speed_nm = speed_nm * 1.0625
    s = Serial(com, baudrate = 500000, timeout = 1)     ### Настройка сериал порта
    time.sleep(4)
    ###############################################
    
    time_scan = ((end_nm - start_nm) / speed_nm) * 60  ### Расчетное время сканирования 
    print(time_scan)
    s.read_all() ### Считываем все из порта
    time.sleep(4)
    s.write(b"s") ### Отправка команды микрокотроллеру для старта
#     started = s.readline().strip()
    q_str.put('Get ready')
    
    while True:
        started = s.readline().strip()
        print("started")
        if started.endswith(b"started"): 
            print("started")
            break
        try:
            stop = q_stop.get_nowait()
            if stop == True:
                print('Stop')
                break
        except Empty as end_scan:
            print(end_scan)                  
                 
    ############################################### Проверка ответной команды от микроконтроллера о страте
#     if not started.endswith(b"started"):
#         print(started)
#         s.close()
#         raise RuntimeError("Couldn't start reading!")
#     else:
#         print("Started")
    ###############################################    
    
    cur = b""
    a = bytearray()
    q_str.put('Scaning')
    start_scan = time.time()
    end_scan = 0
    
    if stop != True:
        while True:
            try:
                end_scan = time.time()
                
                if end_scan-start_scan >= time_scan:
                    break
                
                l = (int(end_scan-start_scan) * 100) / time_scan
                
                if l != old_l:
                    q_bar.put(l)
                    
                cur = s.read(70)
                a.extend(cur)
                old_l = l
                stop = q_stop.get_nowait()
                
                if   stop == True:
                    print('Stop')
                    break 
                
            except Empty as end_scan:
                print(end_scan)
    
    in_buf = s.in_waiting
    print(in_buf)
    cur = s.read(in_buf)
    a.extend(cur)
    print(s.in_waiting)           
    s.write(b"e")   ### Отправка команды микрокотроллеру для завершения
    stopped = s.readline().strip()
    s.close()
    
    ############################################### Проверка ответной команды от микроконтроллера о заерщении
    
    if stop != True:
        if not stopped.endswith(b"stopped"): 
            print("Uncorrect stop!")
        else:
            print("Succesfully stopped.")
        print("Elapsed", end_scan - start_scan)
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
        np.save(direct + '//' + name_file, data)
        time.sleep(1)
        speed_nm = 128
        q_str.put('Mathematical processing')
        if mode == 'Dual beam mode':
            mat_c.mat_calculations(start_nm, speed_nm, name_file, q_str, direct)
        if mode == 'Single beam mode':
            s_mar_c.mat_calculations(start_nm, speed_nm, name_file, q_str, direct)    