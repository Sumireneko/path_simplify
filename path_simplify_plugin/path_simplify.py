# ======================================
# Krita path simplify plug-in v0.8
# ======================================
# Copyright (C) 2026 L.Sumireneko.M
# This program is free software: you can redistribute it and/or modify it under the 
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>. 

import re, math, time
import krita
from .qt_compat import qt_exec,QC
from .qt_compat import (
    QtWidgets, QtCore, QtGui, QC, qt_exec, qt_event,QHBoxLayout,QVBoxLayout,
    QApplication, QDialog, QTextEdit, QVBoxLayout, QPushButton,QCheckBox,
    QRadioButton, QButtonGroup, QObject, QEvent, QTimer, QLabel,QDockWidget,
    QSignalBlocker, pyqtSignal, QLineEdit, QPointF, Qt,QWidget,QTextCursor
)

version_ = 0.8
tolr = 0.8 # Tolerance smooth 0.8 - 1.5 rough
quality = True # precision mode ( Default:True)
remv_orig = False # Remove original

# ====================
# Krita io function
# ====================
def parse(p):

    # p = xxx yyyC ...
    ms = [] # points data  ['xx yy',...]
    cp_match = None # closed path match
    division = 10
    pattern = r'^M?\s*([-+]?[0-9]*\.?[0-9]+)\s+([-+]?[0-9]*\.?[0-9]+)'

    match = re.search(pattern, p)
    prev_x, prev_y = None, None
    if match:
        prev_x = float(match.group(1))
        prev_y = float(match.group(2))
        ms.append(f"{prev_x} {prev_y}")
        #print("start:", prev_x, prev_y)
    else:
        raise ValueError("Start coord is Not found")
    
    pattern2 = r"Z$"  # Z command is exist at last wether or not 
    cp_match = re.search(pattern2, p)


    # extract SVG path commands
    commands = re.findall(r'[MLHVCSQTAZ][^MLHVCSQTAZ]*', p)


    for command in commands:
        type = command[0]
        # extract number and parse float
        values = list(map(float, re.findall(r'-?\d+\.?\d*', command[1:])))
        
        if type in ('M', 'L'):  # MoveTo, LineTo
            x, y = values[:2]
            ms.append(f"{x} {y}")
            prev_x, prev_y = x, y

        elif type == 'H':  # Horizontal line
            x = values[0]
            if prev_y is not None:
                ms.append(f"{x} {prev_y}")
            prev_x = x

        elif type == 'V':  # Vertical line
            y = values[0]
            if prev_x is not None:
                ms.append(f"{prev_x} {y}")
            prev_y = y

        elif type in ('C', 'S', 'Q', 'T', 'A'):  # Curves and arcs

            if type == 'C':
                if len(values) % 6 != 0:
                    print(f"Unexpected number of parameters in C command: {values}")
                else:
                    for i in range(0, len(values), 6):  # read 6 params
                        x1, y1, x2, y2, x3, y3 = values[i:i+6]
                        for t in range(division + 1):
                            t /= division
                            bx = (1 - t)**3 * prev_x + 3 * (1 - t)**2 * t * x1 + 3 * (1 - t) * t**2 * x2 + t**3 * x3
                            by = (1 - t)**3 * prev_y + 3 * (1 - t)**2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3 * y3
                            ms.append(f"{bx} {by}")
                        prev_x, prev_y = x3, y3

            elif type == 'S':  # Smooth Cubic Bezier curve
                # start
                x0, y0 = prev_x, prev_y
                # use reflection of previous control point(simply use same previous point )
                x1, y1 = prev_x, prev_y
                x2, y2, x3, y3 = values
                for i in range(division + 1):
                    t = i / division
                    bx = (1 - t)**3 * x0 + 3 * (1 - t)**2 * t * x1 + 3 * (1 - t) * t**2 * x2 + t**3 * x3
                    by = (1 - t)**3 * y0 + 3 * (1 - t)**2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3 * y3
                    ms.append(f"{bx} {by}")
                prev_x, prev_y = x3, y3

            elif type == 'Q':  # Quadratic Bezier curve
                # start
                x0, y0 = prev_x, prev_y
                # one control point and last point
                x1, y1, x2, y2 = values
                for i in range(division + 1):
                    t = i / division
                    bx = (1 - t)**2 * x0 + 2 * (1 - t) * t * x1 + t**2 * x2
                    by = (1 - t)**2 * y0 + 2 * (1 - t) * t * y1 + t**2 * y2
                    ms.append(f"{bx} {by}")
                prev_x, prev_y = x2, y2
        
            elif type == 'T':  # Smooth Quadratic Bezier curve
                # start
                x0, y0 = prev_x, prev_y
                # use reflection  of previous control point(simply use same previous point )
                x1, y1 = prev_x, prev_y
                # last point only
                x2, y2 = values
                for i in range(division + 1):
                    t = i / division
                    bx = (1 - t)**2 * x0 + 2 * (1 - t) * t * x1 + t**2 * x2
                    by = (1 - t)**2 * y0 + 2 * (1 - t) * t * y1 + t**2 * y2
                    ms.append(f"{bx} {by}")
                prev_x, prev_y = x2, y2
        
            elif type == 'A':  # Arc
                # start
                x0, y0 = prev_x, prev_y
                # parameter rx, ry, x_axis_rotation, large_arc_flag, sweep_flag, last(x, y)
                rx, ry, x_axis_rotation, large_arc_flag, sweep_flag, x, y = values
                # not use acculate elipse arc for convert,impliment with line interpolate
                for i in range(division + 1):
                    t = i / division
                    bx = rx * (1 - t) + t * x
                    by = ry * (1 - t) + t * y
                    ms.append(f"{bx} {by}")
                prev_x, prev_y = x, y

    return cp_match,ms

def get_array(name,path, tolr, quality):
    if not path.startswith('<path'):
        message("Selected shape isn't a Path Line. Circle, Rectangle, and Polyline probably don't need simplification.")
        return None

    # other attributes
    at = {
        "tr": re.search(r'\s(transform=".*?")', path),
        "fi": re.search(r'\s(fill=".*?")', path),
        "st": re.search(r'\s(stroke=".*?")', path),
        "sw": re.search(r'\s(stroke-width=".*?")', path),
        "sc": re.search(r'\s(stroke-linecap=".*?")', path),
        "sj": re.search(r'\s(stroke-linejoin=".*?")', path)
    }
    at = {k: (v.group(1) if v else "") for k, v in at.items()}

    # Path data
    p_match = re.search(r'\sd="(.*?)"', path)
    if not p_match:
        message("Path data (d attribute) not found.")
        return None
    p = p_match.group(1)


    # Check for line segment compatibility, re.IGNORECASE
    mat = re.search(r'[csqthva]', p)
    if mat:
        message(
        '''=== ERROR : Line segment ONLY support ===
The shape contain Spline or Bezier curve
(C,c,S,s,Q,q,T,t,H,h,V,v,A,a cmds in data)

Please the segments change curve to line 
    1.Switch to "Edit Shapes Tool",
    2.Select all segment(points) in the shape
    3.Do "Segment to Line" command/button
    (from RMB menu or Tool Options Docker)
So it will works.
        ''')
        return None




    if str(p) is None:print('No match');return None

    # Make simple data for treat easily
    #  d="blahblah" ->  L00 00,L00 00... -> {'x':00,'y':00}...

    # Split by Hole Paths,  ps = ['274 995L272 706L....

    ps=re.split('M',p);ps.pop(0);

    ms = []
    zs = []

    # ms = ['274 208','272 706', ..., zs= [ Zmatch , None ... ]
    for i in range(0,len(ps)): 
        closed_match,point_pair =parse(ps[i])
        if len(point_pair) == 0:continue
        if len(point_pair) <= 4:continue
        zs.append(closed_match)
        ms.append(point_pair)

    if len(ms) == 0:return None
    # Split by separate (White space),and make dict   {'x':00,'y':00} ...
    o=''
    cnt = 0
    for d in ms:
        x=y=""
        pary={}
        holes=[]

        # point data to array with dict 
        for i, ar in enumerate(d):
            ar=str(ar)
            if i >= len(d):continue
            try:
                (x,y) = ar.split()
            except:
                print("Error",i,"/",len(d),"__Data:",ar)
                continue
            pary[i]=dict({'x': float(x) , 'y': float(y)})

        # all point converted
        #message(f'Process {tolr},{quality}')
        vs = simplify(pary, tolr, quality)
        
        notice_autoclose_dialog(f"Updated the total points from {len(d)} to {len(vs)}")

        # array to point data
        # print(str(holes))
        for j in range(0,len(vs)):
            type = "L"
            if j == 0: type = "M"
            
            x = vs[j]['x']
            y = vs[j]['y']
            
            x = round(x, 5)
            y = round(y, 5)
            
            o+=f"{type}{x} {y}"

        #message(zs[cnt])
        o+="Z" if zs[cnt] else ""
        # ms for loop end
    # make one smplifyed path data
    o=f'<path id="{name}" {at["tr"]} {at["fi"]} {at["st"]} {at["sw"]} {at["sc"]} {at["sj"]} d="{o}"/>'
    
    # print("=== simplified ===")
    # print(o)
    return o



# ================================================================
# simplify.js python port
#
# https://github.com/omarestrella/simplify.py
# Lisense: Unlisense
# usage: simplify(points, tolerance=0.1, highestQuality=True):
# ================================================================

def getSquareDistance(p1, p2):
    """
    Square distance between two points
    """
    dx = p1['x'] - p2['x']
    dy = p1['y'] - p2['y']

    return dx * dx + dy * dy


def getSquareSegmentDistance(p, p1, p2):
    """
    Square distance between point and a segment
    """
    x = p1['x']
    y = p1['y']

    dx = p2['x'] - x
    dy = p2['y'] - y

    if dx != 0 or dy != 0:
        t = ((p['x'] - x) * dx + (p['y'] - y) * dy) / (dx * dx + dy * dy)

        if t > 1:
            x = p2['x']
            y = p2['y']
        elif t > 0:
            x += dx * t
            y += dy * t

    dx = p['x'] - x
    dy = p['y'] - y

    return dx * dx + dy * dy


def simplifyRadialDistance(points, tolerance):
    length = len(points)
    prev_point = points[0]
    new_points = [prev_point]

    for i in range(length):
        point = points[i]

        if getSquareDistance(point, prev_point) > tolerance:
            new_points.append(point)
            prev_point = point

    if prev_point != point:
        new_points.append(point)

    return new_points


def simplifyDouglasPeucker(points, tolerance):
    length = len(points)
    markers = [0] * length  # Maybe not the most efficent way?

    first = 0
    last = length - 1

    first_stack = []
    last_stack = []

    new_points = []

    markers[first] = 1
    markers[last] = 1

    while last:
        max_sqdist = 0

        for i in range(first, last):
            sqdist = getSquareSegmentDistance(points[i], points[first], points[last])

            if sqdist > max_sqdist:
                index = i
                max_sqdist = sqdist

        if max_sqdist > tolerance:
            markers[index] = 1

            first_stack.append(first)
            last_stack.append(index)

            first_stack.append(index)
            last_stack.append(last)

        # Can pop an empty array in Javascript, but not Python, so check
        # the length of the list first
        if len(first_stack) == 0:
            first = None
        else:
            first = first_stack.pop()

        if len(last_stack) == 0:
            last = None
        else:
            last = last_stack.pop()

    for i in range(length):
        if markers[i]:
            new_points.append(points[i])

    return new_points


def simplify(points, tolerance=0.1, highestQuality=True):
    sqtolerance = tolerance * tolerance

    if not highestQuality:
        points = simplifyRadialDistance(points, sqtolerance)

    points = simplifyDouglasPeucker(points, sqtolerance)

    return points

# ====================
# Utilities
# ====================

def message(mes):
    mb = QMessageBox()
    mb.setText(str(mes))
    mb.setWindowTitle('Message')
    mb.setStandardButtons(QC.StdBtn.Ok) 
    
    ret = qt_exec(mb) 

    if ret == QC.StdBtn.Ok:
        pass # OK clicked


# create dialog  and show it
def notice_autoclose_dialog(message_text):
    app = Krita.instance()
    qwin = app.activeWindow().qwindow()
    qq = qwin.size()
    
    wpos = math.ceil(qq.width() * 0.45)
    hpos = math.ceil(qq.height() * 0.45)

    noticeDialog = QDialog()

    noticeDialog.setWindowFlags(QC.Window.FramelessWindowHint)

    label = QLabel(message_text)
    hboxd = QHBoxLayout()
    hboxd.addWidget(label)
    noticeDialog.setLayout(hboxd)
    noticeDialog.setWindowTitle("Title")
    # print("qwin.x() wpos hpos = ",qwin.x(),wpos,hpos)
    noticeDialog.move(qwin.x() + wpos, qwin.y() + hpos)
    
    # Close window
    QtCore.QTimer.singleShot(1500, noticeDialog.close)

    qt_exec(noticeDialog)


# debug

def d(text):
    return text;

def dprint(text):
    message(text)

# ====================
# Main function
# ====================
def main(tolr,quality,remv_orig):
    app = Krita.instance()
    doc = app.activeDocument()
    lay = doc.activeNode()
    selected_shapes = None
    if lay.type() == 'vectorlayer':
        app.action('InteractionTool').trigger()# Select shape tool
        shapes = lay.shapes()
        #print(" "+str(len(shapes))+" shapes found in this active VectorLayer")
        #print(lay.toSvg())
        selected_shapes = []
        sel_cnt=0
        #debug=""
        #debug+=d("-- ↑ Front -- \n") 
        
        # Get All shape info
        # Range = len()-1 .... 0 
        for i in range(len(shapes)-1,-1,-1):
            sp = shapes[i]
            #debug+=d(f'* Shape({i}), Name: {sp.name()}  ,Type: {sp.type()} , isSelected?: {sp.isSelected()} , ID :{sp} \n')

            # Get the selected shape
            if sp.isSelected() == True:
                sel_cnt += 1
                if sp.type()=='groupshape':
                    # extend groupshape
                    #debug+=d(sp.toSvg()+"\n")
                    g_transfrom = re.search( r'<g.*?>', sp.toSvg()).group()
                    g_shape = sp.children()
                    selected_shapes.append('</g>')
                    selected_shapes.extend(g_shape)
                    selected_shapes.append(g_transfrom)
                    #for m in sp.children():
                    #    debug+=d(m.name(),m.type())
                    continue;
                selected_shapes.append(sp)
        
        #debug+=d("-- ↓ Back -- \n")
        #debug+=d(f" {len(selected_shapes)} / {len(shapes)} shapes selected\n")
        #dprint(debug)

        # Create a simplifyed svg src
        new_src = ""
        new_path = ""
        sel_ids = []
        
        # Get the selected shapes info
        for j in range(len(selected_shapes)-1,-1,-1):
            s = selected_shapes[j]
            
            # The case groupshape
            if isinstance(s, str):
                print(s)
                if s.startswith('<g') or s.startswith('</g>'):
                    new_src += s
                    continue
            
            name = s.name()
            type = s.type()
            pos = s.position()
            # print(" ------------------ ")
            # print(f'* Shape({j}), Type:{type} , \n '+s.toSvg())

            if name == "":
                tid = round(time.time())
                name = f"shape{tid}_s"
            sel_ids.append(name)

            src = s.toSvg()
            new_path = get_array(name,src,tolr,quality)
            if new_path is None:break
            new_src+= new_path

        if new_path is None:return

        # get documentsize px → pt
        wpt = doc.width()*0.72
        hpt = doc.height()*0.72
        
        new_src = f'<svg width="{wpt}pt" height="{hpt}pt" viewBox="0 0 {wpt} {hpt}">'+new_src+'</svg>'

        # print("Result")
        # print(newsrc)

        # Output to VectorLayer
        # Remove original, and Add to current VectorLayer

        if remv_orig == True:
            for j in range(len(selected_shapes)-1,-1,-1):
                s = selected_shapes[j]
                # The case groupshape
                if isinstance(s, str):continue
                s.remove()
            lay.addShapesFromSvg(new_src)
            
            # Re-Selection
            updated_shapes = lay.shapes()
            for j in updated_shapes:
                if j.name() in sel_ids:
                    j.select()
            app.action('PathTool').trigger()
            

        # Add to new VectorLayer
        elif len(selected_shapes) > 0:
            root = doc.rootNode()
            vnode = doc.createVectorLayer('Simplified path data')
            vnode.addShapesFromSvg(new_src)
            root.addChildNode(vnode , None )
            
        
        if selected_shapes is None or len(selected_shapes)==0: notice_autoclose_dialog('No selection for vector shape(s)')
        elif remv_orig == True:notice_autoclose_dialog('Path simplify finished (Replaced)')
        else:notice_autoclose_dialog('Path simplify finished!')
        # End of function


# ====================================
# GUI Data
# ====================================

text = 'Default:0.8\n Ineffective: 0.0 - 0.4 \n Good result: 0.5 - 1.0\n Polygonalize: 1.5 - 2.5\n'
label_s= QLabel("Tolerance :")
texbox = QLineEdit(str(tolr))
texbox.resize(40, 20)
label_s.setToolTip(text)
texbox.setToolTip(text)

hbox = QHBoxLayout()
hbox.addWidget(label_s)
hbox.addWidget(texbox)

chkbox = QCheckBox("Hi-Quality")
chkbox.setChecked(True)
chkbox.setToolTip('If it checked,it try to make it \nas close to the original Shape \nas possible.')

chkbox2 = QCheckBox("Remove Original")
chkbox2.setChecked(False)
chkbox2.setToolTip('If it checked,the original shape replaced \n to simplified one.')


hbox2 = QHBoxLayout()
hbox2.addWidget(chkbox)
hbox2.addWidget(chkbox2)


# Boolean bypass (Unite Intersect Subtract Split)
hbox3 = QHBoxLayout()
btn_u = QPushButton();btn_u.setIcon(Krita.instance().icon('selection_add'))
btn_i = QPushButton();btn_i.setIcon(Krita.instance().icon('selection_intersect'))
btn_s = QPushButton();btn_s.setIcon(Krita.instance().icon('selection_subtract'))
btn_sp = QPushButton();btn_sp.setIcon(Krita.instance().icon('selection_symmetric_difference'))




btn_u.setToolTip('Unite(Simplify):Create boolean union of mutiple shapes')
btn_i.setToolTip('Intersect(Simplify):Create intersection of mutiple shapes')
btn_s.setToolTip('Subtract(Simplify):Subtract multiple objects from the first selected one')
btn_sp.setToolTip('Split:Split shapes with multiple subpaths into multiple shapes')

hbox3.addWidget(btn_u)
hbox3.addWidget(btn_i)
hbox3.addWidget(btn_s)
hbox3.addWidget(btn_sp)


def get_param(txt):
    #print("Param:"+str(txt))
    if txt == '':txt='0'
    txt = re.sub(r'[A-Za-z]','',txt) 
    num=float(eval(txt))
    #print("Calculated:"+str(num))
    return num
# ====================================
# Log Window Class
# ====================================
class LogWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.resize(400, 300)

        self.text_area = QTextEdit(self)
        self.text_area.setReadOnly(True)

        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.text_area)
        layout.addWidget(close_button)
        self.setLayout(layout)

    def append_log(self, message):
        self.text_area.append(message)
        self.text_area.moveCursor(QC.TextMove.Start)

    def clear_log(self):
        self.text_area.clear()

    def closeEvent(self, event):
        if self.parent():
            self.parent().log_window = None
        super().closeEvent(event)

# ====================================
# Main Class
# ====================================
class Simplify_docker(krita.DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Path Simplify")
        widget = QWidget()
        layout = QVBoxLayout()
        hlayout = QHBoxLayout()
        total_layout = QHBoxLayout()
        
        btn = QPushButton("Simplify the selected\n Vector shape!",self)
        btn.setToolTip('This can apply to SVG path shapes(single/multiple)')
        btn.clicked.connect(self.exec_)

        self.log_window = None
        label_info=[
            '------------------------------------',
            f'Path Simplify Plug-in ver {version_}',
            '------------------------------------',
            'Reduce points of Vector Path for:',
            ' * Boolean-ed Shape',
            ' * Create shape from Selection',
            ' * No for Ellipse and Rectangle',
            ' ',
            'Tolerance parameter:(Default:0.8)',
            ' * Ineffective: 0.0 - 0.4 ',
            ' * Get good result: 0.5 - 1.0',
            ' * More polygonalized: 1.5 - 2.5',
            ' ',
            'Boolean path fix options:',
            'How to use:',
            '1. Select two or more overlapping shapes.',
            '2. Click one of the following buttons.',
            ' ',
            ' * Unite(Simplify):\n Create boolean union of mutiple shapes \n',
            ' * Intersect(Simplify):\n Create intersection of mutiple shapes\n',
            ' * Subtract(Simplify):\n Subtract multiple objects from the first selected one\n',
            ' * Split:\n Split shapes with multiple subpaths into multiple shapes',
            ' ',
            'Note:\n In currently Krita(v5.2.14) boolean commands',
            'these could not get simply path result',
            'So this plugin enables support by bypassing these commands.'
        ]
        infobtn = QPushButton();infobtn.setIcon(Krita.instance().icon('selection-info'))
        infobtn.clicked.connect(lambda text: self.show_info(label_info))
        infobtn.setFixedSize(25, 25)
        hbox.addWidget(infobtn)

        layout.addLayout(hbox)
        layout.addLayout(hbox2)
        layout.addLayout(hbox3)
        hlayout.addWidget(btn)

        layout.addLayout(hlayout)
        layout.addSpacing(16)
        total_layout.addSpacing(16)
        total_layout.addLayout(layout)
        total_layout.addSpacing(16)


        btn_u.clicked.connect(self.pathfinder_add)
        btn_i.clicked.connect(self.pathfinder_intersect)
        btn_s.clicked.connect(self.pathfinder_subtract)
        btn_sp.clicked.connect(self.pathfinder_split)


        widget.setLayout(total_layout)
        self.setWidget(widget)


    def pathfinder_add(self):
        Krita.instance().action('object_unite').trigger()
        qt_exec(self)

    def pathfinder_intersect(self):
        Krita.instance().action('object_intersect').trigger()
        qt_exec(self)

    def pathfinder_subtract(self):
        Krita.instance().action('object_subtract').trigger()
        qt_exec(self)

    def pathfinder_split(self):
        Krita.instance().action('object_split').trigger()


    def exec_(self):
        global tolr,quality,remv_orig
        if QC.CheckState.Checked == chkbox.checkState():
            quality = True
        else:
            quality = False

        if QC.CheckState.Checked == chkbox2.checkState():
            remv_orig = True
        else:
            remv_orig = False


        tolr = get_param(texbox.text())
        # message(f' Push Button {tolr},{quality}')
        main(tolr,quality,remv_orig)
        

    def canvasChanged(self, canvas):
        pass

    # ----------------
    # log window
    # ----------------

    def show_info(self,array):
        slog=[]
        for a in array:
            lines = a
            slog.append(f"{a}")

        # call_log window
        if self.log_window is None:
            self.add_log_message("\n".join(slog))



    def show_log_window(self):
        if self.log_window is None:
            self.log_window = LogWindow(self)

        self.log_window.show()
        self.log_window.raise_()  # bring to front
        self.log_window.activateWindow()

    def add_log_message(self, message):
        if self.log_window is None:
            self.show_log_window()
        self.log_window.clear_log()
        self.log_window.append_log(message)


