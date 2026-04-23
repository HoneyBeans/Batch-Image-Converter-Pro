import sys
import subprocess
import os
import concurrent.futures
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, 
                             QHBoxLayout, QWidget, QComboBox, QPushButton, 
                             QCheckBox, QFileDialog, QProgressBar, QMessageBox, QListWidget)
from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

def get_magick_path():
    """Finds the bundled ImageMagick engine whether running in Python or as a compiled .exe"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temporary folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Running normally from VS Code
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Points exactly to the magick executable inside our bundled folder
    return os.path.join(base_path, 'imagemagick', 'magick.exe')

# Store the path in a variable to use later
MAGICK_EXE = get_magick_path()

# --- THE PARALLEL WORKER THREAD ---
class ConversionWorker(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(list)

    def __init__(self, files, output_dir, target_format, resize, quality, strip, gray, watermark_cmd):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.target_format = target_format
        self.resize = resize
        self.quality = quality
        self.strip = strip
        self.gray = gray
        self.watermark_cmd = watermark_cmd

    def run(self):
        error_log = []
        completed_count = 0

        def process_single_file(file_path):
            command = [MAGICK_EXE, file_path]

            if self.strip:
                command.append("-strip")
            if self.gray:
                command.extend(["-colorspace", "Gray"])

            if self.watermark_cmd:
                command.extend(["-draw", self.watermark_cmd])

            if "1920x1080" in self.resize:
                command.extend(["-resize", "1920x1080>"])
            elif "50%" in self.resize:
                command.extend(["-resize", "50%"])

            if "75%" in self.quality:
                command.extend(["-quality", "75"])
            elif "50%" in self.quality:
                command.extend(["-quality", "50"])

            filename = os.path.basename(file_path)
            base_name = os.path.splitext(filename)[0]
            out_filename = f"{base_name}_edited.{self.target_format}"
            
            if self.output_dir:
                out_path = os.path.join(self.output_dir, out_filename)
            else:
                out_path = os.path.join(os.path.dirname(file_path), out_filename)
                
            command.append(out_path)

            try:
                subprocess.run(command, check=True, creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True)
                return None 
            except subprocess.CalledProcessError as e:
                return f"Failed on {filename}: {e.stderr.strip()}"

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(process_single_file, path): path for path in self.files}
            for future in concurrent.futures.as_completed(futures):
                err = future.result()
                if err:
                    error_log.append(err)
                completed_count += 1
                self.progress_update.emit(completed_count)
            
        self.finished.emit(error_log)


class DraggableWatermark(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.original_pixmap = None

    def set_image(self, path):
        self.original_pixmap = QPixmap(path)
        self.setPixmap(self.original_pixmap)
        aspect_ratio = self.original_pixmap.height() / self.original_pixmap.width()
        start_width = 100
        self.resize(start_width, int(start_width * aspect_ratio))
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.pos() - self.drag_start_pos
            self.move(self.pos() + delta)

    def wheelEvent(self, event):
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        new_w = int(self.width() * zoom_factor)
        new_h = int(self.height() * zoom_factor)
        self.resize(new_w, new_h)


class ConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Batch Image Converter Pro V7 - UI Upgrade")
        self.setGeometry(100, 100, 520, 780) # Increased height to fit the new list cleanly
        self.setAcceptDrops(True)
        self.files_to_convert = []
        self.output_dir = ""
        self.watermark_path = ""
        self.reference_img_width = 0
        self.reference_img_height = 0

        main_layout = QVBoxLayout()

        canvas_wrapper = QWidget()
        canvas_layout = QVBoxLayout(canvas_wrapper)
        canvas_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.canvas = QLabel("Drag & Drop Images Anywhere\n(First image will be used as a preview)")
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setStyleSheet("background-color: #222; color: white; border: 2px dashed #aaa;")
        self.canvas.setFixedSize(450, 300) 
        
        canvas_layout.addWidget(self.canvas)
        main_layout.addWidget(canvas_wrapper)

        self.watermark_obj = DraggableWatermark(self.canvas)
        self.watermark_obj.hide()

        # --- NEW: The Visual File Queue ---
        queue_layout = QVBoxLayout()
        queue_layout.addWidget(QLabel("File Queue:"))
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(100) # Prevents the list from taking up the whole screen
        self.file_list.setStyleSheet("background-color: #f0f0f0; border-radius: 5px;")
        queue_layout.addWidget(self.file_list)

        self.clear_btn = QPushButton("Clear Queue")
        self.clear_btn.clicked.connect(self.clear_queue)
        queue_layout.addWidget(self.clear_btn)

        main_layout.addLayout(queue_layout)

        # Controls
        control_layout = QHBoxLayout()

        self.format_dropdown = QComboBox()
        self.format_dropdown.addItems(["png", "jpeg", "webp", "gif"])
        control_layout.addWidget(QLabel("Format:"))
        control_layout.addWidget(self.format_dropdown)

        self.resize_dropdown = QComboBox()
        self.resize_dropdown.addItems(["Original Size", "1920x1080", "50% Scale"])
        control_layout.addWidget(QLabel("Resize:"))
        control_layout.addWidget(self.resize_dropdown)
        
        self.quality_dropdown = QComboBox()
        self.quality_dropdown.addItems(["100% (Lossless)", "75% (High)", "50% (Low)"])
        control_layout.addWidget(QLabel("Quality:"))
        control_layout.addWidget(self.quality_dropdown)

        main_layout.addLayout(control_layout)

        self.strip_check = QCheckBox("Strip Metadata")
        self.gray_check = QCheckBox("Grayscale")
        chk_layout = QHBoxLayout()
        chk_layout.addWidget(self.strip_check)
        chk_layout.addWidget(self.gray_check)
        main_layout.addLayout(chk_layout)

        self.watermark_btn = QPushButton("Select Watermark Logo (Then scroll to resize)")
        self.watermark_btn.clicked.connect(self.choose_watermark)
        main_layout.addWidget(self.watermark_btn)

        self.folder_btn = QPushButton("Save Location: Original Folder")
        self.folder_btn.clicked.connect(self.choose_folder)
        main_layout.addWidget(self.folder_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.convert_btn = QPushButton("Convert Files")
        self.convert_btn.setStyleSheet("padding: 10px; font-weight: bold; background-color: #0078D7; color: white;")
        self.convert_btn.clicked.connect(self.start_conversion_thread)
        main_layout.addWidget(self.convert_btn)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    # --- NEW: Function to safely wipe the queue ---
    def clear_queue(self):
        self.files_to_convert.clear()
        self.file_list.clear()
        self.canvas.setPixmap(QPixmap()) # Clears the preview image
        self.canvas.setText("Drag & Drop Images Anywhere\n(First image will be used as a preview)")
        self.canvas.setFixedSize(450, 300)
        self.watermark_obj.hide()
        self.progress_bar.setValue(0)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_dir = folder
            self.folder_btn.setText(f"Save Location: {folder}")

    def choose_watermark(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Watermark", "", "Images (*.png *.jpg *.webp)")
        if file_path:
            self.watermark_path = file_path
            self.watermark_obj.set_image(file_path)
            self.watermark_btn.setText("Watermark Loaded! Drag to move, Scroll to resize.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        new_files = [url.toLocalFile() for url in event.mimeData().urls()]
        
        # --- NEW: Smart Appending Logic ---
        # Loops through the dropped files and adds them to the list ONLY if they aren't already there
        for file_path in new_files:
            if file_path not in self.files_to_convert:
                self.files_to_convert.append(file_path)
                # Adds just the file name to the visual UI list, not the whole C:/ path
                self.file_list.addItem(os.path.basename(file_path))
        
        if self.files_to_convert:
            preview_path = self.files_to_convert[0]
            pixmap = QPixmap(preview_path)
            self.reference_img_width = pixmap.width()
            self.reference_img_height = pixmap.height()
            scaled_pixmap = pixmap.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            self.canvas.setPixmap(scaled_pixmap)
            self.canvas.setFixedSize(scaled_pixmap.size())
            
        self.progress_bar.setValue(0)

    def start_conversion_thread(self):
        if not self.files_to_convert:
            return
            
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Processing in background...")
        self.progress_bar.setMaximum(len(self.files_to_convert))
        
        watermark_cmd = ""
        if self.watermark_path and not self.watermark_obj.isHidden():
            ui_x = self.watermark_obj.x()
            ui_y = self.watermark_obj.y()
            ui_w = self.watermark_obj.width()
            ui_h = self.watermark_obj.height()

            ratio_x = self.reference_img_width / self.canvas.width()
            ratio_y = self.reference_img_height / self.canvas.height()

            true_x = int(ui_x * ratio_x)
            true_y = int(ui_y * ratio_y)
            true_w = int(ui_w * ratio_x)
            true_h = int(ui_h * ratio_y)

            safe_wm_path = self.watermark_path.replace("\\", "/")
            watermark_cmd = f"image Over {true_x},{true_y} {true_w},{true_h} '{safe_wm_path}'"

        self.worker = ConversionWorker(
            files=self.files_to_convert,
            output_dir=self.output_dir,
            target_format=self.format_dropdown.currentText(),
            resize=self.resize_dropdown.currentText(),
            quality=self.quality_dropdown.currentText(),
            strip=self.strip_check.isChecked(),
            gray=self.gray_check.isChecked(),
            watermark_cmd=watermark_cmd
        )

        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def conversion_finished(self, error_log):
        # NEW: Automatically clears the list and UI when the batch is done
        self.clear_queue() 
        self.canvas.setText("Batch Complete!\nDrag & Drop more images.")
        
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("Convert Files")

        if error_log:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Diagnostic Report")
            msg.setText(f"{len(error_log)} file(s) failed.")
            msg.setDetailedText("\n\n".join(error_log))
            msg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConverterApp()
    window.show()
    sys.exit(app.exec())