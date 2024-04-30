# ======================================
# Krita path simplify plug-in v0.3
# ======================================
# Copyright (C) 2024 L.Sumireneko.M
# This program is free software: you can redistribute it and/or modify it under the 
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>. 

from krita import *
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from PyQt5.QtGui import *
from PyQt5 import QtCore
import re,math



tolr = 0.8 # Tolerance smooth 0.8 - 1.5 rough
quality = True # precision mode ( Default:True)
remv_orig = False # Remove original

# ====================
# Krita io function
# ====================

def get_array(path,tolr,quality):
    # Filterling 
    if not path.startswith('<path'):
        message("Selected shape isn't Path Line \n  Circle,Rectangle and Polyline are \n no need to simplify probably.")
        return None
 
    # get original path information
    # id
    id = re.search(r'\sid="(.*?)"', path ).group(1)
    
    # path data
    p = re.search(r'\sd="(.*?)"', path )
    
    # other attributes
    tr = re.search(r'\s(transform=".*?")', path )
    fi = re.search(r'\s(fill=".*?")', path )
    st = re.search(r'\s(stroke=".*?")', path )
    sw = re.search(r'\s(stroke-width=".*?")', path )
    ca = re.search(r'\s(stroke-linecap=".*?")', path )
    jo = re.search(r'\s(stroke-linejoin=".*?")', path )

    tr = "" if tr is None else tr.group(1)
    fi = "" if fi is None else fi.group(1)
    st = "" if st is None else st.group(1)
    sw = "" if sw is None else sw.group(1)
    ca = "" if ca is None else ca.group(1)
    jo = "" if jo is None else jo.group(1)


    # Currently Not support expect Line segment
    mat=re.search(r'(?i)(C|S|Q|T|H|V|A)',str(p.group(1)))
    # print(mat)
    if not mat is None:
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
    dd = str(p.group(1))
    dd=re.sub(r'[Z"]','',dd)

    # Split by Hole Paths,  ps = ['274 995L272 706L....
    ps=re.split('M',dd);ps.pop(0);
    # print(ps)

    # Split by LinePath ,  ms = [['274 208','272 706', ...
    ms = []
    for i in range(0,len(ps)):
        ms.append(re.split(r'L',ps[i]))
    # print(ms)
    
    # Split by separate (White space),and make dict   {'x':00,'y':00} ...
    o=''
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
        o+="Z"
        # ms for loop end
    # make one smplifyed path data
    o=f'<path id="{id}_s" {tr} {fi} {st} {sw} {ca} {jo} d="{o}"/>'
    
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
    mb.setStandardButtons(QMessageBox.Ok)
    ret = mb.exec()
    if ret == QMessageBox.Ok:
        pass # OK clicked

# create dialog  and show it
def notice_autoclose_dialog(message):
    app = Krita.instance()
    qwin = app.activeWindow().qwindow()
    qq = qwin.size()
    wpos = math.ceil(qq.width() * 0.45)
    hpos = math.ceil(qq.height() * 0.45)
    
    noticeDialog = QDialog() 
    noticeDialog.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    label = QLabel(message)
    hboxd = QHBoxLayout()
    hboxd.addWidget(label)
    noticeDialog.setLayout(hboxd)
    noticeDialog.setWindowTitle("Title") 
    
    print(qwin.x(),wpos,hpos)
    noticeDialog.move(qwin.x()+wpos,qwin.y()+hpos)
    QtCore.QTimer.singleShot(1500, noticeDialog.close)
    noticeDialog.exec_() # show


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
        #print("-- ↑ Front -- ") 
        
        # Get All shape info
        # Range = len()-1 .... 0 
        for i in range(len(shapes)-1,-1,-1):
            sp = shapes[i]
            #print(f'* Shape({i}), Name: {sp.name()}  ,Type: {sp.type()} , isSelected?: {sp.isSelected()} , ID :{sp} ')

            # Get the selected shape
            if sp.isSelected() == True:
                if sp.type()=='groupshape':
                    # extend groupshape
                    #print(sp.toSvg())
                    g_transfrom = re.search( r'<g.*?>', sp.toSvg()).group()
                    g_shape = sp.children()
                    selected_shapes.append('</g>')
                    selected_shapes.extend(g_shape)
                    selected_shapes.append(g_transfrom)
                    #for m in sp.children():
                    #    print(m.name(),m.type())
                    continue;
                selected_shapes.append(sp)
        #print("-- ↓ Back -- ")
        
        #print(" ")
        #print(f" {len(selected_shapes)} / {len(shapes)} shapes selected")

        # Create a simplifyed svg src
        new_src = ""
        new_path = ""
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

            src = s.toSvg()
            new_path = get_array(src,tolr,quality)
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
        # The case that add to new VectorLayer

        # Remove original, and Add to current VectorLayer
        if remv_orig == True:
            for j in range(len(selected_shapes)-1,-1,-1):
                s = selected_shapes[j]
                # The case groupshape
                if isinstance(s, str):continue
                s.remove()
            lay.addShapesFromSvg(new_src)

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


def get_param(txt):
    #print("Param:"+str(txt))
    if txt == '':txt='0'
    txt = re.sub(r'[A-Za-z]','',txt) 
    num=float(eval(txt))
    #print("Calculated:"+str(num))
    return num

# ====================================
# Main Class
# ====================================
class Simplify_docker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Path Simplify")
        widget = QWidget()
        layout = QVBoxLayout()
        hlayout = QHBoxLayout()
        total_layout = QHBoxLayout()
        
        btn = QPushButton("Simplify the selected\n Vector shape!",self)
        btn.setToolTip('This can apply to SVG path with\n line segment only')
        btn.clicked.connect(self.exec_)
        labele = QLabel('Reduce points of Vector Path for\n * Boolean-ed Shape \n * Create shape from Selection\n * No for Ellipse and Rectangle')
        
        layout.addWidget(labele)
        layout.addLayout(hbox)
        layout.addLayout(hbox2)
        hlayout.addWidget(btn)

        layout.addLayout(hlayout)
        layout.addSpacing(16)
        total_layout.addSpacing(16)
        total_layout.addLayout(layout)
        total_layout.addSpacing(16)
        widget.setLayout(total_layout)
        self.setWidget(widget)

    def exec_(self):
        global tolr,quality,remv_orig
        if QtCore.Qt.Checked == chkbox.checkState():quality = True
        else:quality = False

        if QtCore.Qt.Checked == chkbox2.checkState():remv_orig = True
        else:remv_orig = False

        tolr = get_param(texbox.text())
        # message(f' Push Button {tolr},{quality}')
        main(tolr,quality,remv_orig)
        
    def canvasChanged(self, canvas):
        pass