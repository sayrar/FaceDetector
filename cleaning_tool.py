import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QKeySequence, QPixmap
from PyQt5.QtWidgets import (QGridLayout, QWidget, QMessageBox, QAction, QLabel, QPushButton, 
                            QScrollArea,QApplication, QToolButton, QDockWidget, QRadioButton,
                            QHBoxLayout, QVBoxLayout, QMainWindow, QToolBar, QListWidget)
from PyQt5.QtCore import Qt, QSize 

import glob
import platform
from datetime import datetime as dt
import time
import re
import os

from PyQt5.sip import delete

#change this depending on the data folder you're working with
#The folder should be the folder containing folders of celebrities
if platform.system() == "Windows":\
    DATA_FOLDER = "downloads\\"
else:
    DATA_FOLDER = "downloads/"


class MainWindow(QMainWindow):
    """
    Main window class
    """

    def __init__(self, parent = None):
        super(MainWindow,self).__init__(parent)
        self.initGUI()

    def initGUI(self):

        self.output_file = "session-{}.txt".format(time.time())
        self.id_folders = sorted(glob.glob(DATA_FOLDER + "*"))
        self.current_folder = 0
        self.step_size = 1
        self.gender = ""
        self.paths_processed = []

        files = glob.glob("./*")

        #Checking to see if there was a previous session
        for path in reversed(sorted(files)):
            prev_sess = re.search("(session-(\d+\.\d+)\.txt)", path)
            if prev_sess:
                readable_time = dt.fromtimestamp(float(
                              prev_sess.group(2))).strftime('%Y-%m-%d %H:%M:%S')
                resume = QMessageBox.question(self, 'Load Session', 'Detected session: ' + readable_time
                                       + '\n\nWould you like to resume this session?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if resume == QMessageBox.Yes :
                    self.output_file = path
                    with open(path) as label_file:
                        last_labeled = label_file.readlines()[-1].split(":")[0]
                        #print(self.id_folders.index(DATA_FOLDER + last_labeled))
                        self.current_folder = self.id_folders.index(DATA_FOLDER + last_labeled) \
                            + self.step_size
                break
        
        folder = self.id_folders[self.current_folder]
        self.setWindowTitle(self.id_folders[self.current_folder].split("/")[-1])

        #Creating delete button and action
        delete_action = QAction("Delete",  self)
        delete_action.triggered.connect(self.confirm_delete)
        delete_action.setShortcut(QKeySequence("Shift+D"))
        
        #Creating next button and action
        next_btn = QAction("Next", self)
        next_btn.triggered.connect(self.next_images)
        next_btn.setShortcut(QKeySequence("Shift+Right"))

        #Creating previous button and action
        prev_btn = QAction("Previous", self)
        prev_btn.triggered.connect(self.prev_images)
        prev_btn.setShortcut(QKeySequence("Shift+Left"))

        #Adding the buttons to the toolbar
        self.toolbar = self.addToolBar('Exit')
        self.toolbar.addAction(delete_action)
        self.toolbar.addAction(prev_btn)
        self.toolbar.addAction(next_btn)
        
        #Making the main image window
        self.window = Window(folder)
        self.setCentralWidget(self.window)

        #Experimental dock widget 
        log_dock_widget = QDockWidget("Log", self)
        log_dock_widget.setObjectName("log_dock_widget")
        log_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea|
                                      Qt.RightDockWidgetArea)
        self.listWidget = QListWidget()


        self.vbox = QVBoxLayout()
        
        self.listWidg = QListWidget()


        self.listWidg.addItems(self.id_folders)
        self.vbox.addWidget(self.listWidg)

        

        widegt = QWidget(self)
        widegt.setLayout(self.vbox)
        log_dock_widget.setWidget(widegt)
        self.addDockWidget(Qt.RightDockWidgetArea, log_dock_widget)

        self.show()

    
    def confirm_delete(self):
        """
        A Dialog window that asks if you're sure you want to delete images.
        """
        length = len(self.window.get_selection())
        resume = QMessageBox.warning(self, 'Confirm', 'Are you sure you would like to delete these '+ str(length) + ' item(s)',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resume ==QMessageBox.Yes:
            self.delete_images()
        
    def delete_images(self):
        """
        A function that takes the highlighted images and deletes them, then 
        repopulates the window, removing the selected images from the view.
        """
        
        current_selection = self.window.get_selection()
        self.paths_processed += current_selection
        remaining_paths = self.window.img_paths

        delete_imgs(current_selection)


        for path in self.paths_processed:
            try:
                remaining_paths.remove(path)
            except ValueError:
                pass

        self.window = Window(remaining_paths, same =True)
        self.setCentralWidget(self.window)

    
    def next_images(self):
        """
        A function that writes the selected person to a file with the format:
        person: done
        to note when you are done with a cleaning sessions, so you don't need to go all
        the way back.
        Also repopulates the window with the next person
        """
        subject = self.id_folders[self.current_folder].split("/")[-1].split("\\")[-1]
        self.current_folder = (self.current_folder + self.step_size) % len(self.id_folders)

        with open(self.output_file, "a") as label_file:
            #output_string = "{}: {}\n".format(subject, self.gender)
            output_string = subject + ": done\n"
            label_file.write(output_string)

        self.window = Window(self.id_folders[self.current_folder])
        self.setWindowTitle(self.id_folders[self.current_folder].split("/")[-1])
        self.setCentralWidget(self.window)
    
    
    def prev_images(self):
        """
        Goes back to the previous person, removing the line from the file marking them done.
        Repopulates the window with the subject after.
        """
        with open(self.output_file, "r") as label_file:
            lines = label_file.readlines()
        with open(self.output_file, "w") as label_file:
            label_file.writelines(lines[:-1])

        self.current_folder = (self.current_folder - self.step_size) % len(self.id_folders)
        
        self.window = Window(self.id_folders[self.current_folder])
        self.setWindowTitle(self.id_folders[self.current_folder].split("/")[-1])
        self.setCentralWidget(self.window)

class Window(QScrollArea):
    """
    Class for the grid image viewer
    Number of columns can be changed if needed
    """
    def __init__(self, folder, same = False):
        QScrollArea.__init__(self)
        widget = QtWidgets.QWidget()
        self.folder = folder

        self.layout = QGridLayout(widget)
        self.all_labels = []
        self.no_cols = 3
        if same == False:
            
            self.populate(self.folder)
            
        else:
            self.populate(self.folder, same = True)
        self.setWidget(widget)

        self.setWidgetResizable(True)


    def populate(self, folder, same=False):
        """
        A function that takes in a folder and repopulates the window with the images
        the same parameter is if the person needs to be repopulated with the same
        person (ie when delete_images is called)
        """
        while True:
            img_paths = []
            if same == True:
                for i, file in enumerate(folder):
                    img_paths.append(file)
                    if i == 101:
                        break
            else:

                for i, file in enumerate(sorted(glob.glob(folder + "/*"))):
                    img_paths.append(file)
                    if i == 101:
                        break

            if len(img_paths) < 5:
                self.current_folder = (self.current_folder + 1) \
                                      % len(self.id_folders)
                folder = self.id_folders[self.current_folder]
            else:
                break

        self.img_paths = img_paths


        row = 0
        column = 0

        for idx, path in enumerate(img_paths):
            label = ClickableLabels(path)
            self.all_labels.append(label)
            self.layout.addWidget(self.all_labels[idx], row, column)

            column += 1
            if column % self.no_cols == 0:
                row += 1
                column = 0

    def get_selection(self):
        """A function which returns the list of the hightlighted file paths"""
        selection = []
        for idx, path in enumerate(self.img_paths):
            if self.all_labels[idx].checked:
                selection.append(path)
        

        return selection


class ClickableLabels(QLabel):
    """
    This class is for the image labels that are able to be clicked and highlighted
    """
    def __init__(self, path):
        super(ClickableLabels,self).__init__()
        
        #Size can be changed here
        size = QSize(400,400)

        self.checked = False

        pixmap = QPixmap(path)
        pixmap = pixmap.scaled(size, QtCore.Qt.KeepAspectRatio)
        self.setPixmap(pixmap)
    
    def mousePressEvent(self, event):
        self.checked = not self.checked
        
        if self.checked:
            self.setStyleSheet("border: 5px inset red;")
        else:
            self.setStyleSheet("")
def delete_imgs(image_paths):
    """
    This function will delete our detected images to the desired location.
    :param image_paths: A list containing the paths to every images detected
    :return: Nothing
    """

    for path in image_paths:
        os.remove(path)
if __name__ == '__main__':

    path = sorted(glob.glob(DATA_FOLDER + "*"))
    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    win.show()
    sys.exit(app.exec_())

