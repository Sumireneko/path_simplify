from krita import DockWidgetFactory, DockWidgetFactoryBase
from .path_simplify import Simplify_docker

# And add docker:
DOCKER_ID = 'PathSimplify'
dock = DockWidgetFactory(DOCKER_ID,DockWidgetFactoryBase.DockRight,Simplify_docker)
Krita.instance().addDockWidgetFactory(dock)

