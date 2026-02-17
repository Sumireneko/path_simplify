# ============================================================
#  qt_compat.py — Python   Qt5/Qt6 compatibility layer
# ============================================================
#  How to use
# from .qt_compat import SafeQtWidgets as QtWidgets, QC, qt_exec

# Example usage:
# action = QtWidgets.QAction("Label", parent)
# label.setSizePolicy(QC.Policy.Expanding, QC.Policy.Fixed)
# frame.setFrameShape(QC.Shape.Box)

import krita

try:
    # Krita 5.x -> qVersion() exists
    qt_major = int(krita.qVersion().split('.')[0])
except AttributeError:
    # Krita 6.x -> qVersion() does NOT exist
    qt_major = 6

if qt_major >= 6:
    # --- PyQt6 Branch ---#Qt6 QAction -> QtGui
    from PyQt6 import QtCore, QtGui, QtWidgets, uic
    from PyQt6.QtCore import (
            Qt, QEvent, QObject, pyqtSignal, pyqtSlot, QTimer, QPointF, QRectF, QSize,QPoint, QFile,QIODevice
        )
    from PyQt6.QtCore import QSignalBlocker
    from PyQt6.QtGui import QCursor, QPalette, QFont,QColor, QIcon,QClipboard,QTextCursor,QGuiApplication, QAction , QPainter, QPen,QTransform, QIntValidator,QImage, QPixmap
    from PyQt6.QtWidgets import (
            QApplication, QDialog, QTextEdit, QVBoxLayout, QPushButton, QSlider,QLineEdit,QFormLayout,
            QRadioButton, QButtonGroup, QLabel, QHBoxLayout, QMessageBox,QSpinBox,QCheckBox,QComboBox,
            QFrame, QSizePolicy, QAbstractSpinBox, QColorDialog,QDockWidget,QWidget,QFileDialog,QDoubleSpinBox
        )
    try:
        from PyQt6.QtCore import QMimeDatabase # Does it found in PyQt6 QtCore?
    except ImportError:
        try:
            from PyQt6.QtGui import QMimeDatabase
        except ImportError:
            QMimeDatabase = None

else:
    # --- PyQt5 Branch ---
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5 import uic # PyQt5 uic 
    from PyQt5.QtCore import (
            Qt, QEvent, QObject, pyqtSignal, pyqtSlot, QTimer, QPointF, QRectF, QSize,
            QSignalBlocker,QPoint, QFile,QIODevice
        )
    from PyQt5.QtGui import QCursor, QPalette, QFont, QColor, QIcon,QClipboard,QTextCursor, QGuiApplication,QPainter, QPen,QTransform, QIntValidator,QImage, QPixmap
    # PyQt5  QAction exist in QtWidgets
    from PyQt5.QtWidgets import (
            QApplication, QDialog, QTextEdit, QVBoxLayout, QPushButton, QSlider,QLineEdit,QFormLayout,
            QRadioButton, QButtonGroup, QLabel, QHBoxLayout, QMessageBox,QSpinBox,QCheckBox,QComboBox,
            QAction, QFrame, QSizePolicy, QAbstractSpinBox, QColorDialog,QDockWidget,QWidget,QFileDialog,QDoubleSpinBox
        )
    try:
        from PyQt5.QtCore import QMimeDatabase
    except ImportError:
        QMimeDatabase = None

# ---  Compatibility Core ---
def qt_event(name):
    if qt_major >= 6:
        # Qt5 → Qt6 
        map_qt5_to_qt6 = {
            "ActivationChange": "ApplicationActivate",
            "Enter": "Enter",
        }
        if name in map_qt5_to_qt6:
            name = map_qt5_to_qt6[name]

        return qt_enum(QEvent, "Type", name)

    else:
        # Qt6 → Qt5 （Qt5 has not ApplicationActivate  ）
        map_qt6_to_qt5 = {
            "ApplicationActivate": "ActivationChange",
            "ApplicationDeactivate": "ActivationChange",
        }
        if name in map_qt6_to_qt5:
            name = map_qt6_to_qt5[name]

        return getattr(QEvent, name)



def qt_enum(base, group, name):
    """Bridge for Enum differences between Qt5 and Qt6"""
    if hasattr(base, group):  # Qt6 (Nested Enums)
        res = getattr(getattr(base, group), name)
    else:                     # Qt5 (Flat Enums)
        res = getattr(base, name)
    return res




class CompatQtWidgets:
    """Namespace wrapper to keep other plugins safe"""
    def __init__(self, real_widgets, qaction_class):
        self.__dict__.update(real_widgets.__dict__)
        self.QAction = qaction_class

# Use SafeQtWidgets to avoid polluting the global QtWidgets
SafeQtWidgets = CompatQtWidgets(QtWidgets, QAction)

class QtConstant:
    """Helper to access Enums with dot notation"""
    def __init__(self, base, group):
        self.base = base
        self.group = group

    def __getattr__(self, name):
        return qt_enum(self.base, self.group, name)

    def __call__(self, value):
        """Return Enum class(value) for Qt6, or raw int for Qt5"""
        if hasattr(self.base, self.group):  # Qt6
            enum_class = getattr(self.base, self.group)
            return enum_class(value)
        else:  # Qt5
            return value

# ---   Unified Constants (QC) ---
class QtEnums:
    """Namespace for Enums to prevent naming conflicts"""
    Policy = QtConstant(QSizePolicy, "Policy")
    Role   = QtConstant(QPalette, "ColorRole")
    Cursor = QtConstant(Qt, "CursorShape")
    Window = QtConstant(Qt, "WindowType")
    Shape  = QtConstant(QFrame, "Shape")
    Shadow = QtConstant(QFrame, "Shadow")
    SpinButton = QtConstant(QAbstractSpinBox, "ButtonSymbols")
    StdBtn = QtConstant(QMessageBox, "StandardButton")# Ok button etc
    BtnRole = QtConstant(QMessageBox, "ButtonRole")# yes/no buttona
    CheckState = QtConstant(Qt, "CheckState")
    DockArea = QtConstant(Qt, "DockWidgetArea")
    TransformMode = QtConstant(Qt, "TransformationMode")
    FontWeight = QtConstant(QFont, "Weight")
    Align = QtConstant(Qt, "AlignmentFlag")
    ImgFormat = QtConstant(QImage, "Format")
    TextMove = QtConstant(QTextCursor, "MoveOperation")
    IO = QtConstant(QIODevice, "OpenModeFlag") # Qt6:OpenModeFlag、Qt5:QIODevice

QC = QtEnums()

# ---  Helper Functions ---
def qt_exec(dialog):
    """Unified exec() for Dialogs"""
    return int(dialog.exec()) if hasattr(dialog, "exec") else int(dialog.exec_())


def qt_exec(dialog):
    """Unified exec() for Dialogs (Python 3.10 - 3.13 compatible)"""
    # Handle the rename of exec_() to exec() in PyQt6
    method = getattr(dialog, "exec", None) or getattr(dialog, "exec_", None)
    
    if method:
        res = method()
        # PyQt6 exec() may return None or an Enum instead of a raw int in some environments
        return int(res) if res is not None else 0
    return 0




def qt_load_ui(ui_path):
    """Compatibility loader for .ui files"""
    import krita
    try:
        from PyQt6 import uic
        form_class, base_class = uic.loadUiType(ui_path)
        widget = base_class()
        form = form_class()
        form.setupUi(widget)
        return widget
    except ImportError:
        # Fallback for Krita 5.x / Qt5
        form_class, _ = krita.Krita.instance().loadUI(ui_path)
        return form_class()


def qt_load_ui(ui_path):
    """Compatibility loader for .ui files"""
    from .qt_compat import qt_major
    
    try:
        if qt_major >= 6:
            from PyQt6 import uic
        else:
            from PyQt5 import uic
        return uic.loadUi(ui_path)
        
    except Exception as e:
        print(f"Failed to load UI: {ui_path}, error: {e}")
        return None