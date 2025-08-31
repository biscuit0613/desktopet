# main.py
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from pet import DesktopPet

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序属性，确保中文正常显示
    font = app.font()
    font.setFamily("SimHei")
    app.setFont(font)
    
    pet = DesktopPet()
    pet.show()
    
    # 捕获应用退出事件，确保设置被保存
    app.aboutToQuit.connect(pet._save_settings)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("程序已退出")