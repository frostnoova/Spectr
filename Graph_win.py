from multiprocessing import Process, Queue
import serial.tools.list_ports
from queue import Empty
import pyqtgraph as pg
from PyQt5 import Qt
import numpy as np
import write_raw
import datetime
import h5py


class Window(Qt.QMainWindow):

    def __init__(self):
        super().__init__()
        resolution = Qt.QDesktopWidget().screenGeometry()
        self.resize(resolution.width() // 2, resolution.height() // 2)
        self.setWindowIcon(Qt.QIcon('pythonlogo.png'))
        self.setWindowTitle("Spectr")
        self.q_bar = Queue()
        self.q_str = Queue()
        self.q_stop = Queue()
        self.init_gui()
        
        
    def init_gui(self):
        
        
        self.comlist = serial.tools.list_ports.comports()
        self.list_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.setAttribute(Qt.Qt.WA_DeleteOnClose)
        self.view = pg.GraphicsWindow(title = "Basic plotting")
        self.plot = self.view.addPlot(name = "Plot", title = '')
        self.setCentralWidget(self.view)
        self.view.setBackground('k')


        controls_dock = Qt.QDockWidget("Controls")
        controls = Qt.QWidget()
        
        
        grid = Qt.QGridLayout(controls)
        grid.addWidget(Qt.QLabel("Open file to plot graph"), 0, 0)
        grid.addWidget(Qt.QLabel("Clear Plot"), 1, 0)
        grid.addWidget(Qt.QLabel("Start Measure"), 2, 0)
        grid.addWidget(Qt.QLabel("Speed Scan"), 3, 0)
        grid.addWidget(Qt.QLabel("Com Port"), 4, 0)
        grid.addWidget(Qt.QLabel("Refresh Port"), 5, 0)
        grid.addWidget(Qt.QLabel("Start, nm"), 6, 0)
        grid.addWidget(Qt.QLabel("Stop, nm"), 7, 0)
        grid.addWidget(Qt.QLabel("Stop Measure"), 8, 0)
        
        
        openButton = Qt.QPushButton("Open")
        grid.addWidget(openButton, 0, 1)
        openButton.clicked.connect(self.on_open)
        
        
        clearButton = Qt.QPushButton("Clear")
        grid.addWidget(clearButton, 1, 1)
        clearButton.clicked.connect(self.clear_plot)
        
        
        self.startButton = Qt.QPushButton("Start")
        grid.addWidget(self.startButton, 2, 1)
        self.startButton.clicked.connect(self.start_measure)
        
        
        combo = Qt.QComboBox(self)
        combo.addItems(["128", "32", "8"])
        combo.activated[str].connect(self.speed_scan)
        grid.addWidget(combo, 3, 1)    
        
        
        self.combo1 = Qt.QComboBox(self)
        self.combo1.addItems(self.list_ports)
        self.combo1.activated[str].connect(self.com_port)
        self.com = self.list_ports
        grid.addWidget(self.combo1, 4, 1)

       
        refreshButton = Qt.QPushButton("Refresh")
        grid.addWidget(refreshButton, 5, 1)
        refreshButton.clicked.connect(self.refresh_port)
               
        
        self.spinBoxStart = Qt.QSpinBox()
        self.spinBoxStart.setRange(0 , 1200)
        grid.addWidget(self.spinBoxStart, 6, 1)
        self.spinBoxStart.setValue(400)
        
                
        self.spinBoxEnd = Qt.QSpinBox()
        self.spinBoxEnd.setRange(0 , 1200)
        grid.addWidget(self.spinBoxEnd, 7, 1)
        self.spinBoxEnd.setValue(500)
        
        
        self.stopButton = Qt.QPushButton("Stop")
        grid.addWidget(self.stopButton, 8, 1)
        self.stopButton.clicked.connect(self.stop)
        self.stopButton.setEnabled(False)
        
        self.pbar = Qt.QProgressBar(self)
        grid.addWidget(self.pbar, 9, 0, 1 , 2)
        
        
        self.label = Qt.QLabel()
        self.label.setStyleSheet('background-color: rgb(255, 0, 0);')  
        grid.addWidget(self.label, 10, 0, 1 , 2)
        grid.setRowStretch(10, 5)
        self.statusbar = self.statusBar()
        
        
        grid.setRowStretch(15, 6)
        controls_dock.setWidget(controls)
        self.addDockWidget(Qt.Qt.LeftDockWidgetArea, controls_dock)
        
        
        self.old_val_bar = False
        self.start = False
        self.speed_nm = 128       
        self.j = 0
             
                              
    def on_open(self):
        op = Qt.QFileDialog.getOpenFileName(parent = None, 
        caption = 'Open file to plot graph',
        directory = Qt.QDir.currentPath(), 
        filter = '(*.npz) ;; (*.H5)')
        if len(op[0]) != 0:
            self.graph(op[0])
        

    def graph(self, data):
        color = ['y','b', 'r', 'g']
        print(data)
        print(type(data))
        if not data.endswith('npz'):
            hf = h5py.File('{}'.format(data), 'r')
            T = np.array(hf['T'])
            wave = np.array(hf['Wavelength'])
            labelStyle = {'color': '#eeeeee', 'font-size': '10pt'}
            self.plot.plot(wave, T, pen = pg.mkPen(color[self.j], width = 3))
        else:      
            data = np.load(data)
            labelStyle = {'color': '#eeeeee', 'font-size': '10pt'}
            self.plot.plot(data['Wavelength'], data['T'], pen = pg.mkPen(color[self.j], width = 3))
        self.plot.showGrid(x = True, y = True, alpha = 0.7)
        self.plot.setYRange(0, 100)
        self.plot.setLabel('left', "T, %", **labelStyle)
        self.plot.setLabel('bottom', "Wavelength, nm", **labelStyle)
        self.j = self.j +1
    
    def tick(self):
        try:    ###  progress bar
            self.val_bar = self.q_bar.get_nowait()
            
            if self.val_bar > self.old_val_bar:
                    self.pbar.setValue(self.val_bar)
                    
            self.old_val_bar = self.val_bar   
 
 
        except Empty as e:
                print(e)    
                
        try:    ###  status bar
            
            self.val_str = self.q_str.get_nowait()     
            self.statusbar.showMessage(self.val_str)
            
            if self.val_str == 'Get ready':
                self.label.setStyleSheet("background-color: rgb(255, 255, 50)")
                
            if self.val_str == 'Scaning':
                self.label.setStyleSheet("background-color: rgb(50, 205, 50)") 
                   
            if self.val_str == 'mat_end':
                self.graph('{}.npz'.format(self.name_file))
                self.statusbar.showMessage('Done')
                self.startButton.setEnabled(True)
                self.pbar.setValue(100)
                self.timer.disconnect()
                

        except Empty as e:
                print(e)        
                
    def start_measure(self):
        self.start_nm = self.spinBoxStart.value()
        self.end_nm = self.spinBoxEnd.value()
        if self.end_nm <= self.start_nm:
            self.statusbar.showMessage('Wrong range')
        if self.end_nm > self.start_nm: 
            self.stopButton.setEnabled(True)
            self.startButton.setEnabled(False)

            self.q_stop.put(False)
            self.pbar.setValue(0)
            self.plot.clear()
            self.name_file = '{}__Scan Range {}-{}__Speed Scan {}'.format(datetime.datetime.now().strftime("%y-%m-%d, %H-%M"), 
                          self.start_nm, self.end_nm, self.speed_nm)
        
            if self.list_ports != 0:
                try:
#                 self.name_file = '05.02.19_400_800_32_filtr3-528'
                    print(self.name_file)
                    proc = Process(target = write_raw.write, args = (self.name_file, self.start_nm, 
                                                        self.end_nm, self.speed_nm, self.com[0], self.q_bar, self.q_str, self.q_stop, ))
                    proc.start()
                    self.timer = Qt.QTimer()
                    self.timer.timeout.connect(self.tick)
                    self.timer.start(300)

                
                except Empty as e:
                    print(e)     
            
            
                except RuntimeError as e:
                    print(e)
                       
        
    def clear_plot(self):
        self.plot.clear()
        self.statusbar.showMessage('Clear')
        
        
    def speed_scan(self, text):
        self.speed_nm = int(text)
        
        
    def com_port(self, text):
        if len(text) != 0:
            self.start = True    
            self.com = text
        
    
    def refresh_port(self):
        self.combo1.clear()
        self.list_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.combo1.addItems(self.list_ports)
        
        
    def stop(self):
        self.label.setStyleSheet('background-color: rgb(255, 0, 0);')
        self.statusbar.showMessage('Stop')
        self.startButton.setEnabled(True)
        self.q_stop.put(True)
        self.timer.disconnect()
        
        
if __name__ == "__main__":
    
    app = Qt.QApplication([])
    w = Window()
    w.show()
    app.exec()    