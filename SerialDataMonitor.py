"""!
@file SerialDataMonitor.py
@brief 시리얼 포트로부터 들어오는 데이터를 텍스트 로그로 표시하고 저장하는 프로그램
@details 그래프 기능 없이 순수하게 시리얼 데이터를 확인하고 로깅하는 데 최적화된 버전입니다.
         - 실시간 데이터 텍스트 표시
         - 시리얼 포트 연결/해제 및 설정
         - 데이터 CSV 저장 (타임스탬프 포함)
         - 데이터 송신 기능

@author User (JeongWhan Lee)
@date 2026-01-11
@version 1.0.0
"""

import sys
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox, QCheckBox)
from PyQt5.QtCore import QTimer, QDateTime, Qt
import serial
import serial.tools.list_ports

class SerialDataMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial Data Monitor")
        self.setGeometry(100, 100, 800, 600)

        # --- 변수 초기화 ---
        self.serial_port = None
        self.is_saving = False
        self.csv_buffer = []
        
        self.data_packets_received = 0
        self.last_rate_update_time = 0

        # --- 메인 위젯 및 레이아웃 설정 ---
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # --- 타이틀 라벨 ---
        title_label = QLabel("Serial Data Monitor")
        title_label.setStyleSheet("""
            font-family: 'Times New Roman', serif;
            font-size: 24px;
            font-weight: bold;
            font-style: italic;
            padding-left: 10px;
        """)
        title_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(title_label)

        # --- 상단 컨트롤 패널 ---
        control_panel_layout = QHBoxLayout()

        # 시리얼 포트 선택
        self.port_combo = QComboBox()
        control_panel_layout.addWidget(QLabel("Serial Port:"))
        control_panel_layout.addWidget(self.port_combo)

        # 스캔 버튼
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.scan_serial_ports)
        control_panel_layout.addWidget(self.scan_button)
        
        # 통신 속도(Baudrate) 선택
        self.baud_rate_combo = QComboBox()
        common_baud_rates = ["9600", "19200", "38400", "57600", "115200"]
        self.baud_rate_combo.addItems(common_baud_rates)
        self.baud_rate_combo.setCurrentText("115200")
        control_panel_layout.addWidget(QLabel("Baudrate:"))
        control_panel_layout.addWidget(self.baud_rate_combo)

        # 연결/해제 버튼
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        control_panel_layout.addWidget(self.connect_button)
        
        # 연결 상태 LED
        self.connection_status_led = QLabel()
        self.connection_status_led.setFixedSize(16, 16)
        self.connection_status_led.setStyleSheet("background-color: red; border-radius: 8px;")
        control_panel_layout.addWidget(self.connection_status_led)

        # 수신 속도 표시
        self.rate_label = QLabel("Rate: 0.0 Hz")
        self.rate_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #AAAAFF; margin-left: 10px;")
        control_panel_layout.addWidget(self.rate_label)
        control_panel_layout.addStretch()

        # Timestamp Checkbox
        self.timestamp_check = QCheckBox("Timestamp")
        self.timestamp_check.setChecked(False)
        control_panel_layout.addWidget(self.timestamp_check)

        # CSV 저장 버튼
        self.save_button = QPushButton("Start Saving")
        self.save_button.clicked.connect(self.toggle_saving)
        self.save_button.setEnabled(False)
        control_panel_layout.addWidget(self.save_button)
        
        # 로그 지우기 버튼
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)
        control_panel_layout.addWidget(self.clear_button)

        main_layout.addLayout(control_panel_layout)

        # --- 로그 텍스트 박스 ---
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        # 가독성을 위해 고정폭 글꼴 사용
        self.log_box.setStyleSheet("font-family: Courier New; font-size: 12px; background-color: #F0F0F0;")
        main_layout.addWidget(self.log_box)

        # --- 시리얼 데이터 송신 입력창 ---
        self.send_input = QLineEdit()
        self.send_input.setPlaceholderText("Type a message and press Enter to send")
        self.send_input.returnPressed.connect(self.send_serial_data)
        self.send_input.setEnabled(False)
        main_layout.addWidget(self.send_input)

        # --- 하단 레이아웃 (종료 버튼) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        # 종료 버튼
        self.exit_button = QPushButton("Quit")
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setStyleSheet("font-size: 16px; font-weight: bold; color: white; background-color: #555555; border-radius: 10px; padding: 5px 15px;")
        bottom_layout.addWidget(self.exit_button)

        main_layout.addLayout(bottom_layout)

        # --- 타이머 설정 ---
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.read_serial_data)

        self.rate_update_timer = QTimer()
        self.rate_update_timer.timeout.connect(self.update_rate_display)

        # 초기 포트 스캔
        self.scan_serial_ports()
        self.update_led_status(False)
        
        # 상태바 초기화
        self.statusBar().showMessage("Ready")

    def update_led_status(self, connected):
        if connected:
            self.connection_status_led.setStyleSheet("background-color: green; border-radius: 8px;")
        else:
            self.connection_status_led.setStyleSheet("background-color: red; border-radius: 8px;")

    def scan_serial_ports(self):
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        
        index = self.port_combo.findText(current_port)
        if index != -1:
            self.port_combo.setCurrentIndex(index)
        
        if not ports:
            self.log_message("No available serial ports found.")
            self.statusBar().showMessage("No available serial ports found.")
        else:
            self.log_message("Updated serial port list.")
            self.statusBar().showMessage("Updated serial port list.")

    def toggle_connection(self):
        if self.serial_port is None or not self.serial_port.is_open:
            self.connect_serial()
        else:
            self.disconnect_serial()

    def connect_serial(self):
        port_name = self.port_combo.currentText()
        baud_rate = self.baud_rate_combo.currentText()

        if not port_name:
            self.log_message("Error: Please select a port.")
            self.statusBar().showMessage("Error: Please select a port.")
            return
        if not baud_rate.isdigit():
            self.log_message("Error: Baudrate must be a number.")
            self.statusBar().showMessage("Error: Baudrate must be a number.")
            return

        try:
            self.serial_port = serial.Serial(port_name, int(baud_rate), timeout=0.1)
            self.data_timer.start(50) # 50ms 간격으로 데이터 읽기
            self.connect_button.setText("Disconnect")
            self.save_button.setEnabled(True)
            self.send_input.setEnabled(True)
            self.update_led_status(True)
            self.log_message(f"Connected to {port_name} at {baud_rate} bps.")
            self.statusBar().showMessage(f"Connected to {port_name} at {baud_rate} bps.")
            
            self.data_packets_received = 0
            self.last_rate_update_time = QDateTime.currentDateTime().toMSecsSinceEpoch() / 1000.0
            self.rate_update_timer.start(1000)
        except serial.SerialException as e:
            self.log_message(f"Error: {e}")
            self.statusBar().showMessage(f"Connection Error: {e}")
            self.update_led_status(False)

    def disconnect_serial(self):
        if self.serial_port and self.serial_port.is_open:
            self.data_timer.stop()
            if self.is_saving:
                self.stop_saving()
            self.rate_update_timer.stop()
            self.rate_label.setText("Rate: 0.0 Hz")
            self.serial_port.close()
            self.connect_button.setText("Connect")
            self.save_button.setEnabled(False)
            self.send_input.setEnabled(False)
            self.log_message("Disconnected.")
            self.statusBar().showMessage("Disconnected.")
            self.update_led_status(False)

    def read_serial_data(self):
        if self.serial_port and self.serial_port.is_open:
            while self.serial_port.in_waiting > 0:
                try:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        self.log_message(line, "rx")
                        self.data_packets_received += 1
                        if self.is_saving:
                            self.buffer_csv_data(line)
                except UnicodeDecodeError:
                    self.log_message("UnicodeDecodeError: Could not decode received data.")
    
    def send_serial_data(self):
        if self.serial_port and self.serial_port.is_open:
            data_to_send = self.send_input.text()
            if not data_to_send:
                return
            
            data_with_newline = data_to_send + '\n'
            try:
                self.serial_port.write(data_with_newline.encode('utf-8'))
                self.log_message(data_to_send, "tx")
                self.statusBar().showMessage(f"Sent: {data_to_send}")
                self.send_input.clear()
            except serial.SerialException as e:
                self.log_message(f"Error sending data: {e}")
                self.statusBar().showMessage(f"Error sending data: {e}")
        else:
            self.log_message("Cannot send data: Not connected.")
            self.statusBar().showMessage("Cannot send data: Not connected.")

    def toggle_saving(self):
        if not self.is_saving:
            self.start_saving()
        else:
            self.stop_saving()

    def start_saving(self):
        self.csv_buffer.clear()
        self.is_saving = True
        self.save_button.setText("Stop Saving")
        self.timestamp_check.setEnabled(False)
        self.log_message("Started buffering data for CSV export.")
        self.statusBar().showMessage("Started buffering data for CSV export.")

    def stop_saving(self):
        self.is_saving = False
        self.save_button.setText("Start Saving")
        self.timestamp_check.setEnabled(True)
        self.log_message("Stopped buffering data.")
        self.statusBar().showMessage("Stopped buffering data.")

        if not self.csv_buffer:
            self.log_message("No data to save.")
            self.statusBar().showMessage("No data to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if self.timestamp_check.isChecked():
                        writer.writerow(['Timestamp', 'Raw Data'])
                    writer.writerows(self.csv_buffer)
                self.log_message(f"Data successfully saved to {file_path}.")
                self.statusBar().showMessage(f"Data successfully saved to {file_path}.")
            except Exception as e:
                self.log_message(f"Error saving file: {e}")
                self.statusBar().showMessage(f"Error saving file: {e}")
        else:
            self.log_message("Save operation cancelled.")
            self.statusBar().showMessage("Save operation cancelled.")
        
        self.csv_buffer.clear()

    def buffer_csv_data(self, data_line):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz")
        # 그래프용 파싱 없이 원본 데이터 그대로 저장
        if self.timestamp_check.isChecked():
            self.csv_buffer.append([timestamp, data_line])
        else:
            self.csv_buffer.append([data_line])

    def clear_log(self):
        self.log_box.clear()
        self.log_message("Log cleared.")
        self.statusBar().showMessage("Log cleared.")

    def log_message(self, message, msg_type="system"):
        safe_msg = str(message).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        if msg_type == "system":
            formatted_msg = f'<span style="color:green;">[{safe_msg}]</span>'
        elif msg_type == "rx":
            formatted_msg = f'<span style="color:black;">&gt; {safe_msg}</span>'
        elif msg_type == "tx":
            formatted_msg = f'<span style="color:blue;">&lt; {safe_msg}</span>'
        else:
            formatted_msg = safe_msg
            
        self.log_box.append(formatted_msg)
        # 자동으로 스크롤을 맨 아래로 이동
        cursor = self.log_box.textCursor()
        cursor.movePosition(cursor.End)
        self.log_box.setTextCursor(cursor)

    def closeEvent(self, event):
        if self.serial_port and self.serial_port.is_open:
            reply = QMessageBox.question(self, 'Disconnect Confirmation',
                                         "Serial port is connected. Do you want to disconnect and exit?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.disconnect_serial()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def update_rate_display(self):
        current_time = QDateTime.currentDateTime().toMSecsSinceEpoch() / 1000.0
        elapsed_time = current_time - self.last_rate_update_time

        if elapsed_time > 0:
            rate = self.data_packets_received / elapsed_time
            self.rate_label.setText(f"Rate: {rate:.1f} Hz")
        
        self.data_packets_received = 0
        self.last_rate_update_time = current_time

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = SerialDataMonitor()
    main_win.show()
    sys.exit(app.exec_())