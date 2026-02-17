from krita import Krita, DockWidgetFactory, DockWidgetFactoryBase
from .path_simplify import Simplify_docker

DOCKER_ID = 'PathSimplify'

# Qt5 / Qt6 compatible position
# Qt5: DockWidgetFactoryBase.DockRight (num)
# Qt6: DockWidgetFactoryBase.DockPosition.DockRight (Enum)
try:
    # Try Qt6 (Nested Enum) form
    dock_right = DockWidgetFactoryBase.DockPosition.DockRight
except AttributeError:
    # Try Qt5 (Flat) form
    dock_right = DockWidgetFactoryBase.DockRight

# Get Instance
instance = Krita.instance()
dock = DockWidgetFactory(DOCKER_ID, dock_right, Simplify_docker)
instance.addDockWidgetFactory(dock)