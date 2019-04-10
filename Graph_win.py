from multiprocessing import Process, Queue
from pyqtgraph import exporters
import serial.tools.list_ports
from queue import Empty
import pyqtgraph as pg
from PyQt5 import Qt
import numpy as np
import write_raw
import datetime
import h5py
import os


class Window(Qt.QMainWindow):

    def __init__(self):
        super().__init__()
        
        resolution = Qt.QDesktopWidget().screenGeometry()
        self.resize(resolution.width() // 1.5, resolution.height() // 1.5)
        self.setWindowIcon(Qt.QIcon('pythonlogo.png'))
        self.setWindowTitle("Spectr")
        self.mode = 'Dual beam mode'
        self.exporters = exporters
        self.old_val_bar = False
        self.q_stop = Queue()
        self.q_bar = Queue()
        self.q_str = Queue()
        self.speed_nm = 128
        work_data = '\data'
        self.start = False  
        path = os.getcwd()
        self.work_space = path + work_data
        print(path)
        try:              
            os.mkdir(self.work_space)
            
        except OSError:  
            print ("Creation of the directory %s failed" % path)   
                     
        print(self.work_space)
#         print('data'in work_space)
        self.j = 0
        self.init_gui()
        
        
    def init_gui(self):
        
        self.comlist = serial.tools.list_ports.comports()
        self.list_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.setAttribute(Qt.Qt.WA_DeleteOnClose)
        self.view = pg.GraphicsWindow(title = "Basic plotting")
        self.plot = self.view.addPlot(name = "Plot", title = '')
        self.setCentralWidget(self.view)
        self.view.setBackground('w')
        self.vLine = pg.InfiniteLine(angle = 90, movable = False, label = 'x={value:0.2f}', labelOpts={'position':0.94, 'color': (255,69,0)})
        self.hLine = pg.InfiniteLine(angle = 0, movable = False, label = 'y={value:0.2f}', labelOpts={'position':0.94,  'color': (255, 0, 0)})
        self.plot.addItem(self.vLine, ignoreBounds = True)
        self.plot.addItem(self.hLine, ignoreBounds = True)

        controls_dock = Qt.QDockWidget("Controls")
        controls = Qt.QWidget()
        
        grid = Qt.QGridLayout(controls)
        grid.addWidget(Qt.QLabel("Start Measure"), 0, 0)
        grid.addWidget(Qt.QLabel("Speed Scan"), 1, 0)
        grid.addWidget(Qt.QLabel("Mode Scan"), 2, 0)
        grid.addWidget(Qt.QLabel("Start, nm"), 3, 0)
        grid.addWidget(Qt.QLabel("Stop, nm"), 4, 0)
        grid.addWidget(Qt.QLabel("Stop Measure"), 5, 0)
        grid.addWidget(Qt.QLabel("Open file to plot graph"), 6, 0)
        grid.addWidget(Qt.QLabel("Clear Plot"), 7, 0)
        grid.addWidget(Qt.QLabel("Com Port"), 8, 0)
        grid.addWidget(Qt.QLabel("Refresh Port"), 9, 0)
        grid.addWidget(Qt.QLabel("Save PNG"), 10, 0)
#         grid.addWidget(Qt.QLabel("Save TXT"), 11, 0)
        
        self.startButton = Qt.QPushButton("Start")
        grid.addWidget(self.startButton, 0, 1)
        self.startButton.clicked.connect(self.start_measure)
        
        combo = Qt.QComboBox(self)
        combo.addItems(["128", "32", "8"])
        combo.activated[str].connect(self.speed_scan)
        grid.addWidget(combo, 1, 1)
        
        
        combo1 = Qt.QComboBox(self)
        combo1.addItems(["Dual beam mode", "Single beam mode"])
        combo1.activated[str].connect(self.mode_scan)
        grid.addWidget(combo1, 2, 1)
        
        
        self.spinBoxStart = Qt.QDoubleSpinBox()
        self.spinBoxStart.setRange(0 , 1200)
        grid.addWidget(self.spinBoxStart, 3, 1)
        self.spinBoxStart.setValue(400)
        
        
        self.spinBoxEnd = Qt.QDoubleSpinBox()
        self.spinBoxEnd.setRange(0 , 1200)
        grid.addWidget(self.spinBoxEnd, 4, 1)
        self.spinBoxEnd.setValue(800)
        
        
        self.stopButton = Qt.QPushButton("Stop")
        grid.addWidget(self.stopButton, 5, 1)
        self.stopButton.clicked.connect(self.stop)
        self.stopButton.setEnabled(False)
        
        
        openButton = Qt.QPushButton("Open")
        grid.addWidget(openButton, 6, 1)
        openButton.clicked.connect(self.on_open)
        
        
        clearButton = Qt.QPushButton("Clear")
        grid.addWidget(clearButton, 7, 1)
        clearButton.clicked.connect(self.clear_plot)
        
        
        self.combo1 = Qt.QComboBox(self)
        self.combo1.addItems(self.list_ports)
        self.combo1.activated[str].connect(self.com_port)
        self.com = self.list_ports
        if len(self.com) != 0:
            self.com = self.com[0]
        grid.addWidget(self.combo1, 8, 1)


        refreshButton = Qt.QPushButton("Refresh")
        grid.addWidget(refreshButton, 9, 1)
        refreshButton.clicked.connect(self.refresh_port)
    
        
        self.pngButton = Qt.QPushButton("PNG")
        grid.addWidget(self.pngButton, 10, 1)
        self.pngButton.clicked.connect(self.png)
        self.pngButton.setEnabled(False)
        
#         self.txtButton = Qt.QPushButton("TXT")
#         grid.addWidget(self.txtButton, 11, 1)
#         self.txtButton.clicked.connect(self.txt)
#         self.txtButton.setEnabled(False)
        
        self.pbar = Qt.QProgressBar(self)
        grid.addWidget(self.pbar, 12, 0, 2 , 2)
        
        self.label = Qt.QLabel()
        self.label.setStyleSheet('background-color: rgb(255, 255, 0);')  
        grid.addWidget(self.label, 14, 0, 2 , 2)
        grid.setRowStretch(14, 2)
        grid.setRowStretch(16, 1)
        
        self.statusbar = self.statusBar()
        
        controls_dock.setWidget(controls)
        self.addDockWidget(Qt.Qt.LeftDockWidgetArea, controls_dock)
             
                              
    def on_open(self):
        op = Qt.QFileDialog.getOpenFileName(parent = None, 
        caption = 'Open file to plot graph',
        directory = Qt.QDir.currentPath(), 
        filter = '(*.H5)')  #### ;; (*.npz)
        if len(op[0]) != 0:
            self.graph(op[0]) 
        

    def graph(self, val):
        
        color = ['k','b','g', 'r', 'y']
        if self.j == len(color)-1:
            self.j = 0
        labelStyle = {'color': '#000000', 'font-size': '10pt'}
        self.plot.setAutoVisible(y = True)
        
#    if not val.endswith('npz'):
        self.name_file = val[:-3]
        hf = h5py.File('{}'.format(val), 'r')
        coef_t = np.array(hf['T'])
        self.wave = np.array(hf['Wavelength'])
        self.plot.plot(self.wave, coef_t, pen = pg.mkPen(color[self.j], width = 3))
        hf.close()
#        else:
#            self.name_file = val[:-4]      
#            self.data = np.load(val)
#            self.plot.plot(self.data['Wavelength'], self.data['T'], pen = pg.mkPen(color[self.j], width = 3))
        
        self.plot.showGrid(x = True, y = True, alpha = 0.7)
        self.plot.setYRange(0, 100)
        self.plot.setLabel('left', "T, %", **labelStyle)
        self.plot.setLabel('bottom', "Wavelength, nm", **labelStyle)
        
        self.pngButton.setEnabled(True)
#        self.txtButton.setEnabled(True)
        
        self.label.setStyleSheet('background-color: rgb(255, 255, 0);')
        self.plot.scene().sigMouseMoved.connect(self.mouseMoved)
        self.vb = self.plot.vb
        self.j = self.j +1
        
        
    def mouseMoved(self, evt):
        pos = evt  ## using signal proxy turns original arguments into a tuple
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            if index > 0 and index < len(self.wave):
                self.label.setText("<span style='font-size: 15pt'>x=%0.1f, <span style='color: black'>y=%0.1f</span>" % (mousePoint.x(), mousePoint.y()))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
    
    
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
                self.label.setStyleSheet("background-color: rgb(255, 0, 0)")
                self.label.setText("<span style='font-size: 15pt'>Нажмите красную кнопку</span>")
                
            if self.val_str == 'Scaning':
                self.label.setStyleSheet("background-color: rgb(50, 205, 50)")
                self.label.setText("") 
                   
            if self.val_str == 'Mathematical processing':
                self.label.setStyleSheet("background-color: rgb(255, 255, 0)")
                self.label.setText("<span style='font-size: 15pt'>Можете нажать <br /> желтую кнопку</span>")
            
            if self.val_str == 'mat_end':
                self.label.setText("")
                print(self.graph_file)
                self.graph('{}.h5'.format(self.graph_file))
                self.statusbar.showMessage('Done')
                self.startButton.setEnabled(True)
                self.stopButton.setEnabled(False)
                self.pbar.setValue(100)
                self.timer.disconnect()
                
        except Empty as e:
            print(e)
                
                
    def start_measure(self):
        if len(self.list_ports) != 0:
            self.label.setText("")
    #         if self.plot.scene().sigMouseMoved.connect(self.mouseMoved):
    #             self.plot.scene().sigMouseMoved.disconnect(self.mouseMoved)
            self.start_nm = self.spinBoxStart.value()
            self.end_nm = self.spinBoxEnd.value()
            
            if self.end_nm <= self.start_nm:
                self.statusbar.showMessage('Wrong range')
                
            if self.end_nm > self.start_nm: 
                self.stopButton.setEnabled(True)
                self.startButton.setEnabled(False)
            
                if self.mode == 'Dual beam mode':
                    print("Dual beam mode") 
                    self.name_file = 'Dual_{}__Scan Range {}-{}__Speed Scan {}'.format(datetime.datetime.now().strftime("%y-%m-%d, %H-%M"), 
                                  self.start_nm, self.end_nm, self.speed_nm)   
            
                if self.mode == 'Single beam mode':
                    print("Single beam mode") 
                    self.name_file = 'Single_{}__Scan Range {}-{}__Speed Scan {}'.format(datetime.datetime.now().strftime("%y-%m-%d, %H-%M"), 
                                  self.start_nm, self.end_nm, self.speed_nm)
                    
                print(self.name_file)
                self.q_stop.put(False)
                self.pbar.setValue(0)
                self.plot.clear()
                self.direct = self.work_space + "\\" + self.name_file
                self.graph_file = self.direct + '\\' + self.name_file
                try:
                    self.direction = os.mkdir(self.direct)
                    print(self.direction)
                except OSError:  
                    print ("Creation of the directory failed")
                
                print(self.list_ports, 'self.list_ports')
                
                try:
                    proc = Process(target = write_raw.write, args = (self.name_file, self.start_nm, 
                                                        self.end_nm, self.speed_nm, self.com, self.q_bar, self.q_str, self.q_stop, self.mode, self.direct, ))
                    proc.start()
                    self.timer = Qt.QTimer()
                    self.timer.timeout.connect(self.tick)
                    self.timer.start(300)

                except Empty as e:
                    print(e)     
            
                except RuntimeError as e:
                    print(e)
                       
        
    def clear_plot(self):
        self.statusbar.showMessage('Clear')
        self.label.setText("")
        self.plot.clear()  
        
        
    def speed_scan(self, text):
        self.speed_nm = int(text)
       
        
    def mode_scan(self, text):
        print(text)
        self.mode = text
        
        
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
        self.stopButton.setEnabled(False)
        self.q_stop.put(True)
        self.timer.disconnect()
        
        
    def png(self):
        exporter = self.exporters.ImageExporter(self.plot)
        params = exporter.parameters()
        params.param("width").setValue(1920, blockSignal = exporter.widthChanged)
        params.param("height").setValue(1080, blockSignal = exporter.heightChanged)
        exporter.export('{}.png'.format(self.name_file))
        
    
#     def txt(self):
# 
#         np.savetxt('{}.txt'.format(self.name_file), np.transpose([self.data['Wavelength'], self.data['T']]), delimiter= 10*' '
#                    , fmt='%1.3f', header = 'Wavelength    T')
        
        
if __name__ == "__main__":
    
    app = Qt.QApplication([])
    w = Window()
    w.show()
    app.exec()    