import numpy as np
import h5py
#################################################
def mat_calculations(start_nm, speed_nm, name_file, q_str, direct):
    print('single')
    save_file = direct + '\\' + name_file
    data = np.load('{}.npy'.format(save_file))
    
    ch1 = (data['signals'] & 0b00000010) >> 1
    time = data['time']
    val = data['value']
    ################################
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
    ################################
    def division1(x, y, m, n):
        v = []
        t = []       
        for sl in zip(m, n):
                v.append(x[sl[0]:sl[1]])
                t.append(y[sl[0]:sl[1]])
        return v, t
    
    div1 = division1(val, time, rch1[0][1:], rch1[1][1:len(rch1[0])])
    ################################
    l = (len(div1[0])//2)*2
    data1 = div1[0][:l]
    time1 = div1[1][:l]
    ################################
    def mean(data):
        sr = []
        for i in zip(data[::2], data[1::2]):
            sr.append((np.max(i[0]) + np.max(i[1]))/2)
        return sr
    
    sr_val = mean(data1)
    ################################
    def time_to_nm(time):
        m = []
        for i in time:
            mean = np.mean(i)
            nm = (mean/1000000)*(speed_nm/60)
            m.append(nm)
        return m
    
    nm1 = time_to_nm(time1)
    ################################    
    nm1 = nm1 - nm1[0]
    nm1 = np.asarray(nm1)
    nm2 = (nm1) + start_nm
    nm = (nm2[::2] + nm2[1::2])/2
    ################################
    np.savez(save_file, Wavelength = nm, T = sr_val)
    np.savetxt('{}.csv'.format(save_file), np.transpose([nm, sr_val]), delimiter = ',', fmt='%s')
    hf = h5py.File('{}.h5'.format(save_file), 'w')
    hf.create_dataset('Wavelength', data = nm)
    hf.create_dataset('T', data = sr_val)
    hf.close()
    q_str.put('mat_end')