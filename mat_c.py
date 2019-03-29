import scipy.signal as sig
import numpy as np
import h5py
###############################################
def mat_calculations(start_nm, speed_nm, name_file, q_str):

    speed_nm = speed_nm * 1.0625 ### Скорость сканирования с учетом коэффициента 1.0338153250597744 
    save_file = '{}.npz'.format(name_file)
    data = np.load('{}.npy'.format(name_file))
    ch1 = (data['signals'] & 0b00000100) >> 2   #### Перевый канал
    ch2 = (data['signals'] & 0b00000010) >> 1   #### Втрой канал
    time = data['time']     #### Веремя
    val = data['value']     #### Сигнал с  ФЭУ
    print('wait')
    #############################
                                ###    Интервалы каналов
    def range_ch(signal):
        m = []
        n = []
        old_item = False
        old_indx = False
        i = 0
        while i <= len(signal):
            if signal[i] == 1 and old_item == 0:
                m.append(old_indx)
                i+=260
                j = i
                while True:
                    j+=-1
                    if signal[j] == 1:
                        n.append(j)
                        break
            old_item = signal[i] 
            old_indx = i
            i+=1    
            if i+260 > len(signal):
                break
            
        return m, n
    
    rch1 = range_ch(ch1)
    rch2 = range_ch(ch2)
    #############################
                                ### Сортировка данных (сигнала с ФЭУ и времени по каналам)
    def division(x, y, m, n):
        v = []
        t = []       
        for sl in zip(m, n):
            v.append(x[sl[0]:sl[1]])
            t.append(y[sl[0]:sl[1]])
                
        return v, t
    
    
    div1 = division(val, time, rch1[0][1:len(rch2[1])], rch1[1][1:len(rch2[1])]) 
    div2 = division(val, time, rch2[0][1:], rch2[1][1:])
    ################################    Четное колличество каналов
    l = (len(div1[0])//2)*2
    data1 = div1[0][:l]
    data2 = div2[0][:l]
    time1 = div1[1][:l]
    time2 = div2[1][:l]
    print('nm')
    #############################
                                ###     Переход к нанометрам
    def time_to_nm(time):
        m = []
        for i in time:
            mean = np.mean(i)
            nm = (mean/1000000)*(speed_nm/60)
            m.append(nm)
            
        return m
    
    nm1 = time_to_nm(time1)
    nm2 = time_to_nm(time2)
    #############################
                                ###    Усреднение nm с двух каналов
    nm1 = nm1 - nm1[0]
    nm2 = nm2 - nm2[0]
    nm1 = np.asarray(nm1)
    nm2 = np.asarray(nm2)
    nm1 = (nm1) + start_nm
    nm2 = (nm2) + start_nm
    nm = (nm1 + nm2)/2
    print('savgol')
    #############################
                                ###     Устранеие выбросов и отделение от темновго тока
    def savgol_filtr(data):
        sr = []  
        for i in range(len(data)):
            arr = data[i]
            arr = arr[:int(len(arr)*0.7)]
            sarr = np.sort(arr)
            sarr1 = sarr[:int(len(arr)*0.9)]
            filt_sarr = sig.savgol_filter(sarr1, 15, 1, deriv = 0, delta = 1.0, axis = -1, mode = 'interp', cval = 0.0)
            filt_diff = sig.savgol_filter(np.diff(filt_sarr)*10, 15, 1, deriv = 0, delta = 1.0, axis = -1, mode='interp', cval=0.0)
            ind = np.where(filt_diff == np.max(filt_diff))
            plato = sarr[ind[0][0]:int(len(arr)*0.9)]
            plato = plato[25:]        
            sr.append(np.mean(plato))
        
        return sr
           
    U1 = savgol_filtr(data1)
    U2 = savgol_filtr(data2)
    #############################
                                ###    Расчет коэффициэнта пропускания и сохранение струтуры (coef_t, nm) в файл
    u1 = np.asarray(U1)
    u2 = np.asarray(U2)   
    print(u1, len(u1), type(u1))
    print(u2, len(u2), type(u2))
    coef_t = u2/u1
    coef_t = coef_t*100                   ### Нормируем коээф на единицу
    np.savez(save_file, Wavelength = nm, T = coef_t)
    hf = h5py.File('{}.h5'.format(name_file), 'w')
    hf.create_dataset('Wavelength', data = nm)
    hf.create_dataset('T', data = coef_t)
    hf.close()
    q_str.put('mat_end')