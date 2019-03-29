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


class Window(Qt.QMainWindow):

    def __init__(self):
        super().__init__()
        resolution = Qt.QDesktopWidget().screenGeometry()
        self.resize(resolution.width() // 2, resolution.height() // 2)
        self.setWindowIcon(Qt.QIcon('pythonlogo.png'))
        self.setWindowTitle("Spectr")
        self.exporters = exporters
        self.q_bar = Queue()
        self.q_str = Queue()
        self.q_stop = Queue()
        self.old_val_bar = False
        self.speed_nm = 128
        self.start = False     
        self.j = 0
        self.init_gui()
        
        
    def init_gui(self):
        
        self.comlist = serial.tools.list_ports.comports()
        self.list_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.setAttribute(Qt.Qt.WA_DeleteOnClose)
        self.view = pg.GraphicsWindow(title = "Basic plotting")
        self.plot = self.view.addPlot(name = "Plot", title = '')
        self.setCentralWidget(self.view)
        self.view.setBackground('k')
        self.vLine = pg.InfiniteLine(angle = 90, movable = False, label = 'x={value:0.2f}', labelOpts={'position':0.94, 'color': (255,69,0)})
        self.hLine = pg.InfiniteLine(angle = 0, movable = False, label = 'y={value:0.2f}', labelOpts={'position':0.94,  'color': (255, 0, 0)})
        self.plot.addItem(self.vLine, ignoreBounds = True)
        self.plot.addItem(self.hLine, ignoreBounds = True)

        controls_dock = Qt.QDockWidget("Controls")
        controls = Qt.QWidget()
        
        grid = Qt.QGridLayout(controls)
        grid.addWidget(Qt.QLabel("Start Measure"), 0, 0)
        grid.addWidget(Qt.QLabel("Speed Scan"), 1, 0)
        grid.addWidget(Qt.QLabel("Start, nm"), 2, 0)
        grid.addWidget(Qt.QLabel("Stop, nm"), 3, 0)
        grid.addWidget(Qt.QLabel("Stop Measure"), 4, 0)
        grid.addWidget(Qt.QLabel("Open file to plot graph"), 5, 0)
        grid.addWidget(Qt.QLabel("Clear Plot"), 6, 0)
        grid.addWidget(Qt.QLabel("Com Port"), 7, 0)
        grid.addWidget(Qt.QLabel("Refresh Port"), 8, 0)
        grid.addWidget(Qt.QLabel("Save PNG"), 9, 0)
        grid.addWidget(Qt.QLabel("Save TXT"), 10, 0)
        
        openButton = Qt.QPushButton("Open")
        grid.addWidget(openButton, 5, 1)
        openButton.clicked.connect(self.on_open)
        
        clearButton = Qt.QPushButton("Clear")
        grid.addWidget(clearButton, 6, 1)
        clearButton.clicked.connect(self.clear_plot)
        
        self.startButton = Qt.QPushButton("Start")
        grid.addWidget(self.startButton, 0, 1)
        self.startButton.clicked.connect(self.start_measure)
        
        combo = Qt.QComboBox(self)
        combo.addItems(["128", "32", "8"])
        combo.activated[str].connect(self.speed_scan)
        grid.addWidget(combo, 1, 1)    
        
        self.combo1 = Qt.QComboBox(self)
        self.combo1.addItems(self.list_ports)
        self.combo1.activated[str].connect(self.com_port)
        self.com = self.list_ports
        if len(self.com) != 0:
            self.com = self.com[0]
        grid.addWidget(self.combo1, 7, 1)

        refreshButton = Qt.QPushButton("Refresh")
        grid.addWidget(refreshButton, 8, 1)
        refreshButton.clicked.connect(self.refresh_port)
               
        self.spinBoxStart = Qt.QSpinBox()
        self.spinBoxStart.setRange(0 , 1200)
        grid.addWidget(self.spinBoxStart, 2, 1)
        self.spinBoxStart.setValue(400)
        
        self.spinBoxEnd = Qt.QSpinBox()
        self.spinBoxEnd.setRange(0 , 1200)
        grid.addWidget(self.spinBoxEnd, 3, 1)
        self.spinBoxEnd.setValue(800)
        
        self.stopButton = Qt.QPushButton("Stop")
        grid.addWidget(self.stopButton, 4, 1)
        self.stopButton.clicked.connect(self.stop)
        self.stopButton.setEnabled(False)
        
        self.pngButton = Qt.QPushButton("PNG")
        grid.addWidget(self.pngButton, 9, 1)
        self.pngButton.clicked.connect(self.png)
        self.pngButton.setEnabled(False)
        
        self.txtButton = Qt.QPushButton("TXT")
        grid.addWidget(self.txtButton, 10, 1)
        self.txtButton.clicked.connect(self.txt)
        self.txtButton.setEnabled(False)
        
        self.pbar = Qt.QProgressBar(self)
        grid.addWidget(self.pbar, 11, 0, 2 , 2)
        
        self.label = Qt.QLabel()
        self.label.setStyleSheet('background-color: rgb(255, 0, 0);')  
        grid.addWidget(self.label, 13, 0, 2 , 2)
        
        grid.setRowStretch(15, 5)
        self.statusbar = self.statusBar()
        
        grid.setRowStretch(13, 6)
        controls_dock.setWidget(controls)
        self.addDockWidget(Qt.Qt.LeftDockWidgetArea, controls_dock)
             
                              
    def on_open(self):
        op = Qt.QFileDialog.getOpenFileName(parent = None, 
        caption = 'Open file to plot graph',
        directory = Qt.QDir.currentPath(), 
        filter = '(*.npz) ;; (*.H5)')
        if len(op[0]) != 0:
            self.graph(op[0]) 
        

    def graph(self, val):
        
        color = ['y','b', 'r', 'g']
        labelStyle = {'color': '#eeeeee', 'font-size': '10pt'}
        self.plot.setAutoVisible(y = True)
        
        if not val.endswith('npz'):
            self.name_file = val[:-3]
            hf = h5py.File('{}'.format(val), 'r')
            T = np.array(hf['T'])
            wave = np.array(hf['Wavelength'])
            self.plot.plot(wave, T, pen = pg.mkPen(color[self.j], width = 3))
            hf.close()
        else:
            self.name_file = val[:-4]      
            self.data = np.load(val)
            
            self.plot.plot(self.data['Wavelength'], self.data['T'], pen = pg.mkPen(color[self.j], width = 3))
        self.plot.showGrid(x = True, y = True, alpha = 0.7)
        self.plot.setYRange(0, 100)
        self.plot.setLabel('left', "T, %", **labelStyle)
        self.plot.setLabel('bottom', "Wavelength, nm", **labelStyle)
        
        self.pngButton.setEnabled(True)
        self.txtButton.setEnabled(True)
        
        self.label.setStyleSheet('background-color: rgb(255, 255, 255);')
        self.plot.scene().sigMouseMoved.connect(self.mouseMoved)
        self.vb = self.plot.vb
        self.j = self.j +1
        
        
    def mouseMoved(self, evt):
        pos = evt  ## using signal proxy turns original arguments into a tuple
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            if index > 0 and index < len(self.data['Wavelength']):
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
                self.label.setStyleSheet("background-color: rgb(255, 255, 50)")
                
            if self.val_str == 'Scaning':
                self.label.setStyleSheet("background-color: rgb(50, 205, 50)") 
                   
            if self.val_str == 'Mathematical processing':
                self.label.setStyleSheet("background-color: rgb(255, 255, 50)")
            
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
                    proc = Process(target = write_raw.write, args = (self.name_file, self.start_nm, 
                                                        self.end_nm, self.speed_nm, self.com, self.q_bar, self.q_str, self.q_stop, ))
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
        
        
    def png(self):
        exporter = self.exporters.ImageExporter(self.plot)
        params = exporter.parameters()
        params.param("width").setValue(1920, blockSignal = exporter.widthChanged)
        params.param("height").setValue(1080, blockSignal = exporter.heightChanged)
        exporter.export('{}.png'.format(self.name_file))
        
    
    def txt(self):
        print(self.data['Wavelength'])
        np.savetxt('{}.txt'.format(self.name_file), np.transpose([self.data['Wavelength'], self.data['T']]), delimiter= 10*' '
                   , fmt='%1.3f', header = 'Wavelength    T')
        
        
if __name__ == "__main__":
    
    app = Qt.QApplication([])
    w = Window()
    w.show()
    app.exec()    